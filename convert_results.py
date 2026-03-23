"""
Convert VLMEvalKit inference output (XLSX) to Evaluator-compatible JSONL.

Usage:
    python convert_results.py VLMEvalKit/outputs/GPT4o_20241120/results.xlsx -o results/GPT4o.jsonl
    python convert_results.py results.xlsx -o pred.jsonl --verbose
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas is required. Install with: pip install pandas openpyxl", file=sys.stderr)
    sys.exit(1)


BOND_TYPE_TO_STR = {
    "single": "single",
    "double": "double",
    "triple": "triple",
    "aromatic": "aromatic",
    "solid wedge": "solid wedge",
    "dashed wedge": "dashed wedge",
    "solid_wedge": "solid wedge",
    "dashed_wedge": "dashed wedge",
    "hollow wedge": "hollow wedge",
    "hollow_wedge": "hollow wedge",
    "any": "any",
    "wavy": "wavy",
    "bold": "bold",
    "dashed bold": "dashed bold",
    "dashed_bold": "dashed bold",
    "dashed double": "dashed double",
    "dashed_double": "dashed double",
    "dashed triple": "dashed triple",
    "dashed_triple": "dashed triple",
    "single or double": "single or double",
    "single_or_double": "single or double",
    "bold double": "bold double",
    "bold_double": "bold double",
    "double either": "double either",
    "double_either": "double either",
    "single or aromatic": "single or aromatic",
    "single_or_aromatic": "single or aromatic",
    "double or aromatic": "double or aromatic",
    "double_or_aromatic": "double or aromatic",
    "dipolar": "dipolar",
    "dative": "dative",
    "dashed dative": "dashed dative",
    "dashed_dative": "dashed dative",
    "hydrogen": "hydrogen",
    "attachment point": "attachment point",
    "attachment_point": "attachment point",
    "triple with single dash": "triple with single dash",
    "triple_with_single_dash": "triple with single dash",
}


def parse_prediction(prediction_str):
    """Parse VLMEvalKit prediction JSON into Evaluator-compatible fields."""
    empty = {
        "symbols": [], "charges": [], "radicals": [], "valences": [],
        "isotopes": [], "attach_points": [], "coords": [],
        "bonds": [], "brackets": [],
    }

    if not prediction_str or (isinstance(prediction_str, float)):
        return empty

    try:
        if isinstance(prediction_str, str):
            prediction_str = re.sub(r'<\|begin_of_box\|>', '', prediction_str)
            prediction_str = re.sub(r'<\|end_of_box\|>', '', prediction_str)
            prediction_str = prediction_str.strip()

            code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)```', prediction_str, re.DOTALL)
            if code_block_match:
                prediction_str = code_block_match.group(1).strip()

        if isinstance(prediction_str, str):
            try:
                prediction = json.loads(prediction_str)
            except json.JSONDecodeError:
                return empty
        else:
            prediction = prediction_str

        if isinstance(prediction, dict) and "atoms" not in prediction:
            return empty

        atoms_raw = prediction.get("atoms", [])
        symbols, charges, radicals, valences = [], [], [], []
        isotopes, attach_points, coords = [], [], []

        for atom in atoms_raw:
            symbols.append(atom.get("atom", ""))
            charges.append(atom.get("charge", 0))
            radicals.append(atom.get("radical", 0))
            valences.append(atom.get("valence", 0))
            isotopes.append(atom.get("isotope", 0))
            attach_points.append(atom.get("attach_point", 0))
            coords.append(atom.get("point_2d", []))

        bonds_raw = prediction.get("bonds", [])
        bonds = []
        for bond in bonds_raw:
            a1 = bond.get("atom1")
            a2 = bond.get("atom2")
            bt = bond.get("bond_type", "single")
            bt = BOND_TYPE_TO_STR.get(bt, bt)
            if a1 is not None and a2 is not None:
                bonds.append([a1, a2, bt])

        brackets_raw = prediction.get("brackets", [])
        brackets = []
        for br in brackets_raw:
            brackets.append({
                "atoms": br.get("atoms", []),
                "alias": br.get("mark", br.get("alias", "")),
            })

        return {
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

    except Exception as e:
        print(f"  Warning: failed to parse prediction: {e}", file=sys.stderr)
        return empty


def convert(input_xlsx, output_jsonl, verbose=False):
    df = pd.read_excel(input_xlsx, engine="openpyxl")

    if "index" not in df.columns or "prediction" not in df.columns:
        print(f"Error: XLSX must contain 'index' and 'prediction' columns. "
              f"Found: {list(df.columns)}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_jsonl)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    skipped = 0

    with open(output_path, "w", encoding="utf-8") as f:
        for _, row in df.iterrows():
            img_name = str(row["index"])
            parsed = parse_prediction(row["prediction"])

            if not parsed["symbols"]:
                skipped += 1
                if verbose:
                    print(f"  Skipped {img_name}: empty prediction", file=sys.stderr)
                continue

            record = {"img_name": img_name, **parsed}
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written += 1

    print(f"Converted {written} predictions -> {output_jsonl}", file=sys.stderr)
    if skipped:
        print(f"  ({skipped} samples skipped due to empty/unparseable predictions)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Convert VLMEvalKit XLSX output to Evaluator JSONL format."
    )
    parser.add_argument("input_xlsx", help="VLMEvalKit output XLSX file")
    parser.add_argument("-o", "--output", required=True, help="Output JSONL path")
    parser.add_argument("--verbose", action="store_true", help="Print skipped samples")
    args = parser.parse_args()

    if not Path(args.input_xlsx).exists():
        print(f"Error: '{args.input_xlsx}' not found", file=sys.stderr)
        sys.exit(1)

    convert(args.input_xlsx, args.output, args.verbose)


if __name__ == "__main__":
    main()
