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
}
