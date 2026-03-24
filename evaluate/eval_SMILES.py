import os
import sys
import argparse
from tqdm import tqdm

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jsonlines
from evaluate.MolGraph import MolGraph
from evaluate.utils import (
    canonicalize_smiles_w_superatom,
    replace_superatom_with_mol,
)
from rdkit import RDLogger


def load_gt_smiles(gt_path):
    """
    加载GT注释文件，返回{id: smiles}的字典
    """
    gt_smiles = {}
    with jsonlines.open(gt_path) as reader:
        gt_annotation = list(reader)
    for item in gt_annotation:
        try:
            mol_graph_gt = MolGraph(
                carbon_info={
                    "id": item["id"],
                    "symbols": item["symbols"],
                    "charges": item["charges"],
                    "radicals": item["radicals"],
                    "valences": item["valences"],
                    "isotopes": item["isotopes"],
                    "attach_points": item["attach_points"],
                    "coords": item["coords"],
                    "bonds_list": item["bonds"],
                    "brackets": item["brackets"],
                }
            )
            smiles_gt, super_atom_map_gt = mol_graph_gt.dump_to_SMILES()
            gt_smiles[item["id"]] = smiles_gt
        except Exception as e:
            continue
    return gt_smiles


def load_pred_smiles(pred_path):
    """
    加载预测结果文件，返回{id: smiles}的字典
    """
    pred_smiles = {}
    with jsonlines.open(pred_path) as reader:
        pred_annotation = list(reader)
    for item in pred_annotation:
        id = item["id"]
        smiles = item["smiles"]
        pred_smiles[id] = smiles
    return pred_smiles


def evaluate_smiles(gt_smiles, pred_smiles):
    total_count = 0
    success_count = 0
    for id in tqdm(gt_smiles.keys(), desc="Evaluating SMILES"):
        if id not in pred_smiles:
            print(f"ID {id} not found in pred results")
            continue
        smiles_gt = gt_smiles[id]
        smiles_pred = pred_smiles[id]
        smiles_gt = replace_superatom_with_mol(smiles_gt)
        smiles_pred = replace_superatom_with_mol(smiles_pred)
        smiles_gt = canonicalize_smiles_w_superatom(smiles_gt)
        smiles_pred = canonicalize_smiles_w_superatom(smiles_pred)
        if smiles_gt == smiles_pred:
            success_count += 1
        total_count += 1

    print(f"SMILES Precision: {round(success_count / total_count, 4)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate SMILES predictions.")
    parser.add_argument("--gt_path", type=str, default="")
    parser.add_argument("--pred_path", type=str, default="")
    args = parser.parse_args()

    print("*" * 100)
    print(f"Evaluating: {args.pred_path}")

    # Only show severe errors, suppress warnings and information
    lg = RDLogger.logger()
    lg.setLevel(RDLogger.CRITICAL)

    # load gt annotation
    gt_smiles = load_gt_smiles(args.gt_path)
    # load pred results
    pred_smiles = load_pred_smiles(args.pred_path)

    # evaluate
    evaluate_smiles(gt_smiles, pred_smiles)
