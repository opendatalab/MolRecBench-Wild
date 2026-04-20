import os
import sys
import argparse
import jsonlines

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from evaluate.Evaluator import Evaluator


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt_path", default="")
    parser.add_argument("--pred_path", default="")
    args = parser.parse_args()
    print("*" * 100)
    print(f"Evaluating: {args.pred_path}")
    gt_path = args.gt_path
    pred_path = args.pred_path
    # gt_path = "dataset/annotation.jsonl"
    # pred_path = "results/Graph-based_Expert_Models/GTR-Mol-VLM/GTR-Mol-VLM_graph_simple.jsonl"
    with jsonlines.open(gt_path) as reader:
        gt_list = list(reader)
    with jsonlines.open(pred_path) as reader:
        pred_list = list(reader)

    evaluator = Evaluator(gt_list=gt_list, pred_list=pred_list, debug=True)
    success, correct = evaluator.evaluate_simplified_graph()
    print(f"Simplified Graph Precision: {round(correct / success, 4)}")
