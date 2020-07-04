<p align="center">
<img width="200" src="https://gist.githubusercontent.com/DavHau/9a66b8c66b798254b714cc3ca44ffda8/raw/ef6b947b3753425118c730a5dfe81084c1bcfe86/logo_small.jpg">  
</p>

## mach-nix - Create highly reproducible python environments
Mach-nix makes it easy to create and share reproducible python environments. While other python package management tools are mostly a trade off between ease of use and reproducibility, mach-nix aims to provide both at the same time. Mach-nix is based on the nix ecosystem but doesn't require you to understand anything about nix. Given a simple requirements.txt file, mach-nix will take care about the rest. 


## Who is this meant for?
 - Anyone who has no idea about nix but wants to maintain python environments for their projects which are reliable and easy to reproduce.
 - Anyone who is already working with nix but wants to reduce the effort needed to create nix expressions for their python projects.


## Donate
Want to support mach-nix? A beer always helps ;)

<a href="https://checkout.opennode.com/p/0063d37e-dcb5-4da7-bfa4-462b34c2b5bb" target="_blank"><img style="width:100px;" src="https://app.opennode.com/donate-with-bitcoin.svg"/></a>
or
<a href="https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=8Q5L3AM7SMJCG&source=url" target="_blank"><img style="width:100px;" src="https://www.paypalobjects.com/en_US/DK/i/btn/btn_donateCC_LG.gif"/></a>

Table of Contents
=================
<!--ts-->
  * [mach-nix - Create highly reproducible python environments](#mach-nix---create-highly-reproducible-python-environments)
  * [Who is this meant for?](#who-is-this-meant-for)
  * [Donate](#donate)
   * [Table of Contents](#table-of-contents)
  * [Usage from cmdline](#usage-from-cmdline)
     * [Installation](#installation)
        * [Installing via pip](#installing-via-pip)
        * [Installing via nix](#installing-via-nix)
     * [Build a virtualenv-style python environment from a requirements.txt](#build-a-virtualenv-style-python-environment-from-a-requirementstxt)
     * [Generate a nix expression from a requirements.txt](#generate-a-nix-expression-from-a-requirementstxt)
  * [Usage in Nix Expression](#usage-in-nix-expression)
     * [Basic](#basic)
     * [Advanced](#advanced)
        * [Required Arguments:](#required-arguments)
        * [Optional Arguments:](#optional-arguments)
        * [Configure Providers](#configure-providers)
  * [Why nix?](#why-nix)
  * [How does mach-nix work?](#how-does-mach-nix-work)
     * [Dependency resolution](#dependency-resolution)
     * [Generating a nix expression](#generating-a-nix-expression)
  * [Contributing](#contributing)
  * [Limitations](#limitations)
  * [Alternative / Similar Software:](#alternative--similar-software)

<!-- Added by: grmpf, at: Sat 04 Jul 2020 12:03:37 PM UTC -->

<!--te-->

## Usage from cmdline

### Installation
You can either install mach-nix via pip or by using nix in case you already have the nix package manager installed.
#### Installing via pip
```shell
pip install git+git://github.com/DavHau/mach-nix@2.0.1
```
#### Installing via nix
```shell
nix-env -if https://github.com/DavHau/mach-nix/tarball/2.0.1 -A mach-nix
```

---
### Build a virtualenv-style python environment from a requirements.txt
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
### Generate a nix expression from a requirements.txt
```bash
mach-nix gen -r requirements.txt
```
...to print out the nix expression which defines a python derivation (optionally use `-o` to define an `output file`)

---

## Usage in Nix Expression

### Basic
You can call mach-nix directly from a nix expression
```nix
let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "2.0.1";
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
find mroe examples under [./examples.md](/examples.md)

### Advanced
Mach-nix can be fine tuned with additional arguments by importing it via `builtins.fetchGit`. Examples can be found in [./examples.md](/examples.md). There are 4 different methods which can be invoked:
1. **mkPython** - builds a python environment for a given `requirements.txt`.
1. **mkPythonShell** - returns the python environment suitable for nix-shell.
1. **buildPytonPackage** - build a single python package from a source code and a list of requirements
1. **buildPythonApplication** - same as **buildPytonPackage**, but package will not be importable by other python packages.

**buildPytonPackage** and **buildPythonApplication** require the same arguments like their equally named partners in nixpkgs, plus the arguments of **mkPython**.  
**mkPython** and **mkPythonShell** take exactly the following arguments:

#### Required Arguments:
 - **requirements** (string): Text content of a typical `requirements.txt`.

#### Optional Arguments:
 - **disable_checks** (bool): Disable tests wherever possible to decrease build time and failures due to nix incompatible tests
 - **overrides_pre** (list): list of pythonOverrides to apply before the machnix overrides
 - **overrides_post** (list): list of pythonOverrides to apply after the machnix overrides
 - **pkgs** (set): pass custom nixpkgs version (20.03 or higher is required for wheel support)
 - **providers** (set): define provider preferences
 - **pypi_deps_db_commit** (string): commit hash of a specific version of the dependency graph ([pypi-deps-db](https://github.com/DavHau/pypi-deps-db)).
 - **pypi_deps_db_sha256** (string): sha256 hash obtained via `nix-prefetch-url --unpack https://github.com/DavHau/pypi-deps-db/tarball/<pypi_deps_db_commit>`
 - **python** (set): select custom python to base overrides on. Should be from nixpkgs >= 20.03
 - **_provider_defaults** (set): builtin provider defaults. Disable them by passing {}
 
#### Configure Providers
**Providers** allow you to configure the origin for your packages on a granular basis.

The following 3 providers are available in version 2.0.0:
  1. **nixpkgs**: Provides packages directly from nixpkgs without modifying their sources. Has only a few versions available, but has a high success rate and all the nix features, like `cudaSupport` for tensorflow for example.
  2. **sdist**: Provides all package versions available from pypi which support setuptools and builds them via nixpkgs overlays wherever possible to resolve external dependencies. It still supports the nixpkgs specific features no matter which package version is selected. But chances are higher for a build to fail than with the **nixpkgs** provider.
  3. **wheel**: Provides all linux compatible wheel releases from pypi. Wheels can contain binaries. Mach-nix autopatches them to work on nix. Wheels are super quick to install and work quite reliable. Therefore this provider is preferred by default.

Mach-nix builds environments by mixing packages from all 3 providers. You decide which providers should be preferred for which packages, or which providers shouldn't be used at all.
The default preferred order of providers is `wheel`, `sdist`, `nixpkgs`.

Providers can be disabled/enabled/preferred like in the following examples:
 - A provider specifier like **`"wheel,sdist,nixpkgs"`** means, that the resolver will first try to satisfy the requirements with candidates from the wheel provider. If a resolution is impossible or a package doesn't provide a wheel release, it falls back to sdist/nixpkgs for a minimal number of packages. In general it will choose as many packages from wheel as possible, then sdist, then nixpkgs.

 - **`"nixpkgs,sdist"`** means, that `nixpkgs` candidates are preferred, but mach-nix falls back to build from source (sdist). **`wheel`** is not listed and therefore wheels are disabled.

 A full provider config passed to mach-nix looks like this:
 ```nix
{
  # The default for all packages which are not specified explicitly
  _default = "nixpkgs,wheel,sdist";

  # Explicit settings per package
  numpy = "wheel,sdist";
  tensorflow = "wheel";
}
 ```

Mach-nix will always satisfy your **requirements.txt** fully with the configured providers or fail with a **ResolutionImpossible** error.

If a mach-nix build fails, Most of the times it can be resolved by just switching the provider of a package, which is simple and doesn't require writing a lot of nix code. For some more complex scenarios, checkout the following examples.

## Why nix?
 Usually people rely on multiple layers of different package management tools for building their software environments. These tools are often not well integrated with each other and don't offer strong reproducibility. Example: You are on debian/ubuntu and use APT (layer 1) to install python. Then you use venv (layer 2) to overcome some of your layer 1 limitations (not being able to have multiple versions of the same package installed) and afterwards you are using pip (layer 3) to install python packages. You notice that even after pinning all your requirements, your environment behaves differently on your server or your colleagues machine because their underlying system differs from yours. You start using docker (layer 4) to overcome this problem which adds extra complexity to the whole process and gives you some nasty limitations during development. You need to configure your IDE's docker integration and so on. Despite all the effort you put in, still the problem is not fully solved and from time to time your build pipeline just breaks and you need to fix it manually. 
 
 In contrast to that, the nix package manager provides a from ground up different approach to build software systems. Due to it's purly functional approach, nix doesn't require additional layers to make your software reliable. Software environments built with nix are known to be reproducible, and portable, which makes many processes during development and deployment easier. Mach-nix leverages that potential by abstracting away the complexity involved in building python environments with nix. Basically it just generates nix expressions for you.

## How does mach-nix work?
The general mechanism can be broken down into [Dependency resolution](#dependency-resolution) and [Generating a nix expression](#generating-a-nix-expression):

###  Dependency resolution
Mach-nix contains a dependency graph of nearly all python packages available on pypi.org. This allows mach-nix to resolve dependencies offline within seconds.

The dependency graph data can be found here: https://github.com/DavHau/pypi-deps-db  
The dependency graph is updated on a daily basis by this set of tools: https://github.com/DavHau/pypi-crawlers  

Despite this graph being updated constantly, mach-nix always pins one specific version of the graph to ensure reproducibility.

As core for the resolving resolvelib is used: https://github.com/sarugaku/resolvelib

Mach-nix supports multiple providers to retrieve python packages from. The user can specify which providers should be preferred. Packages from different providers can be mixed.

### Generating a nix expression
After all python dependencies and their providers have been determined by the dependency resolver, mach-nix will generate a nix expression defining your python environment.

Individual python packages are either built by overriding an existing package definition from nixpkgs, or by creating the package from scratch via nixpkgs' `buildPythonPackage`. Which strategy is used depends on the provider of a package and if it is already packaged in nixpkgs.

Using nixpkgs as a base has the following benefits:  
1. **Non-python Dependencies**:  
   Many python packages have non-python dependencies like various C libraries. Mach-nix can resolve those dependencies by taking the build inputs from python package definitions in nixpkgs.
1. **Special features**:
   Some python packages can be built with special features, like for example SSE/AVX/FMA support in tensorflow. The nixpkgs versions of those python packages often include these features.
1. **Nix specific fixes**:  
   Some python packages might need some additional modification to work with nix. Those are already done in nixpkgs.
   
If a package is built by overriding nixpkgs, the following attributes are modified:  
   - `src`: updated to the required version
   - `name`: modified to match the new version
   - `buildInputs`: replaced with mach-nix determined python deps
   - `propagatedBuildInputs`: non-python deps of old definition + mach-nix determined python deps
   - `doCheck`: set to false by default if not specified by user
   - `doInstallCheck`: set to false by default if not specified by user

## Contributing
Contributions to this project are welcome in the form of GitHub PRs. If you are planning to make any considerable changes, you should first present your plans in a GitHub issue so it can be discussed.

## Limitations
 - Currently mach-nix does not provide any functionality which supports you in publishing python projects, like [Poetry](https://python-poetry.org/) does for example.

## Alternative / Similar Software:
 - [Poetry](https://python-poetry.org/)
 - [Pipenv](https://github.com/pypa/pipenv)
 - [peotry2nix](https://github.com/nix-community/poetry2nix)
 - [pypi2nix](https://github.com/nix-community/pypi2nix)
