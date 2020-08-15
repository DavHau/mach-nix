{ config, pkgs, ...}:
let
  python = (import ../python.nix);
  user = "crawler";
  src = "${../../src}";
  nixpkgs_src = (import ../../nix/nixpkgs-src.nix).stable;
  db_host = "10.147.19.69";
  extractor = import ../../src/extractor;
  branch = "master";
  enable = true;
  serviceConfig = {
    Type = "simple";
    User = "${user}";
    RuntimeMaxSec = 60 * 60 * 10; # 10h
  };
  cd_into_updated_proj_branch = name: dir: branch: email: ''
    if [ ! -e /home/${user}/${dir} ]; then
      git clone git@github.com:DavHau/${name}.git /home/${user}/${dir}
      cd /home/${user}/${dir}
      git config user.email "${email}"
      git config user.name "DavHau-bot"
    fi
    cd /home/${user}/${dir}
    git fetch --all
    git checkout ${branch}
    git pull
  '';
in
{
  deployment.keys = {
    db_pass = {
      keyFile = ./keys/db_pass;
      destDir = "/home/${user}/";
      user = "${user}";
    };
    id_ed25519 = {
      keyFile = ./keys/crawler_ssh_key;
      destDir = "/home/${user}/.ssh/";
      user = "${user}";
    };
    id_ed25519_deps_db = {
      keyFile = ./keys/id_ed25519_deps_db;
      destDir = "/home/${user}/.ssh/";
      user = "${user}";
    };
  };
  swapDevices = [{
    size = 10000;
    device = "/tmp/swapfile";
  }];
  nix.nixPath = [ "nixpkgs=${nixpkgs_src}" ];
  services.journald.extraConfig = ''
    SystemMaxUse=1G
  '';
  nixpkgs.config.allowUnfree = true;
  environment.systemPackages = [
    python
    pkgs.htop
    pkgs.vim
    pkgs.bmon
    extractor.py27
    extractor.py35
    extractor.py36
    extractor.py37
    extractor.py38
  ];
  nix.maxJobs = 2;
  nix.extraOptions = ''
    http-connections = 300
    #keep-env-derivations = true
    keep-outputs = true
  '';
  services.zerotierone.enable = true;
  services.zerotierone.joinNetworks = ["93afae59636cb8e3"];  # db network
  users = {
    mutableUsers = false;
    users."${user}" = {
      home = "/home/${user}";
      createHome = true;
    };
  };
  programs.ssh.knownHosts = {
    github = {
      hostNames = [ "github.com" "13.229.188.59" ];
      publicKeyFile = "${./github_pub_key}";
    };
  };
  system.activationScripts = {
    ssh_dir = {
      text = ''
        chown -R crawler /home/crawler/.ssh
      '';
      deps = [];
    };
   };
  systemd.services.crawl-urls =
    let
      environment = {
        WORKERS = "5";
        PYTHONPATH = src;
        EMAIL = "hsngrmpf+pypiurlcrawler@gmail.com";
      };
    in
    {
      inherit serviceConfig environment;
      description = "Crawl PyPi URLs";
      after = [ "network-online.target" ];
      path = [ python pkgs.git ];
      script = with environment; ''
        set -x
        ${cd_into_updated_proj_branch "nix-pypi-fetcher" "nix-pypi-fetcher_update" "${branch}" EMAIL}
        rm -f ./pypi/*
        ${python}/bin/python -u ${src}/crawl_urls.py ./pypi
        echo $(date +%s) > UNIX_TIMESTAMP
        git add ./pypi UNIX_TIMESTAMP
        git pull
        git commit -m "$(date)"
        git push
      '';
    };
  systemd.timers.crawl-urls = {
    inherit enable;
    wantedBy = [ "timers.target" ];
    partOf = [ "crawl-urls.service" ];
    timerConfig.OnCalendar = "00/12:00";  # at 00:00 and 12:00
  };
  systemd.services.crawl-sdist =
    let
      environment = {
        WORKERS = "5";
        PYTHONPATH = src;
        NIX_PATH = "nixpkgs=${nixpkgs_src}";
        DB_HOST = db_host;
        EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
        CLEANUP = "y";
        pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
      };
    in
    {
    inherit serviceConfig environment;
    description = "Crawl PyPi Sdist Deps and push to github";
    after = [ "network-online.target" ];
    path = [ python ] ++ (with pkgs; [ git nix gawk gnutar gzip ]);
    script = with environment; ''
      export DB_PASS=$(cat /home/${user}/db_pass)
      ${python}/bin/python -u ${src}/crawl_sdist_deps.py
      set -x
      export GIT_SSH_COMMAND="${pkgs.openssh}/bin/ssh -i /home/${user}/.ssh/id_ed25519_deps_db"
      ${cd_into_updated_proj_branch "nix-pypi-fetcher" "nix-pypi-fetcher" "${branch}" EMAIL}
      ${cd_into_updated_proj_branch "pypi-deps-db" "pypi-deps-db" "${branch}" EMAIL}
      rm -f ./sdist/*
      ${python}/bin/python -u ${src}/dump_sdist_deps.py ./sdist
      echo $(date +%s) > UNIX_TIMESTAMP
      pypi_fetcher_commit=$(git ls-remote https://github.com/DavHau/nix-pypi-fetcher ${branch} | awk '{print $1;}')
      pypi_fetcher_url="https://github.com/DavHau/nix-pypi-fetcher/archive/''${pypi_fetcher_commit}.tar.gz"
      pypi_fetcher_hash=$(nix-prefetch-url --unpack $pypi_fetcher_url)
      echo $pypi_fetcher_commit > PYPI_FETCHER_COMMIT
      echo $pypi_fetcher_hash > PYPI_FETCHER_SHA256
      git add ./sdist UNIX_TIMESTAMP PYPI_FETCHER_COMMIT PYPI_FETCHER_SHA256
      git pull
      git commit -m "$(date) - sdist_update"
      git push
    '';
  };
  systemd.timers.crawl-sdist = {
    inherit enable;
    wantedBy = [ "timers.target" ];
    partOf = [ "crawl-deps.service" ];
    timerConfig.OnCalendar = [
      "Mon-Sun *-*-* 4:00:00"
      "Mon-Sun *-*-* 16:00:00"
    ];
  };
  systemd.services.crawl-wheel =
    let
      environment = {
        WORKERS = "5";
        PYTHONPATH = src;
        EMAIL = "hsngrmpf+pypidepscrawler@gmail.com";
        pypi_fetcher = "/home/${user}/nix-pypi-fetcher";
        dump_dir = "/home/${user}/pypi-deps-db/wheel";
      };
    in
    {
    inherit serviceConfig environment;
    description = "Crawl Pypi Wheel Deps and push to gitub";
    after = [ "network-online.target" ];
    path = [ python ] ++ (with pkgs; [ git nix gawk gnutar gzip ]);
    script = with environment; ''
      set -x
      export GIT_SSH_COMMAND="${pkgs.openssh}/bin/ssh -i /home/${user}/.ssh/id_ed25519_deps_db"
      ${cd_into_updated_proj_branch "nix-pypi-fetcher" "nix-pypi-fetcher" "${branch}" EMAIL}
      ${cd_into_updated_proj_branch "pypi-deps-db" "pypi-deps-db" "${branch}" EMAIL}
      export PYTONPATH=${src}
      ${python}/bin/python -u ${src}/crawl_wheel_deps.py $dump_dir
      echo $(date +%s) > UNIX_TIMESTAMP
      pypi_fetcher_commit=$(git ls-remote https://github.com/DavHau/nix-pypi-fetcher ${branch} | awk '{print $1;}')
      pypi_fetcher_url="https://github.com/DavHau/nix-pypi-fetcher/archive/''${pypi_fetcher_commit}.tar.gz"
      pypi_fetcher_hash=$(nix-prefetch-url --unpack $pypi_fetcher_url)
      echo $pypi_fetcher_commit > PYPI_FETCHER_COMMIT
      echo $pypi_fetcher_hash > PYPI_FETCHER_SHA256
      git add ./wheel UNIX_TIMESTAMP PYPI_FETCHER_COMMIT PYPI_FETCHER_SHA256
      git pull
      git commit -m "$(date) - wheel_update"
      git push
    '';
  };
  systemd.timers.crawl-wheel = {
    inherit enable;
    wantedBy = [ "timers.target" ];
    partOf = [ "dump-deps.service" ];
    timerConfig.OnCalendar = [
      "Mon-Sun *-*-* 8:00:00"
      "Mon-Sun *-*-* 20:00:00"
    ];
  };
}