SAVE_FILE="${XDG_RUNTIME_DIR:-/tmp}/sunshine_saved_mode"

modes_for_output() {
  kscreen-doctor --outputs 2>/dev/null \
    | awk -v output="$OUTPUT_NAME" '
      /^Output: / {
        in_output = ($0 ~ (" " output " "))
        next
      }
      in_output && /Modes:/ {
        for (i = 1; i <= NF; i++) {
          mode = $i
          sub(/^[0-9]+:/, "", mode)
          sub(/[!*].*/, "", mode)
          print mode
        }
      }
    '
}

current_mode() {
  kscreen-doctor --outputs 2>/dev/null \
    | awk -v output="$OUTPUT_NAME" '
      /^Output: / {
        in_output = ($0 ~ (" " output " "))
        next
      }
      in_output && /Modes:/ {
        for (i = 1; i <= NF; i++) {
          if ($i ~ /^[0-9]+:.*\*/) {
            mode = $i
            sub(/^[0-9]+:/, "", mode)
            sub(/[!*].*/, "", mode)
            print mode
            exit
          }
        }
      }
    '
}

resolve_mode() {
  modes_for_output \
    | awk -v requested="$1" '
      BEGIN {
        split(requested, parts, "@")
        requested_resolution = parts[1]
        requested_refresh = parts[2] + 0
      }
      {
        mode = $0

        if (mode == requested) {
          print mode
          exit
        }

        split(mode, mode_parts, "@")
        if (mode_parts[1] == requested_resolution) {
          diff = mode_parts[2] - requested_refresh
          if (diff < 0) {
            diff = -diff
          }
          if (diff <= 0.1) {
            print mode
            exit
          }
        }
      }
    '
}

set_mode() {
  mode=$(resolve_mode "$1")
  if [[ -z "$mode" ]]; then
    return 1
  fi

  kscreen-doctor "output.$OUTPUT_NAME.mode.$mode"
}

case "${1:-}" in
  start)
    if [[ $# -lt 2 ]]; then
      echo "Usage: $0 start MODE [MODE ...]" >&2
      exit 1
    fi
    shift

    if [[ ! -f "$SAVE_FILE" ]]; then
      active_mode=$(current_mode)

      if [[ -n "$active_mode" ]]; then
        echo "$active_mode" > "$SAVE_FILE"
      else
        echo "Warning: could not detect active mode" >&2
        exit 1
      fi
    fi

    for mode in "$@"; do
      if set_mode "$mode"; then
        exit 0
      fi
    done

    echo "Warning: none of the requested display modes worked: $*" >&2
    exit 1
    ;;
  stop)
    if [[ -f "$SAVE_FILE" ]]; then
      saved=$(cat "$SAVE_FILE")
      set_mode "$saved"
      rm -f "$SAVE_FILE"
    else
      echo "No saved mode found, skipping restore" >&2
    fi
    ;;
  *)
    echo "Usage: $0 start MODE [MODE ...] | stop" >&2
    exit 1
    ;;
esac
