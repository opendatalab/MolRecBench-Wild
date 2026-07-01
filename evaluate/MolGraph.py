import json

import networkx as nx
from rdkit import Chem

from evaluate.constants import EQUAL_ABBREVIATION

from evaluate.utils import (
    format_atoms,
    format_bonds,
    parse_structure_gtr1,
    parse_structure_gtr2,
    replace_superatom_with_mol,
    simplify_bonds,
    split_charges_and_symbols,
    convert_graph_to_mol_block_v2,
    convert_graph_to_mol_block_v2_for_vis,
    convert_mol_block_to_graph_gtr_2_0,
)


class MolGraph:
    def __init__(
        self,
        id=None,
        mol_block=None,
        response=None,
        carbon_info=None,
        infer_version="v1",
        attribute=None,
        debug=False,
    ):
        self.id = id
        self.infer_version = infer_version
        self.attribute = attribute
        self.symbols = []
        self.charges = []
        self.radicals = []
        self.valences = []
        self.isotopes = []
        self.attach_points = []
        self.coords = []
        self.bonds_list = []
        self.brackets = []
        if mol_block is not None:
            self.load_from_mol_block(mol_block)
        elif response is not None:
            self.load_from_response(response, debug=debug)
        elif carbon_info is not None:
            self.load_from_carbon_info(carbon_info)

    def load_from_mol_block(self, mol_block):
        (
            self.symbols,
            self.charges,
            self.radicals,
            self.valences,
            self.isotopes,
            self.attach_points,
            self.coords,
            self.bonds_list,
            self.brackets,
        ) = convert_mol_block_to_graph_gtr_2_0(mol_block)
        self.symbols = [
            EQUAL_ABBREVIATION.get(symbol, symbol) for symbol in self.symbols
        ]

    def load_from_response(self, response, correct_y=True, debug=False):
        # 需要将 预测坐标反转， 保证与molfile中的一致
        if self.infer_version == "v1":
            try:
                symbols, coords, bonds_list = parse_structure_gtr1(
                    response=response["messages"][-1]["content"],
                    img_path=response["images"][0]["path"],
                    rescale_bond=False,
                    correct_y=correct_y,
                )
            except Exception as e:
                if debug:
                    print(f"parse_structure_gtr1 ERROR: {e}")
                symbols = []
                coords = []
                bonds_list = []
            # NOTE: 这里只评估元素符号，不评估电荷，所以需要分割开
            self.symbols, self.charges = split_charges_and_symbols(symbols)
            self.coords = coords
            self.bonds_list = bonds_list
            self.radicals = [None] * len(symbols)
            self.valences = [None] * len(symbols)
            self.attach_points = [None] * len(symbols)
            self.isotopes = [None] * len(symbols)
            self.brackets = []
        elif self.infer_version == "v2":
            try:
                (
                    self.symbols,
                    self.charges,
                    self.radicals,
                    self.valences,
                    self.isotopes,
                    self.attach_points,
                    self.coords,
                    self.bonds_list,
                    self.brackets,
                ) = parse_structure_gtr2(
                    response=response["messages"][-1]["content"],
                    img_path=response["images"][0]["path"],
                    correct_y=correct_y,
                )
            except Exception as e:
                if debug:
                    print(f"parse_structure_gtr2 ERROR: {e}")
                self.symbols = []
                self.charges = []
                self.radicals = []
                self.valences = []
                self.isotopes = []
                self.attach_points = []
                self.coords = []
                self.bonds_list = []
                self.brackets = []
        # 替换等效的缩写
        self.symbols = [
            EQUAL_ABBREVIATION.get(symbol, symbol) for symbol in self.symbols
        ]

    def load_from_carbon_info(self, carbon_info):
        self.symbols = carbon_info["symbols"]
        self.charges = carbon_info["charges"]
        self.radicals = carbon_info["radicals"]
        self.valences = carbon_info["valences"]
        self.isotopes = carbon_info["isotopes"]
        self.attach_points = carbon_info.get(
            "attach_points", [None] * len(carbon_info["symbols"])
        )
        self.coords = carbon_info["coords"]
        self.bonds_list = carbon_info["bonds"]
        self.brackets = carbon_info["brackets"]

    def dump_to_simplify_graph(self):
        # TODO: 创建一个有向图
        graph = nx.DiGraph()
        # TODO: 添加节点信息
        for i in range(len(self.symbols)):
            # 需要确保没有特殊值的时候保持为 None
            symbol = (
                self.symbols[i][1:-1]
                if len(self.symbols[i]) > 0
                and self.symbols[i][0] == "["
                and self.symbols[i][-1] == "]"
                else self.symbols[i]
            )
            graph.add_node(i, symbol=symbol)
        # TODO: 需要先简化化学键
        bond_simplified_list = simplify_bonds(self.bonds_list)
        # TODO: 添加边信息
        for i, j, bt in bond_simplified_list:
            # 有方向的键
            if bt in [5, 6, 11, 13, 17, 21]:
                graph.add_edge(i, j, bond=bt)
            else:
                graph.add_edge(i, j, bond=bt)
                graph.add_edge(j, i, bond=bt)
        return graph

    def dump_to_graph(self):
        # 创建一个有向图
        graph = nx.DiGraph()
        for i in range(len(self.symbols)):
            # 需要确保没有特殊值的时候保持为 None
            symbol = (
                self.symbols[i][1:-1]
                if len(self.symbols[i]) > 0
                and self.symbols[i][0] == "["
                and self.symbols[i][-1] == "]"
                else self.symbols[i]
            )
            graph.add_node(
                i,
                symbol=symbol,
                charge=self.charges[i],
                radical=self.radicals[i],
                valence=self.valences[i],
                isotope=self.isotopes[i],
                attach_point=self.attach_points[i],
            )
        for i, j, bt in self.bonds_list:
            if bt in [5, 6, 11, 13, 17, 21]:
                graph.add_edge(i, j, bond=bt)
            else:
                graph.add_edge(i, j, bond=bt)
                graph.add_edge(j, i, bond=bt)
        return graph

    def dump_to_mol_block(self, super_atom_map=None, flip_y=False, debug=False):
        if super_atom_map is None:
            super_atom_map = {}
        # try:
        mol_block = convert_graph_to_mol_block_v2_for_vis(
            self.symbols,
            self.charges,
            self.radicals,
            self.valences,
            self.isotopes,
            self.attach_points,
            self.coords,
            self.bonds_list,
            self.brackets,
            flip_y=flip_y,
            debug=debug,
        )

        return mol_block

    def dump_to_SMILES(
        self,
        expand=True,
        super_atom_map=None,
        super_index_init=40,
        kekuleSmiles=True,
        canonical=True,
        debug=False,
    ):
        smiles = ""
        missing_abbrs = {}
        if super_atom_map is None:
            super_atom_map = {}
        mol_block, super_atom_map = convert_graph_to_mol_block_v2(
            self.symbols,
            self.charges,
            self.radicals,
            self.valences,
            self.isotopes,
            self.attach_points,
            self.coords,
            simplify_bonds(self.bonds_list),
            self.brackets,
            super_atom_map=super_atom_map,
            super_index_init=super_index_init,
        )
        # sanitize 设置为False可以提高GT的有效数量
        mol = Chem.MolFromMolBlock(mol_block, sanitize=False)
        if mol is None:
            if debug:
                print(f"mol_block:{mol_block}")
            return smiles, super_atom_map, missing_abbrs
        # kekuleSmiles 设置为True可以提高GT的有效数量
        if kekuleSmiles:
            try:
                smiles = Chem.MolToSmiles(
                    mol, canonical=canonical, kekuleSmiles=True
                )
            except Exception as e:
                smiles = Chem.MolToSmiles(
                    mol, canonical=canonical, kekuleSmiles=False
                )
        else:
            smiles = Chem.MolToSmiles(
                mol, canonical=canonical, kekuleSmiles=False
            )
        # 还原超原子
        if debug:
            print("还原超原子符号")
            print(f"super_atom_map:{super_atom_map}")
            print(f"smiles:{smiles}")
        for symbol, idx in super_atom_map.items():
            if symbol.startswith("[") and symbol.endswith("]"):
                symbol = symbol[1:-1]
            smiles = smiles.replace(f"{idx}Tc", f"{symbol}")
        if expand:
            smiles, missing_abbrs = replace_superatom_with_mol(
                smiles,
                canonical=canonical,
                kekuleSmiles=kekuleSmiles,
                report_missing_abbr=False,
            )
        return smiles, super_atom_map, missing_abbrs

    def dump_to_dict(self, simplify=False):
        if simplify:
            return {
                "symbols": self.symbols,
                "coords": self.coords,
                "bonds_list": simplify_bonds(self.bonds_list),
            }
        else:
            return {
                "symbols": self.symbols,
                "charges": self.charges,
                "radicals": self.radicals,
                "valences": self.valences,
                "isotopes": self.isotopes,
                "attach_points": self.attach_points,
                "coords": self.coords,
                "bonds_list": self.bonds_list,
                "brackets": self.brackets,
            }

    def dump_to_response(self):
        import textwrap

        response_template_qwen25vl = textwrap.dedent("""
        ```json
        {list_of_atoms_and_bonds}
        ```
        ```json
        {{
            "smiles": "{smiles}"
        }}
        ```
        """)
        # 整理原子以及原子状态信息
        atoms = format_atoms(
            self.symbols,
            self.coords,
            [300, 300],
            flip_y=True,
            charges=self.charges,
            valences=self.valences,
            isotopes=self.isotopes,
            radicals=self.radicals,
            attach_points=self.attach_points,
        )
        atoms_bonds = format_bonds(self.bonds_list, atoms)
        tight_atoms_bonds = json.dumps(atoms_bonds).replace(" ", "")
        response_template_qwen25vl = response_template_qwen25vl.format(
            list_of_atoms_and_bonds=tight_atoms_bonds,
            smiles="N/A",
        )

        return response_template_qwen25vl
