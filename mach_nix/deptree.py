from operator import itemgetter
from typing import Iterable, List

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

    def all_parents(self) -> List['Node']:
        if self.parent is None:
            return []
        return [self.parent] + self.parent.all_parents()


def make_name(pkg: ResolvedPkg, nixpkgs: NixpkgsIndex):
    pi = pkg.provider_info
    extras = f"[{' '.join(pkg.extras_selected)}]" if pkg.extras_selected else ''
    name = f"{pkg.name}{extras} - {pkg.ver} - {pi.provider.name}"
    if pi.provider == 'wheel':
        name += f" - {'-'.join(pi.wheel_fname.split('-')[-3:])[:-4]}"
    if pi.provider == 'nixpkgs':
        name += f" (attrs: {' '.join(c.nix_key for c in nixpkgs.get_all_candidates(pkg.name))})"
    return name


def build_tree(pkgs: dict, root: Node, nixpkgs: NixpkgsIndex) -> List[str]:
    """
    Recursively adds children to given root node.
    Removes cycles from original graph while processing.
    Returns list of warnings.
    """
    root_pkg = pkgs[root.pkg.name]
    warnings = []
    for name in sorted(root_pkg.build_inputs + root_pkg.prop_build_inputs):
        child_pkg: ResolvedPkg = pkgs[name]
        # detect circles
        if child_pkg in [node.pkg for node in root.all_parents()]:
            warnings.append(
                f"WARNING: Circular dependency detected and removed:"
                f" {root.pkg.name}:{root.pkg.ver} -> {child_pkg.name}:{child_pkg.ver}")
            root.pkg.build_inputs = [bi for bi in root.pkg.build_inputs if bi != child_pkg.name]
            root.pkg.prop_build_inputs = [bi for bi in root.pkg.prop_build_inputs if bi != child_pkg.name]
            root.pkg.removed_circular_deps.append(child_pkg.name)
            continue
        child_node = Node(child_pkg, make_name(child_pkg, nixpkgs), root)
        warnings += build_tree(pkgs, child_node, nixpkgs)
    return warnings


def tree_to_dict(root_node: Node):
    return root_node.name, [tree_to_dict(child) for child in root_node.children]


def print_tree(root_node):
    d = tree_to_dict(root_node)
    print(format_tree(
        d, format_node=itemgetter(0), get_children=itemgetter(1)))


def remove_circles_and_print(pkgs: Iterable[ResolvedPkg], nixpkgs: NixpkgsIndex):
    print("\n### Resolved Dependencies ###\n")
    indexed_pkgs = {p.name: p for p in sorted(pkgs, key=lambda p: p.name)}
    roots: Iterable[ResolvedPkg] = (p for p in pkgs if p.is_root)
    for root in roots:
        root_node = Node(root, make_name(root, nixpkgs))
        warnings = build_tree(indexed_pkgs, root_node, nixpkgs)
        print_tree(root_node)
        if warnings:
            print(''.join(warnings) + '\n')
