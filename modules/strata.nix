{ pkgs, unstable, ... }:

let
  version = "0.1.44.1";
  image = "strata:${version}";
  source = pkgs.fetchFromGitHub {
    owner = "Niko1221";
    repo = "Strata";
    rev = "v${version}";
    hash = "sha256-Jfo2uldtyXW8Y/wQxA7WcYwtmzCGAOaXgnlMSo7K9LE=";
  };

  # Match the catalog schema to the CLI; local Qwen uses conventional tools.
  codexCatalog = pkgs.runCommand "strata-codex-models.json" {
    nativeBuildInputs = [ unstable.codex pkgs.jq ];
  } ''
    codex debug models --bundled | jq '
      {models: [
        (.models | (map(select(.tool_mode == null)) + .) | .[0])
        | .slug = "qwen3.8-flash-next-iq2_xs"
        | .display_name = "Qwen Flash (Strata, local)"
        | .description = "Local text model served by Strata"
        | .context_window = 32768 | .max_context_window = 32768
        | .default_reasoning_level = "medium"
        | .supported_reasoning_levels = [.supported_reasoning_levels[]
            | select(.effort == "low" or .effort == "medium" or .effort == "high")]
        | .input_modalities = ["text"]
        | .supports_search_tool = false | .supports_image_detail_original = false
        | .support_verbosity = false | .node_repl_disabled = true
        | .tool_mode = null | .use_responses_lite = false
        | .experimental_supported_tools = []
        | .additional_speed_tiers = [] | .service_tiers = []
        | .availability_nux = null | .upgrade = null
      ]}
    ' > "''$out"
  '';

  codexLocal = pkgs.writeShellApplication {
    name = "codex-local";
    runtimeInputs = [ unstable.codex ];
    text = ''
      exec codex --no-daemon \
        -m qwen3.8-flash-next-iq2_xs \
        -s workspace-write -a on-request \
        -c 'model_provider="strata"' \
        -c 'model_providers.strata={name="Strata (local)",base_url="http://127.0.0.1:8082/v1",wire_api="responses",stream_idle_timeout_ms=600000}' \
        -c 'model_catalog_json="${codexCatalog}"' \
        -c 'model_context_window=32768' \
        -c 'model_auto_compact_token_limit=24576' \
        -c 'model_reasoning_effort="medium"' \
        -c 'web_search="disabled"' \
        -c 'mcp_servers.local_gemma.enabled=false' \
        -c 'mcp_servers.openaiDeveloperDocs.enabled=false' \
        --disable apps --disable plugins --disable multi_agent \
        "''$@"
    '';
  };
in
{
  environment.systemPackages = [ codexLocal ];

  hardware.nvidia-container-toolkit.enable = true;

  virtualisation.oci-containers = {
    backend = "docker";
    containers.strata = {
      inherit image;
      autoStart = false;
      pull = "never";
      ports = [ "127.0.0.1:8082:8080" ];
      volumes = [ "/var/lib/strata:/data" ];
      devices = [ "nvidia.com/gpu=all" ];
      environment.MODEL = "IQ2_XS";
      extraOptions = [ "--ulimit=memlock=-1:-1" ];
    };
  };

  # Upstream provides a Dockerfile rather than a published container image.
  systemd.services.strata-image = {
    description = "Build the official Strata image for the RTX 4090";
    requires = [ "docker.service" ];
    after = [ "docker.service" ];
    path = [ pkgs.docker ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      TimeoutStartSec = "infinity";
    };
    script = ''
      if ! docker image inspect ${image} >/dev/null 2>&1; then
        docker build --build-arg CUDA_ARCHITECTURES=89 --tag ${image} ${source}
      fi
    '';
  };

  systemd.services.docker-strata = {
    requires = [ "strata-image.service" ];
    after = [ "strata-image.service" ];
  };

  systemd.tmpfiles.rules = [ "d /var/lib/strata 0750 root root -" ];

  environment.persistence."/persist".directories = [
    "/var/lib/strata"
    "/var/lib/docker"
    "/var/lib/containerd"
  ];
}
