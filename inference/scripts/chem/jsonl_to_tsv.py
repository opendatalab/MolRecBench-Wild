#!/usr/bin/env python3
"""
Script to convert JSONL file to TSV format for chemical molecule recognition task.

Required TSV fields:
- index: unique identifier from data_id or questionnaire_id
- image: base64 encoded image (loaded from image_dir_p field)
- image_url: original image URL from raw_image_url or image_dir_p
- question: question string (fixed)
- answer: answer from gt_molfile or kekule_editor v2000
"""

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from PIL import Image

# Add parent directory to path to import vlmeval
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from vlmeval.smp.vlm import encode_image_to_base64


def load_image_from_path(image_path):
    """Load image from local file path and return PIL Image object."""
    try:
        if not os.path.exists(image_path):
            print(f"Error: Image file does not exist: {image_path}", file=sys.stderr)
            return None
        img = Image.open(image_path)
        return img
    except Exception as e:
        print(f"Error loading image from {image_path}: {e}", file=sys.stderr)
        return None


def process_jsonl_line(line, question_text="请你对图片进行化学分子式预测"):
    """Process a single JSONL line and return TSV row data."""
    try:
        data = json.loads(line.strip())
        
        # Extract index from data_id or questionnaire_id (for backward compatibility)
        index = data.get('data_id', '') or data.get('questionnaire_id', '')
        
        # Get image path from image_dir_p field
        image_path = data.get('image_dir_p', '')
        
        if not image_path:
            print(f"Warning: No image_dir_p found for index {index}", file=sys.stderr)
            return None
        
        print(f"Processing {index}: loading image from {image_path}", file=sys.stderr)
        img = load_image_from_path(image_path)
        
        if img is None:
            print(f"Warning: Failed to load image for index {index}", file=sys.stderr)
            return None
        
        # Encode image to base64
        image_base64 = encode_image_to_base64(img)
        
        # Get image_url from raw_image_url or use image_path as fallback
        image_url = data.get('raw_image_url', '') or image_path
        
        # Set question
        question = question_text
        
        # Extract answer from gt_molfile or evaluation.conversation_evaluation.contents[0].kekule_editor['v2000']
        answer = ''
        
        # First try to get from gt_molfile (for the new format)
        if 'gt_molfile' in data:
            answer = data.get('gt_molfile', '').strip()
        
        # If not found, try the old format
        if not answer:
            try:
                evaluation = data.get('evaluation', {})
                if evaluation:
                    conversation_eval = evaluation.get('conversation_evaluation')
                    if conversation_eval and isinstance(conversation_eval, dict):
                        contents = conversation_eval.get('contents', [])
                        if contents and len(contents) > 0:
                            kekule_editor = contents[0].get('kekule_editor')
                            if kekule_editor and isinstance(kekule_editor, dict):
                                answer = kekule_editor.get('v2000', '')
                            elif isinstance(kekule_editor, str):
                                # Handle case where kekule_editor is a string directly
                                answer = kekule_editor
            except Exception as e:
                print(f"Warning: Failed to extract answer for index {index}: {e}", file=sys.stderr)
                answer = ''  # Set empty answer if extraction fails (for test set)
        
        return {
            'index': index,
            'image': image_base64,
            'image_url': image_url,
            'question': question,
            'answer': answer
        }
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON line: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error processing line: {e}", file=sys.stderr)
        return None


def convert_jsonl_to_tsv(input_jsonl, output_tsv, question_text="请你对图片进行化学分子式预测", num_samples=None):
    """Convert JSONL file to TSV file.
    
    Args:
        input_jsonl: Input JSONL file path
        output_tsv: Output TSV file path
        question_text: Question text to use
        num_samples: Number of samples to convert (None = convert all)
    """
    
    # Read JSONL and process each line
    rows = []
    with open(input_jsonl, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            # Check if we've reached the desired number of samples
            if num_samples is not None and len(rows) >= num_samples:
                print(f"\nReached target of {num_samples} samples, stopping.", file=sys.stderr)
                break
            
            print(f"Processing line {line_num}...", file=sys.stderr)
            row_data = process_jsonl_line(line, question_text)
            
            if row_data:
                rows.append(row_data)
    
    # Write to TSV
    if rows:
        with open(output_tsv, 'w', encoding='utf-8', newline='') as f:
            # Define field names
            fieldnames = ['index', 'image', 'image_url', 'question', 'answer']
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t', 
                                   quoting=csv.QUOTE_MINIMAL)
            
            # Write header
            writer.writeheader()
            
            # Write data rows
            for row in rows:
                writer.writerow(row)
        
        print(f"\nSuccessfully converted {len(rows)} records to {output_tsv}", file=sys.stderr)
    else:
        print("No valid records found to convert", file=sys.stderr)


def load_question_from_file(file_path):
    """Load question text from file.
    
    Args:
        file_path: Path to the text file containing the question
        
    Returns:
        str: The question text from the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading question file '{file_path}': {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Convert JSONL file to TSV format for chemical molecule recognition task.'
    )
    parser.add_argument('input_jsonl', help='Input JSONL file path')
    parser.add_argument('output_tsv', help='Output TSV file path')
    parser.add_argument(
        '--question-file', 
        default=str(Path(__file__).parent / 'default_prompt.txt'),
        help='Path to text file containing the question/prompt (default: scripts/chem/default_prompt.txt)'
    )
    parser.add_argument(
        '--question',
        default=None,
        help='Question text to use directly (overrides --question-file)'
    )
    parser.add_argument(
        '-n', '--num-samples',
        type=int,
        default=None,
        help='Number of samples to convert (default: convert all samples)'
    )
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_jsonl):
        print(f"Error: Input file '{args.input_jsonl}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Determine question text to use
    if args.question:
        # If --question is provided directly, use it
        question_text = args.question
        print(f"Using question text provided via --question argument", file=sys.stderr)
    else:
        # Load from file
        if not os.path.exists(args.question_file):
            print(f"Error: Question file '{args.question_file}' does not exist", file=sys.stderr)
            sys.exit(1)
        question_text = load_question_from_file(args.question_file)
        print(f"Loaded question text from: {args.question_file}", file=sys.stderr)
    
    # Convert
    convert_jsonl_to_tsv(args.input_jsonl, args.output_tsv, question_text, args.num_samples)


if __name__ == '__main__':
    # Usage examples:
    # 
    # 1. Use default prompt file (scripts/chem/default_prompt.txt):
    #    python scripts/chem/jsonl_to_tsv.py examples/input.jsonl output.tsv -n 10
    # 
    # 2. Use custom prompt file:
    #    python scripts/chem/jsonl_to_tsv.py examples/分子识别编辑-cc40-v1.jsonl ~/LMUData/chem.tsv --question-file scripts/chem/prompt/smiles.txt -n 100
    #    python scripts/chem/jsonl_to_tsv.py examples/分子识别编辑-cc40-v1.jsonl ~/LMUData/chem_graph_simple.tsv --question-file scripts/chem/prompt/graph_simple.txt -n 100
    #    python scripts/chem/jsonl_to_tsv.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/infer_dat_1028_1428.jsonl ~/LMUData/chem_smiles_with_url.tsv --question-file scripts/chem/prompt/smiles.txt -n 100
    #    python scripts/chem/jsonl_to_tsv.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/infer_dat_1028_1428.jsonl ~/LMUData/chem_smiles_with_url.tsv --question-file scripts/chem/prompt/smiles.txt -n 100
    # 
    # 3. Use direct question text (overrides prompt file):
    #    python scripts/chem/jsonl_to_tsv.py examples/input.jsonl output.tsv --question "Please predict the SMILES"
    #
    main()
