import copy
import itertools
import json
import argparse
import sys
import jsonlines
from pathlib import Path
from indigo import Indigo
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))

from rdkit import RDLogger

from evaluate.MolGraph import MolGraph
from evaluate.utils import (
    Convert_Rx_to_R,
    canonicalize_smiles_w_superatom,
    check_R_atom,
    compare_brackets,
    is_special_R,
    replace_superatom_with_mol,
)

indigo = Indigo()
from networkx.algorithms import isomorphism

lg = RDLogger.logger()
lg.setLevel(RDLogger.CRITICAL)


class Evaluator:
    def __init__(self, gt_list, pred_list, debug=False):
        self.eval_info = {}
        self.mol_graph_gts = {}
        self.mol_graph_preds = {}
        self.attribute = {"smiles": {}, "simplified_graph": {}, "graph": {}}
        self.debug = debug

        # 处理 GT
        for i in tqdm(range(len(gt_list)), desc="Loading GT"):
            img_id_gt = gt_list[i]["id"]
            self.eval_info[img_id_gt] = {}
            try:
                mol_graph_gt = MolGraph(
                    id=img_id_gt,
                    carbon_info={
                        "symbols": gt_list[i]["symbols"],
                        "charges": gt_list[i]["charges"],
                        "radicals": gt_list[i]["radicals"],
                        "valences": gt_list[i]["valences"],
                        "isotopes": gt_list[i]["isotopes"],
                        "attach_points": gt_list[i]["attach_points"],
                        "coords": gt_list[i]["coords"],
                        "bonds_list": gt_list[i]["bonds"],
                        "brackets": gt_list[i]["brackets"],
                    },
                )
            except Exception as e:
                if self.debug:
                    print(f"ERROR LOAD GT: {e}")
                mol_graph_gt = MolGraph(id=img_id_gt)
            self.mol_graph_gts[img_id_gt] = mol_graph_gt
        # 处理 Pred
        for i in range(len(pred_list)):
            img_id_pred = pred_list[i]["id"]
            try:
                mol_graph_pred = MolGraph(
                    id=img_id_pred,
                    carbon_info={
                        "symbols": pred_list[i]["symbols"],
                        "charges": pred_list[i]["charges"],
                        "radicals": pred_list[i]["radicals"],
                        "valences": pred_list[i]["valences"],
                        "isotopes": pred_list[i]["isotopes"],
                        "attach_points": pred_list[i]["attach_points"],
                        "coords": pred_list[i]["coords"],
                        "bonds_list": pred_list[i]["bonds"],
                        "brackets": pred_list[i]["brackets"],
                    },
                )
            except Exception as e:
                if self.debug:
                    print("*" * 100)
                    print(f"ERROR LOAD PRED: {e}")
                    print(f"pred_list[i]: {pred_list[i]}")
                mol_graph_pred = MolGraph(id=img_id_pred)
            self.mol_graph_preds[img_id_pred] = mol_graph_pred

    def evaluate_simplified_graph(self):
        node_match = isomorphism.categorical_node_match("symbol", None)
        edge_match = isomorphism.categorical_edge_match("bond", None)
        correct_count = 0
        success_count = 0
        for id in tqdm(
            self.eval_info.keys(), desc="Evaluating Simplified Graph"
        ):
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
        for id in tqdm(self.eval_info.keys(), desc="Evaluating Graph"):
            correct = False
            self.eval_info[id]["graph_eval"] = False
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            self.eval_info[id]["graph_gt"] = mol_graph_gt.dump_to_dict()
            self.eval_info[id]["graph_pred"] = mol_graph_pred.dump_to_dict()
            if len(mol_graph_gt.symbols) == 0:
                correct = False
            success_count += 1
            if len(mol_graph_pred.symbols) == 0:
                correct = False
            graph_correct, mapping = self._compare_graph(
                mol_graph_gt,
                mol_graph_pred,
                node_match,
                edge_match,
                simplify=False,
            )
            if graph_correct:
                # Compare brackets
                if compare_brackets(
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
        Compare two graphs whether they are equal, here only compare the nodes and edges whether they are equal, not compare the brackets
        Args:
            mol_graph_gt: GT graph instance
            mol_graph_pred: Pred graph instance
            node_match: node matching function
            edge_match: edge matching function
        Returns:
            True if equal, False if not equal
        """
        return self._compare_graph_impl(
            mol_graph_gt,
            mol_graph_pred,
            node_match,
            edge_match,
            simplify,
        )

    def _compare_graph_impl(
        self,
        mol_graph_gt,
        mol_graph_pred,
        node_match,
        edge_match,
        simplify,
    ):
        if check_R_atom(mol_graph_gt.symbols):
            # First check whether the symbols are equal except for the special R
            # Copy the instance
            mol_graph_gt_copy = copy.deepcopy(mol_graph_gt)
            mol_graph_pred_copy = copy.deepcopy(mol_graph_pred)

            # Convert Rx to R
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
            # If equal, then compare Rx
            if DiGM.is_isomorphic():
                gt_Rs = set(x for x in mol_graph_gt.symbols if is_special_R(x))
                pred_Rs = set(
                    x for x in mol_graph_pred.symbols if is_special_R(x)
                )
                # If the number of SR is not equal, then it is considered to be incorrect
                if len(gt_Rs) != len(pred_Rs):
                    return False
                # Perform permutation
                for perm in itertools.permutations(pred_Rs):
                    # Iterate over each combination, perform replacement
                    mol_graph_pred_copy = copy.deepcopy(mol_graph_pred)
                    mapping = dict(
                        zip(perm, gt_Rs)
                    )  # For example, {'Rb':'Ra', 'Ra':'Rb', 'Rc':'Rc'}
                    # Replace R in graph_pred["symbols"] with R in GT, other symbols remain unchanged
                    mol_graph_pred_copy.symbols = [
                        mapping.get(x, x) if x in mapping else x
                        for x in mol_graph_pred_copy.symbols
                    ]
                    assert len(mol_graph_pred_copy.symbols) == len(
                        mol_graph_gt.symbols
                    )
                    # Compare whether they are completely equal.
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

    def evaluate_smiles(self, expand=False, debug=False):
        correct_count = 0
        success_count = 0
        for id in tqdm(self.eval_info.keys(), desc="Evaluating SMILES"):
            self.eval_info[id]["smiles_eval"] = False
            self.eval_info[id]["smiles_gt"] = None
            self.eval_info[id]["smiles_pred"] = None
            mol_graph_gt = self.mol_graph_gts[id]
            mol_graph_pred = self.mol_graph_preds[id]
            try:
                smiles_gt, super_atom_map_gt = mol_graph_gt.dump_to_SMILES(
                    super_atom_map={}
                )
                self.eval_info[id]["smiles_gt"] = smiles_gt
                success_count += 1
            except Exception as e:
                if debug:
                    print(f"ERROR SMILES GT: {e}")
                continue
            try:
                smiles_pred, super_atom_map_pred = (
                    mol_graph_pred.dump_to_SMILES(
                        super_atom_map=super_atom_map_gt
                    )
                )
                self.eval_info[id]["smiles_pred"] = smiles_pred
            except Exception as e:
                if debug:
                    print(f"ERROR SMILES Pred: {e}")
                continue
            if expand:
                smiles_gt_canonical, super_atom_map, succeed = (
                    canonicalize_smiles_w_superatom(
                        smiles_gt, super_atom_map={}
                    )
                )
                smiles_pred_canonical, super_atom_map, succeed = (
                    canonicalize_smiles_w_superatom(
                        smiles_pred, super_atom_map=super_atom_map
                    )
                )
                smiles_exp_gt, missing_abbrs = replace_superatom_with_mol(
                    smiles_gt_canonical, canonical=True
                )

                try:
                    smiles_exp_pred, missing_abbrs = replace_superatom_with_mol(
                        smiles_pred_canonical, canonical=True
                    )
                except Exception as e:
                    print(f"ERROR SMILES EXP Pred: {e}")
                    continue
                smiles_exp_gt_canonical, super_atom_map, succeed = (
                    canonicalize_smiles_w_superatom(
                        smiles_exp_gt, super_atom_map={}
                    )
                )
                smiles_exp_pred_canonical, super_atom_map, succeed = (
                    canonicalize_smiles_w_superatom(
                        smiles_exp_pred, super_atom_map=super_atom_map
                    )
                )
                smiles_exp_pred_canonical, super_atom_map, succeed = (
                    canonicalize_smiles_w_superatom(
                        smiles_exp_pred, super_atom_map=super_atom_map
                    )
                )
                self.eval_info[id]["smiles_exp_gt_canonical"] = (
                    smiles_exp_gt_canonical
                )
                self.eval_info[id]["smiles_exp_pred_canonical"] = (
                    smiles_exp_pred_canonical
                )
                if smiles_exp_gt_canonical == smiles_exp_pred_canonical:
                    correct_count += 1
                    self.eval_info[id]["smiles_eval"] = True
            else:
                try:
                    smiles_gt_canonical, super_atom_map, succeed = (
                        canonicalize_smiles_w_superatom(
                            smiles_gt, super_atom_map={}
                        )
                    )
                    success_count += 1
                except Exception as e:
                    continue
                try:
                    smiles_pred_canonical, super_atom_map, succeed = (
                        canonicalize_smiles_w_superatom(
                            smiles_pred, super_atom_map=super_atom_map
                        )
                    )
                except Exception as e:
                    continue
                self.eval_info[id]["smiles_gt_canonical"] = smiles_gt_canonical
                self.eval_info[id]["smiles_pred_canonical"] = (
                    smiles_pred_canonical
                )
                if smiles_gt_canonical == smiles_pred_canonical:
                    correct_count += 1
                    self.eval_info[id]["smiles_eval"] = True
        return success_count, correct_count

    def save_eval_info(self, save_path):
        with open(save_path, "w") as f:
            json.dump(self.eval_info, f, indent=4)

    def save_attribute_result(self, save_path):
        with open(save_path, "w") as f:
            json.dump(self.attribute, f, indent=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Evaluate molecule predictions."
    )
    parser.add_argument(
        "--gt_path",
        type=str,
        required=True,
        help="Path to ground truth .jsonl file",
    )
    parser.add_argument(
        "--pred_path",
        type=str,
        required=True,
        help="Path to prediction .jsonl file",
    )
    parser.add_argument(
        "--save_path", type=str, help="Path to save eval info json"
    )
    args = parser.parse_args()

    # 加载参考的评估结果
    with jsonlines.open(args.gt_path) as reader:
        gt_list = list(reader)
    with jsonlines.open(args.pred_path) as reader:
        pred_list = list(reader)

    evaluator = Evaluator(gt_list=gt_list, pred_list=pred_list)
    success, smiles_correct = evaluator.evaluate_smiles(expand=True)
    print(
        f"SMILES           Success: {success}, Correct: {smiles_correct} R: {round(smiles_correct / success, 4)}"
    )
    success, correct = evaluator.evaluate_simplified_graph()
    print(
        f"Simplified Graph Success: {success}, Correct: {correct} R: {round(correct / success, 4)}"
    )
    success, correct = evaluator.evaluate_graph()
    print(
        f"Graph            Success: {success}, Correct: {correct} R: {round(correct / success, 4)}"
    )
    if args.save_path:
        evaluator.save_eval_info(args.save_path)
