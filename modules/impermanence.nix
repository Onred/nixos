{ config, pkgs, utils, ... }:

{
  fileSystems."/persist".neededForBoot = true;

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/var/log"
      "/var/db/sudo"
      "/var/lib/nixos"
      "/etc/cups"
      "/var/lib/cups"
      {
        directory = "/var/lib/bluetooth";
        mode = "0700";
      }
      {
        directory = "/etc/NetworkManager/system-connections";
        mode = "0700";
      }
      {
        directory = "/var/lib/NetworkManager";
        mode = "0700";
      }
      {
        directory = "/var/lib/sbctl";
        mode = "0700";
      }
    ];
    files = [
      "/etc/machine-id"
      "/var/lib/systemd/random-seed"
    ];
  };

  boot.initrd.systemd.services.reset-root =
    let
      device = "/dev/disk/by-label/nixos";
      deviceUnit = "${utils.escapeSystemdPath device}.device";
    in
    {
      description = "Reset the Btrfs root subvolume";
      requiredBy = [ "sysroot.mount" ];
      before = [ "sysroot.mount" ];
      requires = [ deviceUnit ];
      after = [ deviceUnit ];
      unitConfig.DefaultDependencies = false;
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
      };
      path = with pkgs; [
        btrfs-progs
        coreutils
        findutils
        config.boot.initrd.systemd.package.util-linux
      ];

      script = ''
        mkdir -p /btrfs_tmp
        mount -o subvol=/ ${device} /btrfs_tmp
        trap 'mountpoint -q /btrfs_tmp && umount /btrfs_tmp' EXIT

        old_roots=/btrfs_tmp/old_roots
        mkdir -p "$old_roots"

        if [[ -e /btrfs_tmp/root ]]; then
          archive="$old_roots/$(date --utc "+%Y-%m-%d_%H-%M-%S")"
          mkdir "$archive"
          mv /btrfs_tmp/root "$archive/root"
        fi

        for archive in $(
          find "$old_roots" -mindepth 1 -maxdepth 1 -type d -mtime +30
        ); do
          if btrfs subvolume delete --recursive -- "$archive/root"; then
            rmdir "$archive"
          else
            echo "Warning: could not delete expired root in $archive" >&2
          fi
        done

        btrfs subvolume create /btrfs_tmp/root
        umount /btrfs_tmp
        trap - EXIT
        rmdir /btrfs_tmp
      '';
    };
}
