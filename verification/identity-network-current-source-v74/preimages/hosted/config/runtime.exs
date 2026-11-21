import Config

# Tests start their own isolated services explicitly with --no-start. Normal
# startup and releases have no fallback credentials, database, or combined role.
if config_env() != :test do
  env = System.get_env()
  # RuntimeConfig validates MIXER_BUILD_OPERATION_INTENT for the builds_v1
  # processor. The selection is part of the startup snapshot.
  settings = MixerHosted.RuntimeConfig.load!(env)
  release = MixerHosted.Releases.RuntimeProvisioning.load!(env, settings)
  settings = MixerHosted.CustomerArtifacts.LocalUpload.configure!(env, settings, release)
  installation = MixerHosted.BrowserAuth.Installation.load!(env, settings)
  config :mixer_hosted, :startup, {settings, installation}

  case release do
    :disabled ->
      :ok

    {target, delivery} ->
      config :mixer_hosted, :local_release_target, target
      config :mixer_hosted, :local_release_delivery, delivery
  end

  writer = MixerHosted.Releases.RuntimeProvisioning.writer_options!(env, settings, release)

  if writer do
    config :mixer_hosted, MixerHosted.Releases.WriterRepo, writer
  end

  config :mixer_hosted,
         :local_stage_promotion_directions,
         MixerHosted.Releases.RuntimeProvisioning.stage_promotion_directions!(
           env,
           release,
           writer
         )

  config :mixer_hosted,
         MixerHosted.CustomerBuilds.LocalStarter,
         MixerHosted.CustomerBuilds.LocalStarter.runtime_config!(env)

  config :mixer_hosted, :role, settings.role
  config :mixer_hosted, :identity_startup, settings.identity_startup
  config :mixer_hosted, MixerHosted.Repo, settings.repo
  config :mixer_hosted, Oban, settings.oban
  config :mixer_hosted, MixerHostedWeb.Endpoint, settings.endpoint
end
