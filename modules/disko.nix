{ inputs, ... }:

{
  imports = [ inputs.disko.nixosModules.disko ];

  disko.devices.disk.main = {
    type = "disk";

    # Deliberately invalid: the installer will supply the selected target with
    # `disko-install --disk main ...`.
    device = "/dev/disk/by-id/SET_TARGET_DISK_DURING_INSTALL";

    content = {
      type = "gpt";
      partitions = {
        ESP = {
          size = "1G";
          type = "EF00";
          content = {
            type = "filesystem";
            format = "vfat";
            mountpoint = "/boot";
            mountOptions = [ "umask=0077" ];
          };
        };

        system = {
          size = "100%";
          content = {
            type = "btrfs";
            extraArgs = [
              "-L"
              "nixos"
            ];
            subvolumes = {
              "/root" = {
                mountpoint = "/";
              };

              "/nix" = {
                mountpoint = "/nix";
              };

              "/persist" = {
                mountpoint = "/persist";
              };

              "/home" = {
                mountpoint = "/home";
              };
            };
          };
        };
      };
    };
  };
}
