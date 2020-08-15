{
  machine =
  { config, pkgs, nodes, ... }:
  {
    imports = [
      <nixpkgs/nixos/modules/profiles/qemu-guest.nix>
      ./configuration.nix
    ];

    deployment.targetHost = "194.61.20.239";

    boot.cleanTmpDir = true;
    networking.hostName = "nixos";
    networking.firewall.allowPing = true;
    services.openssh.enable = true;
    services.openssh.forwardX11 = true;
    services.openssh.passwordAuthentication = false;
    users.users.root.openssh.authorizedKeys.keys = [
      "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDuhpzDHBPvn8nv8RH1MRomDOaXyP4GziQm7r3MZ1Syk"
    ];

    boot.loader.grub.device = "/dev/vda";
    fileSystems."/" = { device = "/dev/mapper/gc--vg-root"; fsType = "ext4"; };
  };
}
