{
  imports = [
    # Enable ./comfyui.nix when the comfyui-nix input is active.
    ./ollama.nix
    ./local-model-tools.nix
  ];
}
