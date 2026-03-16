import networkx as nx
from rdkit import Chem
from evaluate.utils import convert_graph_to_mol_block
from evaluate.utils import simplify_bonds


class MolGraph:
    def __init__(self, id=None, carbon_info=None, attribute=None):
        self.id = id
        self.attribute = attribute
        self.symbols = carbon_info["symbols"]
        self.charges = carbon_info["charges"]
        self.radicals = carbon_info["radicals"]
        self.valences = carbon_info["valences"]
        self.isotopes = carbon_info["isotopes"]
        self.attach_points = carbon_info["attach_points"]
        self.coords = carbon_info["coords"]
        self.bonds_list = carbon_info["bonds_list"]
        self.brackets = carbon_info["brackets"]

    def dump_to_simplify_graph(self):
        # Create a directed graph
        graph = nx.DiGraph()
        # Add node information
        for i in range(len(self.symbols)):
            # Ensure that when there are no special values, it remains None
            symbol = (
                self.symbols[i][1:-1]
                if len(self.symbols[i]) > 0
                and self.symbols[i][0] == "["
                and self.symbols[i][-1] == "]"
                else self.symbols[i]
            )
            graph.add_node(i, symbol=symbol)
        # Need to simplify the chemical bonds first
        bond_simplified_list = simplify_bonds(self.bonds_list)
        # Add edge information
        for i, j, bt in bond_simplified_list:
            # Chiral bonds
            if bt in [5, 6, 11, 13, 17, 21]:
                graph.add_edge(i, j, bond=bt)
            else:
                graph.add_edge(i, j, bond=bt)
                graph.add_edge(j, i, bond=bt)
        return graph

    def dump_to_graph(self):
        # Create a directed graph
        graph = nx.DiGraph()
        for i in range(len(self.symbols)):
            # Ensure that when there are no special values, it remains None
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

    def dump_to_SMILES(
        self, super_atom_map=None, super_index_init=40, debug=False
    ):
        if super_atom_map is None:
            super_atom_map = {}

        mol_block, super_atom_map = convert_graph_to_mol_block(
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
        mol = Chem.MolFromMolBlock(mol_block)

        smiles = Chem.MolToSmiles(mol, isomericSmiles=True)
        # Recover superatoms
        if debug:
            print("Recover superatom symbols")
            print(f"super_atom_map:{super_atom_map}")
            print(f"smiles:{smiles}")
        for symbol, idx in super_atom_map.items():
            if symbol.startswith("[") and symbol.endswith("]"):
                symbol = symbol[1:-1]
            smiles = smiles.replace(f"{idx}Tc", f"{symbol}")
        return smiles, super_atom_map

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
