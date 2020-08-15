{ config, pkgs, nodes, ... }:
let
  python = (import ../python.nix);
  user = "crawler";
  src = "${../../src}";
in
{
  swapDevices = [
    {
      size = 150000;
      device = "/tmp/swapfile";
    }
    #{
    #  size = 50000;
    #  device = "/tmp/swapfile2";
    #}
  ];
  environment.systemPackages =  with pkgs; [
    bmon htop
    screen
    git
    vim
    lz4
  ];
  users = {
    mutableUsers = false;
    users."${user}" = {
      home = "/home/${user}";
      createHome = true;
    };
  };
  systemd.services.crawl-deps = {
    description = "Crawl PyPi Deps for wheels";
    after = [ "network-online.target" ];
    serviceConfig = { Type = "simple"; };
    serviceConfig = { User = "${user}"; };
    environment = {
      WORKERS = "100";
      PYTHONPATH = src;
      EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
      pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
      dump_dir = "/home/${user}/wheels";
      #skip = "21";
    };
    path = [ python pkgs.git ];
    script = ''
      if [ ! -e /home/${user}/nix-pypi-fetcher ]; then
        git clone --single-branch --branch wheels https://github.com/DavHau/nix-pypi-fetcher.git /home/${user}/nix-pypi-fetcher
        cd /home/${user}/nix-pypi-fetcher
        git config user.email "$EMAIL"
        git config user.name "DavHau"
      fi
      cd /home/${user}/nix-pypi-fetcher
      #git checkout wheels
      #git pull
      ${python}/bin/python -u ${src}/wheel_deps_spider.py
    '';
  };
  systemd.services.crawl-deps2 = {
    description = "Crawl PyPi Deps for wheels 2";
    after = [ "network-online.target" ];
    serviceConfig = { Type = "simple"; };
    serviceConfig = { User = "${user}"; };
    environment = {
      WORKERS = "100";
      PYTHONPATH = src;
      EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
      pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
      dump_dir = "/home/${user}/wheels";
      skip = "40";
    };
    path = [ python pkgs.git ];
    script = ''
      if [ ! -e /home/${user}/nix-pypi-fetcher ]; then
        git clone --single-branch --branch wheels https://github.com/DavHau/nix-pypi-fetcher.git /home/${user}/nix-pypi-fetcher
        cd /home/${user}/nix-pypi-fetcher
        git config user.email "$EMAIL"
        git config user.name "DavHau"
      fi
      cd /home/${user}/nix-pypi-fetcher
      #git checkout wheels
      #git pull
      ${python}/bin/python -u ${src}/wheel_deps_spider.py
    '';
  };
  systemd.services.crawl-deps3 = {
    description = "Crawl PyPi Deps for wheels 3";
    after = [ "network-online.target" ];
    serviceConfig = { Type = "simple"; };
    serviceConfig = { User = "${user}"; };
    environment = {
      WORKERS = "100";
      PYTHONPATH = src;
      EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
      pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
      dump_dir = "/home/${user}/wheels";
      skip = "80";
    };
    path = [ python pkgs.git ];
    script = ''
      if [ ! -e /home/${user}/nix-pypi-fetcher ]; then
        git clone --single-branch --branch wheels https://github.com/DavHau/nix-pypi-fetcher.git /home/${user}/nix-pypi-fetcher
        cd /home/${user}/nix-pypi-fetcher
        git config user.email "$EMAIL"
        git config user.name "DavHau"
      fi
      cd /home/${user}/nix-pypi-fetcher
      #git checkout wheels
      #git pull
      ${python}/bin/python -u ${src}/wheel_deps_spider.py
    '';
  };
  systemd.services.crawl-deps4 = {
    description = "Crawl PyPi Deps for wheels 4";
    after = [ "network-online.target" ];
    serviceConfig = { Type = "simple"; };
    serviceConfig = { User = "${user}"; };
    environment = {
      WORKERS = "100";
      PYTHONPATH = src;
      EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
      pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
      dump_dir = "/home/${user}/wheels";
      skip = "c0";
    };
    path = [ python pkgs.git ];
    script = ''
      if [ ! -e /home/${user}/nix-pypi-fetcher ]; then
        git clone --single-branch --branch wheels https://github.com/DavHau/nix-pypi-fetcher.git /home/${user}/nix-pypi-fetcher
        cd /home/${user}/nix-pypi-fetcher
        git config user.email "$EMAIL"
        git config user.name "DavHau"
      fi
      cd /home/${user}/nix-pypi-fetcher
      #git checkout wheels
      #git pull
      ${python}/bin/python -u ${src}/wheel_deps_spider.py
    '';
  };
}