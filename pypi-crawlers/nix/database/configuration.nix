with import (import ../nixpkgs-src.nix).stable {};
{ config, pkgs, nodes, ... }:
{ environment.systemPackages =  [
    bmon htop
    screen
    git
    lz4
  ];
  deployment.keys = {
    initial_script = {
      keyFile = ./keys/initial_script;
      destDir = "/keys";
    };
  };
  services.postgresql = {
    enable = true;
    package = pkgs.postgresql_11;
    enableTCPIP = true;
    authentication = pkgs.lib.mkOverride 10 ''
      local all all ident
      #host all all ::1/128 md5
      host all all 0.0.0.0/0 password
    '';
    ensureDatabases = [ "almighty" "test" ];
    ensureUsers = [
      {
        name = "almighty";
        ensurePermissions = {
          "DATABASE almighty" = "ALL PRIVILEGES";
          "DATABASE test" = "ALL PRIVILEGES";
        };
      }
      {
        name = "root";
        ensurePermissions = {
          "ALL TABLES IN SCHEMA public" = "ALL PRIVILEGES";
        };
      }
    ];
    initialScript = "/keys/initial_script";
    extraConfig = ''
      max_connections = 20
      shared_buffers = 768MB
      effective_cache_size = 2304MB
      maintenance_work_mem = 192MB
      checkpoint_completion_target = 0.9
      wal_buffers = 16MB
      default_statistics_target = 100
      random_page_cost = 1.1
      effective_io_concurrency = 200
      work_mem = 19660kB
      min_wal_size = 1GB
      max_wal_size = 4GB
      max_worker_processes = 2
      max_parallel_workers_per_gather = 1
      max_parallel_workers = 2
      max_parallel_maintenance_workers = 1
    '';
  };
  nixpkgs.config.allowUnfree = true;
  services.zerotierone.enable = true;
  services.zerotierone.joinNetworks = ["93afae59636cb8e3"];
  users.users.postgres.hashedPassword = "$6$JdTxB0NOfAXl$oKWTqnPuE67WikhRHNM3r/.fef2NEIZeEybkEJnkL8D0jh65YwsdlwKC86ig6VK1EuA6R4UARFVwCTdTk7npk/";
  networking.firewall.allowedTCPPorts = [ 5432 ];
}