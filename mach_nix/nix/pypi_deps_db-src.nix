let 
    rev = builtins.fromJSON (builtins.readFile ./PYPI_DEPS_DB.json);
in
builtins.fetchTarball {
    name = "pypi-deps-db";
    url = "https://github.com/davhau/pypi-deps-db/tarball/${rev.rev}";
    sha256 = "${rev.sha256}";
}