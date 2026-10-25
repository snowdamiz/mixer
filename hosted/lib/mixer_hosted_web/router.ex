defmodule MixerHostedWeb.Router do
  use Phoenix.Router

  pipeline :customer_identity do
    plug(MixerHostedWeb.Plugs.BearerIdentity)
  end

  # This only reports process liveness. It neither queries PostgreSQL nor claims
  # that auth, workers, migrations, delivery, or a production service are ready.
  get("/health/live", MixerHostedWeb.HealthController, :live)

  scope "/v3" do
    pipe_through(:customer_identity)
    get("/orgs", MixerHostedWeb.CustomerWorkspaceController, :organizations)
    get("/projects", MixerHostedWeb.CustomerWorkspaceController, :projects)
  end

  scope "/v3/orgs/:organization_id/projects/:project_id" do
    pipe_through(:customer_identity)
    put("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :upload)
    get("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :read)
    get("/audit", MixerHostedWeb.CustomerArtifactController, :audit)
  end
end
