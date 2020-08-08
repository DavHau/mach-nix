from operator import itemgetter
from typing import Iterable
from tree_format import format_tree

from mach_nix.data.nixpkgs import NixpkgsIndex
from mach_nix.resolver import ResolvedPkg


class Node:
    def __init__(self, pkg: ResolvedPkg, name, parent: 'Node' = None):
        self.pkg = pkg
        self.name = name
        self.children = []
        self.parent = parent
        if parent:
            self.parent.children.append(self)


def make_name(pkg: ResolvedPkg, nixpkgs: NixpkgsIndex):
    pi = pkg.provider_info
    name = f"{pkg.name} - {pkg.ver} - {pi.provider}"
    if pi.provider == 'wheel':
        name += f" - {'-'.join(pi.wheel_fname.split('-')[-3:])[:-4]}"
    if pi.provider == 'nixpkgs':
        name += f" (attrs: {' '.join(c.nix_key for c in nixpkgs.get_all_candidates(pkg.name))})"
    return name


def build_tree(pkgs: dict, root: Node, nixpkgs: NixpkgsIndex):
    root_pkg = pkgs[root.pkg.name]
    for name in sorted(root_pkg.build_inputs + root_pkg.prop_build_inputs):
        child_pkg: ResolvedPkg = pkgs[name]
        child_node = Node(child_pkg, make_name(child_pkg, nixpkgs), root)
        build_tree(pkgs, child_node, nixpkgs)


def tree_to_dict(root_node: Node):
    return root_node.name, [tree_to_dict(child) for child in root_node.children]


def print_tree(root_node):
    d = tree_to_dict(root_node)
    print(format_tree(
        d, format_node=itemgetter(0), get_children=itemgetter(1)))


def print_deps(pkgs: Iterable[ResolvedPkg], nixpkgs: NixpkgsIndex):
    print("\n### Resolved Dependencies ###\n")
    indexed_pkgs = {p.name: p for p in sorted(pkgs, key=lambda p: p.name)}
    roots: Iterable[ResolvedPkg] = (p for p in pkgs if p.is_root)
    for root in roots:
        root_node = Node(root, make_name(root, nixpkgs))
        build_tree(indexed_pkgs, root_node, nixpkgs)
        print_tree(root_node)
