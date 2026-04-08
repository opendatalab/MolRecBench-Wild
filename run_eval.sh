# Evaluate SMILES predictions
python evaluate/eval_SMILES.py --gt_path dataset/annotation.jsonl --pred_path results_origin_jsonl/GPT4o_20241120/GPT4o_20241120_chem_smiles.jsonl

# Evaluate S-GRAPH predictions
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results_origin_jsonl/GPT4o_20241120/GPT4o_20241120_chem_graph_simple.jsonl

# Evaluate S-GRAPH predictions
# python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results_origin_jsonl/GPT4o_20241120/GPT4o_20241120_chem.jsonl
# python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results_origin_jsonl/QwenVLMax-OpenAI/QwenVLMax-OpenAI_chem.jsonl
# python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results_origin_jsonl/InternVL3.5-241B-A28B-API/InternVL3.5-241B-A28B-API_chem.jsonl
