import argparse
import json
import os
import re
import sys
from collections import Counter

import jsonlines
import numpy as np
import pandas as pd

sys.path.append("./")
from evaluate.constants import BOND_TYPES


def safe_json_loads(s):
    s = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", s)
    return json.loads(s)


def dataframe_to_jsonl(df, jsonl_path, is_smiles_only=False):
    carbon_info_list = []

    for idx, row in df.iterrows():
        id = str(row["index"])
        if ".jpg" not in jsonl_path:
            id += ".jpg"
        if is_smiles_only:
            try:
                smiles = re.search(
                    r'"smiles"\s*:\s*"((?:\\.|[^"\\])*)"', row["prediction"]
                ).group(1)
                carbon_new = {
                    "id": id,
                    "smiles": smiles,
                    "symbols": None,
                    "charges": None,
                    "radicals": None,
                    "valences": None,
                    "isotopes": None,
                    "attach_points": None,
                    "coords": None,
                    "bonds": None,
                    "brackets": None,
                }
            except Exception:
                carbon_new = {
                    "id": id,
                    "smiles": "",
                    "symbols": None,
                    "charges": None,
                    "radicals": None,
                    "valences": None,
                    "isotopes": None,
                    "attach_points": None,
                    "coords": None,
                    "bonds": None,
                    "brackets": None,
                }
        else:
            if "glm" in jsonl_path.lower():
                try:
                    match = re.search(
                        r"<\|begin_of_box\|>([\s\S]*?)<\|end_of_box\|>",
                        row["prediction"],
                    )
                    if match is None:
                        carbon_info = None
                    else:
                        carbon_info = safe_json_loads(match.group(1))
                except Exception:
                    carbon_info = None
            else:
                try:
                    carbon_info = safe_json_loads(row["prediction"])
                except Exception:
                    match = re.search(
                        r"```json\s*([\s\S]*?)\s*```", str(row["prediction"])
                    )
                    if match is None:
                        carbon_info = None
                    else:
                        try:
                            carbon_info = safe_json_loads(match.group(1))
                        except Exception:
                            carbon_info = None
            if carbon_info:
                if "atoms" in carbon_info:
                    atoms = carbon_info.get("atoms", [])
                    symbols = []
                    charges = []
                    radicals = []
                    valences = []
                    isotopes = []
                    attach_points_index = []
                    remove_atom_index = []
                    coords = []
                    brackets = []
                    for atom in atoms:
                        symbol = atom.get("atom", None)
                        if symbol is None:
                            symbol = ""
                        symbols.append(symbol)
                        coords.append(atom.get("point_2d", None))
                        charges.append(atom.get("charge", None))
                        radicals.append(atom.get("radical", None))
                        valences.append(atom.get("valence", None))
                        isotopes.append(atom.get("isotope", None))
                    bonds = []
                    for bond in carbon_info.get("bonds", []):
                        if None in bond:
                            continue
                        bt = bond.get("bond_type", "None")
                        if bt in ["attachment point", "attachment_point"]:
                            attach_points_index.append(bond.get("atom1"))
                            remove_atom_index.append(bond.get("atom2"))
                        elif bt not in BOND_TYPES.keys() and bt not in [
                            "dashed",
                            "dipolar",
                            "dashed dipolar",
                            "double either",
                            "None",
                            "ionic",
                            "arromatic",
                            "solid",
                            "bold wedge",
                            "dashed single",
                            "dot",
                            "disulfide",
                            "wedge",
                            "dotted",
                            "arrow",
                            "coordinate",
                            "coordination",
                            "solid_bold",
                            "bold_wedge",
                        ]:
                            print(f"bond type not in BOND_TYPES: {bt}")
                        bt = (
                            BOND_TYPES.get(bond.get("bond_type"))
                            if bond.get("bond_type") in BOND_TYPES
                            else None
                        )
                        bonds.append([bond.get("atom1"), bond.get("atom2"), bt])
                    brackets = carbon_info.get("brackets", [])
                    bonds_matrix = np.zeros((len(symbols), len(symbols)))
                    for bond in bonds:
                        try:
                            if bond[2] is None or (
                                isinstance(bond[2], float) and np.isnan(bond[2])
                            ):
                                continue
                            bonds_matrix[bond[0], bond[1]] = bond[2]
                        except Exception:
                            continue
                    bonds_new = []
                    for i in range(len(symbols)):
                        for j in range(len(symbols)):
                            if bonds_matrix[i, j] != 0:
                                bonds_new.append([i, j, bonds_matrix[i, j]])
                    bonds = bonds_new
                    attach_points = [None] * len(symbols)
                    attach_points_index_count = Counter(attach_points_index)
                    for index, count in attach_points_index_count.items():
                        attach_points[index] = count
                    remove_atom_index = sorted(remove_atom_index, reverse=True)
                    for i in range(len(remove_atom_index) - 1, -1, -1):
                        try:
                            if remove_atom_index[i] >= len(symbols):
                                continue
                        except Exception as e:
                            print(
                                f"remove_atom_index: {remove_atom_index[i]} error: {e}"
                            )
                            continue
                        symbols.pop(remove_atom_index[i])
                        charges.pop(remove_atom_index[i]) if charges else None
                        radicals.pop(remove_atom_index[i]) if radicals else None
                        valences.pop(remove_atom_index[i]) if valences else None
                        isotopes.pop(remove_atom_index[i]) if isotopes else None
                        coords.pop(remove_atom_index[i])
                        attach_points.pop(
                            remove_atom_index[i]
                        ) if attach_points else None
                        bonds_matrix = np.delete(
                            bonds_matrix, remove_atom_index[i], axis=0
                        )
                        bonds_matrix = np.delete(
                            bonds_matrix, remove_atom_index[i], axis=1
                        )
                        if brackets:
                            new_brackets = []
                            for bracket in brackets:
                                atom_idx = bracket.get("atoms")
                                if remove_atom_index[i] in atom_idx:
                                    atom_idx.remove(remove_atom_index[i])
                                atom_idx = [
                                    aidx - 1
                                    if aidx > remove_atom_index[i]
                                    else aidx
                                    for aidx in atom_idx
                                ]
                                bracket["atoms"] = atom_idx
                                new_brackets.append(bracket)
                            brackets = new_brackets
                    if brackets:
                        new_brackets = []
                        for bracket in brackets:
                            new_bracket = {
                                "alias": bracket.get("mark"),
                                "atoms": bracket.get("atoms"),
                            }
                            new_brackets.append(new_bracket)
                        brackets = new_brackets
                else:
                    symbols = []
                    charges = []
                    radicals = []
                    valences = []
                    isotopes = []
                    attach_points = []
                    coords = []
                    bonds = []
                    brackets = []

                carbon_new = {
                    "id": id,
                    "smiles": None,
                    "symbols": symbols,
                    "charges": charges,
                    "radicals": radicals,
                    "valences": valences,
                    "isotopes": isotopes,
                    "attach_points": attach_points,
                    "coords": coords,
                    "bonds": bonds,
                    "brackets": brackets,
                }
            else:
                carbon_new = {
                    "id": id,
                    "smiles": None,
                    "symbols": [],
                    "charges": [],
                    "radicals": [],
                    "valences": [],
                    "isotopes": [],
                    "attach_points": [],
                    "coords": [],
                    "bonds": [],
                    "brackets": [],
                }
        carbon_info_list.append(carbon_new)

    print(f"total_count:{len(df)}")
    os.makedirs(os.path.dirname(jsonl_path), exist_ok=True)
    with jsonlines.open(jsonl_path, mode="w") as writer:
        for carbon_info in carbon_info_list:
            writer.write(carbon_info)


def main(excel_path, jsonl_path):
    excel = pd.ExcelFile(excel_path)
    for sheet_name in excel.sheet_names:
        df = pd.read_excel(excel, sheet_name=sheet_name)
        is_smiles_only = "smiles" in os.path.basename(jsonl_path).lower()
        print(f"Converted Sheet: {sheet_name} -> {jsonl_path}")
        dataframe_to_jsonl(df, jsonl_path, is_smiles_only)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--input",
        default="results_origin/QwenVLMax-OpenAI/QwenVLMax-OpenAI_chem_smiles.xlsx",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="results/Vision_Language_Models/Qwen-VL-Max/Qwenvlmax_smiles.jsonl",
    )
    args = parser.parse_args()
    input_path = args.input
    output_path = args.output
    main(input_path, output_path)
