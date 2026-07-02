{ pkgs, ... }:

{
  environment.systemPackages = with pkgs; [
    (writeShellApplication {
      name = "update-flake";
      runtimeInputs = [ git nix ];
      text = ''
        cd ~/nixos || exit 1

        sudo -v

        echo "Updating flake inputs..."
        nix flake update

        # Check if flake.lock actually changed
        if ! git diff --quiet flake.lock; then
          echo "flake.lock changed — building..."
          nh os boot .

          echo "Committing flake.lock…"
          git add flake.lock
          git commit -m "chore: update flake.lock"
        else
          echo "No changes in flake.lock."
        fi
      '';
    })
  ];
}
