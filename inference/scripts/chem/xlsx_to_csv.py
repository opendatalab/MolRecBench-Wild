#!/usr/bin/env python3
"""
Script to convert XLSX file to CSV format for chemical molecule recognition task.

This script reads an XLSX file with 'index' and 'prediction' fields, and converts
the prediction JSON data into structured CSV format with the following fields:
- img_id: converted from index
- symbols: list of atom symbols
- charges: list of charges (None if not present)
- isotopes: list of isotopes (0 if not present)
- valences: list of valences (0 if not present)
- radicals: list of radicals (None if not present)
- coords: list of point_2d coordinates
- edges: list of edges, each edge is [atom1, atom2, bond_type_id]
- brackets: list of brackets, each bracket is {'atoms': [...], 'alias': '...'}
- smiles: SMILES string (if prediction contains 'smiles' field)

The script supports two prediction formats:
1. Standard format with 'atoms', 'bonds', 'brackets' fields
2. SMILES format with only 'smiles' field: {"smiles": "..."}
"""

import argparse
import csv
import json
import os
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Please install it with: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)


# Bond type to ID mapping based on visual_example.txt
BOND_TYPE_TO_ID = {
    'single': 1,
    'double': 2,
    'triple': 3,
    'aromatic': 4,
    'solid wedge': 5,
    'dashed wedge': 6,
    'hollow wedge': 17,
    'solid_wedge': 5,
    'dashed_wedge': 6,
    'hollow_wedge': 17,
    'any': 7,
    'wavy': 13,
    'bold': 10,
    'dashed bold': 11,
    'dashed double': 19,
    'dashed triple': 20,
    'single or double': 8,
    'bold double': 18,
    'double either': 14,
    'single or aromatic': 9,
    'double or aromatic': 10,
    
    'dashed_bold': 11,
    'dashed_double': 19,
    'dashed_triple': 20,
    'single_or_double': 8,
    'bold_double': 18,
    'double_either': 14,
    'single_or_aromatic': 9,
    'double_or_aromatic': 10,

    'dipolar': 11,
    'dative': 11,
    'dashed dative': 21,
    'dashed_dative': 21,
    'hydrogen': 12,
    'attachment point': 23,
    'triple with single dash': 22,
    'attachment_point': 23,
    'triple_with_single_dash': 22,
}


def parse_prediction(prediction_str):
    """Parse prediction JSON string and extract atom and bond information.
    
    Args:
        prediction_str: JSON string containing atoms, bonds, and brackets, or smiles
        
    Returns:
        dict: Dictionary with symbols, charges, isotopes, valences, radicals, coords, edges, brackets, smiles
    """
    try:
        # Clean up the prediction string by removing special markers
        if isinstance(prediction_str, str):
            # Remove <|begin_of_box|> and <|end_of_box|> markers
            prediction_str = re.sub(r'<\|begin_of_box\|>', '', prediction_str)
            prediction_str = re.sub(r'<\|end_of_box\|>', '', prediction_str)
            # Strip leading/trailing whitespace
            prediction_str = prediction_str.strip()
            
            # Extract JSON from markdown code blocks (```json ... ``` or ``` ... ```)
            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)```', prediction_str, re.DOTALL)
            if code_block_match:
                prediction_str = code_block_match.group(1).strip()
        
        # First, try to extract smiles using regex (in case the string is not valid JSON)
        if isinstance(prediction_str, str):
            # Try to match "smiles": "..." pattern (handles escaped quotes and multiline)
            smiles_match = re.search(r'"smiles"\s*:\s*"((?:[^"\\]|\\.)*)"', prediction_str, re.DOTALL)
            if smiles_match:
                smiles = smiles_match.group(1).replace('\\"', '"').replace('\\\\', '\\')
                # If smiles found, directly return
                return {
                    'symbols': [],
                    'charges': [],
                    'isotopes': [],
                    'valences': [],
                    'radicals': [],
                    'coords': [],
                    'edges': [],
                    'brackets': [],
                    'smiles': smiles
                }
        
        # Try to parse as JSON
        if isinstance(prediction_str, str):
            try:
                prediction = json.loads(prediction_str)
            except json.JSONDecodeError:
                # If JSON parsing fails and no smiles found, return empty structure
                return {
                    'symbols': [],
                    'charges': [],
                    'isotopes': [],
                    'valences': [],
                    'radicals': [],
                    'coords': [],
                    'edges': [],
                    'brackets': [],
                    'smiles': ''
                }
        else:
            prediction = prediction_str
        
        # Check if smiles exists in parsed JSON
        if 'smiles' in prediction:
            smiles = prediction.get('smiles', '')
            return {
                'symbols': [],
                'charges': [],
                'isotopes': [],
                'valences': [],
                'radicals': [],
                'coords': [],
                'edges': [],
                'brackets': [],
                'smiles': smiles
            }
        
        # Extract atoms list
        atoms = prediction.get('atoms', [])
        
        # Initialize lists
        symbols = []
        charges = []
        isotopes = []
        valences = []
        radicals = []
        coords = []
        
        # Process each atom
        for atom in atoms:
            # Extract atom symbol
            atom_symbol = atom.get('atom', '')
            symbols.append(atom_symbol)
            
            # Extract charge (None if not present)
            charge = atom.get('charge', None)
            charges.append(charge)
            
            # Extract isotope (0 if not present)
            isotope = atom.get('isotope', 0)
            isotopes.append(isotope)
            
            # Extract valence (0 if not present)
            valence = atom.get('valence', 0)
            valences.append(valence)
            
            # Extract radical (None if not present)
            radical = atom.get('radical', None)
            radicals.append(radical)
            
            # Extract point_2d coordinates
            point_2d = atom.get('point_2d', [])
            coords.append(point_2d)
        
        # Extract bonds and convert to edges
        bonds = prediction.get('bonds', [])
        edges = []
        
        for bond in bonds:
            atom1 = bond.get('atom1', None)
            atom2 = bond.get('atom2', None)
            bond_type_str = bond.get('bond_type', '')
            
            # Map bond type string to ID
            bond_type_id = BOND_TYPE_TO_ID.get(bond_type_str, 1)  # Default to 1 if unknown
            
            # Create edge as [atom1, atom2, bond_type_id]
            if atom1 is not None and atom2 is not None:
                edges.append([atom1, atom2, bond_type_id])
        
        # Extract brackets and convert mark to alias
        brackets_raw = prediction.get('brackets', [])
        brackets = []
        
        for bracket in brackets_raw:
            atoms = bracket.get('atoms', [])
            mark = bracket.get('mark', '')
            
            # Convert mark to alias
            bracket_dict = {
                'atoms': atoms,
                'alias': mark
            }
            brackets.append(bracket_dict)
        
        # Extract smiles if present (for mixed format)
        smiles = prediction.get('smiles', '')
        
        return {
            'symbols': symbols,
            'charges': charges,
            'isotopes': isotopes,
            'valences': valences,
            'radicals': radicals,
            'coords': coords,
            'edges': edges,
            'brackets': brackets,
            'smiles': smiles
        }
        
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON prediction: {e}", file=sys.stderr)
        return {
            'symbols': [],
            'charges': [],
            'isotopes': [],
            'valences': [],
            'radicals': [],
            'coords': [],
            'edges': [],
            'brackets': [],
            'smiles': ''
        }
    except Exception as e:
        print(f"Error processing prediction: {e}", file=sys.stderr)
        return {
            'symbols': [],
            'charges': [],
            'isotopes': [],
            'valences': [],
            'radicals': [],
            'coords': [],
            'edges': [],
            'brackets': [],
            'smiles': ''
        }


def convert_xlsx_to_csv(input_xlsx, output_csv):
    """Convert XLSX file to CSV file.
    
    Args:
        input_xlsx: Input XLSX file path
        output_csv: Output CSV file path
    """
    
    # Read XLSX file
    print(f"Reading XLSX file: {input_xlsx}", file=sys.stderr)
    try:
        df = pd.read_excel(input_xlsx, engine='openpyxl')
    except Exception as e:
        print(f"Error reading XLSX file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check required columns
    if 'index' not in df.columns:
        print("Error: 'index' column not found in XLSX file", file=sys.stderr)
        sys.exit(1)
    
    if 'prediction' not in df.columns:
        print("Error: 'prediction' column not found in XLSX file", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(df)} rows in XLSX file", file=sys.stderr)
    
    # Process each row
    rows = []
    for idx, row in df.iterrows():
        img_id = row['index']
        prediction_str = row['prediction']
        
        # Parse prediction
        parsed_data = parse_prediction(prediction_str)
        
        # Create output row
        output_row = {
            'img_id': img_id,
            'symbols': parsed_data['symbols'],
            'charges': parsed_data['charges'],
            'isotopes': parsed_data['isotopes'],
            'valences': parsed_data['valences'],
            'radicals': parsed_data['radicals'],
            'coords': parsed_data['coords'],
            'edges': parsed_data['edges'],
            'brackets': parsed_data['brackets'],
            'smiles': parsed_data['smiles']
        }
        
        rows.append(output_row)
        
        if (idx + 1) % 100 == 0:
            print(f"Processed {idx + 1} rows...", file=sys.stderr)
    
    # Write to CSV
    print(f"Writing to CSV file: {output_csv}", file=sys.stderr)
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['img_id', 'symbols', 'charges', 'isotopes', 'valences', 'radicals', 'coords', 'edges', 'brackets', 'smiles']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # Write header
        writer.writeheader()
        
        # Write data rows
        for row in rows:
            # Convert lists to string representation for CSV
            csv_row = {
                'img_id': row['img_id'],
                'symbols': str(row['symbols']),
                'charges': str(row['charges']),
                'isotopes': str(row['isotopes']),
                'valences': str(row['valences']),
                'radicals': str(row['radicals']),
                'coords': str(row['coords']),
                'edges': str(row['edges']),
                'brackets': str(row['brackets']),
                'smiles': str(row['smiles']) if row['smiles'] else ''
            }
            writer.writerow(csv_row)
    
    print(f"\nSuccessfully converted {len(rows)} records to {output_csv}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description='Convert XLSX file to CSV format for chemical molecule recognition task.'
    )
    parser.add_argument('input_xlsx', help='Input XLSX file path')
    parser.add_argument('output_csv', help='Output CSV file path')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.exists(args.input_xlsx):
        print(f"Error: Input file '{args.input_xlsx}' does not exist", file=sys.stderr)
        sys.exit(1)
    
    # Convert
    convert_xlsx_to_csv(args.input_xlsx, args.output_csv)


if __name__ == '__main__':
    main()

