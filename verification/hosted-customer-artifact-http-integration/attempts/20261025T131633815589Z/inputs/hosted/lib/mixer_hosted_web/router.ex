defmodule MixerHostedWeb.Router do
  use Phoenix.Router

  pipeline :customer_artifacts do
    plug(MixerHostedWeb.Plugs.BearerIdentity)
  end

  # This only reports process liveness. It neither queries PostgreSQL nor claims
  # that auth, workers, migrations, delivery, or a production service are ready.
  get("/health/live", MixerHostedWeb.HealthController, :live)

  scope "/v3/orgs/:organization_id/projects/:project_id" do
    pipe_through(:customer_artifacts)
    put("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :upload)
    get("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :read)
    get("/audit", MixerHostedWeb.CustomerArtifactController, :audit)
  end
end
