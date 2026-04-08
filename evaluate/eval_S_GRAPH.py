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
    # 加载参考的评估结果
    with jsonlines.open(args.gt_path) as reader:
        gt_list = list(reader)
    pred_list = []
    with jsonlines.open(args.pred_path) as reader:
        for item in reader:
            pred_list.append(item)

    evaluator = Evaluator(gt_list=gt_list, pred_list=pred_list, debug=True)
    success, correct = evaluator.evaluate_simplified_graph()
    print(f"Simplified Graph Precision: {round(correct / success, 4)}")
