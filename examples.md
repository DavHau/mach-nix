
<!--ts-->
  * [Basic Usage in Nix Expressions:](#basic-usage-in-nix-expressions)
     * [mkPython / mkPythonShell](#mkpython--mkpythonshell)
     * [buildPythonPackage / buildPythonApplication](#buildpythonpackage--buildpythonapplication)
     * [buildPythonPackage from GitHub](#buildpythonpackage-from-github)
  * [Examples for Tensorflow / PyTorch](#examples-for-tensorflow--pytorch)
     * [Tensorflow with SSE/AVX/FMA support](#tensorflow-with-sseavxfma-support)
     * [Tensorflow via wheel (newer versions, quicker builds)](#tensorflow-via-wheel-newer-versions-quicker-builds)
     * [Recent PyTorch with nixpkgs dependencies, overlays, and custom python](#recent-pytorch-with-nixpkgs-dependencies-overlays-and-custom-python)
  * [Using overrides](#using-overrides)
     * [Fixing packages via overrides](#fixing-packages-via-overrides)
     * [Include poetry2nix overrides](#include-poetry2nix-overrides)

<!-- Added by: grmpf, at: Sat 04 Jul 2020 12:18:42 PM UTC -->

<!--te-->


## Basic Usage in Nix Expressions:
### mkPython / mkPythonShell
build a python environment from a list of requirements
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.mkPython {
  requirements = builtins.readFile ./requirements.txt;
}
```

### buildPythonPackage / buildPythonApplication
Build a python package from its source code and a list of requirements
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.buildPythonPackage {
  pname = "my-package";
  version = "1.0.0";
  src = /project-path;
  requirements = builtins.readFile /project-path/requirements.txt;
}
```

### buildPythonPackage from GitHub
Build a python package from its source code and a list of requirements
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.buildPythonPackage rec {
  pname = "projectname";
  version = "1.0.0";
  src = builtins.fetchGit{
    url = "https://github.com/user/projectname";
    ref = "master";
    # rev = "put_commit_hash_here";
  };
  doCheck = false;
  doInstallCheck = false;
  requirements = builtins.readFile "${src}/requirements.txt";
}
```

## Examples for Tensorflow / PyTorch

### Tensorflow with SSE/AVX/FMA support
I have a complex set of requirements including tensorflow. I'd like to have tensorflow with the usual nix features enabled like SSE/AVX/FMA which I cannot get from pypi. Therefore I must take tensorflow from nixpkgs. For everything else I keep the default, which means wheels are preferred. This allows for quicker installation of dependencies.
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.mkPython {

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
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.mkPython {

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

### Recent PyTorch with nixpkgs dependencies, overlays, and custom python
I'd like to use a recent version of Pytorch from wheel, but I'd like to build the rest of the requirements from sdist or nixpkgs. I want to use python 3.6.
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
overlays = []; # some very useful overlays
in mach-nix.mkPython rec {

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
I have a complex requirements.txt which includes `imagecodecs`. It is available via wheel, but I prefer to build everything from source. This package has complex build dependencies and is not available from nixpkgs. Luckily poetry2nix` overrides make it work. The peotry2nix overrides depend on nixpkgs-unstable.
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.2.2";
  });
in mach-nix.mkPython rec {

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
