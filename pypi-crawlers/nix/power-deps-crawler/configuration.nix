{ config, pkgs, nodes, ... }:
let
  python = (import ../python.nix);
  user = "crawler";
  src = "${../../src}";
  nixpkgs_src = "${../nixpkgs-src.nix}";
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
  };
  environment.systemPackages =  with pkgs; [
    bmon htop
    screen
    git
    vim
    lz4
  ];
  nix.maxJobs = 100;
  nix.extraOptions = ''
    #use-sqlite-wal = false
    http-connections = 300
    keep-env-derivations = true
    keep-outputs = true
  '';

  fileSystems."/tmp-store" =
    { fsType = "tmpfs";
      options = [ "size=50%" ];
    };
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
  systemd.services.crawl-deps = {
    description = "Crawl PyPi Deps";
    after = [ "network-online.target" ];
    serviceConfig = { Type = "simple"; };
    serviceConfig = { User = "${user}"; };
    environment = {
      WORKERS = "60";
      PYTHONPATH = src;
      NIXPKGS_SRC = nixpkgs_src;
      almighty_cleanup = "y";
      almighty_store = "/tmp-store";
      almighty_workers = "60";
    };
    path = [ python pkgs.git pkgs.nix pkgs.gnutar];
    script = ''
      export DB_PASS=$(cat /home/${user}/db_pass)
      ${python}/bin/python -u ${src}/crawl_deps.py
    '';
  };
  system.activationScripts = {
    ssh_dir = {
      text = ''
        chown -R crawler /home/crawler/.ssh
      '';
      deps = [];
    };
   };
}