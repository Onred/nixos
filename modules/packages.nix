{
  pkgs,
  unstable,
  username,
  ...
}:

{
  programs.direnv.enable = true;
  programs.firefox.enable = true;
  programs.nix-ld.enable = true;

  # Firefox 153 corrupts browser chrome on NVIDIA/Wayland.
  environment.sessionVariables.MOZ_ENABLE_WAYLAND = "0";

  fonts.packages = with pkgs; [
    nerd-fonts.jetbrains-mono
    inter
  ];

  fonts.fontconfig.defaultFonts.sansSerif = [
    "Inter"
    "Noto Sans"
  ];

  users.users.${username}.packages = with pkgs; [
    # Desktop
    alacritty
    discord
    drawy
    libreoffice-qt6
    localsend
    pavucontrol
    vscode
    zed-editor
    btop
    fastfetch
    neovim
    unstable.codex
  ];

  environment.systemPackages = with pkgs; [
    gh
    git
    jq
    nh
    pciutils
    sbctl
    tree
    usbutils
    vim
    wget
  ];
}
