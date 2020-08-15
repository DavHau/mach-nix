{
  network.description = "Pypi Crawler";
  network.enableRollback = true;

  machine =
    { config, pkgs, ... }:
    { imports = [
        <nixpkgs/nixos/modules/profiles/qemu-guest.nix>
        ./configuration.nix
      ];
      boot.loader.grub.device = "/dev/sda";
      fileSystems."/" = { device = "/dev/sda1"; fsType = "ext4"; };
      boot.cleanTmpDir = true;
      networking.hostName = "pypi-crawler";
      networking.firewall.allowPing = true;
      services.openssh.enable = true;
      users.users.root.openssh.authorizedKeys.keys = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDuhpzDHBPvn8nv8RH1MRomDOaXyP4GziQm7r3MZ1Syk"
      ];
      deployment.targetHost = "95.217.166.31";
    };
}