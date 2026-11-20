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
    post("/orgs", MixerHostedWeb.CustomerWorkspaceAdminController, :create_organization)

    post(
      "/orgs/:organization_id/projects",
      MixerHostedWeb.CustomerWorkspaceAdminController,
      :create_project
    )

    put(
      "/orgs/:organization_id/memberships/:target_id",
      MixerHostedWeb.CustomerWorkspaceAdminController,
      :set_member
    )

    get("/orgs/:organization_id/usage", MixerHostedWeb.CustomerWorkspaceAdminController, :usage)
    get("/orgs/:organization_id/export", MixerHostedWeb.CustomerWorkspaceAdminController, :export)

    delete(
      "/orgs/:organization_id/projects/:target_id",
      MixerHostedWeb.CustomerWorkspaceAdminController,
      :delete_project
    )

    delete(
      "/orgs/:organization_id",
      MixerHostedWeb.CustomerWorkspaceAdminController,
      :delete_organization
    )

    get("/projects", MixerHostedWeb.CustomerWorkspaceController, :projects)
  end

  scope "/v3/orgs/:organization_id/projects/:project_id" do
    pipe_through(:customer_identity)
    put("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :upload)
    get("/artifacts/:manifest_sha256", MixerHostedWeb.CustomerArtifactController, :read)
    get("/audit", MixerHostedWeb.CustomerArtifactController, :audit)
  end
end
