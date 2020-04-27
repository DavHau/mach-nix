# mach-nix - Create highly reproducible python environments
Mach-nix makes it easy to create and share reproducible python environments. While other python package management tools are mostly a trade off between ease of use and reproducibility, mach-nix aims to provide both at the same time. Mach-nix is based on the nix ecosystem but doesn't require you to understand anything about nix. Given a simple requirements.txt file, mach-nix will take care about the rest. 

## Who is this meant for?
 - Anyone who has no idea about nix but wants to maintain python environments for their projects which are reliable and easy to reproduce.
 - Anyone who is already working with nix but wants to reduce the effort needed to create nix expressions for their python projects.

## Installation
You can either install mach-nix via pip or by using nix in case you already have the nix package manager installed.
### Installing via pip
```shell
pip install git+git://github.com/DavHau/mach-nix@1.0.0
```
### Installing via nix
```shell
nix-env -if https://github.com/DavHau/mach-nix/tarball/1.0.0 -A mach-nix
```

## Basic usage

---
### **Use Case 1**: Build a virtualenv-style python environment from a requirements.txt
```bash
mach-nix env ./env -r requirements.txt
```
This will generate the python environment into `./env`. To activate it, execute:
```bash
nix-shell ./env
```
The `./env` directory contains a portable and reproducible definition of your python environment. To reuse this environment on another system, just copy the `./env` directory 
and use `nix-shell` to activate it.

---
### **Use Case 2**: Generate a nix expression from a requirements.txt
```bash
mach-nix gen -r requirements.txt
```
...to print out the nix expression which defines a python derivation (optionally use `-o` to define an `output file`)

---
### **Use Case 3**: Define a python derivation via nix expression language
If you are comfortable with writing nix expressions, you don't need to install this program. You can call it directly from a nix expression
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "master";
    rev = "fa2bb2d33fb9b9dc3113046e4fcc16088f56981a";
  });
in
mach-nix.mkPython {
  requirements = ''
    pillow
    numpy
    requests
  '';
}

```

---


## Why nix?
 Usually people rely on multiple layers of different package management tools for building their software environments. These tools are often not well integrated with each other and don't offer strong reproducibility. Example: You are on debian/ubuntu and use APT (layer 1) to install python. Then you use venv (layer 2) to overcome some of your layer 1 limitations (not being able to have multiple versions of the same package installed) and afterwards you are using pip (layer 3) to install python packages. You notice that even after pinning all your requirements, your environment behaves differently on your server or your colleagues machine because their underlying system differs from yours. You start using docker (layer 4) to overcome this problem which adds extra complexity to the whole process and gives you some nasty limitations during development. You need to configure your IDE's docker integration and so on. Despite all the effort you put in, still the problem is not fully solved and from time to time your build pipeline just breaks and you need to fix it manually. 
 
 In contrast to that, the nix package manager provides a from ground up different approach to build software systems. Due to it's purly functional approach, nix doesn't require additional layers to make your software reliable. Software environments built with nix are known to be reproducible, and portable, which makes many processes during development and deployment easier. Mach-nix leverages that potential by abstracting away the complexity involved in building python environments with nix. Basically it just generates nix expressions for you.

## How does mach-nix work?
The general mechanism can be broken down into the following:

###  Dependency resolution
Mach-nix contains a  dependency graph of nearly all python packages available on pypi.org. With this, mach-nix is able to do dependency resolution offline within seconds.

The dependency graph data can be found here: https://github.com/DavHau/pypi-deps-db  
The dependency graph is updated on a daily basis by this set of tools: https://github.com/DavHau/pypi-crawlers  

Despite this graph being updated constantly, mach-nix always pins one specific version of the graph to ensure reproducibility.

The default strategy of the resolver is to reuse as many packages as possible directly from the nixpkgs repository because those can be downloaded from the nixos cache which reduces build time. As core for the resolver, resolvelib is used: https://github.com/sarugaku/resolvelib

### Generating a nix expression
After all the python requirements have been determined by the dependency resolver, mach-nix will generate a nix expression defining your python environment. This expression mainly consists of an overlay for nixpkgs.

Using nixpkgs as a base brings the following benefits:  
1. Non-python Dependencies:  
   Many python packages have non-python dependencies like various C libraries for example. These are the situations where pip and other package managers fail during the installation complaining about missing header files or similar stuff. For many python packages these requirements are already specified in nixpkgs. Mach-nix reuses these definitions to provide a smooth build experience.
2. Nix specific fixes:  
   Some python packages might need some additional modification to work with nix. Those are already done in nixpkgs and mach-nix will reuse them.

The overlay is generated by applying the following strategy to each required python package:
   - If the exact required python package version already exists in nixpkgs, its definition stays untouched but it might be used as build input for other packages.
   - If one or more versions of the required python package can be found in nixpkgs, but none of them matches the exact required version, the one with the closest version to our requirement is picked and its definition is modified via `overrideAttrs`. The following attributes are modified:
      - `src`: updated to the required version
      - `name`: modified to match the new version
      - `buildInputs`: missing python inputs are added
      - `propagatedBuildInputs`: missing python inputs are added
      - `doCheck`: set to false by default if not specified by user
      - `doInstallCheck`: set to false by default if not specified by user
   - If no version of the required package is found in nixpkgs, the package is built from scratch by using `buildPythonPackage`.

## Advanced Usage (Nix Only)
Mach-nix can be fine tuned with additional arguments by importing it via `builtins.fetchGit`. Examples can be found in [./example](./example/). There are 3 different methods which can be invoked:
1. **mkPythonExpr** - returns a derivation containing a nix expression in $out/share/expr.nix which describes the python environment defined by your inputs
1. **mkPython** - returns the python environment derivation. It basically just evaluates the expression coming from **mkPythonExpr**. 
1. **mkPythonShell** - returns the python environment suitable for nix-shell.

All 3 methods take the following set of inputs which are processed in [./mach_nix/nix/expression.nix](./mach_nix/nix/expression.nix):

### Required Arguments:
 - **requirements** (string): Text content of a typical `requirements.txt`.

### Optional Arguments:
 - **python_attr** (string): Select one of (python27, python35, python36, python37, python38). (default: python37)
 - **prefer_nixpkgs** (bool): Prefer python package versions from nixpkgs instead of newer ones. Decreases build time. (default: true)
 - **disable_checks** (bool): Disable tests wherever possible to decrease build time.
 - **nixpkgs_commit** (string): commit hash of nixpkgs version to use python packages from
 - **nixpkgs_tarball_sha256** (string): sha256 hash of the unpacked tarball for the selected nixpkgs version. (obtained via `nix-prefetch-url --unpack https://github.com/nixos/nixpkgs/tarball/<nixpkgs_commit>`)
 - **pypi_deps_db_commit** (string): commit hash of a specific version of the dependency graph ([pypi-deps-db](https://github.com/DavHau/pypi-deps-db)).
 - **pypi_deps_db_sha256** (string): sha256 hash obtained via `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`

