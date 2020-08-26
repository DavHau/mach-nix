
<!--ts-->
  * [Usage in Nix Expressions:](#usage-in-nix-expressions)
     * [import mach-nix](#import-mach-nix)
     * [mkPython / mkPythonShell](#mkpython--mkpythonshell)
        * [From a list of requirements](#from-a-list-of-requirements)
        * [Mix arbitrary sources with requirements.](#mix-arbitrary-sources-with-requirements)
     * [buildPythonPackage / buildPythonApplication](#buildpythonpackage--buildpythonapplication)
        * [Build python package from its source code and autodetect requirements](#build-python-package-from-its-source-code-and-autodetect-requirements)
        * [buildPythonPackage from GitHub](#buildpythonpackage-from-github)
        * [buildPythonPackage from GitHub with extras](#buildpythonpackage-from-github-with-extras)
        * [buildPythonPackage from GitHub and add missing requirements](#buildpythonpackage-from-github-and-add-missing-requirements)
        * [buildPythonPackage from GitHub (reproducible source)](#buildpythonpackage-from-github-reproducible-source)
        * [buildPythonPackage from GitHub (manual requirements)](#buildpythonpackage-from-github-manual-requirements)
  * [Examples for Tensorflow / PyTorch](#examples-for-tensorflow--pytorch)
     * [Tensorflow with SSE/AVX/FMA support](#tensorflow-with-sseavxfma-support)
     * [Tensorflow via wheel (newer versions, quicker builds)](#tensorflow-via-wheel-newer-versions-quicker-builds)
     * [Recent PyTorch with nixpkgs dependencies, and custom python](#recent-pytorch-with-nixpkgs-dependencies-and-custom-python)
  * [Using overrides](#using-overrides)
     * [Fixing packages via overrides](#fixing-packages-via-overrides)
     * [Include poetry2nix overrides](#include-poetry2nix-overrides)

<!-- Added by: grmpf, at: Tue 25 Aug 2020 02:28:02 PM +07 -->

<!--te-->

## Usage in Nix Expressions:

### import mach-nix
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "heads/refs/2.3.0";
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

#### Mix requirements with packages from arbitrary sources.
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
alternatively if requirements are not needed, extra_pkgs can be passed directly to mkPython
```nix
mach-nix.mkPython [
  "https://github.com/psf/requests/tarball/2a7832b5b06d"   # from tarball url
  ./some/local/project                                     # from local path
  mach-nix.buildPythonPackage { ... };                     # from package
]
```

### buildPythonPackage / buildPythonApplication
Whenever `requirements` are not explicitly specified, they will be extracted automatically from teh packages setup.py/setup.cfg. The same goes for the `name` and `version`
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

#### buildPythonPackage from GitHub and add missing requirements
use this in case autdetecting requirements failed
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
Use this if automatic requirements extraction doesn't work.
```nix
mach-nix.buildPythonPackage {
  src = "https://github.com/psf/requests/tarball/2a7832b5b06d";
  requirements = ''
    # list of requirements
  '';
}
```

## Examples for Tensorflow / PyTorch

### Tensorflow with SSE/AVX/FMA support
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
  overrides_post = [( pythonSelf: pythonSuper: {
    tensorflow = pythonSuper.tensorflow.overridePythonAttrs ( oldAttrs: {
      postInstall = ''
        rm $out/bin/tensorboard
      '';
    });
  })];
}

```

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

## Using overrides
### Fixing packages via overrides
See previous example for tensorflow wheel

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
