#!/usr/bin/env python3
"""
Script to build TSV file directly from image directory.

Required TSV fields:
- index: unique identifier from image filename (without extension)
- image: base64 encoded image
- question: question string (fixed)
- answer: empty string
"""

import argparse
import csv
import os
import sys
from pathlib import Path

from PIL import Image

# Add parent directory to path to import vlmeval
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from vlmeval.smp.vlm import encode_image_to_base64


def process_image_file(image_path, question_text="请你对图片进行化学分子式预测", visual_example_paths=None):
    """Process a single image file and return TSV row data.
    
    Args:
        image_path: Path to the image file to process
        question_text: Question text to use
        visual_example_paths: List of paths to visual example images (optional)
    """
    try:
        # Get index from filename without extension
        index = Path(image_path).stem
        
        print(f"Processing {index}: loading image from {image_path}", file=sys.stderr)
        
        # Load image
        try:
            if not os.path.exists(image_path):
                print(f"Error: Image file does not exist: {image_path}", file=sys.stderr)
                return None
            img = Image.open(image_path)
        except Exception as e:
            print(f"Error loading image from {image_path}: {e}", file=sys.stderr)
            return None
        
        # Encode image to base64
        image_base64 = encode_image_to_base64(img)
        
        # Set question
        question = question_text
        
        # Set answer to empty string
        answer = ''
        
        row_data = {
            'index': index,
            'image': image_base64,
            'question': question,
            'answer': answer
        }
        
        # Add visual_examples if provided (store as paths, not base64)
        if visual_example_paths:
            for idx, visual_example_path in enumerate(visual_example_paths, 1):
                if visual_example_path:  # Only add if path is not None/empty
                    row_data[f'visual_example_{idx}'] = visual_example_path
        
        return row_data
        
    except Exception as e:
        print(f"Error processing image {image_path}: {e}", file=sys.stderr)
        return None


def build_tsv_from_image_dir(image_dir, output_tsv, question_text="请你对图片进行化学分子式预测", num_samples=None, visual_example_paths=None):
    """Build TSV file from image directory.
    
    Args:
        image_dir: Input image directory path
        output_tsv: Output TSV file path
        question_text: Question text to use
        num_samples: Number of samples to process (None = process all)
        visual_example_paths: List of paths to visual example images (optional)
    """
    
    # Check and validate visual example paths if provided (don't convert to base64, just use the paths)
    valid_visual_example_paths = []
    if visual_example_paths:
        for idx, visual_example_path in enumerate(visual_example_paths, 1):
            if visual_example_path:
                if not os.path.exists(visual_example_path):
                    print(f"Warning: Visual example file {idx} does not exist: {visual_example_path}", file=sys.stderr)
                else:
                    valid_visual_example_paths.append(visual_example_path)
                    print(f"Using visual example {idx} path: {visual_example_path}", file=sys.stderr)
    
    # Update visual_example_paths to only include valid paths
    visual_example_paths = valid_visual_example_paths if valid_visual_example_paths else None
    
    # Common image extensions
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    
    # Get all image files from directory
    image_files = []
    for file in os.listdir(image_dir):
        file_path = os.path.join(image_dir, file)
        if os.path.isfile(file_path):
            ext = Path(file).suffix.lower()
            if ext in image_extensions:
                image_files.append(file_path)
    
    # Sort image files for consistent ordering
    image_files.sort()
    
    if not image_files:
        print(f"Error: No image files found in {image_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(image_files)} image files", file=sys.stderr)
    
    # Process each image file
    rows = []
    for idx, image_path in enumerate(image_files, 1):
        # Check if we've reached the desired number of samples
        if num_samples is not None and len(rows) >= num_samples:
            print(f"\nReached target of {num_samples} samples, stopping.", file=sys.stderr)
            break
        
        print(f"Processing image {idx}/{len(image_files)}...", file=sys.stderr)
        row_data = process_image_file(image_path, question_text, visual_example_paths)
        
        if row_data:
            rows.append(row_data)
    
    # Write to TSV
    if rows:
        with open(output_tsv, 'w', encoding='utf-8', newline='') as f:
            # Define field names (include visual_example columns if provided)
            fieldnames = ['index', 'image', 'question', 'answer']
            if visual_example_paths:
                for idx in range(1, len(visual_example_paths) + 1):
                    fieldnames.append(f'visual_example_{idx}')
            
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
        description='Build TSV file from image directory for chemical molecule recognition task.'
    )
    parser.add_argument('image_dir', help='Input image directory path')
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
        help='Number of samples to process (default: process all images)'
    )
    parser.add_argument(
        '--visual-example',
        action='append',
        default=None,
        help='Path to visual example image to include in prompt (can be specified multiple times for multiple examples)'
    )
    
    args = parser.parse_args()
    
    # Check if image directory exists
    if not os.path.exists(args.image_dir):
        print(f"Error: Image directory '{args.image_dir}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(args.image_dir):
        print(f"Error: '{args.image_dir}' is not a directory", file=sys.stderr)
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
    
    # Build TSV
    build_tsv_from_image_dir(args.image_dir, args.output_tsv, question_text, args.num_samples, args.visual_example)


if __name__ == '__main__':
    # Usage examples:
    # 
    # 1. Use default prompt file (scripts/chem/default_prompt.txt):
    #    python scripts/chem/build_tsv_from_image_dir.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/Full_Images output.tsv -n 10
    # 
    # 2. Use custom prompt file:
    #    python scripts/chem/build_tsv_from_image_dir.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/Full_Images output.tsv --question-file scripts/chem/prompt/smiles.txt -n 100
    # 
    # 3. Use direct question text (overrides prompt file):
    #    python scripts/chem/build_tsv_from_image_dir.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/Full_Images output.tsv --question "Please predict the SMILES"
    # 
    # 4. Use visual example in prompt:
    #    python scripts/chem/build_tsv_from_image_dir.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/Full_Images output.tsv --question-file scripts/chem/prompt/visual_example.txt --visual-example scripts/chem/prompt/visual_example.png -n 10
    # 
    # 5. Use multiple visual examples in prompt:
    #    python scripts/chem/build_tsv_from_image_dir.py /mnt/dhwfile/Mineru4S/aohuijie/MolRecBench-Wild/Infer_data/Full_Images output.tsv --question-file scripts/chem/prompt/visual_example.txt --visual-example scripts/chem/prompt/visual_example.png --visual-example scripts/chem/prompt/cases.png -n 200
    #
    main()

