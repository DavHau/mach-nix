let
  pkgs = import <nixpkgs> { config = { allowUnfree = true; }; overlays = []; };
  commit = "1434cc0ee2da462f0c719d3a4c0ab4c87d0931e7";
  fetchPypiSrc = builtins.fetchTarball {
   name = "nix-pypi-fetcher";
   url = "https://github.com/DavHau/nix-pypi-fetcher/archive/${commit}.tar.gz";
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
        for f in $(ls ${python_env}/bin); do
          sed -i "s|${python_env}|$out|g" $out/bin/$f
          sed -i "/NIX_PYTHONPATH/a export PYTHONPATH=$out\/lib\/python${major}.${minor}" $out/bin/$f
        done
      '';
  };

  mkPy = python:
    let
      python_env = python.withPackages (ps: with ps; [
        # base requirements
        setuptools
        pkgconfig
      ]);
    in
      patchDistutils python_env;

in
let
  py27 = mkPy pkgs.python27;
  py35 = mkPy pkgs.python35;
  py36 = mkPy pkgs.python36;
  py37 = mkPy pkgs.python37;
  py38 = mkPy pkgs.python38;
  # This is how pip invokes setup.py. We do this manually instead of using pip to increase performance by ~40%
  setuptools_shim = ''
    import sys, setuptools, tokenize; sys.argv[0] = 'setup.py'; __file__='setup.py';
    f=getattr(tokenize, 'open', open)(__file__);
    code=f.read().replace('\r\n', '\n');
    f.close();
    exec(compile(code, __file__, 'exec'))
  '';
  script = ''
    mkdir $out
    echo "python27"
    out_file=$out/python27.json ${py27}/bin/python -c "${setuptools_shim}" install &> $out/python27.log || true
    echo "python35"
    out_file=$out/python35.json ${py35}/bin/python -c "${setuptools_shim}" install &> $out/python35.log || true
    echo "python36"
    out_file=$out/python36.json ${py36}/bin/python -c "${setuptools_shim}" install &> $out/python36.log || true
    echo "python37"
    out_file=$out/python37.json ${py37}/bin/python -c "${setuptools_shim}" install &> $out/python37.log || true
    echo "python38"
    out_file=$out/python38.json ${py38}/bin/python -c "${setuptools_shim}" install &> $out/python38.log || true
  '';
  script_single = py: ''
    mkdir $out
    echo "extracting dependencies"
    out_file=$out/python.json ${py}/bin/python -c "${setuptools_shim}" install &> $out/python.log || true
  '';
  base_derivation = with pkgs; {
    buildInputs = [ unzip pkg-config pipenv ];
    phases = ["unpackPhase" "installPhase"];
    # Tells our modified python builtins to dump setup attributes instead of doing an actual installation
    dump_setup_attrs = "y";
    PYTHONIOENCODING = "utf8";  # My gut feeling is that encoding issues might decrease by this
    LANG = "C.utf8";
    installPhase = script;
  };
in
with pkgs;
rec {
  inherit py27 py35 py36 py37 py38;
  all = { inherit py27 py35 py36 py37 py38; };
  inherit machnix_source;
  example = extractor {pkg = "requests"; version = "2.22.0";};
  extract_from_src = {py, src}:
    stdenv.mkDerivation ( base_derivation // {
      inherit src;
      name = "package-requirements";
      installPhase = script_single (mkPy py);
    });
  extractor = {pkg, version}:
    stdenv.mkDerivation ({
      name = "${pkg}-${version}-requirements";
      src = fetchPypi pkg version;
    } // base_derivation);
  extractor-fast = {pkg, version, url, sha256}:
    stdenv.mkDerivation ({
      name = "${pkg}-${version}-requirements";
      src = pkgs.fetchurl {
        inherit url sha256;
      };
    } // base_derivation);
}
