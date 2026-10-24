import Config

config :mixer_hosted, ecto_repos: [MixerHosted.Repo]
config :phoenix, :json_library, Jason
config :jose, json_module: :jose_json_jason, unsecured_signing: false, crypto_fallback: false

config :mixer_hosted, MixerHostedWeb.Endpoint,
  adapter: Bandit.PhoenixAdapter,
  server: false,
  render_errors: [formats: [json: MixerHostedWeb.ErrorJSON], layout: false],
  debug_errors: false

config :logger, level: :warning
