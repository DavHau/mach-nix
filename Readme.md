# mach-nix - Create highly reproducible python environments
Mach-nix makes it easy to create and share reproducible python environments. While other python package management tools are mostly a trade off between ease of use and reliability, mach-nix aims to provide both at the same time. Mach-nix is based on the nix ecosystem but doesn't require you to understand anything about nix.

## Who is this meant for?
 - Everyone who has no idea about nix but wants to maintain python environments for their projects which are reliable and easy to reproduce.
 - Everyone who is already working with nix but wants to reduce the effort needed to create a nix expression for their python project.

## Installation
You can either install mach-nix via pip or by using nix in case you already have the nix package manager installed.
### Installing via pip
```shell
pip install git+git://github.com/DavHau/mach-nix@master
```
### Installing via nix
```shell
nix-env -if https://github.com/DavHau/mach-nix/tarball/master -A mach-nix
```

## Basic usage

---
### **Use Case 1**: Build a virtualenv-style python environment from a requirements.txt
```bash
mach-nix env ./venv -r requirements.txt
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
### **Use Case 3**: Defina a python derivation via nix expression language
If you are familier writing nix expressions, you don't need to install this program. You can call it directly from a nix expression
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "master";
    rev = "e2893a5c64e42298c889d05adba7965b5d1ea1b7";
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
 Usually people rely on multiple layers of different package mamagement tools for building their software environments. These tools are often not well integrated with each other and don't offer strong reproducibility. Example: You are on debian/ubuntu and use APT (layer 1) to install python. Then you use venv (layer 2) to overcome some of your layer 1 limitations (not being able to have multiple versions of the same package installed) and afterwards you are using pip (layer 3) to install python packages. You notice that even after pinning all your requirements, your environment behaves differently on your server or your colleagues machine because their underlying system differs from yours. You start using docker (layer 4) to overcome this problem which adds extra complexity to the whole process and gives you some nasty limitations while development. You need to configure your IDE's docker integration and so on. Despite all the effort you put in, still the problem is not fully solved and from time to time your build pipeline just breaks and you need to fix it manually. 
 
 In contrast to that, the nix package manager provides a from ground up different approach to build software systems. Due to it's purly functional approach, nix doesn't require additional layers to make your software reliable. Software environments built with nix are known to be reliable, reproducible, and portable, which makes many processes during development and deployment easier. Mach-nix leverages that potential by abstracting away the complexity involved in building python environments with nix. Basically it just generates nix expressions for you.

## How does mach-nix work?
The general mechanism can be broken down into the following:

###  Dependency resolution
Mach-nix contains a  dependency graph of nearly all python packages available on pypi.org. With this, mach-nix is able to do dependency resolution offline within seconds. The default strategy of the resolver is to reuse as many packages as possible directly from the nixpkgs repository because those can be downlaoded from the nixos cache which in turn will reduce the build time.

### Generating a nix expression
After all the python requirements have been determined by the dependency resolver, mach-nix will generate a nix expression defining your python environment. This expression mainly consists of an overlay for nixpkgs.

Using nixpkgs as a base brings the following benefits:  
1. Non-python Dependencies:  
   Many python packages have non-python dependencies like various C libraries for example. These are the situations where pip and other package managers fail during the installation complaining about missing header files or similar stuff. For many python packages these requirements are already specified in nixpkgs. Mach-nix reuses these definitions to provide a smooth build experience.
2. Nix specific fixes:  
   Some python packages might need some additional modification to work with nix. Those are already done in nixpkgs and mach-nix will reuse them.

