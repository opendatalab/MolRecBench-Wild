
## Graph-based_Expert_Models
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Graph-based_Expert_Models/MolGrapher/Molgrapher_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Graph-based_Expert_Models/MolNexTR/MolNexTR_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Graph-based_Expert_Models/MolScribe/MolScribe_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Graph-based_Expert_Models/GTR-Mol-VLM/GTR-Mol-VLM_graph_simple.jsonl

# ## Vision Language Models
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/GPT-4o/GPT4o_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/Qwen-VL-Max/Qwenvlmax_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/InternVL3_5/InternVL3_5_graph_simple.jsonl

# ## Vision Reasoning Models
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/GPT-5/gpt5_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Seed1.6-Thinking/seed16_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Intern-S1/inters1_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Gemini-2.5-Pro/gemini_graph_simple.jsonl
python evaluate/eval_S_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/GLM-4.5V/glm45_graph_simple.jsonl