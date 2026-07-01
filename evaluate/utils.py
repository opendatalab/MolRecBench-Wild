from collections import defaultdict
from typing import Counter
import numpy as np
import contextlib
import io
import re
from rdkit import Chem
from evaluate.constants import ABBR2MOLBLOCK, GREEK_LETTERS, CONFLICT_SYMBOLS
import copy


def load_list_from_jsonl(file_path):
    if "s3://" in file_path:
        return load_jsonl_from_s3_file(file_path)
    else:
        with open(file_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f]


greek_letters = [
    "α",
    "β",
    "γ",
    "δ",
    "ε",
    "ζ",
    "η",
    "θ",
    "ι",
    "κ",
    "λ",
    "μ",
    "ν",
    "ξ",
    "ο",
    "π",
    "ρ",
    "σ",
    "τ",
    "υ",
    "φ",
    "χ",
    "ψ",
    "ω",
]


def parse_attach_points_v2000(molblock: str):
    """
    Parse the attachment points information in a molblock.
    Args:
        molblock: molblock string
    Returns:
        attach_points_idx: a list of indices of attachment points
    """
    attach_points_idx = []
    lines = molblock.splitlines()
    for line in lines:
        if line.startswith("M  APO"):
            parts = line.split()
            count = int(parts[2])
            idx = 3
            for _ in range(count):
                atom_idx = int(parts[idx]) - 1  # convert to 0-based index
                attach_points_idx.append(atom_idx)
                idx += 2
    return attach_points_idx


def convert_bonds_list_to_bonds_matrix(bonds_list, num_atoms, debug=False):
    """
    Convert a list of bonds to a bonds matrix.
    Args:
        bonds_list: a list of bonds, each bond is a tuple of (i, j, bond_type)
        num_atoms: the number of atoms
    Returns:
        bonds_matrix: a numpy matrix of shape (num_atoms, num_atoms)
    """
    bonds_matrix = np.zeros((num_atoms, num_atoms))
    for bond in bonds_list:
        if bond[0] >= num_atoms or bond[1] >= num_atoms:
            if debug:
                print(
                    f"ERROR in convert_bonds_list_to_bonds_matrix: bond out of range: {bond}"
                )
            continue
        bonds_matrix[bond[0], bond[1]] = bond[2]
    return bonds_matrix


def simplify_bonds(edges_gt):
    """
    Simplify the bonds in a graph.
    Args:
        edges_gt: a list of edges, each edge is a tuple of (i, j, bond_type)
    Returns:
        bonds_simplified: a list of simplified bonds, each bond is a tuple of (i, j, bond_type)
    """
    bonds_simplified = []
    for i, j, bt in edges_gt:
        if bt in [1, 7, 8, 11, 12, 13, 15, 16, 17, 21, 23]:
            bonds_simplified.append([i, j, 1])
        elif bt in [2, 9, 10, 14, 18, 19]:
            bonds_simplified.append([i, j, 2])
        elif bt in [3, 20, 22]:
            bonds_simplified.append([i, j, 3])
        elif bt in [4, 5, 6]:
            bonds_simplified.append([i, j, bt])
    return bonds_simplified


def Convert_Rx_to_R(symbols):
    symbols_new = []
    for symbol in symbols:
        if is_special_R(symbol):
            symbols_new.append("R")
        else:
            symbols_new.append(symbol)
    return symbols_new


def check_R_atom(symbols):
    """
    Check if the symbols contain Rα or Rβ.
    Args:
        symbols: a list of symbols
    Returns:
        True if the symbols contain Rα or Rβ, False otherwise
    """
    symbols_str = "".join(symbols)
    if "Rα" in symbols_str and "Rβ" in symbols_str:
        return True
    else:
        return False


def is_special_R(symbol):
    """
    Check if the symbol is a special R.
    Args:
        symbol: a symbol
    Returns:
        True if the symbol is a special R, False otherwise
    """
    if (
        symbol.startswith("R")
        and len(symbol) == 2
        and symbol[1] in GREEK_LETTERS
    ):
        return True
    else:
        return False


def extract_brackets(smiles):
    """
    Extract the brackets in a SMILES string.
    Args:
        smiles: a SMILES string
    Returns:
        results: a list of brackets
    """
    stack = []
    results = []

    for i, ch in enumerate(smiles):
        if ch == "[":
            stack.append(i)
        elif ch == "]":
            if stack:
                start = stack.pop()
                if len(stack) == 0:
                    results.append(smiles[start + 1 : i])

    return results


def replace_superatoms_with_ts(smiles, tmp_atom="Tc", tmp_isotope_start_idx=20):
    """
    Replace the superatoms with Ts in a SMILES string.
    Args:
        smiles: a SMILES string
        tmp_atom: the atom to replace the superatoms
        tmp_isotope_start_idx: the start index of the isotope
    Returns:
        smiles: a SMILES string with the superatoms replaced with Ts
        superatom_map: a dictionary of superatoms and their isotopes
    """
    superatom_matches = extract_brackets(smiles)
    superatom_set = set(superatom_matches)
    superatom_map = {}
    for superatom in superatom_set:
        if superatom in CONFLICT_SYMBOLS:
            isotope_atom = f"{tmp_isotope_start_idx}{tmp_atom}"
            superatom_map[isotope_atom] = superatom
            smiles = smiles.replace(f"[{superatom}]", f"[{isotope_atom}]")
            tmp_isotope_start_idx += 1
        else:
            atom = Chem.AtomFromSmiles(f"[{superatom}]")
            if atom is not None:
                continue
            isotope_atom = f"{tmp_isotope_start_idx}{tmp_atom}"
            superatom_map[isotope_atom] = superatom
            smiles = smiles.replace(f"[{superatom}]", f"[{isotope_atom}]")
            tmp_isotope_start_idx += 1

    return smiles, superatom_map


def replace_superatom_with_mol(smiles_main: str, canonical=True, debug=False):
    """
    Replace the superatoms with mol blocks in a SMILES string.
    Args:
        smiles_main: a SMILES string
        canonical: whether to canonicalize the SMILES string
    Returns:
        smiles_exp: a SMILES string with the superatoms replaced with mol blocks
        missing_abbrs: a list of superatoms that are still in the SMILES string after replacement
    """
    # 1. Replace the superatoms with Ts in the SMILES string
    smiles_main_with_placeholder, superatom_map = replace_superatoms_with_ts(
        smiles_main
    )

    # 2. Read the main molecule
    mol_main = Chem.MolFromSmiles(smiles_main_with_placeholder, sanitize=False)
    if mol_main is None:
        if debug:
            print(
                f"Failed to parse the main molecule SMILES: \n smiles_main : {smiles_main} \n smiles_main_with_placeholder : {smiles_main_with_placeholder}"
            )
        return ""
    rw_main_mol = Chem.RWMol(mol_main)

    # 3. Iterate over the superatom mapping, and replace each superatom with a mol block
    need_to_remove_atoms = []
    for atom in rw_main_mol.GetAtoms():
        # Iterate over all atoms in the main molecule, find the corresponding superatom, and replace it with a mol block
        ind = atom.GetIdx()
        symbol = atom.GetSymbol()
        isotope = atom.GetIsotope()
        placeholder_atom = f"{isotope}{symbol}"
        # If this is a placeholder atom, then it needs to be deleted and replaced with a mol block
        if (
            placeholder_atom in superatom_map.keys()
            and superatom_map[placeholder_atom] in ABBR2MOLBLOCK.keys()
        ):
            need_to_remove_atoms.append(
                ind
            )  # Here we temporarily save the indices of the atoms that need to be deleted
            neighbors = atom.GetNeighbors()
            main_link_atom_inds = []
            for neighbor in neighbors:
                main_link_atom_inds.append(neighbor.GetIdx())
            # Add the sub molecule
            mol_sub = Chem.MolFromMolBlock(
                ABBR2MOLBLOCK[superatom_map[placeholder_atom]], removeHs=False
            )
            # If the sub molecule is not parsed successfully, then skip
            if mol_sub is None:
                continue
            attach_points_idx = parse_attach_points_v2000(
                ABBR2MOLBLOCK[superatom_map[placeholder_atom]]
            )
            # Combine the two molecules
            atom_idx_offset = mol_main.GetNumAtoms()
            mol_main = Chem.CombineMols(mol_main, mol_sub)
            mol_main_rm = Chem.RWMol(mol_main)
            # If there are attachment points, then add the bond, otherwise no bond is needed
            if attach_points_idx:
                sub_link_atom_ind = attach_points_idx[0] + atom_idx_offset

                for main_link_atom_ind in main_link_atom_inds:
                    mol_main_rm.AddBond(
                        main_link_atom_ind,
                        sub_link_atom_ind,
                        Chem.rdchem.BondType.SINGLE,
                    )
            mol_main = mol_main_rm.GetMol()
    mol_main_rm = Chem.RWMol(mol_main)
    # Delete the extra atoms, need_to_remove_atoms, in reverse order
    need_to_remove_atoms.sort(reverse=True)
    for atom_ind in need_to_remove_atoms:
        mol_main_rm.RemoveAtom(atom_ind)
    mol_final = mol_main_rm.GetMol()
    # mol_final = Chem.RemoveHs(mol_final)
    # Chem.SanitizeMol(mol_final)
    smiles_exp = Chem.MolToSmiles(
        mol_final, canonical=canonical, kekuleSmiles=False
    )
    # Replace the unexpanded abbreviations back
    missing_abbrs = []
    for superatom, isotope_atom in superatom_map.items():
        if superatom in smiles_exp:
            missing_abbrs.append(isotope_atom)
            smiles_exp = smiles_exp.replace(superatom, isotope_atom)
    if debug:
        print(f"INFO DEBUG: missing_abbrs: {missing_abbrs}")
    return smiles_exp


def _compare_bracket(bracket_gt, bracket_pred, mapping):
    """
    Compare two brackets.
    Args:
        bracket_gt: a bracket from the ground truth
        bracket_pred: a bracket from the prediction
        mapping: a dictionary of mapping from the ground truth to the prediction
    Returns:
        correct: True if the two brackets are the same, False otherwise
    """
    correct = True

    if bracket_gt["alias"] != bracket_pred["alias"]:
        correct = False
    bracket_gt_atoms_maped = []
    for atom in bracket_gt["atoms"]:
        bracket_gt_atoms_maped.append(mapping[atom])
    bracket_gt_atoms_maped.sort()
    bracket_pred_atoms = bracket_pred["atoms"]
    bracket_pred_atoms.sort()
    if bracket_gt_atoms_maped != bracket_pred_atoms:
        correct = False
    return correct


def compare_brackets(brackets_gt, brackets_pred, mapping):
    """
    Compare two lists of brackets.
    Args:
        brackets_gt: a list of brackets from the ground truth
        brackets_pred: a list of brackets from the prediction
        mapping: a dictionary of mapping from the ground truth to the prediction
    Returns:
        True if the two lists of brackets are the same, False otherwise
    """
    # if len(brackets_gt) > 0:
    #     print("*" * 100)
    #     print(f"mapping: {mapping}")
    #     print(f"brackets_gt: {brackets_gt}")
    #     print(f"brackets_pred: {brackets_pred}")
    if len(brackets_gt) == 0 and len(brackets_pred) == 0:
        return True
    # If only the prediction has brackets, then the prediction is incorrect
    if len(brackets_gt) == 0 and len(brackets_pred) > 0:
        return False
    # GT和预测的都有括号，则进行括号匹配
    for bracket_gt in brackets_gt:
        if brackets_pred:
            for bracket_pred in brackets_pred:
                if not _compare_bracket(bracket_gt, bracket_pred, mapping):
                    break
                else:
                    brackets_pred.remove(bracket_pred)
        else:
            return False
    return True


def get_max_isotope(mol_block, debug=False):
    """
    Get the maximum isotope number of R in a molblock, used to set the superatom index
    Args:
        mol_block: a molblock
        debug: whether to print debug information
    Returns:
        The maximum isotope number of R in the molblock
    """
    mol = None
    try:
        mol = Chem.MolFromMolBlock(mol_block, sanitize=False)
        if mol is None:
            if debug:
                print(
                    f"Error in get_max_isotope: mol is None, mol_block: {mol_block}"
                )
            return 0
        smiles = Chem.MolToSmiles(mol)
        return get_max_isotope_in_smiles(smiles)
    except Exception as e:
        if debug:
            print(f"Error in get_max_isotope: {e}")
            if mol_block:
                print(f"mol_block: {mol_block}")
        return 0


def get_max_isotope_in_smiles(smiles, debug=False):
    """
    Get the maximum isotope number of R in a SMILES string, used to set the superatom index
    Args:
        smiles: a SMILES string
        debug: whether to print debug information
    Returns:
        The maximum isotope number of R in the SMILES string
    """
    try:
        matches = re.findall(r"\[(\d+)\*]", smiles)
        return max(int(match) for match in matches) if matches else 2
    except Exception as e:
        if debug:
            print(f"Error in get_max_isotope_in_smiles: {e}")
        return 2


def atomwise_tokenizer(smi, exclusive_tokens=None):
    """
    Tokenize a SMILES string.
    Args:
        smi: a SMILES string
        exclusive_tokens: a list of exclusive tokens
    Returns:
        tokens: a list of tokens
    """
    pattern = r"(\[(?:[^\[\]]+|\[[^\[\]]+])+\]|Br?|Cl?|N|O|S|P|F|I|b|c|n|o|s|p|\(|\)|\.|=|#|-|\+|\\\\|\/|:|~|@|\?|>|\*|\$|\%[0-9]{2}|[0-9])"
    regex = re.compile(pattern)

    tokens = [token for token in regex.findall(smi)]

    if exclusive_tokens:
        for i, tok in enumerate(tokens):
            if tok.startswith("["):
                if tok not in exclusive_tokens:
                    tokens[i] = "[UNK]"

    return tokens


def canonicalize_smiles_w_superatom(
    smiles,
    super_atom_map={},
    ignore_chiral=False,
    ignore_cistrans=True,
    recover_super_atom=True,
    debug=False,
):
    """
    Canonicalize a SMILES string with superatoms.
    Args:
        smiles: a SMILES string
        super_atom_map: a dictionary of superatoms and their isotopes
        ignore_chiral: whether to ignore chiral
        ignore_cistrans: whether to ignore cistrans
        recover_super_atom: whether to recover superatoms
        debug: whether to print debug information
    Returns:
        smiles: a canonicalized SMILES string
        super_atom_map: a dictionary of superatoms and their isotopes
        succeed: True if the canonicalization is successful, False otherwise
    """
    if debug:
        print(f"INFO DEBUG: Canonicalize begin...")
    super_index = get_max_isotope_in_smiles(smiles)
    super_index = max(super_index, len(super_atom_map))
    succeed = True
    if type(smiles) is not str or smiles == "":
        return "", {}
    if ignore_cistrans:
        smiles = smiles.replace("/", "").replace("\\", "")

    tokens = atomwise_tokenizer(smiles)
    # Here we only process the superatom strings, not the mol blocks
    for j, token in enumerate(tokens):
        if token[0] == "[" and token[-1] == "]":  # If it is an R group
            symbol = token[1:-1]
            if token in super_atom_map:
                tokens[j] = super_atom_map[token]
            elif symbol[0] == "R" and symbol[1:].isdigit():
                super_index += 1
                tokens[j] = f"[{super_index}*]"
                super_atom_map[token] = f"[{super_index}*]"
            elif Chem.AtomFromSmiles(token) is None:
                super_index += 1
                tokens[j] = f"[{super_index}*]"
                super_atom_map[token] = f"[{super_index}*]"

    smiles = "".join(tokens)
    # canonicalize
    try:
        smiles = Chem.CanonSmiles(smiles, useChiral=(not ignore_chiral))
    except Exception as e:
        if debug:
            print(f"INFO Error: SMILES:{smiles} canonicalize failed: {e}")
        succeed = False
    if debug:
        print(
            f"INFO DEBUG: recover_super_atom:{recover_super_atom}, super_atom_map: {super_atom_map}"
        )

    # recover super atom
    if recover_super_atom:
        for key, value in super_atom_map.items():
            smiles = smiles.replace(value, key)
            if debug:
                print(f"INFO DEBUG: recover super atom: {value} -> {key}")
    if ignore_cistrans:  # Remove cis/trans isomers
        smiles = smiles.replace("/", "").replace("\\", "")
    if debug:
        print(f"INFO DEBUG: canonicalize result: {succeed}")
    return smiles, super_atom_map


def convert_graph_to_mol_block(
    symbols,
    charges,
    radicals,
    valences,
    isotopes,
    attach_points,
    coords,
    bonds_list,
    brackets,
    super_atom_map={},
    super_index_init=40,
    debug=False,
):
    """
    This function is used to convert a graph to a MolBlock, where the charge, isotope, radical, AttachPoint, etc. need to be added to the MolBlock
    NOTE: The bracket functionality has not been added to the MolBlock yet
    """
    # TODO: 2. Create an empty molecule
    mol = Chem.RWMol()  # Create an empty molecule
    atom_num = len(symbols)  # Get the number of atoms
    super_index = (
        super_index_init + len(super_atom_map) + 1
    )  # Get the superatom index
    ids = []  # Initialize the atom ID list
    for i in range(atom_num):
        symbol = symbols[i]  # 获取当前原子符号
        charge = charges[i]
        radical = radicals[i]
        valence = valences[i]
        isotope = isotopes[i]
        attach_point = attach_points[i]

        with contextlib.redirect_stdout(io.StringIO()):
            # Try to convert the atom symbol to an atom object
            if (
                symbol[1:-1] not in CONFLICT_SYMBOLS
            ):  # If the symbol is not a conflict symbol
                # 260120 Chem cannot read Fe, H
                if symbol in ["Fe", "H"]:
                    symbol = f"[{symbol}]"
                atom = Chem.AtomFromSmiles(symbol)
                if atom is None:  # If it is None, then it means failure
                    if symbol in super_atom_map:  # If it is in the map,
                        atom = Chem.Atom("Tc")
                        atom.SetIsotope(
                            super_atom_map[symbol]
                        )  # Set the isotope
                    else:  # If it is not in the list,
                        atom = Chem.Atom("Tc")
                        atom.SetIsotope(super_index)
                        super_atom_map[symbol] = super_index
                        super_index += 1
            elif symbol in super_atom_map:
                atom = Chem.Atom("Tc")
                atom.SetIsotope(super_atom_map[symbol])
            else:
                atom = Chem.Atom("Tc")
                atom.SetIsotope(super_index)
                super_atom_map[symbol] = super_index
                super_index += 1
            if charge is not None:
                atom.SetFormalCharge(charge)
            if isotope is not None:
                atom.SetIsotope(isotope)
            atom.SetChiralTag(
                Chem.rdchem.ChiralType.CHI_UNSPECIFIED
            )  # Set the chirality to unspecified
            # Add the atom to the molecule and get the index
            idx = mol.AddAtom(atom)
            assert idx == i  # Ensure the index is correct
            ids.append(idx)  # Add the index to the ID list
    # Need to ensure that the chiral bond is from C to any atom
    for i, j, bt in bonds_list:
        if bt == 1:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
        elif bt == 2:
            mol.AddBond(ids[i], ids[j], Chem.BondType.DOUBLE)
        elif bt == 3:
            mol.AddBond(ids[i], ids[j], Chem.BondType.TRIPLE)
        elif bt == 4:
            mol.AddBond(ids[i], ids[j], Chem.BondType.AROMATIC)
        elif bt == 5:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINWEDGE
            )
        elif bt == 6:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINDASH
            )

    # Convert the bonds list to a bonds matrix
    bonds_matrix = convert_bonds_list_to_bonds_matrix(bonds_list, atom_num)
    # Verify the chirality
    mol = verify_chirality_evaluation(
        mol, coords, symbols, bonds_matrix, debug=debug
    )
    # Convert the molecule to a mol block
    try:
        mol_block = Chem.MolToMolBlock(mol, kekulize=True)
    except Exception as e:
        mol_block = Chem.MolToMolBlock(mol, kekulize=False)
    return mol_block, super_atom_map


def verify_chirality_evaluation(
    mol, coords, symbols, edges_matrix, debug=False
):
    """
    Correct the chirality in the evaluation
    Args:
        mol: a molecule
        coords: a list of coordinates
        symbols: a list of symbols
        edges_matrix: a matrix of edges
        debug: whether to print debug information
    Returns:
        mol: a molecule with the chirality corrected
    """
    init_mol = copy.deepcopy(mol)
    try:
        n = mol.GetNumAtoms()
        mol_tmp = mol.GetMol()
        Chem.SanitizeMol(mol_tmp)
        chiral_centers = Chem.FindMolChiralCenters(
            mol_tmp,
            includeUnassigned=True,
            includeCIP=False,
            useLegacyImplementation=False,
        )
        # print(f"chiral_centers: {chiral_centers}")
        chiral_center_ids = [
            idx for idx, _ in chiral_centers
        ]  # List[Tuple[int, any]] -> List[int]

        # correction to clear pre-condition violation (for some corner cases)
        for bond in mol.GetBonds():
            if bond.GetBondType() == Chem.BondType.SINGLE:
                bond.SetBondDir(Chem.BondDir.NONE)

        # Create conformer from 2D coordinate
        conf = Chem.Conformer(n)
        conf.Set3D(True)
        for i, (x, y) in enumerate(coords):
            conf.SetAtomPosition(i, (x, y, 0))
        mol.AddConformer(conf)
        Chem.SanitizeMol(mol)
        Chem.AssignStereochemistryFrom3D(mol)
        # NOTE: seems that only AssignStereochemistryFrom3D can handle double bond E/Z
        # So we do this first, remove the conformer and add back the 2D conformer for chiral correction

        mol.RemoveAllConformers()
        conf = Chem.Conformer(n)
        conf.Set3D(False)
        for i, (x, y) in enumerate(coords):
            conf.SetAtomPosition(i, (x, y, 0))
        mol.AddConformer(conf)

        # Magic, inferring chirality from coordinates and BondDir. DO NOT CHANGE.
        Chem.SanitizeMol(mol)
        Chem.AssignChiralTypesFromBondDirs(mol)
        Chem.AssignStereochemistry(mol, force=True)

        # Second loop to reset any wedge/dash bond to be starting from the chiral center)
        for i in chiral_center_ids:
            for j in range(n):
                if edges_matrix[i][j] == 5 or edges_matrix[j][i] == 6:
                    # assert edges[j][i] == 6
                    mol.RemoveBond(i, j)
                    mol.AddBond(i, j, Chem.BondType.SINGLE)
                    mol.GetBondBetweenAtoms(i, j).SetBondDir(
                        Chem.BondDir.BEGINWEDGE
                    )
                elif edges_matrix[i][j] == 6 or edges_matrix[j][i] == 5:
                    # assert edges[j][i] == 5
                    mol.RemoveBond(i, j)
                    mol.AddBond(i, j, Chem.BondType.SINGLE)
                    mol.GetBondBetweenAtoms(i, j).SetBondDir(
                        Chem.BondDir.BEGINDASH
                    )
            Chem.AssignChiralTypesFromBondDirs(mol)
            Chem.AssignStereochemistry(mol, force=True)

        # reset chiral tags for non-carbon atom
        for atom in mol.GetAtoms():
            if atom.GetSymbol() != "C":
                atom.SetChiralTag(Chem.rdchem.ChiralType.CHI_UNSPECIFIED)
        mol = mol.GetMol()
        return mol
    except Exception as e:
        if debug:
            print(f"Error verifying chirality evaluation: {e}")
        return init_mol


def iter_special_R_substitution_mappings(symbols_gt, symbols_pred):
    """
    Yield dicts mapping pred special-R symbol -> gt special-R symbol. Greek
    assignments are permuted independently within each stem group (R1*, R2*, …).
    """
    import itertools

    def collect(sym_list):
        groups = defaultdict(set)
        for x in sym_list:
            if is_special_R(x):
                groups[special_R_stem(x)].add(x)
        return groups

    gt_groups = collect(symbols_gt)
    pred_groups = collect(symbols_pred)
    if set(gt_groups.keys()) != set(pred_groups.keys()):
        return
    for stem in gt_groups:
        if len(gt_groups[stem]) != len(pred_groups[stem]):
            return
    stems_sorted = sorted(gt_groups.keys())
    perm_lists = [
        tuple(itertools.permutations(sorted(pred_groups[k])))
        for k in stems_sorted
    ]
    for combo in itertools.product(*perm_lists):
        m = {}
        for stem, perm in zip(stems_sorted, combo):
            m.update(dict(zip(perm, sorted(gt_groups[stem]))))
        yield m


def simplify_R_group_in_symbols(symbols):
    """
    将符号列表中仅出现一次的特殊R符号（含希腊字母等），去掉希腊字母，只保留stem，加上两个*。
    如: "R1α" 变为 "R1**"；"Rκ" 变为 "R**"。多次出现的保持原样。
    其他符号（如C、N等）保持原样。
    """
    symbol_counts = Counter(symbols)
    # 希腊字母列表，同上
    _GREEK_CHARS = (
        "αβγδεζηθικλμνξοπρστυφχψω"
        "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
        "κ/κ"  # 某些自定义包含在 mol.py
    )

    def _remove_last_greek(symbol):
        # 去掉最后一个希腊字母并加两个*
        for i in range(len(symbol) - 1, -1, -1):
            if symbol[i] in _GREEK_CHARS:
                return symbol[:i] + "**"
        # 如果没有希腊字母，返回 R**
        return "R**"

    simplified_symbols = []
    for symbol in symbols:
        count = symbol_counts.get(symbol, 0)
        if is_special_R(symbol) and count == 1:
            simplified_symbols.append(_remove_last_greek(symbol))
        else:
            simplified_symbols.append(symbol)
    return simplified_symbols


def eval_smiles_impl(smiles_gt, smiles_pred):
    # 将sMILES中出现一次的特殊R*全部替换成R，然后进行匹配

    smiles_gt_simplified = simplify_R_group_in_smiles(smiles_gt)
    smiles_pred_simplified = simplify_R_group_in_smiles(smiles_pred)
    match, smiles_gt_simplified_canonical, smiles_pred_simplified_canonical = (
        SMILES_matching(smiles_gt_simplified, smiles_pred_simplified)
    )
    # 如果简化后的SMILES完全相同，则返回True
    if match:
        return (
            True,
            smiles_gt_simplified_canonical,
            smiles_pred_simplified_canonical,
        )

    symbols_gt = _special_R_symbols_from_smiles(smiles_gt_simplified_canonical)
    symbols_pred = _special_R_symbols_from_smiles(
        smiles_pred_simplified_canonical
    )
    # 如果简化后的SMILES中没有特殊R*，则返回False
    if not symbols_gt and not symbols_pred:
        return (
            False,
            smiles_gt_simplified_canonical,
            smiles_pred_simplified_canonical,
        )
    # 如果简化后的SMILES中有特殊R*，则进行匹配
    symbols_gt = _special_R_symbols_from_smiles(smiles_gt_simplified)
    symbols_pred = _special_R_symbols_from_smiles(smiles_pred_simplified)
    if not symbols_gt and not symbols_pred:
        return (
            False,
            smiles_gt_simplified_canonical,
            smiles_pred_simplified_canonical,
        )

    # 匹配特殊R*
    for mapping in iter_special_R_substitution_mappings(
        symbols_gt, symbols_pred
    ):
        # 替换特殊R*
        smiles_pred_mapped = _replace_special_R_symbols_in_smiles(
            smiles_pred_simplified, mapping
        )
        # 匹配替换后的SMILES
        (
            match,
            smiles_gt_simplified_canonical,
            smiles_pred_simplified_mapped_canonical,
        ) = SMILES_matching(smiles_gt_simplified, smiles_pred_mapped)
        if match:
            return (
                True,
                smiles_gt_simplified_canonical,
                smiles_pred_simplified_mapped_canonical,
            )

    return False, smiles_gt_simplified, smiles_pred_simplified


def normalize_greek_letters(items, sort_items=False):
    pattern = re.compile("[" + "".join(greek_letters) + "]")
    greek_index = {ch: i for i, ch in enumerate(greek_letters)}
    # 找出列表中出现过的希腊字母，并按希腊字母顺序排序
    used_letters = sorted(
        {ch for item in items for ch in pattern.findall(item)},
        key=lambda ch: greek_index[ch],
    )
    # 建立映射：出现的最小希腊字母 -> α，第二个 -> β ...
    mapping = {old: greek_letters[i] for i, old in enumerate(used_letters)}

    # 替换每个字符串中的希腊字母
    def replace_letter(text):
        return pattern.sub(lambda m: mapping[m.group(0)], text)

    result = [replace_letter(item) for item in items]
    # 如果需要按新的希腊字母顺序排序
    if sort_items:

        def sort_key(text):
            m = pattern.search(text)
            if m:
                return greek_index[m.group(0)]
            return float("inf")

        result = sorted(result, key=sort_key)
    return result


def _replace_special_R_symbols_in_smiles(smiles, mapping):
    def replace(match):
        symbol = match.group(1)
        return f"[{mapping.get(symbol, symbol)}]"

    return re.sub(r"\[([^\[\]]+)\]", replace, smiles)


def SMILES_matching(smiles_gt, smiles_pred):
    smiles_gt_canonical, super_atom_map, _ = canonicalize_smiles_w_superatom(
        smiles_gt,
        super_atom_map={},
        recover_super_atom=True,
        kekule=True,
    )
    smiles_pred_canonical, super_atom_map, _ = canonicalize_smiles_w_superatom(
        smiles_pred,
        super_atom_map=super_atom_map.copy(),
        recover_super_atom=True,
        kekule=True,
    )
    if smiles_gt_canonical == smiles_pred_canonical:
        return True, smiles_gt_canonical, smiles_pred_canonical
    else:
        return False, smiles_gt_canonical, smiles_pred_canonical


def _special_R_symbols_from_smiles(smiles):
    return [
        match.group(1)
        for match in re.finditer(r"\[([^\[\]]+)\]", smiles)
        if is_special_R(match.group(1))
    ]


def split_charges_and_symbols(symbols):
    symbols_new = []
    charges_new = []
    for symbol in symbols:
        if symbol == "[NH3+]":
            symbols_new.append("[NH3]")
            charges_new.append(1)
        elif symbol == "[NH+]":
            symbols_new.append("[NH]")
            charges_new.append(1)
        elif symbol == "[PH2+]":
            symbols_new.append("[PH2]")
            charges_new.append(1)
        elif symbol == "[CH3-]":
            symbols_new.append("[CH3]")
            charges_new.append(-1)
        elif symbol == "[CH2-]":
            symbols_new.append("[CH2]")
            charges_new.append(-1)
        elif "+" in symbol or "-" in symbol:
            atom = Chem.AtomFromSmiles(symbol)
            # 如果 atom是 None，或者 atom不止一个原子，则认为是超原子，则不存在电荷问题
            if atom is None:
                symbols_new.append(symbol)
                charges_new.append(None)
            else:
                symbols_new.append(atom.GetSymbol())
                charge = atom.GetFormalCharge()
                charges_new.append(charge if charge != 0 else None)

        else:
            symbols_new.append(symbol)
            charges_new.append(None)

    return symbols_new, charges_new


def parse_structure_gtr2(
    response=None,
    img_path=None,
    rescale_bond=True,
    bond_norm_lengths=1.75,
    correct_y=True,
    debug=False,
):
    """
    解析模型输出中的原子和键信息, 这个版本中 原子符号和电荷是分开预测的
    """
    # 1. 获取模型输出
    if rescale_bond:
        assert img_path is not None, (
            "img_path is required when rescale_bond is True"
        )
        img_size = Image.open(img_path).size
    atom_bond_match = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    try:
        structure_data = json.loads(atom_bond_match[0].strip(","))
    except Exception as e:
        if debug:
            print(f"parse_structure_gtr2 ERROR: {e}")
        return [], [], [], [], [], [], [], [], []

    symbols = []
    charges = []
    radicals = []
    valences = []
    isotopes = []
    attach_points = []
    coords = []
    bonds_list = []
    brackets = []

    for item in structure_data:
        if "a" in item:
            symbols.append(item["a"])
            coords.append(item["xy"] if "xy" in item else None)
            charges.append(item["c"] if "c" in item else None)
            radicals.append(item["r"] if "r" in item else None)
            valences.append(item["v"] if "v" in item else None)
            isotopes.append(item["i"] if "i" in item else None)
            attach_points.append(item["ap"] if "ap" in item else None)
        elif "b" in item:
            try:
                bonds_list.append([item["a1"], item["a2"], item["b"]])
            except Exception as e:
                if debug:
                    print(f"parse_structure_gtr2 ERROR: {e}")
        # TODO: 这块需要处理
        elif "br" in item:
            # 2026.05.18 格式正确的括号信息才会被记录
            if (
                "atoms" in item["br"]
                and "alias" in item["br"]
                and len(item["br"]["atoms"]) > 0
            ):
                brackets.append(item["br"])

    # 可能存在的问题：预测得到的边中的原子idx大于原子数量s
    bonds_matrix = convert_bonds_list_to_bonds_matrix(bonds_list, len(symbols))
    # 对坐标进行归一化
    coords = np.array(coords)
    coords = (coords - np.min(coords, axis=0)) / (
        np.max(coords, axis=0) - np.min(coords, axis=0) + 1e-6
    )
    if correct_y:
        coords[:, 1] = -coords[:, 1]
    if rescale_bond:
        coords = correct_coordinate_scale(
            coords, bonds_matrix, img_size, bond_norm_lengths
        )
    coords = np.round(coords, 4)
    coords = coords.tolist()
    return (
        symbols,
        charges,
        radicals,
        valences,
        isotopes,
        attach_points,
        coords,
        bonds_list,
        brackets,
    )


def parse_structure_gtr1(
    response=None,
    img_path=None,
    rescale_bond=True,
    bond_norm_lengths=1.75,
    correct_y=True,
    debug=False,
):
    """
    解析模型输出中的原子和键信息, 这个版本中 原子符号和电荷时一起预测的
    """
    if rescale_bond:
        assert img_path is not None, (
            "img_path is required when rescale_bond is True"
        )
        img_size = Image.open(img_path).size

    atom_bond_match = re.findall(r"```json\s*(.*?)\s*```", response, re.DOTALL)
    try:
        structure_data = json.loads(atom_bond_match[0].strip(","))
    except Exception as e:
        if debug:
            print(f"parse_structure_gtr1 ERROR: {e}")
        return [], [], []

    symbols = []
    coords = []
    bonds_list = []
    # 不排序，按照出现顺序处理
    for item in structure_data:
        if "a" in item:
            try:
                symbols.append(item["a"])
                coords.append(item["xy"])
            except Exception as e:
                if debug:
                    print(f"parse_structure_gtr1 ERROR: {e}")
        elif "b" in item:
            try:
                bonds_list.append([item["a1"], item["a2"], item["b"]])
            except Exception as e:
                if debug:
                    print(f"parse_structure_gtr1 ERROR: {e}")

    # 可能存在的问题：预测得到的边中的原子idx大于原子数量
    bonds_matrix = convert_bonds_list_to_bonds_matrix(bonds_list, len(symbols))
    # 对坐标进行归一化
    coords = normalize_nodes(coords)
    coords = np.array(coords)
    if correct_y:
        coords[:, 1] = -coords[:, 1]
    if rescale_bond:
        coords = correct_coordinate_scale(
            coords, bonds_matrix, img_size, bond_norm_lengths
        )
    coords = np.round(coords, 4)
    coords = coords.tolist()
    return symbols, coords, bonds_list


def format_bonds(bonds, atoms):
    chiral_up_b_type = 5
    chiral_down_b_type = 6
    chiral_hollow_b_type = 17
    chiral_up_mirror_b_type = -1
    chiral_down_mirror_b_type = -2
    chiral_hollow_mirror_b_type = -3
    dative_bond_b_type = 11
    wavy_bond_b_type = 13
    dashed_dative_bond_b_type = 21
    dative_bond_mirror_b_type = -4
    wavy_bond_mirror_b_type = -5
    dashed_dative_bond_mirror_b_type = -6
    directed_bond_mirrors = (
        chiral_down_mirror_b_type,
        chiral_up_mirror_b_type,
        chiral_hollow_mirror_b_type,
        dative_bond_mirror_b_type,
        wavy_bond_mirror_b_type,
        dashed_dative_bond_mirror_b_type,
    )
    atoms_bonds = []
    graph = [[0] * len(atoms) for _ in range(len(atoms))]
    for b in bonds:
        b_type = b[2]
        if b_type == chiral_up_b_type:
            forward_b_type = chiral_up_b_type
            backward_b_type = chiral_up_mirror_b_type
        elif b_type == chiral_down_b_type:
            forward_b_type = chiral_down_b_type
            backward_b_type = chiral_down_mirror_b_type
        elif b_type == chiral_hollow_b_type:
            forward_b_type = chiral_hollow_b_type
            backward_b_type = chiral_hollow_mirror_b_type
        elif b_type == dative_bond_b_type:
            forward_b_type = dative_bond_b_type
            backward_b_type = dative_bond_mirror_b_type
        elif b_type == wavy_bond_b_type:
            forward_b_type = wavy_bond_b_type
            backward_b_type = wavy_bond_mirror_b_type
        elif b_type == dashed_dative_bond_b_type:
            forward_b_type = dashed_dative_bond_b_type
            backward_b_type = dashed_dative_bond_mirror_b_type
        else:
            forward_b_type = b_type
            backward_b_type = b_type

        graph[b[0]][b[1]] = forward_b_type
        graph[b[1]][b[0]] = backward_b_type

    f_a_cnt = 0
    f_b_cnt = 0

    for idx, a in enumerate(atoms):
        atoms_bonds.append(a)
        f_a_cnt += 1

        for jdx in reversed(range(idx)):
            if graph[jdx][idx] != 0:
                if graph[jdx][idx] in directed_bond_mirrors:
                    b_fwd = graph[idx][jdx]
                    if b_fwd == 0:
                        continue
                    atoms_bonds.append(
                        {
                            "b": b_fwd,
                            "a1": idx,
                            "a2": jdx,
                        }
                    )
                else:
                    atoms_bonds.append(
                        {
                            "b": graph[jdx][idx],
                            "a1": jdx,
                            "a2": idx,
                        }
                    )
                f_b_cnt += 1
    return atoms_bonds


def format_atoms(
    atoms,
    node_coords,
    img_size,
    flip_y=False,
    charges=None,
    valences=None,
    isotopes=None,
    radicals=None,
    attach_points=None,
):
    f_atoms = []
    node_coords = format_coords(node_coords, img_size)
    for idx, (a, xy) in enumerate(zip(atoms, node_coords)):
        atom_dict = {"a": a, "id": idx}
        if flip_y:
            atom_dict["xy"] = [xy[0], img_size[1] - xy[1]]
        else:
            atom_dict["xy"] = xy
        # 电荷
        if (
            charges is not None
            and idx < len(charges)
            and charges[idx] is not None
        ):
            atom_dict["c"] = charges[idx]
        # 价态
        if (
            valences is not None
            and idx < len(valences)
            and valences[idx] is not None
        ):
            atom_dict["v"] = valences[idx]
        # 同位素
        if (
            isotopes is not None
            and idx < len(isotopes)
            and isotopes[idx] is not None
        ):
            atom_dict["i"] = isotopes[idx]
        # 自由基
        if (
            radicals is not None
            and idx < len(radicals)
            and radicals[idx] is not None
        ):
            atom_dict["r"] = radicals[idx]
        # 连接点
        if (
            attach_points is not None
            and idx < len(attach_points)
            and attach_points[idx] is not None
        ):
            atom_dict["ap"] = attach_points[idx]
        f_atoms.append(atom_dict)
    return f_atoms


def convert_graph_to_mol_block_v2(
    symbols,
    charges,
    radicals,
    valences,
    isotopes,
    attach_points,
    coords,
    bonds_list,
    brackets,
    super_atom_map={},
    super_index_init=40,
    verify_chirality=True,
    debug=False,
):
    """
    这个函数用于将图转换为MolBlock, 其中电荷，同位素，自由基，AttachPoint，等信息需要添加到MolBlock当中
    NOTE: 目前括号功能未添加到MolBlock当中
    """
    # 用于存储每个超原子的索引，用于在MolBlock中插入Alias
    # TODO: 1. 将列表转为 numpy
    bonds = np.array(bonds_list)

    # TODO: 2. 创建一个空的分子
    mol = Chem.RWMol()  # 创建一个空分子
    atom_num = len(symbols)  # 获取原子数量
    super_index = super_index_init + len(super_atom_map) + 1  # 获取超原子索引
    ids = []  # 初始化原子ID列表

    for i in range(atom_num):
        symbol = symbols[i]  # 获取当前原子符号
        charge = charges[i]
        radical = radicals[i]
        valence = valences[i]
        isotope = isotopes[i]
        attach_point = attach_points[i]

        # 尝试将原子符号转成原子对象
        if symbol[1:-1] not in CONFLICT_SYMBOLS:  # 如果该符号不是冲突符号
            # 260120 Chem不能读取 Fe
            if symbol in ["Fe", "H"]:
                symbol = f"[{symbol}]"
            atom = Chem.AtomFromSmiles(symbol)
            if atom is None:  # 如果是空，那就说明失败了
                if symbol in super_atom_map:  # 如果在map中，
                    atom = Chem.Atom("Tc")
                    atom.SetIsotope(super_atom_map[symbol])
                else:  # 如果不在列表中
                    atom = Chem.Atom("Tc")
                    atom.SetIsotope(super_index)
                    super_atom_map[symbol] = super_index
                    super_index += 1
        elif symbol in super_atom_map:
            atom = Chem.Atom("Tc")
            atom.SetIsotope(super_atom_map[symbol])
        else:
            atom = Chem.Atom("Tc")
            atom.SetIsotope(super_index)
            super_atom_map[symbol] = super_index
            super_index += 1
        if charge is not None:
            atom.SetFormalCharge(charge)
        if isotope is not None:
            atom.SetIsotope(isotope)
        # FIXME: 目前仅支持单自由基和三自由基
        if radical is not None:
            if radical in [1, 3]:
                atom.SetNumRadicalElectrons(2)
            elif radical == 2:
                atom.SetNumRadicalElectrons(1)
        atom.SetChiralTag(
            Chem.rdchem.ChiralType.CHI_UNSPECIFIED
        )  # 手性设置为空
        idx = mol.AddAtom(atom)  # 将原子添加到分子中并获取索引
        assert idx == i  # 确保索引正确
        ids.append(idx)  # 将索引添加到ID列表
    # 需要确保手性键是从C到任意原子
    for i, j, bt in bonds:  # 遍历所有可能的原子对，添加化学键
        if bt == 1:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
        elif bt == 2:
            mol.AddBond(ids[i], ids[j], Chem.BondType.DOUBLE)
        elif bt == 3:
            mol.AddBond(ids[i], ids[j], Chem.BondType.TRIPLE)
        elif bt == 4:
            mol.AddBond(ids[i], ids[j], Chem.BondType.AROMATIC)
        elif bt == 5:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINWEDGE
            )
        elif bt == 6:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINDASH
            )
    mol.RemoveAllConformers()
    n = mol.GetNumAtoms()
    conf = Chem.Conformer(n)
    conf.Set3D(False)
    for i, (x, y) in enumerate(coords):
        conf.SetAtomPosition(i, (x, y, 0))
    mol.AddConformer(conf)
    mol_block = Chem.MolToMolBlock(mol, kekulize=False)
    return mol_block, super_atom_map


def convert_graph_to_mol_block_v2_for_vis(
    symbols,
    charges,
    radicals,
    valences,
    isotopes,
    attach_points,
    coords,
    bonds_list,
    brackets,
    flip_y=False,
    debug=False,
):
    """
    这个函数用于将图转换为MolBlock, 其中电荷，同位素，自由基，AttachPoint，等信息需要添加到MolBlock当中
    Indigo不太行，它不支持手性键，
    NOTE: 这个函数仅用于绘图，不用于评估，在超原子的替换当中，仅记录索引，不设置同位素
    """
    # 用于存储每个超原子的索引，用于在MolBlock中插入Alias
    super_atom_indexs = {}
    # TODO: 1. 将列表转为 numpy
    bonds_list_simplify = simplify_bonds(bonds_list)
    bonds = np.array(bonds_list_simplify)

    # TODO: 2. 创建一个空的分子
    mol = Chem.RWMol()  # 创建一个空分子
    atom_num = len(symbols)  # 获取原子数量
    ids = []  # 初始化原子ID列表
    for i in range(atom_num):
        symbol = symbols[i]  # 获取当前原子符号
        charge = charges[i]
        radical = radicals[i]
        valence = valences[i]
        isotope = isotopes[i]
        # 激发态和价态不能写入MolBlock
        with contextlib.redirect_stdout(io.StringIO()):
            # 尝试将原子符号转成原子对象
            if symbol[1:-1] not in CONFLICT_SYMBOLS:  # 如果该符号不是冲突符号
                # 260120 Chem不能读取 Fe
                if symbol in METALS:
                    symbol = f"[{symbol}]"
                atom = Chem.AtomFromSmiles(symbol)
                if atom is None:  # 如果是空，那就说明失败了
                    atom = Chem.Atom("C")
                    super_atom_indexs[i] = symbol  # 记录超原子的索引
            else:
                atom = Chem.Atom("C")
                super_atom_indexs[i] = symbol  # 记录超原子的索引

        if charge is not None:
            atom.SetFormalCharge(charge)
        if isotope is not None:
            atom.SetIsotope(isotope)
        # TODO: 设置自由基
        if radical is not None:
            if radical in [1, 3]:
                atom.SetNumRadicalElectrons(2)
            elif radical == 2:
                atom.SetNumRadicalElectrons(1)
        atom.SetChiralTag(
            Chem.rdchem.ChiralType.CHI_UNSPECIFIED
        )  # 手性设置为空
        idx = mol.AddAtom(atom)  # 将原子添加到分子中并获取索引
        assert idx == i  # 确保索引正确
        ids.append(idx)  # 将索引添加到ID列表
    mol.RemoveAllConformers()
    n = mol.GetNumAtoms()
    conf = Chem.Conformer(n)
    conf.Set3D(False)
    for i, (x, y) in enumerate(coords):
        if flip_y:
            y = 1 - y
        conf.SetAtomPosition(i, (x, y, 0))
    mol.AddConformer(conf)
    # 需要确保手性键是从C到任意原子
    for i, j, bt in bonds:  # 遍历所有可能的原子对，添加化学键
        if bt == 1:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
        elif bt == 2:
            mol.AddBond(ids[i], ids[j], Chem.BondType.DOUBLE)
        elif bt == 3:
            mol.AddBond(ids[i], ids[j], Chem.BondType.TRIPLE)
        elif bt == 4:
            mol.AddBond(ids[i], ids[j], Chem.BondType.AROMATIC)
        elif bt == 5:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINWEDGE
            )
        elif bt == 6:
            mol.AddBond(ids[i], ids[j], Chem.BondType.SINGLE)
            mol.GetBondBetweenAtoms(ids[i], ids[j]).SetBondDir(
                Chem.BondDir.BEGINDASH
            )

    # MolToMolBlock( (rdkit.Chem.rdchem.Mol)mol [, (bool)includeStereo=True [, (int)confId=-1 [, (bool)kekulize=True [, (bool)forceV3000=False]]]]) -> str :
    from rdkit.Chem import rdDepictor as ORD

    ORD.SetPreferCoordGen(False)
    try:
        mol_block = Chem.MolToMolBlock(mol, kekulize=True)
    except Exception as e:
        mol_block = Chem.MolToMolBlock(mol, kekulize=False)
    # FIXME: 将MolBlock V3000 转 V2000,存在问题，会报Segmentation fault，不知道原因
    # try:
    #     indigo = Indigo()
    #     mol_indigo = indigo.loadQueryMolecule(mol_block)
    #     indigo.setOption("molfile-saving-mode", "2000")
    #     mol_block = mol_indigo.molfile()
    # except Exception as e:
    #     pass

    # 将连接点插入MolBlock中
    mol_block = insert_attachment_point_to_mol_block(mol_block, attach_points)
    # 将Alias插入MolBlock中
    mol_block = insert_alias_to_mol_block(mol_block, super_atom_indexs)
    # 修正双键问题
    mol_block = fix_molblock_stereo_flag(mol_block)
    # 处理出1-6之外特殊的键类型
    mol_block = fix_molblock_special_bonds(mol_block, bonds_list)
    return mol_block


def convert_mol_block_to_graph_gtr_2_0(mol_block, ignore_valence=False):
    # TODO: 1. 处理 MolBlock中可能存在的问题
    # 1.1 处理 SMT SGroup 中的换行问题
    mol_block = merge_smt_lines(mol_block)
    # 1.2 处理 Alias 中的换行问题
    atoms_to_remove_s0 = []
    # TODO: 1. 处理 MolBlock中可能存在的问题
    # 1.1 处理 SMT SGroup 中的换行问题
    mol_block = merge_smt_lines(mol_block)
    # 1.2 处理 Alias 中的换行问题
    mol_block = merge_alias_lines(mol_block)
    # 1.3 处理 R 原子, MolBlock中的原子块中可能存在 Rn 原子，需要将 Rn 原子替换为 C 原子，保证 indigo正确解析
    mol_block, replaced_atoms = replace_r_atoms(mol_block)
    # 1.4 提取价态信息 NOTE: 这里不提取价态信息，因为 mol_block 中没有价态信息
    if not ignore_valence:
        valence_dict = extract_valence_dict(mol_block)
    else:
        valence_dict = None

    # TODO: 2. 解析 SGroups， 将 SGroups 中的信息提取出来，MolBlock中只保留普通的原子和键
    mol_block, sgroups, ap_dict = parse_sgroups_from_molfile(mol_block)

    # TODO: 3. 使用 indigo 加载 MolBlock， 获取原子信息和键信息
    indigo = Indigo()
    mol = indigo.loadQueryMolecule(mol_block)
    # 3.1 重置过度金属相邻原子的电荷
    mol = process_transition_metal(mol)
    # 3.2 解析原子信息
    symbols, charges, coords, radicals, valences, isotopes = (
        parse_atom_info_from_mol_gtr(mol, valence_dict)
    )
    attach_points = convert_ap_dict_to_ap_list(ap_dict, len(symbols))
    # 3.3 获取键信息，这里的索引从 0 开始
    bonds_s0 = parse_bond_info_v2(mol_block, sgroups)
    # print(f"bonds_s0: {bonds_s0}")
    # 3.4 获取括号信息
    brackets, bonds_s0, sgroups, atoms_to_remove_s0 = parse_bracket(
        coords, bonds_s0, sgroups, atoms_to_remove_s0
    )

    # TODO: 4. 处理Alias， SMT等信息
    # 4.1 处理替换的R
    symbols = restore_replaced_r_atoms(symbols, replaced_atoms)
    # 4.3 处理Alias
    symbols, charges, sgroups = restore_alias(
        symbols, charges, sgroups, merge_alias_and_charge=False
    )
    # 4.4 处理 SMT
    symbols, charges, coords, bonds_s0, atoms_to_remove_s0 = restore_smt(
        symbols, charges, coords, bonds_s0, sgroups, atoms_to_remove_s0
    )
    appended_atom_num = len(symbols) - len(radicals)
    if appended_atom_num > 0:
        radicals.extend([None] * appended_atom_num)
        valences.extend([None] * appended_atom_num)
        isotopes.extend([None] * appended_atom_num)
        attach_points.extend([None] * appended_atom_num)
    # 4.5 删除多余的信息
    (
        symbols,
        charges,
        radicals,
        valences,
        isotopes,
        attach_points,
        coords,
        bonds_s0,
        brackets,
    ) = _remove_redundant_graph_items_gtr_2_0(
        {
            "symbols": symbols,
            "charges": charges,
            "radicals": radicals,
            "valences": valences,
            "isotopes": isotopes,
            "attach_points": attach_points,
            "coords": coords,
            "bonds_s0": bonds_s0,
            "brackets": brackets,
        },
        atoms_to_remove_s0,
    )

    return (
        symbols,
        charges,
        radicals,
        valences,
        isotopes,
        attach_points,
        coords,
        bonds_s0,
        brackets,
    )
