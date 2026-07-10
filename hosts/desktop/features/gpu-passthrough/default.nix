{ config, pkgs, username, ... }:

let
  lookingGlassMemoryMB = 128;
  amdGpuIds = [
    "1002:13c0" # Integrated AMD GPU at 0000:09:00.0
    "1002:1640" # Integrated AMD GPU HDMI audio at 0000:09:00.1
  ];
  extractVfctRom = pkgs.writeShellApplication {
    name = "extract-vfct-rom";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${./extract-vfct-rom.py} "$@"
    '';
  };
  patchVfctBdf = pkgs.writeShellApplication {
    name = "patch-vfct-bdf";
    runtimeInputs = [ pkgs.python3 ];
    text = ''
      exec python3 ${./patch-vfct-bdf.py} "$@"
    '';
  };
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

  virtualisation.libvirtd.qemu.verbatimConfig = ''
    namespaces = []
    cgroup_device_acl = [
      "/dev/null", "/dev/full", "/dev/zero",
      "/dev/random", "/dev/urandom",
      "/dev/ptmx", "/dev/userfaultfd",
      "/dev/kvm", "/dev/vfio/vfio", "/dev/kvmfr0"
    ]
  '';

  users.users.${username} = {
    packages = with pkgs; [
      extractVfctRom
      looking-glass-client
      patchVfctBdf
    ];
    extraGroups = [
      "kvm"
    ];
  };

  services.udev.extraRules = ''
    SUBSYSTEM=="kvmfr", KERNEL=="kvmfr0", GROUP="kvm", MODE="0660"
  '';

  systemd.tmpfiles.rules = [
    "d /persist/vfio 0755 root root - -"
    "z /dev/kvmfr0 0660 root kvm - -"
  ];

  users.users.qemu-libvirtd.extraGroups = [ "kvm" ];
}
