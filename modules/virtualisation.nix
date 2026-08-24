{ pkgs, username, ... }:

{
  virtualisation.libvirtd = {
    enable = true;
    onShutdown = "shutdown";
    qemu = {
      swtpm.enable = true;
      package = pkgs.qemu_kvm;
    };
  };

  virtualisation.spiceUSBRedirection.enable = true;
  programs.virt-manager.enable = true;

  users.users.${username} = {
    packages = with pkgs; [
      virt-viewer
    ];
    extraGroups = [
      "libvirtd"
    ];
  };

  environment.persistence."/persist".directories = [
    "/var/lib/libvirt"
    {
      directory = "/var/lib/swtpm-localca";
      mode = "0700";
    }
  ];

  networking = {
    networkmanager.ensureProfiles.profiles = {
      vpn-vm-bridge = {
        connection = {
          id = "vpn-vm-bridge";
          type = "bridge";
          interface-name = "br-vpn";
          autoconnect = true;
          autoconnect-ports = 1;
        };
        bridge.stp = false;
        ipv4.method = "disabled";
        ipv6.method = "disabled";
      };

      vpn-vm-vlan = {
        connection = {
          id = "vpn-vm-vlan";
          type = "vlan";
          interface-name = "enp6s0.3";
          controller = "br-vpn";
          port-type = "bridge";
          autoconnect = true;
        };
        vlan = {
          id = 3;
          parent = "enp6s0";
        };
        ipv4.method = "disabled";
        ipv6.method = "disabled";
      };
    };

    firewall.extraCommands = ''
      ip46tables -I nixos-fw 1 -i br-vpn -j nixos-fw-refuse
    '';
  };

  virtualisation.libvirtd.allowedBridges = [
    "virbr0"
    "br-vpn"
  ];
}
