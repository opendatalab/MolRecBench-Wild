from huggingface_hub import login
from datasets import load_dataset
import os
from tqdm import tqdm
import jsonlines

# TODO: 发布的时候需要删除
HF_TOKEN = "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"
login(HF_TOKEN)  # 按提示输入 Token

DATASET_NAME = "opendatalab/U-MolRecBench-Wild"
SAVE_PATH = "./dataset"
IMAGE_PATH = "./dataset/images"

os.makedirs(SAVE_PATH, exist_ok=True)
os.makedirs(IMAGE_PATH, exist_ok=True)


dataset = load_dataset(DATASET_NAME, split="test")

# 解析每一行
annotation = []
for idx, row in tqdm(enumerate(dataset)):
    # save image
    image = row["image"]
    id = row["id"]
    image_path = os.path.join(IMAGE_PATH, id)
    image.save(image_path)

    carbon_info = {
        "id": id,
        "image_path": image_path,
        "hardcase_label": row["hardcase_label"],
        "symbols": row["symbols"],
        "charges": row["charges"],
        "radicals": row["radicals"],
        "valences": row["valences"],
        "isotopes": row["isotopes"],
        "attach_points": row["attach_points"],
        "coords": row["coords"],
        "bonds": row["bonds"],
        "brackets": row["brackets"],
    }
    annotation.append(carbon_info)

# save annotation
with jsonlines.open(os.path.join(SAVE_PATH, "annotation.jsonl"), "w") as writer:
    for item in annotation:
        writer.write(item)
