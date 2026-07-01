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

    with jsonlines.open(args.gt_path) as reader:
        gt_list = list(reader)
    with jsonlines.open(args.pred_path) as reader:
        pred_list = list(reader)

    evaluator = Evaluator(
        gt_list=gt_list, pred_list=pred_list, infer_version="v2"
    )
    success_graph, correct_graph = evaluator.evaluate_graph()
    print(
        f"Graph Precision           : {round(correct_graph / success_graph, 4)}"
    )
