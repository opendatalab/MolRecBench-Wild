import copy
import json
import signal
import sys
from contextlib import contextmanager
from pathlib import Path

from indigo import Indigo
from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[2]))

from rdkit import Chem, RDLogger

from evaluate.utils import (
    eval_smiles_impl,
    normalize_greek_letters,
    simplify_R_group_in_symbols,
)
from evaluate.MolGraph import MolGraph
from evaluate.utils import load_list_from_jsonl
from evaluate.utils import (
    Convert_Rx_to_R,
    canonicalize_smiles_w_superatom,
    check_R_atom,
    compare_brackets,
    is_special_R,
    iter_special_R_substitution_mappings,
)

indigo = Indigo()
from networkx.algorithms import isomorphism

lg = RDLogger.logger()
lg.setLevel(RDLogger.CRITICAL)  # 只显示严重错误，屏蔽警告和信息


class TimeoutException(Exception):
    pass


@contextmanager
def time_limit(seconds):
    def signal_handler(signum, frame):
        raise TimeoutException()

    signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)


class Evaluator:
    def __init__(
        self, gt_list, pred_list, infer_version="v2", print_error=False
    ):
        self.ids = []
        self.eval_info = {}
        self.mol_graph_gts = {}
        self.mol_graph_preds = {}
        self.gt_success_count = 0
        self.gt_success_count_other = 0
        self.pred_success_count = 0
        self.infer_version = infer_version
        self.attribute = {"smiles": {}, "simplified_graph": {}, "graph": {}}
        self.total_gt_count = len(gt_list)
        self.print_error = print_error
        # 处理 GT
        for i in tqdm(range(len(gt_list)), desc="Loading GT"):
            img_id_gt = gt_list[i]["id"]
            self.ids.append(img_id_gt)
            self.eval_info[img_id_gt] = {
                "id": gt_list[i]["id"],
            }
            # TODO: 实例化 Graph对象
            mol_graph_gt = MolGraph(
                id=img_id_gt,
                carbon_info=gt_list[i],
                attribute=gt_list[i]["hardcase_label"]
                if "hardcase_label" in gt_list[i]
                else None,
            )
            self.gt_success_count += 1

            self.mol_graph_gts[img_id_gt] = mol_graph_gt
        print(f"GT Load Success Count: {self.gt_success_count}")
        # 处理 Pred
        for i in range(len(pred_list)):
            img_id_pred = pred_list[i]["id"]
            mol_graph_pred = MolGraph(
                id=img_id_pred,
                carbon_info=pred_list[i],
                attribute=pred_list[i]["hardcase_label"]
                if "hardcase_label" in pred_list[i]
                else None,
            )
            self.pred_success_count += 1
            self.mol_graph_preds[img_id_pred] = mol_graph_pred
        print(f"Pred Load Success Count: {self.pred_success_count}")

    def evaluate_simplified_graph(self):
        node_match = isomorphism.categorical_node_match("symbol", None)
        edge_match = isomorphism.categorical_edge_match("bond", None)
        correct_count = 0
        success_count = 0
        for id in tqdm(self.ids, desc="Evaluating Simplified Graph"):
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            self.eval_info[id]["simplified_graph_eval"] = False
            self.eval_info[id]["simplified_graph_gt"] = (
                mol_graph_gt.dump_to_dict(simplify=True)
            )
            self.eval_info[id]["simplified_graph_pred"] = (
                mol_graph_pred.dump_to_dict(simplify=True)
            )
            if len(mol_graph_gt.symbols) == 0:
                continue
            success_count += 1
            if len(mol_graph_pred.symbols) == 0:
                continue
            graph_correct, _ = self._compare_graph(
                mol_graph_gt,
                mol_graph_pred,
                node_match,
                edge_match,
                simplify=True,
            )
            if graph_correct:
                correct_count += 1
                self.eval_info[id]["simplified_graph_eval"] = True
        print(f"Simplified Graph Success Count: {success_count}")
        return success_count, correct_count

    def evaluate_graph(self):
        node_match = isomorphism.categorical_node_match(
            [
                "symbol",
                "charge",
                "radical",
                "valence",
                "isotope",
                "attach_point",
            ],
            [None, None, None, None, None, None],
        )
        edge_match = isomorphism.categorical_edge_match("bond", None)
        correct_count = 0
        success_count = 0
        for id in tqdm(self.ids, desc="Evaluating Graph"):
            correct = False
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            self.eval_info[id]["graph_eval"] = False
            self.eval_info[id]["graph_gt"] = mol_graph_gt.dump_to_dict()
            self.eval_info[id]["graph_pred"] = mol_graph_pred.dump_to_dict()
            if len(mol_graph_gt.symbols) == 0:
                correct = False
                continue
            success_count += 1
            if len(mol_graph_pred.symbols) == 0:
                correct = False
                continue
            graph_correct, mapping = self._compare_graph(
                mol_graph_gt,
                mol_graph_pred,
                node_match,
                edge_match,
                simplify=False,
            )
            # 对比括号
            if graph_correct and compare_brackets(
                mol_graph_gt.brackets, mol_graph_pred.brackets, mapping
            ):
                correct = True
            else:
                correct = False

            if correct:
                correct_count += 1
                self.eval_info[id]["graph_eval"] = True
            else:
                correct = False
            attributes = self.mol_graph_gts[id].attribute
            if attributes:
                for attribute in attributes:
                    if attribute in self.attribute["graph"]:
                        if correct:
                            self.attribute["graph"][attribute].append(1)
                        else:
                            self.attribute["graph"][attribute].append(0)
                    elif correct:
                        self.attribute["graph"][attribute] = [1]
                    else:
                        self.attribute["graph"][attribute] = [0]
        print(f"Graph Success Count: {success_count}")
        return success_count, correct_count

    def _compare_graph(
        self,
        mol_graph_gt,
        mol_graph_pred,
        node_match,
        edge_match,
        simplify,
    ):
        """
        评估两个图是否相等，这里只对比节点和边是否相等，不对比括号
        Args:
            mol_graph_gt:  GT 的 graph 实例
            mol_graph_pred:  Pred 的 graph 实例
            node_match: 节点匹配函数
            edge_match: 边匹配函数
        Returns:
            True 如果相等，False 如果不相等
        """
        try:
            with time_limit(5):
                return self._compare_graph_impl(
                    mol_graph_gt,
                    mol_graph_pred,
                    node_match,
                    edge_match,
                    simplify,
                )
        except TimeoutException:
            return False, None

    def _compare_graph_impl(
        self,
        mol_graph_gt,
        mol_graph_pred,
        node_match,
        edge_match,
        simplify,
    ):
        if check_R_atom(mol_graph_gt.symbols):
            # TODO: 首先简化R*
            mol_graph_gt.symbols = simplify_R_group_in_symbols(
                mol_graph_gt.symbols
            )
            mol_graph_pred.symbols = simplify_R_group_in_symbols(
                mol_graph_pred.symbols
            )
            # TODO: 1. 先判断除特殊R之外是否相等
            # 复制实例
            mol_graph_gt_copy = copy.deepcopy(mol_graph_gt)
            mol_graph_pred_copy = copy.deepcopy(mol_graph_pred)

            # Convert_Rx_to_R
            mol_graph_gt_copy.symbols = Convert_Rx_to_R(
                mol_graph_gt_copy.symbols
            )
            mol_graph_pred_copy.symbols = Convert_Rx_to_R(
                mol_graph_pred_copy.symbols
            )
            if simplify:
                DiGM = isomorphism.DiGraphMatcher(
                    mol_graph_gt_copy.dump_to_simplify_graph(),
                    mol_graph_pred_copy.dump_to_simplify_graph(),
                    node_match=node_match,
                    edge_match=edge_match,
                )
            else:
                DiGM = isomorphism.DiGraphMatcher(
                    mol_graph_gt_copy.dump_to_graph(),
                    mol_graph_pred_copy.dump_to_graph(),
                    node_match=node_match,
                    edge_match=edge_match,
                )
            # TODO: 2. 如果相等，则对比 Rx
            if DiGM.is_isomorphic():
                # 使得 GT 和 Pred 的 symbols 都按照字母顺序排序
                mol_graph_gt.symbols = normalize_greek_letters(
                    mol_graph_gt.symbols
                )
                mol_graph_pred.symbols = normalize_greek_letters(
                    mol_graph_pred.symbols
                )
                # 获取所有的 SR；按前缀分组（如 R1α,R1β 与 R2α,R2β），各组内独立排列希腊角标
                gt_Rs = set(x for x in mol_graph_gt.symbols if is_special_R(x))
                pred_Rs = set(
                    x for x in mol_graph_pred.symbols if is_special_R(x)
                )
                if len(gt_Rs) != len(pred_Rs):
                    return False, None
                for mapping in iter_special_R_substitution_mappings(
                    mol_graph_gt.symbols, mol_graph_pred.symbols
                ):
                    mol_graph_pred_copy = copy.deepcopy(mol_graph_pred)
                    # 将 graph_pred["symbols"] 中 R 替换为 GT 中的 R， 其他的保持不变
                    mol_graph_pred_copy.symbols = [
                        mapping.get(x, x) if x in mapping else x
                        for x in mol_graph_pred_copy.symbols
                    ]
                    assert len(mol_graph_pred_copy.symbols) == len(
                        mol_graph_gt.symbols
                    )
                    # 对比是否完全相同.
                    if simplify:
                        DiGM = isomorphism.DiGraphMatcher(
                            mol_graph_gt.dump_to_simplify_graph(),
                            mol_graph_pred_copy.dump_to_simplify_graph(),
                            node_match=node_match,
                            edge_match=edge_match,
                        )
                    else:
                        DiGM = isomorphism.DiGraphMatcher(
                            mol_graph_gt.dump_to_graph(),
                            mol_graph_pred_copy.dump_to_graph(),
                            node_match=node_match,
                            edge_match=edge_match,
                        )
                    if DiGM.is_isomorphic():
                        return True, DiGM.mapping
        else:
            if simplify:
                DiGM = isomorphism.DiGraphMatcher(
                    mol_graph_gt.dump_to_simplify_graph(),
                    mol_graph_pred.dump_to_simplify_graph(),
                    node_match=node_match,
                    edge_match=edge_match,
                )
            else:
                DiGM = isomorphism.DiGraphMatcher(
                    mol_graph_gt.dump_to_graph(),
                    mol_graph_pred.dump_to_graph(),
                    node_match=node_match,
                    edge_match=edge_match,
                )
            if DiGM.is_isomorphic():
                return True, DiGM.mapping
        return False, None

    def evaluate_smiles(self, expand=False, kekule=False):
        correct_count = 0
        success_count = 0
        for id in tqdm(self.ids, desc="Evaluating SMILES"):
            self.eval_info[id]["smiles_eval"] = False
            self.eval_info[id]["smiles_gt"] = None
            self.eval_info[id]["smiles_pred"] = None
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            try:
                smiles_gt, super_atom_map_gt, _ = mol_graph_gt.dump_to_SMILES(
                    super_atom_map={}, expand=expand
                )
                if len(smiles_gt.strip()) < 1:
                    continue
                self.eval_info[id]["smiles_gt"] = smiles_gt
                success_count += 1
            except Exception as e:
                if self.print_error:
                    print(f"ERROR SMILES GT: {e}")
                continue
            try:
                smiles_pred, _, _ = mol_graph_pred.dump_to_SMILES(
                    super_atom_map=super_atom_map_gt, expand=expand
                )
                self.eval_info[id]["smiles_pred"] = smiles_pred
            except Exception as e:
                if self.print_error:
                    print(f"ERROR SMILES Pred: {e}")
                continue

            correct, smiles_gt_canonical, smiles_pred_canonical = (
                eval_smiles_impl(smiles_gt, smiles_pred)
            )
            self.eval_info[id]["smiles_gt_canonical"] = smiles_gt_canonical
            self.eval_info[id]["smiles_pred_canonical"] = smiles_pred_canonical
            if correct:
                correct_count += 1
                self.eval_info[id]["smiles_eval"] = True
        return success_count, correct_count

    def evaluate_smiles_tanimoto(self, expand=False, kekule=False):
        success_count = 0
        tanimoto_list = []
        for id in tqdm(self.ids, desc="Evaluating SMILES"):
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            try:
                smiles_gt, super_atom_map_gt, missing_abbrs = (
                    mol_graph_gt.dump_to_SMILES(
                        super_atom_map={}, expand=expand
                    )
                )
                if not smiles_gt:
                    continue
            except Exception as e:
                if self.print_error:
                    print(f"ERROR SMILES GT: {e}")
                continue
            try:
                smiles_pred, super_atom_map_pred, missing_abbrs = (
                    mol_graph_pred.dump_to_SMILES(
                        super_atom_map=super_atom_map_gt, expand=expand
                    )
                )
            except Exception as e:
                if self.print_error:
                    print(f"ERROR SMILES Pred: {e}")
                continue

            smiles_gt_canonical, super_atom_map, succeed = (
                canonicalize_smiles_w_superatom(
                    smiles_gt,
                    super_atom_map={},
                    kekule=kekule,
                    replace_H=True,
                    recover_super_atom=False,
                )
            )
            smiles_pred_canonical, super_atom_map, succeed = (
                canonicalize_smiles_w_superatom(
                    smiles_pred,
                    super_atom_map=super_atom_map,
                    kekule=kekule,
                    replace_H=True,
                    recover_super_atom=False,
                )
            )
            try:
                mol1 = Chem.MolFromSmiles(smiles_gt_canonical)
                fp1 = AllChem.GetMorganFingerprintAsBitVect(
                    mol1, radius=2, nBits=2048
                )
                success_count += 1
                try:
                    mol2 = Chem.MolFromSmiles(smiles_pred_canonical)
                    fp2 = AllChem.GetMorganFingerprintAsBitVect(
                        mol2, radius=2, nBits=2048
                    )
                    sim = DataStructs.TanimotoSimilarity(fp1, fp2)
                    tanimoto_list.append(sim)
                except Exception as e:
                    tanimoto_list.append(0)
                    continue
            except Exception as e:
                continue
        return success_count, sum(tanimoto_list)

    def save_eval_info(self, save_path):
        with open(save_path, "w") as f:
            json.dump(self.eval_info, f, indent=4)

    def save_attribute_result(self, save_path):
        with open(save_path, "w") as f:
            json.dump(self.attribute, f, indent=4)


if __name__ == "__main__":
    import argparse

    # 使用 argparse 从 shell 获取参数
    parser = argparse.ArgumentParser(
        description="Evaluate molecule predictions."
    )
    parser.add_argument(
        "--infer_version",
        type=str,
        default="v2",
        choices=["v1", "v2"],
        help="infer_version: v1 or v2",
    )
    parser.add_argument(
        "--gt_path",
        type=str,
        default="/mnt/shared-storage-user/mineru4s/jcwang/MoleculeRecognition/datasets/cvpr2026/cc40/infer_data.jsonl",
        help="Path to ground truth .jsonl file",
    )
    parser.add_argument(
        "--pred_path",
        type=str,
        default="/mnt/shared-storage-user/mineru4s/malixin/ms-swift/output/121394_sft_Qwen2.5-VL-3B-Instruct_lr1e-4_ng8_gas64_pgbs1_e1/v0-20260519-175439/checkpoint-2181/infer_cc40_qwen25vl_0416.jsonl",
        help="Path to prediction .jsonl file",
    )
    parser.add_argument(
        "--save_path",
        type=str,
        default=None,
        help="Path to save eval info json",
    )
    args = parser.parse_args()

    # 加载参考的评估结果
    gt_list = load_list_from_jsonl(args.gt_path)
    pred_list = load_list_from_jsonl(args.pred_path)
    print(
        f"************************ **Evaluating** *************************\n"
    )

    try:
        import rdkit
        from rdkit import __version__ as rdkit_version
    except ImportError:
        print("未检测到rdkit库，请先安装 rdkit==2025.09.1")
        sys.exit(1)
    required_rdkit_version = "2025.09.1"
    if rdkit_version != required_rdkit_version:
        print(
            f"当前RDKit版本为 {rdkit_version}，请使用 RDKit {required_rdkit_version} 版本进行评估。"
        )
        sys.exit(1)

    try:
        import indigo
        from indigo import __version__ as indigo_version
    except ImportError:
        print("未检测到indigo库，请先安装 indigo==1.34.0")
        sys.exit(1)
    required_indigo_version = "1.34.0"
    if indigo_version != required_indigo_version:
        print(
            f"当前Indigo版本为 {indigo_version}，请使用 Indigo {required_indigo_version} 版本进行评估。"
        )
        sys.exit(1)

    print(f"GT Length: {len(gt_list)}, Pred Length: {len(pred_list)}")
    # NOTE: GTR1 和 GTR2 的解析逻辑不同，需要注意更改infer_version，目前只有 v1 和 v2 两种版本
    print(f"infer_version: {args.infer_version}")
    evaluator = Evaluator_2_0(
        gt_list=gt_list, pred_list=pred_list, infer_version=args.infer_version
    )

    success, smiles_correct = evaluator.evaluate_smiles(
        expand=True, kekule=True
    )
    print(
        f"************************ **SMILES Exact Match** *************************\n",
        f"Valid GT: {success}, Correct: {smiles_correct}\n",
        f"Correct/Success R: {round(smiles_correct / success, 4)} Current Used\n",
        f"Correct/Total   R: {round(smiles_correct / evaluator.total_gt_count, 4)}",
    )
    success, tanimoto_correct = evaluator.evaluate_smiles_tanimoto(
        expand=True, kekule=True
    )
    print(
        f"************************ **SMILES Tanimoto** *************************\n",
        f"Valid GT: {success}\n",
        f"Based Success R: {round(tanimoto_correct / success, 4)}  Current Used\n",
        f"Based Total   R: {round(tanimoto_correct / evaluator.total_gt_count, 4)}",
    )
    success, correct = evaluator.evaluate_simplified_graph()
    print(
        f"************************ **S-Graph** *************************\n",
        f"Valid GT: {success}, Correct: {correct}\n",
        f"Correct/Success R: {round(correct / success, 4)}\n",
        f"Correct/Total   R: {round(correct / evaluator.total_gt_count, 4)} Current Used",
    )
    success, correct = evaluator.evaluate_graph()
    print(
        f"************************ **Graph** *************************\n",
        f"Valid GT: {success}, Correct: {correct}\n",
        f"Correct/Success R: {round(correct / success, 4)}\n",
        f"Correct/Total   R: {round(correct / evaluator.total_gt_count, 4)} Current Used",
    )
    if args.save_path:
        evaluator.save_eval_info(args.save_path)
