{ lib, pkgs, ... }:

let
  models = import ./models.nix;
in
{
  virtualisation.docker.enable = true;
  hardware.nvidia-container-toolkit.enable = true;

  services.llama-swap = {
    enable = true;
    listenAddress = "127.0.0.1";
    port = 8082;
    settings = {
      healthCheckTimeout = 7200;
      models.qwen-flash = {
        proxy = "http://127.0.0.1:\${PORT}";
        checkEndpoint = "/health";
        useModelName = models.qwen.serverName;
        ttl = 120;
        unloadTimeout = 150;
        cmd = ''
          ${pkgs.docker}/bin/docker run --rm --pull=always --name strata-qwen
          --device=nvidia.com/gpu=all
          --publish 127.0.0.1:''${PORT}:8080
          --volume /var/lib/strata:/data
          --ulimit memlock=-1:-1
          --shm-size=2g
          --memory=36g --memory-swap=36g
          --stop-timeout=120
          --env FAMILY=${models.qwen.family}
          --env MODEL=${models.qwen.quant}
          --env CONTEXT=${toString models.qwen.context}
          --env PARALLEL=1
          --env VISION=off
          --env KV=int8
          --env TUNE=skip
          --env API_KEY=strata-local-only
          --env 'STRATA_SET=vram-reserve-mib=4564 resident-experts=true'
          ghcr.io/niko1221/strata:latest-cuda13
        '';
        cmdStop = "${pkgs.docker}/bin/docker stop --time 120 strata-qwen";
      };
    };
  };

  systemd.services.llama-swap = {
    requires = [ "docker.service" ];
    after = [ "docker.service" ];
    serviceConfig = {
      SupplementaryGroups = [ "docker" ];
      PrivateUsers = lib.mkForce false;
      TimeoutStopSec = "180s";
    };
  };

  systemd.tmpfiles.rules = [ "d /var/lib/strata 0750 root root -" ];

  environment.persistence."/persist".directories = [
    "/var/lib/strata"
    "/var/lib/docker"
    "/var/lib/containerd"
  ];

  services.restic.backups.desktop.exclude = [
    "/persist/var/lib/strata"
    "/persist/var/lib/docker"
    "/persist/var/lib/containerd"
  ];
}
