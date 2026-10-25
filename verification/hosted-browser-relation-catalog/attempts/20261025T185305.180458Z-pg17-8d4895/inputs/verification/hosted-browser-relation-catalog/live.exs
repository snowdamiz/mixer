# Explicit ordinary dependency closure only, no application boot or frozen tools.
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex")
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex")

defmodule RelationProbe.Admin do
  use Ecto.Repo, otp_app: :relation_probe, adapter: Ecto.Adapters.Postgres
end
defmodule RelationProbe.Lifecycle do
  use Ecto.Repo, otp_app: :relation_probe, adapter: Ecto.Adapters.Postgres
end

defmodule RelationProbe do
  alias MixerHosted.BrowserAuth.RelationCatalog, as: Catalog
  @roles %{lifecycle_login: "browser_lifecycle", writer: "browser_writer",
    relation_owner: "browser_schema_owner", ordinary_runtime_login: "browser_ordinary"}
  def sql(repo, text), do: Ecto.Adapters.SQL.query!(repo,text,[],log: false)
  def check(repo), do: Catalog.check_relation_surface!(repo,@roles,System.monotonic_time(:millisecond)+5000)
  def policy(repo) do
    for text<-["SET LOCAL search_path=pg_catalog","SET LOCAL jit=off","SET LOCAL statement_timeout='5s'",
      "SET LOCAL lock_timeout='500ms'","SET LOCAL idle_in_transaction_session_timeout='5s'","SET LOCAL bytea_output=hex"],
      do: sql(repo,text)
  end
  def run do
    result=RelationProbe.Lifecycle.transaction(fn -> policy(RelationProbe.Lifecycle);check(RelationProbe.Lifecycle) end,log: false)
    IO.inspect(result,label: "baseline")
    if result!={:ok,:relation_surface_verified},do: raise("baseline failed")
  end
end
port=System.fetch_env!("RELATION_PORT")|>String.to_integer()
children=for {repo,user}<-[{RelationProbe.Admin,"browser_admin"},{RelationProbe.Lifecycle,"browser_lifecycle"}] do
  {:ok,pid}=repo.start_link(hostname: "127.0.0.1",port: port,database: "browser_storage",username: user,
    pool_size: 1,log: false,backoff_type: :stop)
  pid
end
try do
  RelationProbe.run()
after
  Enum.each(children,&GenServer.stop/1)
end
