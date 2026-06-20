{ configSource, diskoPackage, pkgs, username }:

pkgs.writeShellApplication {
  name = "install-nixos";

  runtimeInputs = with pkgs; [
    coreutils
    gawk
    git
    gnugrep
    mkpasswd
    nixos-install-tools
    sbctl
    util-linux
    diskoPackage
  ];

  text = ''
    usage() {
      echo "Usage: install-nixos --disk /dev/disk/by-id/DEVICE"
    }

    if [[ ''${1-} == "--help" || ''${1-} == "-h" ]]; then
      usage
      exit 0
    fi

    if [[ ''${1-} != "--disk" || $# -ne 2 ]]; then
      usage >&2
      exit 2
    fi

    if [[ $EUID -ne 0 ]]; then
      echo "Run this installer as root." >&2
      exit 1
    fi

    umask 022

    if [[ -t 1 ]]; then
      red=$'\033[1;31m'
      yellow=$'\033[1;33m'
      reset=$'\033[0m'
    else
      red=
      yellow=
      reset=
    fi

    disk=$2
    case "$disk" in
      /dev/disk/by-id/*) ;;
      *)
        echo "Refusing a disk that is not identified through /dev/disk/by-id/." >&2
        exit 1
        ;;
    esac

    if [[ ! -b $disk ]]; then
      echo "Target is not a block device: $disk" >&2
      exit 1
    fi

    resolved_disk=$(readlink -f -- "$disk")
    if [[ $(lsblk -dnro TYPE -- "$resolved_disk") != "disk" ]]; then
      echo "Target is not a whole disk: $disk -> $resolved_disk" >&2
      exit 1
    fi

    if lsblk -nrpo MOUNTPOINT -- "$resolved_disk" | grep -q '[^[:space:]]'; then
      echo "Refusing to erase a disk with mounted filesystems:" >&2
      lsblk -o NAME,PATH,SIZE,TYPE,MOUNTPOINTS -- "$resolved_disk" >&2
      exit 1
    fi

    printf '\n%sWARNING: The following disk will be completely erased:%s\n' \
      "$red" "$reset"
    lsblk -d -o NAME,PATH,SIZE,MODEL,SERIAL,TRAN -- "$resolved_disk"
    printf '\n%sNo changes have been made yet.%s\n\n' "$yellow" "$reset"

    read -r -s -p "Password for ${username}: " password
    echo
    read -r -s -p "Confirm password: " password_confirmation
    echo

    if [[ -z $password || $password != "$password_confirmation" ]]; then
      unset password password_confirmation
      echo "Passwords were empty or did not match; nothing was changed." >&2
      exit 1
    fi

    workdir=$(mktemp -d)
    target_home="$workdir/target-home"

    cleanup() {
      if mountpoint -q "$target_home"; then
        umount "$target_home"
      fi
      rm -rf "$workdir"
    }
    trap cleanup EXIT

    config_dir="$workdir/config"
    mkdir -p "$config_dir"
    cp -R ${configSource}/. "$config_dir/"
    chmod -R u+w "$config_dir"

    nixos-generate-config --show-hardware-config --no-filesystems \
      > "$config_dir/modules/hardware-configuration.nix"

    home_config="$workdir/home-config"
    git clone --branch master --single-branch \
      https://github.com/Onred/nixos.git "$home_config"
    cp "$config_dir/modules/hardware-configuration.nix" \
      "$home_config/modules/hardware-configuration.nix"

    (
      umask 077
      printf '%s\n' "$password" | mkpasswd --method=yescrypt --stdin \
        > "$workdir/${username}-password-hash"
    )
    unset password password_confirmation

    (
      umask 077
      mkdir -p "$workdir/sbctl"
      sbctl --disable-landlock create-keys \
        --export "$workdir/sbctl/keys" \
        --database-path "$workdir/sbctl/GUID"
    )
    cp -R "$workdir/sbctl" "$workdir/sbctl-persist"

    echo
    echo "Hardware configuration and initial secrets are ready."
    printf '%sThe selected disk and its current layout will be erased:%s\n' \
      "$red" "$reset"
    echo "  $disk -> $resolved_disk"
    lsblk -o NAME,PATH,SIZE,TYPE,FSTYPE,LABEL,MOUNTPOINTS,MODEL,SERIAL \
      -- "$resolved_disk"
    echo
    printf '%sType YES in all capitals to continue:%s ' "$red" "$reset"
    read -r confirmation
    if [[ $confirmation != "YES" ]]; then
      echo "Confirmation was not YES; nothing was changed." >&2
      exit 1
    fi

    disko-install \
      --write-efi-boot-entries \
      --flake "$config_dir#nixos" \
      --disk main "$disk" \
      --extra-files "$workdir/${username}-password-hash" /persist/secrets/${username}-password-hash \
      --extra-files "$workdir/sbctl" /var/lib/sbctl \
      --extra-files "$workdir/sbctl-persist" /persist/var/lib/sbctl \
      --extra-files "$config_dir" /etc/nixos

    filesystem_device=$(
      lsblk -nrpo PATH,LABEL -- "$resolved_disk" \
        | awk '$2 == "nixos" { print $1; exit }'
    )
    if [[ -z $filesystem_device ]]; then
      echo "Installation succeeded, but the new Btrfs filesystem could not be located." >&2
      echo "The repository remains available in /etc/nixos on the target." >&2
      exit 1
    fi

    mkdir -p "$target_home"
    mount -o subvol=home "$filesystem_device" "$target_home"
    if [[ ! -d $target_home/${username} ]]; then
      echo "Installation succeeded, but the ${username} home directory was not created." >&2
      echo "The repository remains available in /etc/nixos on the target." >&2
      exit 1
    fi

    home_owner=$(stat -c '%u:%g' "$target_home/${username}")
    cp -a "$home_config" "$target_home/${username}/nixos"
    chown -R "$home_owner" "$target_home/${username}/nixos"
    umount "$target_home"

    echo
    echo "Installation complete."
    echo "Working repository: /home/${username}/nixos"
    echo "Recovery snapshot:  /etc/nixos"
  '';
}
