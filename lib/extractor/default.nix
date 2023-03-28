{
  pkgs ? import <nixpkgs> { config = { allowUnfree = true; };},
  lib ? pkgs.lib,
  pythonInterpreters ? pkgs.useInterpreters or (with pkgs; [
    python27
    python38
    python39
    python310
    python311
  ]),
  ...
}:
with builtins;
with lib;
let
  commit = "1434cc0ee2da462f0c719d3a4c0ab4c87d0931e7";
  fetchPypiSrc = builtins.fetchTarball {
   name = "nix-pypi-fetcher-2";
   url = "https://github.com/DavHau/nix-pypi-fetcher-2/archive/${commit}.tar.gz";
   # Hash obtained using `nix-prefetch-url --unpack <url>`
   sha256 = "080l189zzwrv75jgr7agvs4hjv4i613j86d4qky154fw5ncp0mnp";
  };
  fetchPypi = import (fetchPypiSrc);
  patchDistutils = python_env:
    with builtins;
    let
      verSplit = split "[\.]" python_env.python.version;
      major = elemAt verSplit 0;
      minor = elemAt verSplit 2;
      lib_dir = "$out/lib/python${major}.${minor}";
      site_pkgs_dir = "${lib_dir}/site-packages";
    in
    pkgs.symlinkJoin {
      name = "${python_env.name}-patched";
      paths = [ python_env ];
      buildInputs = [
        # prefer binary wrapper - but if that's not available (e.g. nixos 21.05)
        # use the regular shell script wrapper
        pkgs.makeBinaryWrapper or pkgs.makeWrapper
      ];
      postBuild = ''
        ### Distutils
        # symlinks to files
        mkdir ${lib_dir}/distutils_tmp
        cp -a ${lib_dir}/distutils/* ${lib_dir}/distutils_tmp/
        rm ${lib_dir}/distutils
        mv ${lib_dir}/distutils_tmp ${lib_dir}/distutils
        # patch distutils/core.py
        patch ${lib_dir}/distutils/core.py ${./distutils.patch}
        # remove .pyc files

        if [ ${major} = 2 ]; then
          rm ${lib_dir}/distutils/core.pyc
        else
          chmod +w ${lib_dir}/distutils/__pycache__/
          rm ${lib_dir}/distutils/__pycache__/core.*
        fi


        ### Setuptools
        # symlinks to files
        mkdir ${site_pkgs_dir}/setuptools_tmp
        cp -a ${site_pkgs_dir}/setuptools/* ${site_pkgs_dir}/setuptools_tmp/
        rm ${site_pkgs_dir}/setuptools
        mv ${site_pkgs_dir}/setuptools_tmp ${site_pkgs_dir}/setuptools
        # patch setuptools/__init__.py
        echo ${site_pkgs_dir}/setuptools/__init__.py
        patch ${site_pkgs_dir}/setuptools/__init__.py ${./setuptools.patch}
        # remove .pyc files
        if [ ${major} = 2 ]; then
          rm ${site_pkgs_dir}/setuptools/__init__.pyc
        else
          chmod +w ${site_pkgs_dir}/setuptools/__pycache__
          rm ${site_pkgs_dir}/setuptools/__pycache__/__init__.*
        fi


        # fix executables
        shopt -s nullglob
        for f in ${python_env}/bin/*; do
          f=$(basename "$f")
          # wrap it once more, set PYTHONPATH, ignoring NIXPYTHON_PATH and NIX_PYTHONEXECUTABLE
          rm "$out/bin/$f" # remove the existing symlink
          makeWrapper "${python_env}/bin/$f" "$out/bin/$f" \
              --set PYTHONPATH "$out/lib/python${major}.${minor}"
        done
      '';
  };

  mkPy = python:
    let
      python_env = python.withPackages (ps: with ps; [
        # base requirements
        setuptools
      ]);
    in
      patchDistutils python_env;

  # This is how pip invokes setup.py. We do this manually instead of using pip to increase performance by ~40%
  setuptools_shim = ''
    import sys, setuptools, tokenize, os; sys.argv[0] = 'setup.py'; __file__='setup.py';
    f=getattr(tokenize, 'open', open)(__file__);
    code=f.read().replace('\r\n', '\n');
    f.close();
    exec(compile(code, __file__, 'exec'))
  '';
  # note on SETUPTOOLS_USE_DISTUTILS=stdlib: Restore old setuptools behaviour (since
  # https://github.com/pypa/setuptools/commit/b6fcbbd00cb6d5607c9272dec452a50457bdb292),
  # to keep it working with mach-nix.
  script = pyVersions: ''
    mkdir $out
    ${concatStringsSep "\n" (forEach pythonInterpreters (interpreter:
      let
        py = mkPy interpreter;
        verSplit = splitString "." interpreter.version;
        major = elemAt verSplit 0;
        minor = elemAt verSplit 1;
        v = "${major}${minor}";
      # only use selected interpreters
      in optionalString (pyVersions == [] || elem v pyVersions) ''
        echo "extracting metadata for python${v}"
        SETUPTOOLS_USE_DISTUTILS=stdlib out_file=$out/python${v}.json ${py}/bin/python -c "${setuptools_shim}" install &> $out/python${v}.log || true
      ''
    ))}
  '';
  script_single = py: ''
    chmod +x setup.py || true
    mkdir $out
    echo "extracting dependencies"
    SETUPTOOLS_USE_DISTUTILS=stdlib out_file=$out/python.json ${py}/bin/python -c "${setuptools_shim}" install &> $out/python.log || true
  '';
  base_derivation = pyVersions: with pkgs; {
    buildInputs = [ unzip pkg-config ];
    phases = ["unpackPhase" "installPhase"];
    # Tells our modified python builtins to dump setup attributes instead of doing an actual installation
    dump_setup_attrs = "y";
    PYTHONIOENCODING = "utf8";  # My gut feeling is that encoding issues might decrease by this
    LANG = "C.utf8";
    installPhase = script pyVersions;
  };

  sanitizeDerivationName = string: lib.pipe string [
    # Get rid of string context. This is safe under the assumption that the
    # resulting string is only used as a derivation name
    unsafeDiscardStringContext
    # Strip all leading "."
    (x: elemAt (match "\\.*(.*)" x) 0)
    # Split out all invalid characters
    # https://github.com/NixOS/nix/blob/2.3.2/src/libstore/store-api.cc#L85-L112
    # https://github.com/NixOS/nix/blob/2242be83c61788b9c0736a92bb0b5c7bbfc40803/nix-rust/src/store/path.rs#L100-L125
    (split "[^[:alnum:]+._?=-]+")
    # Replace invalid character ranges with a "-"
    (concatMapStrings (s: if lib.isList s then "-" else s))
    # Limit to 211 characters (minus 4 chars for ".drv")
    (x: substring (lib.max (stringLength x - 207) 0) (-1) x)
    # If the result is empty, replace it with "unknown"
    (x: if stringLength x == 0 then "unknown" else x)
  ];
in
with pkgs;
rec {
  inherit machnix_source mkPy pythonInterpreters;
  example = extractor {pkg = "requests"; version = "2.22.0";};
  extract_from_src = {py, src}:
    let
      py' = if isString py then pkgs."${py}" else py;
    in
    stdenv.mkDerivation ( (base_derivation []) // {
      inherit src;
      name = "package-requirements";
      installPhase = script_single (mkPy py');
    });
  extractor = {pkg, version, ...}:
    stdenv.mkDerivation ({
      name = "${pkg}-${version}-requirements";
      src = fetchPypi pkg version;
    } // (base_derivation []));
  extractor-fast = {pkg, version, url, sha256, pyVersions ? [], ...}:
    stdenv.mkDerivation ( rec {
      name = sanitizeDerivationName "${pkg}-${version}-requirements";
      src = (pkgs.fetchurl {
        inherit url sha256;
      }).overrideAttrs (_: {
        name = sanitizeDerivationName _.name;
      });
    } // (base_derivation pyVersions));
  make-drvs =
    let
      jobs = fromJSON (readFile (getEnv "EXTRACTOR_JOBS_JSON_FILE"));
      results = listToAttrs (map (job:
        nameValuePair
          "${job.pkg}#${job.version}"
          (extractor-fast job).drvPath
      ) jobs);
    in toJSON results;

}
