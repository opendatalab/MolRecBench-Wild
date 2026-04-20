import numpy as np
import contextlib
import io
import re
from rdkit import Chem
from evaluate.constants import ABBR2MOLBLOCK, GREEK_LETTERS, CONFLICT_SYMBOLS
import copy


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
