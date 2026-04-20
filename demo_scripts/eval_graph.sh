# ## Vision Language Models
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/GPT-4o/GPT4o_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/Qwen-VL-Max/Qwenvlmax_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Language_Models/InternVL3_5/InternVL3_5_graph.jsonl

# ## Vision Reasoning Models
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/GPT-5/gpt5_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Seed1.6-Thinking/seed16_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Intern-S1/inters1_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/Gemini-2.5-Pro/gemini_graph.jsonl
python evaluate/eval_GRAPH.py --gt_path dataset/annotation.jsonl --pred_path results/Vision_Reasoning_Models/GLM-4.5V/glm45_graph.jsonl