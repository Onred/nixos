{ ... }:

{
  fileSystems."/mnt/data" = {
    device = "/dev/disk/by-label/data";
    fsType = "ext4";
    options = [
      "nofail"
      "x-systemd.automount"
      "x-systemd.device-timeout=3s"
    ];
  };
}
