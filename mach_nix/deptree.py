from typing import Iterable, Dict

from networkx import DiGraph, NetworkXNoCycle
from tree_format import format_tree

from mach_nix.data.nixpkgs import NixpkgsIndex
from mach_nix.resolver import ResolvedPkg


def mark_removed_circular_dep(pkgs: Dict[str, ResolvedPkg], G: DiGraph, node, removed_node):
    pkgs[node].removed_circular_deps.add(removed_node)
    for pred in G.predecessors(node):
        mark_removed_circular_dep(pkgs, G, pred, removed_node)


def remove_dependecy(pkgs: Dict[str, ResolvedPkg], G: DiGraph, node_from, node_to):
    if node_to in pkgs[node_from].build_inputs:
        raise Exception(
            f"Fata error: cycle detected in setup requirements\n"
            f"Cannot fix automatically.\n{[node_from, node_to]}")
    G.remove_edge(node_from, node_to)
    pkgs[node_from].prop_build_inputs.remove(node_to)
    print(
        f"WARNING: Circular dependency detected and removed:"
        f" {node_from}:{ pkgs[node_from].ver} -> {node_to}:{ pkgs[node_to].ver}")


def remove_circles_and_print(pkgs: Iterable[ResolvedPkg], nixpkgs: NixpkgsIndex):
    import networkx as nx
    print("\n### Resolved Dependencies ###\n")
    indexed_pkgs = {p.name: p for p in sorted(pkgs, key=lambda p: p.name)}
    roots: Iterable[ResolvedPkg] = sorted([p for p in pkgs if p.is_root], key=lambda p: p.name)

    edges = set()
    for p in pkgs:
        for child in p.build_inputs + p.prop_build_inputs:
            edges.add((p.name, child))
    G = nx.DiGraph(sorted(list(edges)))

    cycle_count = 0
    removed_edges = []
    for root in roots:
        try:
            while True:
                cycle = nx.find_cycle(G, root.name)
                cycle_count += 1
                remove_dependecy(indexed_pkgs, G, cycle[-1][0], cycle[-1][1])
                removed_edges.append((cycle[-1][0], cycle[-1][1]))
        except NetworkXNoCycle:
            continue
    for node, removed_node in removed_edges:
        mark_removed_circular_dep(indexed_pkgs, G, node, removed_node)

    class Limiter:
        visited = set()

        def name(self, node_name):
            if node_name in self.visited:
                if indexed_pkgs[node_name].build_inputs + indexed_pkgs[node_name].prop_build_inputs == []:
                    return node_name
                return f"{node_name} -> ..."
            return node_name

        def get_children(self, node_name):
            if node_name in self.visited:
                return []
            self.visited.add(node_name)
            return list(set(indexed_pkgs[node_name].build_inputs + indexed_pkgs[node_name].prop_build_inputs))

    for root in roots:
        limiter = Limiter()
        print(format_tree(
            root.name,
            format_node=limiter.name,
            get_children=limiter.get_children)
        )
    print(f"Total number of python modules: {len(indexed_pkgs)}")
    print(f"Removed circular dependencies: {cycle_count}\n")

