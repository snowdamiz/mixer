# Pure command capture. No Ecto/Postgrex/application/Repo or database is loaded.
# Only the four allowlisted accepted source files below are evaluated.
defmodule Ecto.Migration do
  defmacro __using__(_) do
    quote do
      import Ecto.Migration, only: [execute: 1]
    end
  end

  def execute(sql) when is_binary(sql) do
    Process.put(:relation_contract_ddl, [sql | Process.get(:relation_contract_ddl, [])])
    :ok
  end
end

root = Path.expand("../..", __DIR__)
storage = Path.join(root, "hosted/lib/mixer_hosted/browser_auth/storage_schema.ex")
Code.require_file(storage)

ordinary =
  for {name, module} <- [
        {"20261025000003_add_customer_authorization.exs", MixerHosted.Repo.Migrations.AddCustomerAuthorization},
        {"20261025000004_add_authorization_state_revisions.exs", MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions},
        {"20261025000006_add_customer_workspace_discovery.exs", MixerHosted.Repo.Migrations.AddCustomerWorkspaceDiscovery}
      ], into: %{} do
    Code.require_file(Path.join(root, "hosted/priv/repo/migrations/" <> name))
    Process.put(:relation_contract_ddl, [])
    module.up()
    {name, Enum.reverse(Process.get(:relation_contract_ddl))}
  end

alias MixerHosted.BrowserAuth.StorageSchema
data = %{
  "ordinary" => ordinary,
  "browser" => StorageSchema.statements(),
  "provisioning" => StorageSchema.provisioning_statements("relation_contract_writer", "relation_contract_login"),
  "trigger_function_source_hashes" =>
    Map.new(~w(mixer_browser_integrity mixer_browser_attempt_integrity mixer_browser_event_integrity mixer_browser_event_immutable), fn name ->
      source = Map.fetch!(StorageSchema.catalog_manifest().functions, name).source
      {name, %{"sha256" => Base.encode16(:crypto.hash(:sha256, source), case: :lower), "bytes" => byte_size(source)}}
    end)
}
IO.puts(:json.encode(data))
