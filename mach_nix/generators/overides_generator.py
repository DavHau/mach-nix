import json
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
            {{ pkgs, python, ... }}:
            with builtins;
            with pkgs.lib;
            let
              pypi_fetcher_src = builtins.fetchTarball {{
                name = "nix-pypi-fetcher";
                url = "https://github.com/DavHau/nix-pypi-fetcher/tarball/{self.pypi_fetcher_commit}";
                # Hash obtained using `nix-prefetch-url --unpack <url>`
                sha256 = "{self.pypi_fetcher_sha256}";
              }};
              pypiFetcher = import pypi_fetcher_src {{ inherit pkgs; }};
              fetchPypi = pypiFetcher.fetchPypi;
              fetchPypiWheel = pypiFetcher.fetchPypiWheel;
              is_py_module = pkg:
                isAttrs pkg && hasAttr "pythonModule" pkg;
              normalizeName = name: (replaceStrings ["_"] ["-"] (toLower name));
              replace_deps = oldAttrs: inputs_type: self:
                map (pypkg:
                  let
                    pname = normalizeName (get_pname pypkg);
                  in
                    if self ? "${{pname}}" && pypkg != self."${{pname}}" then
                      trace "Updated inherited nixpkgs dep ${{pname}} from ${{pypkg.version}} to ${{self."${{pname}}".version}}"
                      self."${{pname}}"
                    else
                      pypkg
                ) (oldAttrs."${{inputs_type}}" or []);
              override = pkg:
                if hasAttr "overridePythonAttrs" pkg then
                    pkg.overridePythonAttrs
                else
                    pkg.overrideAttrs;
              nameMap = {{
                pytorch = "torch";
              }};
              get_pname = pkg:
                let
                  res = tryEval (
                    if pkg ? src.pname then
                      pkg.src.pname
                    else if pkg ? pname then
                      let pname = pkg.pname; in
                        if nameMap ? "${{pname}}" then nameMap."${{pname}}" else pname
                      else ""
                  );
                in
                  toString res.value;
              get_passthru = pypi_name: nix_name:
                # if pypi_name is in nixpkgs, we must pick it, otherwise risk infinite recursion.
                let
                  python_pkgs = python.pkgs;
                  pname = if hasAttr "${{pypi_name}}" python_pkgs then pypi_name else nix_name;
                in
                  if hasAttr "${{pname}}" python_pkgs then 
                    let result = (tryEval 
                      (if isNull python_pkgs."${{pname}}" then
                        {{}}
                      else
                        python_pkgs."${{pname}}".passthru)); 
                    in
                      if result.success then result.value else {{}}
                  else {{}};
              tests_on_off = enabled: pySelf: pySuper:
                let
                  mod = {{
                    doCheck = enabled;
                    doInstallCheck = enabled;
                  }};
                in
                {{
                  buildPythonPackage = args: pySuper.buildPythonPackage ( args // {{
                    doCheck = enabled;
                    doInstallCheck = enabled;
                  }} );
                  buildPythonApplication = args: pySuper.buildPythonPackage ( args // {{
                    doCheck = enabled;
                    doInstallCheck = enabled;
                  }} );
                }};
              pname_passthru_override = pySelf: pySuper: {{
                fetchPypi = args: (pySuper.fetchPypi args).overrideAttrs (oa: {{
                  passthru = {{ inherit (args) pname; }};
                }});
              }};
              mergeOverrides = with pkgs.lib; foldl composeExtensions (self: super: {{}});
              merge_with_overr = enabled: overr:
                mergeOverrides [(tests_on_off enabled) pname_passthru_override overr];

            """
        return unindent(out, 12)

    def _gen_build_inputs(self, build_inputs_local, build_inputs_nixpkgs) -> str:
        name = lambda n: f'python-self."{n}"' if '.' in n else n
        build_inputs_str = ' '.join(
            name(b) for b in sorted(build_inputs_local | build_inputs_nixpkgs))
        return build_inputs_str

    def _gen_prop_build_inputs(self, prop_build_inputs_local, prop_build_inputs_nixpkgs) -> str:
        name = lambda n: f'python-self."{n}"' if '.' in n else n
        prop_build_inputs_str = ' '.join(
            name(b) for b in sorted(prop_build_inputs_local | prop_build_inputs_nixpkgs))
        return prop_build_inputs_str

    def _gen_overrideAttrs(
            self, name, ver, circular_deps, nix_name, provider, build_inputs_str, prop_build_inputs_str,
            keep_src=False):
        out = f"""
            "{name}" = override python-super.{nix_name} ( oldAttrs: {{
              pname = "{name}";
              version = "{ver}";
              passthru = (get_passthru "{name}" "{nix_name}") // {{ provider = "{provider}"; }};
              buildInputs = with python-self; (replace_deps oldAttrs "buildInputs" self) ++ [ {build_inputs_str} ];
              propagatedBuildInputs = with python-self; (replace_deps oldAttrs "propagatedBuildInputs" self) ++ [ {prop_build_inputs_str} ];"""
        if not keep_src:
            out += f"""
              src = fetchPypi "{name}" "{ver}";"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        out += """
            });\n"""
        return unindent(out, 8)

    def _gen_builPythonPackage(self, name, ver, circular_deps, nix_name, build_inputs_str, prop_build_inputs_str):
        out = f"""
            "{name}" = python-self.buildPythonPackage {{
              pname = "{name}";
              version = "{ver}";
              src = fetchPypi "{name}" "{ver}";
              passthru = (get_passthru "{name}" "{nix_name}") // {{ provider = "sdist"; }};"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        if build_inputs_str.strip():
            out += f"""
              buildInputs = with python-self; [ {build_inputs_str} ];"""
        if prop_build_inputs_str.strip():
            out += f"""
              propagatedBuildInputs = with python-self; [ {prop_build_inputs_str} ];"""
        out += """
            };\n"""
        return unindent(out, 8)

    def _gen_wheel_buildPythonPackage(self, name, ver, circular_deps, nix_name, prop_build_inputs_str, fname):
        manylinux = "manylinux1 ++ " if 'manylinux' in fname else ''

        # dontStrip added due to this bug - https://github.com/pypa/manylinux/issues/119
        out = f"""
            "{name}" = python-self.buildPythonPackage {{
              pname = "{name}";
              version = "{ver}";
              src = fetchPypiWheel "{name}" "{ver}" "{fname}";
              format = "wheel";
              dontStrip = true;
              passthru = (get_passthru "{name}" "{nix_name}") // {{ provider = "wheel"; }};"""
        if circular_deps:
            out += f"""
              pipInstallFlags = "--no-dependencies";"""
        if manylinux:
            out += f"""
              nativeBuildInputs = [ autoPatchelfHook ];
              autoPatchelfIgnoreMissingDeps = true;"""
        if prop_build_inputs_str.strip() or manylinux:
            out += f"""
              propagatedBuildInputs = with python-self; {manylinux}[ {prop_build_inputs_str} ];"""
        out += """
            };\n"""
        return unindent(out, 8)

    def _gen_overrides(self, pkgs: Dict[str, ResolvedPkg], overrides_keys):
        pkg_names_str = "".join(
            (f"ps.\"{name}\"\n{' ' * 14}"
             for (name, pkg) in pkgs.items() if pkg.is_root))
        check = json.dumps(not self.disable_checks)
        out = f"""
            select_pkgs = ps: [
              {pkg_names_str.strip()}
            ];
            overrides = manylinux1: autoPatchelfHook: merge_with_overr {check} (python-self: python-super: let self = {{
          """
        out = unindent(out, 10)
        for pkg in pkgs.values():
            if pkg.name not in overrides_keys:
                continue
            overlays_required = True
            build_inputs_local = {b for b in pkg.build_inputs if b in overrides_keys}
            build_inputs_nixpkgs = set(pkg.build_inputs) - build_inputs_local
            prop_build_inputs_local = {b for b in pkg.prop_build_inputs if b in overrides_keys}
            prop_build_inputs_nixpkgs = set(pkg.prop_build_inputs) - prop_build_inputs_local
            # convert build inputs to string
            build_inputs_str = self._gen_build_inputs(build_inputs_local, build_inputs_nixpkgs, ).strip()
            # convert prop build inputs to string
            prop_build_inputs_str = self._gen_prop_build_inputs(
                prop_build_inputs_local, prop_build_inputs_nixpkgs).strip()

            # SDIST
            if isinstance(pkg.provider_info.provider, SdistDependencyProvider):
                # generate package overlays either via `overrideAttrs` if package already exists in nixpkgs,
                # or by creating it from scratch using `buildPythonPackage`
                nix_name = self._get_ref_name(pkg.name, pkg.ver)
                if self.nixpkgs.exists(pkg.name):
                    out += self._gen_overrideAttrs(
                        pkg.name,
                        pkg.provider_info.provider.deviated_version(pkg.name, pkg.ver),
                        pkg.removed_circular_deps,
                        nix_name,
                        'sdist',
                        build_inputs_str,
                        prop_build_inputs_str)
                else:
                    out += self._gen_builPythonPackage(
                        pkg.name,
                        pkg.provider_info.provider.deviated_version(pkg.name, pkg.ver),
                        pkg.removed_circular_deps,
                        nix_name,
                        build_inputs_str,
                        prop_build_inputs_str)
            # WHEEL
            elif isinstance(pkg.provider_info.provider, WheelDependencyProvider):
                out += self._gen_wheel_buildPythonPackage(
                    pkg.name,
                    pkg.provider_info.provider.deviated_version(pkg.name, pkg.ver),
                    pkg.removed_circular_deps,
                    self._get_ref_name(pkg.name, pkg.ver),
                    prop_build_inputs_str,
                    pkg.provider_info.wheel_fname)
            # NIXPKGS
            elif isinstance(pkg.provider_info.provider, NixpkgsDependencyProvider):
                nix_name = self.nixpkgs.find_best_nixpkgs_candidate(pkg.name, pkg.ver)
                out += self._gen_overrideAttrs(
                    pkg.name,
                    pkg.ver,
                    pkg.removed_circular_deps,
                    nix_name,
                    'nixpkgs',
                    build_inputs_str,
                    prop_build_inputs_str,
                    keep_src=True)
        end_overlay_section = f"""
                }}; in self);
          """
        return out + unindent(end_overlay_section, 14)

    def _get_ref_name(self, name, ver) -> str:
        if self.nixpkgs.exists(name):
            return self.nixpkgs.find_best_nixpkgs_candidate(name, ver)
        return name

    def _gen_python_env(self, pkgs: Dict[str, ResolvedPkg]):
        overrides_keys = {p.name for p in pkgs.values()}
        out = self._gen_imports() + self._gen_overrides(pkgs, overrides_keys)
        python_with_packages = f"""
            in
            {{ inherit overrides select_pkgs; }}
            """
        return out + unindent(python_with_packages, 12)
