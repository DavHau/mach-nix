This page contains basic and advanced examples for using mach-nix inside a nix expression


<!--ts-->
 * [Import mach-nix](#import-mach-nix)
 * [mkPython / mkPythonShell](#mkpython--mkpythonshell)
    * [From a list of requirements](#from-a-list-of-requirements)
    * [Include packages from arbitrary sources.](#include-packages-from-arbitrary-sources)
 * [buildPythonPackage / buildPythonApplication](#buildpythonpackage--buildpythonapplication)
    * [Build python package from its source code](#build-python-package-from-its-source-code)
    * [buildPythonPackage from GitHub](#buildpythonpackage-from-github)
    * [buildPythonPackage from GitHub with extras](#buildpythonpackage-from-github-with-extras)
    * [buildPythonPackage from GitHub and add requirements](#buildpythonpackage-from-github-and-add-requirements)
    * [buildPythonPackage from GitHub (explicit source)](#buildpythonpackage-from-github-explicit-source)
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
  * [JupyterLab](#jupyterlab)
     * [Starting point for a geospatial environment](#starting-point-for-a-geospatial-environment)
  * [Docker](#docker)
     * [JupyterLab Docker Image](#jupyterlab-docker-image)

<!-- Added by: grmpf, at: Thu 08 Oct 2020 11:39:10 PM +07 -->

<!--te-->

### Import mach-nix
(every mach-nix expression should begin like this)
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/2.4.1";
  });
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

#### Include packages from arbitrary sources.
`extra_pkgs` accepts python packages built via `mach-nix.buildPythonPackage`. Alternatively, paths or URLs can be passed which are then automatically wrapped in a `mach-nix.buildPythonPackage` call.
```nix
mach-nix.mkPython {
  requirements = builtins.readFile ./requirements.txt;
  extra_pkgs = [
    "https://github.com/psf/requests/tarball/2a7832b5b06d"   # from tarball url
    ./some/local/project                                     # from local path
    mach-nix.buildPythonPackage { ... };                     # from package
  ];
}
```
Alternatively, if requirements are not needed, extra_pkgs can be passed directly to mkPython
```nix
mach-nix.mkPython [
  "https://github.com/psf/requests/tarball/2a7832b5b06d"   # from tarball url
  ./some/local/project                                     # from local path
  mach-nix.buildPythonPackage { ... };                     # from package
]
```

### buildPythonPackage / buildPythonApplication
These functions can be used to manually build individual python modules or applications. Those can either be used directly, or fed as `extra_pkgs` of `mkPython`.
Whenever `requirements` are not explicitly specified, they will be extracted automatically from the packages setup.py/setup.cfg. The same goes for the `name` and `version`.
#### Build python package from its source code
```nix
mach-nix.buildPythonPackage /python-project-path
```

#### buildPythonPackage from GitHub
```nix
mach-nix.buildPythonPackage "https://github.com/psf/requests/tarball/2a7832b5b06d"
```

#### buildPythonPackage from GitHub with extras
```nix
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  extras = "socks";
}
```

#### buildPythonPackage from GitHub and add requirements
Use `add_requirements` in case the auto detected requirements are imcomplete
```nix
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  add_requirements = "pytest";
}
```

#### buildPythonPackage from GitHub (explicit source)
```nix
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
with mach-nix.nixpkgs;
mach-nix.mkPython {

  requirements = "web2ldap";

  # add missing dependencies to ldap0
  _.ldap0.buildInputs.add = [ openldap.dev cyrus_sasl.dev ];
}

```

## Overrides (overrides_pre / overrides_post)
### Include poetry2nix overrides
I have a complex requirements.txt which includes `imagecodecs`. It is available via wheel, but I prefer to build everything from source. This package has complex build dependencies and is not available from nixpkgs. Luckily poetry2nix` overrides make it work.
```nix
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
  overrides_post = [
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
Tensorflow from pypi does not provide any hardware optimization support. To get a SSE/AVX/FMA enabled version, it just needs to be taken from `nixpkgs`.

I have a complex set of requirements including tensorflow. I'd like to have tensorflow with the usual nix features enabled like SSE/AVX/FMA which I cannot get from pypi. Therefore I must take tensorflow from nixpkgs. For everything else I keep the default, which means wheels are preferred. This allows for quicker installation of dependencies.
```nix
mach-nix.mkPython {

  requirements = ''
    # bunch of other requirements
    tensorflow
  '';

  providers = {
    # force tensorflow to be taken from nixpkgs
    tensorflow = "nixpkgs"; 
  };
}
```
This only works if the restrictions in `requirements.txt` allow for the tensorflow version from nixpkgs.

### Tensorflow via wheel (newer versions, quicker builds)
I'd like to install a more recent version of tensorflow which is not available from nixpkgs. Also I don't like long build times and therefore I want to install tensorflow via wheel. Usually most wheels work pretty well out of the box, but the tensorflow wheel has an issue which I need to fix with an override.
```nix
mach-nix.mkPython {

  requirements = ''
    # bunch of other requirements
    tensorflow == 2.2.0rc4
  '';

  # no need to specify provider settings since wheel is the default anyways

  # Fix the tensorflow wheel
  _.tensorflow.postInstall = "rm $out/bin/tensorboard";
}

```
## PyTorch

### Recent PyTorch with nixpkgs dependencies, and custom python
I'd like to use a recent version of Pytorch from wheel, but I'd like to build the rest of the requirements from sdist or nixpkgs. I want to use python 3.6.
```nix
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

  # Select custom python version (Must be taken from pkgs with the overlay applied)
  python = mach-nix.nixpkgs.python36;
}
```

## JupyterLab

### Starting point for a geospatial environment
```nix
with mach-nix.nixpkgs;
let
  pyEnv = mach-nix.mkPython rec {
    python = "python37";
    requirements =  ''
        jupyterlab
        geopandas
        pyproj
        pygeos
        shapely>=1.7.0
      '';
    providers = {
      shapely = "sdist,nixpkgs";
    };
  };
in
mkShell rec {
  buildInputs = [
    bash
    pyEnv
  ] ;

  shellHook = ''
    jupyter lab --notebook-dir=~/
  '';
}
```

## Docker
For every python environment a docker image is available via the `dockerImage` attribute of the `mkPython` result
### JupyterLab Docker Image
Assuming the following expression under `./jupyter-docker.nix`:
```nix
with mach-nix.nixpkgs;
let
  pyEnv = mach-nix.mkPython rec {
    python = "python37";
    requirements =  ''
        jupyterlab
        # add packages here
      '';
  };
in
# The following overrides a call to nixpkgs.dockerTools.buildImage.
# See more buildImage examples here: https://github.com/NixOS/nixpkgs/blob/master/pkgs/build-support/docker/examples.nix
pyEnv.dockerImage.override (oa: {
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
