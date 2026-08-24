# Packaged and configured by modules/sunshine.nix.
SAVE_FILE="${XDG_RUNTIME_DIR:-/tmp}/sunshine_saved_mode"

kscreen_outputs() {
  local outputs

  if ! outputs=$(NO_COLOR=1 kscreen-doctor --outputs 2>&1); then
    echo "Error: kscreen-doctor --outputs failed while inspecting $OUTPUT_NAME" >&2
    printf '%s\n' "$outputs" >&2
    return 1
  fi

  printf '%s\n' "$outputs" \
    | awk '{ gsub(/\033\[[0-9;]*[[:alpha:]]/, ""); print }'
}

modes_for_output() {
  mode_entries_for_output | awk '{ print $2 }'
}

mode_entries_for_output() {
  local outputs
  local modes

  if ! outputs=$(kscreen_outputs); then
    return 1
  fi

  modes=$(
    awk -v output="$OUTPUT_NAME" '
      /^Output: / {
        in_output = ($0 ~ (" " output " "))
        next
      }
      in_output && /Modes:/ {
        for (i = 1; i <= NF; i++) {
          split($i, parts, ":")
          mode_id = parts[1]
          mode = parts[2]
          sub(/[!*].*/, "", mode)
          print mode_id, mode
        }
      }
    ' <<< "$outputs"
  )

  if [[ -z "$modes" ]]; then
    echo "Error: no modes found for output $OUTPUT_NAME" >&2
    echo "Available outputs:" >&2
    kscreen_outputs >&2
    return 1
  fi

  printf '%s\n' "$modes"
}

current_mode() {
  local outputs
  local mode

  if ! outputs=$(kscreen_outputs); then
    return 1
  fi

  mode=$(
    awk -v output="$OUTPUT_NAME" '
      /^Output: / {
        in_output = ($0 ~ (" " output " "))
        next
      }
      matched {
        next
      }
      in_output && /Modes:/ {
        for (i = 1; i <= NF; i++) {
          if ($i ~ /^[0-9]+:.*\*/) {
            mode = $i
            sub(/^[0-9]+:/, "", mode)
            sub(/[!*].*/, "", mode)
            print mode
            matched = 1
          }
        }
      }
    ' <<< "$outputs"
  )

  if [[ -z "$mode" ]]; then
    echo "Error: could not detect active mode for output $OUTPUT_NAME" >&2
    echo "Available outputs:" >&2
    kscreen_outputs >&2
    return 1
  fi

  printf '%s\n' "$mode"
}

resolve_mode() {
  local modes

  if ! modes=$(mode_entries_for_output); then
    return 1
  fi

  awk -v requested="$1" '
      BEGIN {
        split(requested, parts, "@")
        requested_resolution = parts[1]
        requested_refresh = parts[2] + 0
      }
      matched {
        next
      }
      {
        mode_id = $1
        mode = $2

        if (mode == requested) {
          print mode_id
          matched = 1
          next
        }

        split(mode, mode_parts, "@")
        if (mode_parts[1] == requested_resolution) {
          diff = mode_parts[2] - requested_refresh
          if (diff < 0) {
            diff = -diff
          }
          if (diff <= 0.1) {
            print mode_id
            matched = 1
          }
        }
      }
    ' <<< "$modes"
}

set_mode() {
  local mode
  local output

  if ! mode=$(resolve_mode "$1"); then
    return 1
  fi

  if [[ -z "$mode" ]]; then
    echo "Warning: requested mode $1 is not available for output $OUTPUT_NAME" >&2
    echo "Available modes for $OUTPUT_NAME:" >&2
    modes_for_output >&2
    return 1
  fi

  echo "Setting $OUTPUT_NAME to $1 using mode id $mode"

  if ! output=$(kscreen-doctor "output.$OUTPUT_NAME.mode.$mode" 2>&1); then
    printf '%s\n' "$output" >&2
    return 1
  fi

  if [[ "$output" == *"Unable to parse arguments"* ]]; then
    printf '%s\n' "$output" >&2
    return 1
  fi

  printf '%s\n' "$output"
}

case "${1:-}" in
  start)
    if [[ $# -lt 2 ]]; then
      echo "Usage: $0 start MODE [MODE ...]" >&2
      exit 1
    fi
    shift

    if [[ ! -f "$SAVE_FILE" ]]; then
      if ! active_mode=$(current_mode); then
        echo "Error: could not save the current display mode" >&2
        exit 1
      fi

      echo "$active_mode" > "$SAVE_FILE"
      echo "Saved current $OUTPUT_NAME mode: $active_mode"
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
      saved=$(<"$SAVE_FILE")
      set_mode "$saved"
      rm --force -- "$SAVE_FILE"
    else
      echo "No saved mode found, skipping restore" >&2
    fi
    ;;
  *)
    echo "Usage: $0 start MODE [MODE ...] | stop" >&2
    exit 1
    ;;
esac
