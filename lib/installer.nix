{ configSource, diskoPackage, pkgs, username }:

pkgs.writeShellApplication {
  name = "install-nixos";

  runtimeInputs = with pkgs; [
    coreutils
    gawk
    git
    gnugrep
    gum
    mkpasswd
    nixos-install-tools
    sbctl
    util-linux
    diskoPackage
  ];

  text = ''
    usage() {
      echo "Usage: install-nixos [--disk /dev/disk/by-id/DEVICE]"
    }

    if [[ ''${1-} == "--help" || ''${1-} == "-h" ]]; then
      usage
      exit 0
    fi

    disk=
    if [[ $# -eq 0 ]]; then
      disk=
    elif [[ ''${1-} == "--disk" && $# -eq 2 ]]; then
      disk=$2
    else
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

    choose_disk() {
      if [[ ! -t 0 || ! -t 1 ]]; then
        echo "No disk was specified and interactive selection is unavailable." >&2
        usage >&2
        exit 2
      fi

      candidates=$(mktemp)
      index=0

      while IFS= read -r disk_path; do
        best_id=

        for by_id in /dev/disk/by-id/*; do
          [[ -e $by_id ]] || continue
          case "$(basename -- "$by_id")" in
            *-part[0-9]*) continue ;;
          esac

          if [[ $(readlink -f -- "$by_id") != "$disk_path" ]]; then
            continue
          fi

          best_id=$by_id
          case "$(basename -- "$by_id")" in
            nvme-*|ata-*|usb-*)
              break
              ;;
          esac
        done

        if [[ -z $best_id ]]; then
          continue
        fi

        size=$(lsblk -dnro SIZE -- "$disk_path")
        model=$(lsblk -dnro MODEL -- "$disk_path" | awk '{$1=$1; print}')
        serial=$(lsblk -dnro SERIAL -- "$disk_path" | awk '{$1=$1; print}')
        tran=$(lsblk -dnro TRAN -- "$disk_path" | awk '{$1=$1; print}')

        printf '%s\t%s\t%s\t%s\t%s\t%s\n' \
          "$index" "$best_id" "$size" "$tran" "$model" "$serial" >> "$candidates"
        index=$((index + 1))
      done < <(lsblk -dnpo PATH,TYPE | awk '$2 == "disk" { print $1 }')

      if [[ ! -s $candidates ]]; then
        echo "No whole disks with /dev/disk/by-id identifiers were found." >&2
        exit 1
      fi

      selection=$(
        awk -F '\t' '{
          printf "[%s] %s %s %s %s :: %s\n", $1, $3, $4, $5, $6, $2
        }' "$candidates" \
          | gum choose --header "Select the installation target disk"
      ) || true

      if [[ -z $selection ]]; then
        echo "No disk selected; nothing was changed." >&2
        exit 1
      fi

      selected_index=''${selection%%]*}
      selected_index=''${selected_index#[}
      disk=$(awk -F '\t' -v selected="$selected_index" '$1 == selected { print $2 }' "$candidates")

      if [[ -z $disk ]]; then
        echo "Selected disk could not be resolved." >&2
        exit 1
      fi
    }

    if [[ -z $disk ]]; then
      choose_disk
    fi

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
      > "$config_dir/hardware-configuration.nix"

    home_config="$workdir/home-config"
    git clone --branch master --single-branch \
      https://github.com/Onred/nixos.git "$home_config"
    cp "$config_dir/hardware-configuration.nix" \
      "$home_config/hardware-configuration.nix"

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
