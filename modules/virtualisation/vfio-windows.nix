{ config, pkgs, username, ... }:

let
  lookingGlassMemoryMB = 64;
  amdGpuIds = [
    "1002:13c0" # Integrated AMD GPU at 0000:09:00.0
    "1002:1640" # Integrated AMD GPU HDMI audio at 0000:09:00.1
  ];
in
{
  boot = {
    initrd.kernelModules = [
      "vfio"
      "vfio_iommu_type1"
      "vfio_pci"
    ];

    kernelModules = [
      "kvm-amd"
      "kvmfr"
    ];

    extraModulePackages = [
      config.boot.kernelPackages.kvmfr
    ];

    kernelParams = [
      "amd_iommu=on"
      "iommu=pt"
      "kvm.ignore_msrs=1"
      "vfio-pci.ids=${builtins.concatStringsSep "," amdGpuIds}"
    ];

    extraModprobeConfig = ''
      options kvmfr static_size_mb=${toString lookingGlassMemoryMB}
      options vfio-pci ids=${builtins.concatStringsSep "," amdGpuIds} disable_vga=1
    '';
  };

  virtualisation.libvirtd = {
    enable = true;
    onShutdown = "shutdown";
    qemu = {
      runAsRoot = true;
      swtpm.enable = true;
      package = pkgs.qemu_kvm;
    };
  };

  virtualisation.spiceUSBRedirection.enable = true;
  programs.virt-manager.enable = true;

  services.udev.extraRules = ''
    KERNEL=="kvmfr0", GROUP="kvm", MODE="0660"
  '';

  users.users.${username}.packages = with pkgs; [
    looking-glass-client
    pciutils
    usbutils
  ];

  environment.persistence."/persist".directories = [
    "/var/lib/libvirt"
    {
      directory = "/var/lib/swtpm-localca";
      mode = "0700";
    }
  ];
}
