from typing import Dict, List

from mach_nix.data.providers import WheelDependencyProvider, SdistDependencyProvider, NixpkgsDependencyProvider
from mach_nix.data.nixpkgs import NixpkgsIndex
from mach_nix.generators import ExpressionGenerator
from mach_nix.resolver import ResolvedPkg


def unindent(text: str, remove: int):
    # removes indentation of text
    # also strips leading newlines
    return ''.join(map(lambda l: l[remove:], text.splitlines(keepends=True)))


class OverridesGenerator(ExpressionGenerator):

    def __init__(
            self,
            py_ver,
            nixpkgs: NixpkgsIndex,
            pypi_fetcher_commit,
            pypi_fetcher_sha256,
            disable_checks,
            *args,
            **kwargs):
        self.nixpkgs = nixpkgs
        self.disable_checks = disable_checks
        self.pypi_fetcher_commit = pypi_fetcher_commit
        self.pypi_fetcher_sha256 = pypi_fetcher_sha256
        self.py_ver_nix = py_ver.nix()
        super(OverridesGenerator, self).__init__(*args, **kwargs)

    def generate(self, reqs) -> str:
        pkgs = self.resolver.resolve(reqs)
        pkgs = dict(sorted(((p.name, p) for p in pkgs), key=lambda x: x[1].name))
        return self._gen_python_env(pkgs)

    def _gen_imports(self):
        out = f"""
            with builtins;
            let
              pypi_fetcher_src = builtins.fetchTarball {{
                name = "nix-pypi-fetcher";
                url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/{self.pypi_fetcher_commit}";
                # Hash obtained using `nix-prefetch-url --unpack <url>`
                sha256 = "{self.pypi_fetcher_sha256}";
              }};
              fetchPypi = (import pypi_fetcher_src).fetchPypi;
              fetchPypiWheel = (import pypi_fetcher_src).fetchPypiWheel;
              try_get = obj: name:
                if hasAttr name obj
                then obj."${{name}}"
                else [];
              is_py_module = pkg:
                isAttrs pkg && hasAttr "pythonModule" pkg;
              filter_deps = oldAttrs: inputs_type:
                filter (pkg: ! is_py_module pkg) (try_get oldAttrs inputs_type);
            """
        return unindent(out, 12)

    def _gen_build_inputs(self, build_inputs_local, build_inputs_nixpkgs) -> str:
        build_inputs_str = ' '.join(
            f"{b}" for b in sorted(build_inputs_local | build_inputs_nixpkgs))
        return build_inputs_str

    def _gen_prop_build_inputs(self, prop_build_inputs_local, prop_build_inputs_nixpkgs) -> str:
        prop_build_inputs_str = ' '.join(
            f"{b}" for b in sorted(prop_build_inputs_local | prop_build_inputs_nixpkgs))
        return prop_build_inputs_str

    def _gen_overrideAttrs(self, name, ver, circular_deps, nix_name, build_inputs_str, prop_build_inputs_str, keep_src=False):
        out = f"""
            {nix_name} = python-super.{nix_name}.overridePythonAttrs ( oldAttrs: {{
              pname = "{name}";
              version = "{ver}";"""
        if not keep_src:
            out += f"""
              src = fetchPypi "{name}" "{ver}";"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        if build_inputs_str:
            out += f"""
              buildInputs = with python-self; (filter_deps oldAttrs "buildInputs") ++ [ {build_inputs_str} ];"""
        if prop_build_inputs_str:
            out += f"""
              propagatedBuildInputs = with python-self; (filter_deps oldAttrs "propagatedBuildInputs") ++ [ {prop_build_inputs_str} ];"""
        if self.disable_checks:
            out += """
              doCheck = false;
              doInstallCheck = false;"""
        out += """
            });\n"""
        return unindent(out, 8)

    def _gen_builPythonPackage(self, name, ver, circular_deps, nix_name, build_inputs_str, prop_build_inputs_str):
        out = f"""
            {nix_name} = python-self.buildPythonPackage {{
              pname = "{name}";
              version = "{ver}";
              src = fetchPypi "{name}" "{ver}";"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        if build_inputs_str.strip():
            out += f"""
              buildInputs = with python-self; [ {build_inputs_str} ];"""
        if prop_build_inputs_str.strip():
            out += f"""
              propagatedBuildInputs = with python-self; [ {prop_build_inputs_str} ];"""
        if self.disable_checks:
            out += """
              doCheck = false;
              doInstallCheck = false;"""
        out += """
            };\n"""
        return unindent(out, 8)

    def _gen_wheel_buildPythonPackage(self, name, ver, circular_deps, prop_build_inputs_str, fname):
        manylinux = "manylinux1 ++ " if 'manylinux' in fname else ''

        # dontStrip added due to this bug - https://github.com/pypa/manylinux/issues/119
        out = f"""
            "{name}" = python-self.buildPythonPackage {{
              pname = "{name}";
              version = "{ver}";
              src = fetchPypiWheel "{name}" "{ver}" "{fname}";
              format = "wheel";
              doCheck = false;
              doInstallCheck = false;
              dontStrip = true;"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        if manylinux:
            out += f"""
              nativeBuildInputs = [ autoPatchelfHook ];
              autoPatchelfIgnoreNotFound = true;"""
        if prop_build_inputs_str.strip() or manylinux:
            out += f"""
              propagatedBuildInputs = with python-self; {manylinux}[ {prop_build_inputs_str} ];"""
        out += """
            };\n"""
        return unindent(out, 8)

    def _unify_nixpkgs_keys(self, name, main_key=None):
        other_names = set(
            p.nix_key for p in self.nixpkgs.get_all_candidates(name) if p.nix_key not in (name, main_key)
        )
        out = ''
        for key in sorted(other_names):
            out += f"""    {key} = python-self."{name}";\n"""
        return out

    def _gen_overrides(self, pkgs: Dict[str, ResolvedPkg], overlay_keys, pkgs_names: str):
        out = f"""
            select_pkgs = ps: with ps; [
              {pkgs_names.strip()} 
            ];
            overrides = manylinux1: autoPatchelfHook: python-self: python-super: rec {{
          """
        out = unindent(out, 10)
        for pkg in pkgs.values():
            if pkg.name not in overlay_keys:
                continue
            overlays_required = True
            # get correct build input names
            _build_inputs = [self._get_ref_name(b, pkgs[b].ver) for b in pkg.build_inputs]
            build_inputs_local = {b for b in _build_inputs if b in overlay_keys}
            build_inputs_nixpkgs = set(_build_inputs) - build_inputs_local
            # get correct propagated build input names
            _prop_build_inputs = [self._get_ref_name(b, pkgs[b].ver) for b in pkg.prop_build_inputs]
            prop_build_inputs_local = {b for b in _prop_build_inputs if b in overlay_keys}
            prop_build_inputs_nixpkgs = set(_prop_build_inputs) - prop_build_inputs_local
            # convert build inputs to string
            build_inputs_str = self._gen_build_inputs(build_inputs_local, build_inputs_nixpkgs, ).strip()
            # convert prop build inputs to string
            prop_build_inputs_str = self._gen_prop_build_inputs(prop_build_inputs_local,
                                                                prop_build_inputs_nixpkgs).strip()

            if pkg.provider_info.provider == SdistDependencyProvider.name:
                # generate package overlays either via `overrideAttrs` if package already exists in nixpkgs,
                # or by creating it from scratch using `buildPythonPackage`
                nix_name = self._get_ref_name(pkg.name, pkg.ver)
                if self.nixpkgs.exists(pkg.name):
                    out += self._gen_overrideAttrs(pkg.name, pkg.ver, pkg.removed_circular_deps, nix_name, build_inputs_str, prop_build_inputs_str)
                    out += self._unify_nixpkgs_keys(pkg.name, main_key=nix_name)
                else:
                    out += self._gen_builPythonPackage(pkg.name, pkg.ver, pkg.removed_circular_deps, nix_name, build_inputs_str, prop_build_inputs_str)
            elif pkg.provider_info.provider == WheelDependencyProvider.name:
                out += self._gen_wheel_buildPythonPackage(pkg.name, pkg.ver, pkg.removed_circular_deps, prop_build_inputs_str,
                                                          pkg.provider_info.wheel_fname)
                if self.nixpkgs.exists(pkg.name):
                    out += self._unify_nixpkgs_keys(pkg.name)
            elif pkg.provider_info.provider == NixpkgsDependencyProvider.name:
                nix_name = self.nixpkgs.find_best_nixpkgs_candidate(pkg.name, pkg.ver)
                out += self._gen_overrideAttrs(
                    pkg.name, pkg.ver, pkg.removed_circular_deps, nix_name, build_inputs_str, prop_build_inputs_str,
                    keep_src=True)
                out += self._unify_nixpkgs_keys(pkg.name, main_key=nix_name)
        end_overlay_section = f"""
                }};
          """
        return out + unindent(end_overlay_section, 14)

    def _get_ref_name(self, name, ver) -> str:
        if self.nixpkgs.exists(name):
            return self.nixpkgs.find_best_nixpkgs_candidate(name, ver)
        return name

    def _gen_python_env(self, pkgs: Dict[str, ResolvedPkg]):
        pkg_names = "".join(
            (f"{self._get_ref_name(name, pkgs[name].ver)}\n{' ' * 14}" for (name, pkg) in pkgs.items() if pkg.is_root))
        overlay_keys = {p.name for p in pkgs.values()}
        out = self._gen_imports() + self._gen_overrides(pkgs, overlay_keys, pkg_names)
        python_with_packages = f"""
            in
            {{ inherit overrides select_pkgs; }}
            """
        return out + unindent(python_with_packages, 12)
