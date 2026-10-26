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

  users.users.${username}.packages = [
    pkgs.alacritty
    pkgs.discord
    pkgs.drawy
    pkgs.libreoffice-qt6
    pkgs.localsend
    pkgs.pavucontrol
    pkgs.vscode
    pkgs.zed-editor
    pkgs.btop
    pkgs.fastfetch
    pkgs.neovim
    unstable.codex
  ];

  environment.systemPackages = [
    pkgs.gh
    pkgs.git
    pkgs.jq
    pkgs.nh
    pkgs.pciutils
    pkgs.sbctl
    pkgs.tree
    pkgs.usbutils
    pkgs.vim
    pkgs.wget
  ];

  fonts = {
    packages = [
      pkgs.nerd-fonts.jetbrains-mono
      pkgs.inter
    ];
    fontconfig.defaultFonts.sansSerif = [
      "Inter"
      "Noto Sans"
    ];
  };
}
