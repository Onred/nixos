{ config, pkgs, inputs, ... }:

let
  dotfiles = "${config.home.homeDirectory}/dotfiles";
  create_symlink = path: config.lib.file.mkOutOfStoreSymlink path;
  configs = builtins.listToAttrs (map (config: { name = config; value = config; })
    [
      "niri"
      "hypr"
      "nvim"
    ]
  );
in

{
  imports = [
    ./modules/neovim.nix
    inputs.dankMaterialShell.homeModules.dankMaterialShell.default
    # inputs.noctalia.homeModules.default
  ];

  home.username = "onred";
  home.homeDirectory = "/home/onred";
  home.stateVersion = "25.05";

  home.packages = with pkgs; [
    btop
    fastfetch
    discord
    bitwarden-desktop
    protonup-qt
    alacritty
    nautilus
    pavucontrol
    radeontop
  ];

  programs.bash = {
    enable = true;
    shellAliases = {
      nrs = "nh os switch -ua ${dotfiles}";
    };
    initExtra = ''
      export PS1='\[\e[38;5;75m\]\u\[\e[38;5;75m\]@\[\e[38;5;75m\]\h\[\e[0m\] \[\e[38;5;113m\]\w\[\e[0m\] \[\e[38;5;189m\]\$\[\e[0m\] '
    '';
  };

  programs.git = {
    enable = true;
    settings.user.name = "Onred";
    settings.user.email = "jared@onred.com";
  };

  programs.firefox.enable = true;
  programs.firefox.profiles.default.extensions.force = true;

  programs.dankMaterialShell = {
    enable = true;
    quickshell.package = inputs.quickshell.packages.x86_64-linux.quickshell;
  };

  stylix.targets = {
    neovim.enable = false;
    firefox.profileNames = [ "default" ];
    firefox.colorTheme.enable = true;
  };
  # programs.noctalia-shell.enable = true;
  # programs.noctalia-shell.systemd.enable = true;

  # Make linked xdg config files from the configs listed above
  xdg.configFile = builtins.mapAttrs
    (nixpath: dotpath: {
      source = create_symlink "${dotfiles}/config/${dotpath}";
      recursive = true;
    })
    configs;
}
