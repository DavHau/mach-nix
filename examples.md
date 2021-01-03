This page contains basic and advanced examples for using mach-nix inside a nix expression


<!--ts-->
 * [Import mach-nix](#import-mach-nix)
 * [mkPython / mkPythonShell](#mkpython--mkpythonshell)
    * [From a list of requirements](#from-a-list-of-requirements)
    * [Include extra packages.](#include-extra-packages)
 * [buildPythonPackage / buildPythonApplication](#buildpythonpackage--buildpythonapplication)
    * [Build python package from its source code](#build-python-package-from-its-source-code)
    * [buildPythonPackage from GitHub](#buildpythonpackage-from-github)
    * [buildPythonPackage from GitHub with extras](#buildpythonpackage-from-github-with-extras)
    * [buildPythonPackage from GitHub and add requirements](#buildpythonpackage-from-github-and-add-requirements)
    * [buildPythonPackage from GitHub (reproducible source)](#buildpythonpackage-from-github-reproducible-source)
    * [buildPythonPackage from GitHub (manual requirements)](#buildpythonpackage-from-github-manual-requirements)
  * [Simplified overrides ('_' argument)](#simplified-overrides-_-argument)
     * [General usage](#general-usage)
     * [Example: add missing build inputs](#example-add-missing-build-inputs)
  * [Overrides (overrides_pre / overrides_post)](#overrides-overrides_pre--overrides_post)
     * [Include poetry2nix overrides](#include-poetry2nix-overrides)
  * [Tensorflow](#tensorflow)
     * [Tensorflow with SSE/AVX/FMA support](#tensorflow-with-sseavxfma-support)
     * [Tensorflow via wheel (newer versions, quicker builds)](#tensorflow-via-wheel-newer-versions-quicker-builds)
  * [PyTorch](#pytorch)
     * [Recent PyTorch with nixpkgs dependencies, and custom python](#recent-pytorch-with-nixpkgs-dependencies-and-custom-python)
  * [Jupyter](#jupyter)
     * [...using jupyterWith   mach-nix](#using-jupyterwith--mach-nix)
     * [...using mach-nix only](#using-mach-nix-only)
  * [Docker](#docker)
     * [JupyterLab Docker Image](#jupyterlab-docker-image)
  * [R and Python](#r-and-python)
  * [Raspberry PI / aarch64 SD Image](#raspberry-pi--aarch64-sd-image)

<!-- Added by: grmpf, at: Mon 23 Nov 2020 03:10:05 PM +07 -->

<!--te-->

### Import mach-nix
every mach-nix expression should begin like this:
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/3.1.1";
  }) {
    # optionally bring your own nixpkgs
    # pkgs = import <nixpkgs> {};

    # optionally specify the python version
    # python = "python38";

    # optionally update pypi data revision from https://github.com/DavHau/pypi-deps-db
    # pypiDataRev = "some_revision";
    # pypiDataSha256 = "some_sha256";
  };
in
...
```

### mkPython / mkPythonShell
#### From a list of requirements
```nix
mach-nix.mkPython {  # replace with mkPythonShell if shell is wanted
  requirements = builtins.readFile ./requirements.txt;
}
```

#### Include extra packages.
`packagesExtra` accepts:
  - python packages built via `mach-nix.buildPythonPackage`.
  - R Packages from `nixpkgs.rPackages` (see R example further down)
  - python package source trees as paths or derivations
  - URLs pointing to a tarball archives containing a python source tree
```nix
...
mach-nix.mkPython {
  requirements = builtins.readFile ./requirements.txt;
  packagesExtra = [
    "https://github.com/psf/requests/tarball/2a7832b5b06d"   # from tarball url
    ./some/local/project                                     # from local path
    mach-nix.buildPythonPackage { ... };                     # from package
  ];
}
```
Alternatively, if requirements are not needed, packagesExtra can be passed directly to mkPython
```nix
...
mach-nix.mkPython [
  "https://github.com/psf/requests/tarball/2a7832b5b06d"   # from tarball url
  ./some/local/project                                     # from local path
  mach-nix.buildPythonPackage { ... };                     # from package
]
```

### buildPythonPackage / buildPythonApplication
These functions can be used to manually build individual python modules or applications. Those can either be used directly, or fed as `packagesExtra` of `mkPython`.
Whenever `requirements` are not explicitly specified, they will be extracted automatically from the packages setup.py/setup.cfg. The same goes for the `name` and `version`.
#### Build python package from its source code
```nix
...
mach-nix.buildPythonPackage /python-project-path
```

#### buildPythonPackage from GitHub
```nix
...
mach-nix.buildPythonPackage "https://github.com/psf/requests/tarball/2a7832b5b06d"
```

#### buildPythonPackage from GitHub with extras
```nix
...
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  extras = "socks";
}
```

#### buildPythonPackage from GitHub and add requirements
Use `requirementsExtra` in case the auto detected requirements are incomplete
```nix
...
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  requirementsExtra = "pytest";
}
```

#### buildPythonPackage from GitHub (reproducible source)
```nix
...
mach-nix.buildPythonPackage {
  src = builtins.fetchGit{
    url = "https://github.com/user/projectname";
    ref = "master";
    # rev = "put_commit_hash_here";
  };
}
```

#### buildPythonPackage from GitHub (manual requirements)
Use this if automatic requirements extraction doesn't work at all.
```nix
...
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  requirements = ''
    # list of requirements
  '';
}
```


## Simplified overrides ('_' argument)
### General usage
```
with mach-nix.nixpkgs;
mach-nix.mkPython {

  requirements = "some requirements";

  _.{package}.buildInputs = [...];             # replace buildInputs
  _.{package}.buildInputs.add = [...];         # add buildInputs
  _.{package}.buildInputs.mod =                # modify buildInputs
      oldInputs: filter (inp: ...) oldInputs; 

  _.{package}.patches = [...];                 # replace patches
  _.{package}.patches.add = [...];             # add patches
  ...
}
```
### Example: add missing build inputs
For example the package web2ldap depends on another python package `ldap0` which fails to build because of missing dependencies.
```nix
...
with mach-nix.nixpkgs;
mach-nix.mkPython {

  requirements = "web2ldap";

  # add missing dependencies to ldap0
  _.ldap0.buildInputs.add = [ openldap.dev cyrus_sasl.dev ];
}

```

## Overrides (overrides_pre / overrides_post)
### Include poetry2nix overrides
`imagecodecs` is available via wheel, but if one wants to build it from source, dependencies will be missing since there is no nixpkgs candidate available.
poetry2nix luckily maintains overrides for this package. They can be included into the mach-nix build like this.
```nix
...
mach-nix.mkPython rec {

  requirements = ''
    # bunch of other requirements
    imagecodecs
  '';

  providers = {
    _default = "sdist";
  };

  # Import overrides from poetry2nix
  # Caution! Use poetry2nix overrides only in `overrides_post`, not `overrides_pre`.
  overridesPost = [
    (
      import (builtins.fetchurl {
        url = "https://raw.githubusercontent.com/nix-community/poetry2nix/1cfaa4084d651d73af137866622e3d0699851008/overrides.nix";
      }) { pkgs = mach-nix.nixpkgs; }
    )
  ];
}
```

## Tensorflow

### Tensorflow with SSE/AVX/FMA support
Tensorflow from pypi does not provide any hardware optimization support. To get a SSE/AVX/FMA enabled version, set the provider for tensorflow to `nixpkgs`.

```nix
...
mach-nix.mkPython {

  requirements = ''
    # bunch of other requirements
    tensorflow
  '';

  # force tensorflow to be taken from nixpkgs
  providers.tensorflow = "nixpkgs"; 
}
```
This only works if the restrictions in `requirements.txt` allow for the tensorflow version from nixpkgs.

### Tensorflow via wheel (newer versions, quicker builds)
Install recent tensorflow via wheel
```nix
...
mach-nix.mkPython {

  requirements = ''
    # bunch of other requirements
    tensorflow == 2.2.0rc4
  '';
  # no need to specify provider settings since wheel is the default anyways
}

```
## PyTorch

### Recent PyTorch with nixpkgs dependencies, and custom python
Recent pytorch version, Build dependencies from source
```nix
...
mach-nix.mkPython rec {

  requirements = ''
    # bunch of other requirements
    torch == 1.5.0
  '';

  providers = {
    # disallow wheels by default
    _default = "nixpkgs,sdist";
    # allow wheels only for torch
    torch = "wheel";
  };
}
```

## Jupyter 

### ...using jupyterWith + mach-nix
In this example, mach-nix is used to resolve our python dependencies and provide them to [jupyterWith](https://github.com/tweag/jupyterWith) which is a Nix-based framework for the definition of declarative and reproducible Jupyter environments. 
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/3.1.1";  # update this version
  }) {
    python = "python37";
  };

  # load your requirements
  machNix = mach-nix.mkPython rec {
    requirements = builtins.readFile ./requirements.txt;
  };

  jupyter = import (builtins.fetchGit {
    url = https://github.com/tweag/jupyterWith;
    ref = "master";
    #rev = "some_revision";
  }) {};

  iPython = jupyter.kernels.iPythonWith {
    name = "mach-nix-jupyter";
    python3 = machNix.python;
    packages = machNix.python.pkgs.selectPkgs;
  };

  jupyterEnvironment = jupyter.jupyterlabWith {
    kernels = [ iPython ];
  };
in
  jupyterEnvironment.env
```

### ...using mach-nix only
```nix
...
let
  nixPkgs = import mach-nix.nixpkgs.path {config= { allowUnfree = true; }; overlays =  [ ]; } ;
  pyEnv = mach-nix.mkPython rec {

    requirements =  ''
        jupyterlab
        geopandas
        pyproj
        pygeos
        shapely>=1.7.0
      '';

    providers.shapely = "sdist,nixpkgs";
  };
in
nixPkgs.mkShell rec {

  buildInputs = [
    pyEnv
  ] ;

  shellHook = ''
    jupyter lab --notebook-dir=~/
  '';
}
```

## Docker
Docker images can be built by using `mkDockerImage` instead of `mkPython`. It accepts the same arguments.
### JupyterLab Docker Image
Assuming the following expression under `./jupyter-docker.nix`:
```nix
...
let
  image = mach-nix.mkDockerImage {
    requirements =  ''
      jupyterlab
      # add more packages here
    '';
  };
in
# The following overrides a call to nixpkgs.dockerTools.buildImage.
# Find more buildImage examples here: https://github.com/NixOS/nixpkgs/blob/master/pkgs/build-support/docker/examples.nix
image.override (oldAttrs: {
  name = "jupyterlab";
  config.Cmd = [ "jupyter" "lab" "--notebook-dir=/mnt" "--allow-root" "--ip=0.0.0.0" ];
})
```
Execute the build like:
```
nix-build ./jupyter-docker.nix -o ./docker-image
```
Afterwards, load the docker image:
```
docker load < ./docker-image
```
Start the jupyterlab container:
```
docker run --rm -it -p 8888:8888 -v $HOME:/mnt jupyterlab
```

## R and Python
The following is an example for a Python environment mixed with R packages.  
R packages can be added via `packagesExtra`.  
If mach-nix finds R packages inside `packagesExtra`, it will automatically include `rpy2` and add the selected R packages to its buildInputs.
To get a list of available R packages, execute: `echo "builtins.attrNames(import <nixpkgs> {}).rPackages" | nix repl`

```nix
...
mach-nix.mkPython {
  requirements =  ''
    # some python requirements
  '';
  packagesExtra = with mach-nix.rPackages; [
    data_table
  ];
}
```


## Raspberry PI / aarch64 SD Image
This example builds an aarch64 sd image via emulator. For this to work, binfmt support for aarch64 must be installed first. (On NixOS simply set `boot.binfmt.emulatedSystems = [ "aarch64-linux" ]`)  
For the SD-image, create a configuration.nix file which adds the mach-nix tool and some default python packages to the system environment.  
**configuration.nix**:
```nix
{ config, lib, pkgs, ... }:

let
  machNix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/put_version_here";
  }) { inherit pkgs; };

  defaultPythonEnv = machNix.mkPython {
    requirements = ''
      cryptography
    '';
    providers.cffi = "nixpkgs";
  };

in {
  imports = [
    <nixpkgs/nixos/modules/installer/cd-dvd/sd-image-aarch64.nix>
  ];
  environment.systemPackages = [ defaultPythonEnv machNix.mach-nix ];
  sdImage.compressImage = false;  # speeds up the build
}
```
with the following **default.nix**:
```nix
with import <nixpkgs/nixos> {
  system = "aarch64-linux";
};
config.system.build.sdImage
```
Execute:
```bash
NIXOS_CONFIG=$PWD/configuration.nix nix build -f default.nix
```
Or to select a specific channel:
```bash
NIXOS_CONFIG=$PWD/configuration.nix nix build -f default.nix -I nixpkgs=channel:nixos-20.03
```
