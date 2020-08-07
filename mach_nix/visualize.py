from operator import itemgetter
from typing import Iterable
from tree_format import format_tree

from mach_nix.resolver import ResolvedPkg


class Node:
    def __init__(self, pkg: ResolvedPkg, parent: 'Node' = None):
        self.pkg = pkg
        pi = pkg.provider_info
        self.name = f"{pkg.name} - {pkg.ver} - {pi.provider}"
        if pi.provider == 'wheel':
            self.name += f" - {'-'.join(pi.wheel_fname.split('-')[-3:])[:-4]}"
        self.children = []
        self.parent = parent
        if parent:
            self.parent.children.append(self)


def build_tree(pkgs: dict, root: Node):
    root_pkg = pkgs[root.pkg.name]
    for name in sorted(root_pkg.build_inputs + root_pkg.prop_build_inputs):
        child_pkg: ResolvedPkg = pkgs[name]
        child_node = Node(child_pkg, root)
        build_tree(pkgs, child_node)


def tree_to_dict(root_node: Node):
    return root_node.name, [tree_to_dict(child) for child in root_node.children]


def print_tree(root_node):
    d = tree_to_dict(root_node)
    print(format_tree(
        d, format_node=itemgetter(0), get_children=itemgetter(1)))


def print_deps(pkgs: Iterable[ResolvedPkg]):
    print("\n### Resolved Dependencies ###\n")
    indexed_pkgs = {p.name: p for p in sorted(pkgs, key=lambda p: p.name)}
    roots: Iterable[ResolvedPkg] = (p for p in pkgs if p.is_root)
    for root in roots:
        root_node = Node(root)
        build_tree(indexed_pkgs, root_node)
        print_tree(root_node)
