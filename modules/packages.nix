{
  pkgs,
  unstable,
  username,
  ...
}:

{
  programs.direnv.enable = true;
  programs.firefox.enable = true;
  programs.gamemode.enable = true;
  programs.nix-ld.enable = true;

  programs.steam = {
    enable = true;

    package = pkgs.steam.override {
      extraEnv = {
        MANGOHUD = "1";
        PROTON_ENABLE_WAYLAND = "1";
        PROTON_DXVK_LOWLATENCY = "1";
        DXVK_FRAME_PACE = "low-latency-vrr-240";
      };
    };
  };

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

    # Development
    btop
    fastfetch
    neovim
    unstable.codex

    # Gaming
    faugus-launcher
    lutris
    mangohud
    protonplus
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
