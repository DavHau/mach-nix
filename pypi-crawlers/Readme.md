## A set of tools to index python package URL's and dependencies

These crawlers have been created for the purpose of maintaining data required for [mach-nix](https://github.com/DavHau/mach-nix).

This project contains 2 crawlers. One which indexes available `sdist` python package downloads from pypi.org and another one which actually downloads all packages and extracts their dependency information.

The URL index is stored here: [nix-pypi-fetcher-2](https://github.com/DavHau/nix-pypi-fetcher-2) (which at the same time is a convenient standalone pypi fetcher for nix)
The dependency graph is stored here: [pypi-deps-db](https://github.com/DavHau/pypi-deps-db)

---
## URL Crawler
It takes the complete list of packages from pypi's xml API, then retrieves the download URLs for each package via pypi's json [API](https://warehouse.readthedocs.io/api-reference/json/).
The sha256 hashes are already returned by this API. No package downloading needed to build this index.

---
## Dependency Crawler
It doesn't seem like pypi provides any information about dependencies via API. A package's dependencies only get revealed during the installation process itself. Therefore the strategy to extract one package's dependencies is:
1. Download and extract the sdist release of the package
2. Run the package's setup routine through a modified python environment which doesn't do a real `setup` but instead just dumps the packages dependencies.

The main modifications that needed to be done to python to extract the dependencies are:
 - Patch the builtin module `distutils` to run the setup routine until all of the important information gathering is finished, then jsonify some relevant arguments and dump them to a file.
 - Patch `setuptools` to skip the installation of setup requirements and directly call the setup method of `distutils`.

The process to extract requirements for a single package is defined as a nix derivation under `./src/extractor/`.
This allows to run the extraction process as a nix builder in a sandboxed environment.
This extractor derivation takes one python package's downlaod information as input and produces a json output containing the dependencies.
A python based service regularly checks for new packages which werer detected by the URL crawler and runs those packages through the `extractor` builder to update the dependency DB. Afterwards this database is dumped to json and published at [pypi-deps-db](https://github.com/DavHau/pypi-deps-db).

---
### Project Structure
```
|- nix/                     Contains NixOps deployments for the crawler and database
|   |- crawler/             Deployment for both crawlers together on a small machine
|   |- database/            Deployment for the DB needed to store dependency information
|   |- power-deps-crawler   Alternative deployment of the dependency crawler on a strong
|                           machine which was needed to process the complete past history
|                           of python packages.
|
|- src/
    |- extractor/           Nix expression for extracting a single package
    |- crawl_deps.py        Entry point for the dependency crawler
    |- crawl_urls           Entry point for the URL crawler
    |- dump_deps.py         Entry point for dumping the dependencies from the DB into json.

```

### Debugging
see [./debug](./debug)
