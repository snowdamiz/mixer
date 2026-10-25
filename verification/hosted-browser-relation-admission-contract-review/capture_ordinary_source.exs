# Independent inert source evaluation. No Repo, Ecto application, SQL driver,
# database connection, product admission code or producer checker is loaded.
defmodule Ecto.Migration do
  defmacro __using__(_) do
    quote do
      import Ecto.Migration, only: [execute: 1]
    end
  end

  def execute(sql) when is_binary(sql) do
    Process.put(:review_statements, [
      {Process.get(:review_origin), sql} | Process.get(:review_statements, [])
    ])

    :ok
  end
end

Code.require_file("hosted/lib/mixer_hosted/browser_auth/storage_schema.ex")
Code.require_file("hosted/lib/mixer_hosted/customer_artifacts/schema.ex")

for {file, module} <- [
      {"20261025000003_add_customer_authorization.exs",
       MixerHosted.Repo.Migrations.AddCustomerAuthorization},
      {"20261025000004_add_authorization_state_revisions.exs",
       MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
      {"20261025000005_add_customer_artifact_storage.exs",
       MixerHosted.Repo.Migrations.AddCustomerArtifactStorage},
      {"20261025000006_add_customer_workspace_discovery.exs",
       MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery},
      {"20261025000007_add_browser_sessions.exs", MixerHosted.Repo.Migrations.AddBrowserSessions}
    ] do
  path = "hosted/priv/repo/migrations/" <> file
  Code.require_file(path)
  Process.put(:review_origin, path)
  module.up()
end

for sql <-
      MixerHosted.BrowserAuth.StorageSchema.provisioning_statements(
        "review_writer",
        "review_lifecycle"
      ) do
  Process.put(:review_origin, "StorageSchema.provisioning_statements/2")
  Ecto.Migration.execute(sql)
end

for {origin, sql} <- Enum.reverse(Process.get(:review_statements)) do
  IO.puts("sql\t" <> origin <> "\t" <> Base.encode64(sql))
end

for name <-
      ~w(mixer_browser_integrity mixer_browser_attempt_integrity mixer_browser_event_integrity mixer_browser_event_immutable) do
  source = MixerHosted.BrowserAuth.StorageSchema.catalog_manifest().functions[name].source
  IO.puts("function_source\t" <> name <> "\t" <> Base.encode64(source))
end
