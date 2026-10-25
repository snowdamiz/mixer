# Explicit ordinary dependency closure; no application boot or frozen tools.
Application.ensure_all_started(:ecto_sql)
Application.ensure_all_started(:postgrex)
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_manifest.ex")
Code.require_file("hosted/lib/mixer_hosted/browser_auth/relation_catalog.ex")
Code.require_file("verification/hosted-browser-relation-catalog/effects.exs")

defmodule RelationProbe.Admin do
  use Ecto.Repo, otp_app: :relation_probe, adapter: Ecto.Adapters.Postgres
end

defmodule RelationProbe.Lifecycle do
  use Ecto.Repo, otp_app: :relation_probe, adapter: Ecto.Adapters.Postgres
end

# Test-only Ecto adapter seam captures actual Postgrex results, then applies
# malformed-wire/fault controls to the real production checker. It supplies no
# product expectation. The SQL and the returned source-bound oracle stay fixed.
defmodule RelationProbe.WireRepo do
  def in_transaction?, do: Process.get(:probe_replay, false) or RelationProbe.Lifecycle.in_transaction?()
end

defmodule RelationProbe.WireSQL do
  def query(_, sql, params, options) do
    timeout=Keyword.fetch!(options,:timeout)
    true=is_integer(timeout) and timeout>0 and timeout<=5000
    true=Keyword.fetch!(options,:queue)===false
    true=false in Keyword.get_values(options,:log)
    n=Process.get(:probe_index,0)
    Process.put(:probe_index,n+1)
    Process.put(:probe_timeouts,[timeout|Process.get(:probe_timeouts,[])])
    if Process.get(:probe_replay,false) do
      {expected_sql,expected_params,result}=Enum.fetch!(Process.get(:probe_baseline),n)
      true=sql===expected_sql and params===expected_params
      {at,fun}=Process.get(:probe_fault,{-1,& &1})
      if n==at, do: fun.(result), else: {:ok,result}
    else
      result=Ecto.Adapters.SQL.query!(RelationProbe.Lifecycle,sql,params,
        timeout: timeout,queue: false,log: false)
      Process.put(:probe_capture,[{sql,params,result}|Process.get(:probe_capture,[])])
      {:ok,result}
    end
  end
end

defmodule RelationProbe do
  alias MixerHosted.BrowserAuth.RelationCatalog, as: Catalog
  alias MixerHosted.BrowserAuth.RelationCatalog.Unavailable
  @roles %{lifecycle_login: "browser_lifecycle", writer: "browser_writer",
    relation_owner: "browser_schema_owner", ordinary_runtime_login: "browser_ordinary"}
  def sql(repo,text),do: Ecto.Adapters.SQL.query!(repo,text,[],log: false,query_type: :text)
  def policy(repo) do
    for text<-["SET LOCAL search_path=pg_catalog","SET LOCAL jit=off","SET LOCAL statement_timeout='5s'",
      "SET LOCAL lock_timeout='500ms'","SET LOCAL idle_in_transaction_session_timeout='5s'","SET LOCAL bytea_output=hex"],
      do: sql(repo,text)
  end
  def check(repo,roles \\ @roles,deadline \\ nil),
    do: Catalog.check_relation_surface!(repo,roles,deadline || System.monotonic_time(:millisecond)+5000)
  def assert(true),do: :ok
  def assert(_),do: raise("probe assertion failed")
  def unavailable(fun) do
    try do
      fun.()
      raise "expected unavailable"
    rescue
      e in Unavailable ->
        assert(Exception.message(e)==="browser storage unavailable")
        :ok
    end
  end
  def record(name,fun) do
    try do
      fun.()
    rescue
      e -> IO.puts("failed method: "<>name); reraise e,__STACKTRACE__
    end
    Process.put(:probe_checks,[%{name: name,passed: true}|Process.get(:probe_checks,[])])
  end
  def baseline do
    assert(RelationProbe.Lifecycle.transaction(fn ->
      policy(RelationProbe.Lifecycle);check(RelationProbe.Lifecycle)
    end,log: false)==={:ok,:relation_surface_verified})
  end
  def attack(name,mutation) do
    record("actual mutation: "<>name,fn ->
      result=RelationProbe.Admin.transaction(fn ->
        sql(RelationProbe.Admin,mutation)
        fact_sql=RelationProbe.Effects.query(name)
        %{rows: [[effect]]}=Ecto.Adapters.SQL.query!(RelationProbe.Admin,fact_sql,[],log: false)
        assert(effect === true)
        Process.put(:probe_effects,[%{name: name,sql: fact_sql,observed: effect}|Process.get(:probe_effects,[])])
        sql(RelationProbe.Admin,"SET LOCAL SESSION AUTHORIZATION browser_lifecycle")
        policy(RelationProbe.Admin)
        unavailable(fn ->check(RelationProbe.Admin) end)
        RelationProbe.Admin.rollback(:expected_probe)
      end,log: false)
      assert(result==={:error,:expected_probe})
      baseline()
    end)
  end
  def replay(at,fun,deadline \\ nil) do
    Process.put(:probe_replay,true)
    Process.put(:probe_index,0)
    Process.put(:probe_timeouts,[])
    Process.put(:probe_fault,{at,fun})
    try do
      check(RelationProbe.WireRepo,@roles,deadline)
    after
      Process.put(:probe_replay,false)
    end
  end
  def run do
    record("actual lifecycle-login baseline", &baseline/0)
    record("no transaction rejects",fn ->unavailable(fn ->check(RelationProbe.Lifecycle) end) end)
    record("original expired deadline rejects before SQL",fn ->
      unavailable(fn ->check(RelationProbe.Lifecycle,@roles,System.monotonic_time(:millisecond)-1) end)
    end)
    record("future budget above original 5s cap rejects",fn ->
      unavailable(fn ->check(RelationProbe.Lifecycle,@roles,System.monotonic_time(:millisecond)+6000) end)
    end)
    for {name,roles}<-[{"extra key",Map.put(@roles,:request,true)},{"duplicate role",Map.put(@roles,:writer,@roles.lifecycle_login)},
      {"identifier injection",Map.put(@roles,:writer,"writer; select")},{"predefined role",Map.put(@roles,:writer,"pg_monitor")},
      {"NULL role",Map.put(@roles,:writer,nil)},{"missing owner",Map.delete(@roles,:relation_owner)}] do
      record("role shape: "<>name,fn ->unavailable(fn ->check(RelationProbe.Lifecycle,roles) end) end)
    end
    record("actual session identity mismatch denies",fn ->
      assert(RelationProbe.Admin.transaction(fn ->
        policy(RelationProbe.Admin);unavailable(fn ->check(RelationProbe.Admin) end)
      end,log: false)==={:ok,:ok})
    end)
    record("all four configured role names are parameterized",fn ->
      assert(RelationProbe.Admin.transaction(fn ->
        for {key,name}<-@roles,do: sql(RelationProbe.Admin,"ALTER ROLE "<>name<>" RENAME TO relation_"<>Atom.to_string(key))
        sql(RelationProbe.Admin,"SET LOCAL SESSION AUTHORIZATION relation_lifecycle_login")
        policy(RelationProbe.Admin)
        roles=Map.new(@roles,fn {key,_}->{key,"relation_"<>Atom.to_string(key)} end)
        assert(check(RelationProbe.Admin,roles)===:relation_surface_verified)
        RelationProbe.Admin.rollback(:expected_probe)
      end,log: false)==={:error,:expected_probe})
      baseline()
    end)
    record("unchanged catalog in identical admin/session-authorization transaction",fn ->
      assert(RelationProbe.Admin.transaction(fn ->
        sql(RelationProbe.Admin,"SET LOCAL SESSION AUTHORIZATION browser_lifecycle")
        policy(RelationProbe.Admin)
        assert(check(RelationProbe.Admin)===:relation_surface_verified)
        RelationProbe.Admin.rollback(:expected_probe)
      end,log: false)==={:error,:expected_probe})
    end)
    mutations=[
      {"extra check","ALTER TABLE public.mixer_browser_sessions ADD CHECK(true)"},
      {"weakened check","ALTER TABLE public.mixer_browser_sessions DROP CONSTRAINT mixer_browser_sessions_status_check; ALTER TABLE public.mixer_browser_sessions ADD CHECK(status IN('preauth','active','revoked','expired','extra'))"},
      {"NO INHERIT check","ALTER TABLE public.mixer_browser_sessions DROP CONSTRAINT mixer_browser_sessions_status_check; ALTER TABLE public.mixer_browser_sessions ADD CHECK(status IN('preauth','active','revoked','expired')) NO INHERIT"},
      {"extra column","ALTER TABLE public.mixer_browser_sessions ADD COLUMN surprise text"},
      {"dropped column slot","ALTER TABLE public.mixer_browser_sessions ADD COLUMN surprise text; ALTER TABLE public.mixer_browser_sessions DROP COLUMN surprise"},
      {"changed NOT NULL","ALTER TABLE public.mixer_browser_sessions ALTER COLUMN cookie_digest DROP NOT NULL"},
      {"changed collation","ALTER TABLE public.mixer_browser_sessions ALTER COLUMN generation TYPE text COLLATE \"C\""},
      {"changed default","ALTER TABLE public.mixer_authz_profiles ALTER COLUMN state_revision SET DEFAULT 2"},
      {"missing default","ALTER TABLE public.mixer_browser_oidc_attempts ALTER COLUMN ciphertext_version DROP DEFAULT"},
      {"corrupt bigint fast default","CREATE TABLE public.relation_fast_dummy(id bigint); ALTER TABLE public.relation_fast_dummy ADD COLUMN v bigint DEFAULT 2; UPDATE pg_catalog.pg_attribute a SET attmissingval=b.attmissingval FROM pg_catalog.pg_attribute b WHERE a.attrelid='public.mixer_authz_profiles'::regclass AND a.attname='state_revision' AND b.attrelid='public.relation_fast_dummy'::regclass AND b.attname='v'"},
      {"missing incoming FK","ALTER TABLE public.mixer_customer_idempotency DROP CONSTRAINT mixer_customer_idempotency_principal_id_fkey"},
      {"extra incoming FK","CREATE TABLE public.relation_incoming(id text REFERENCES public.mixer_authz_principals(id))"},
      {"unvalidated FK","UPDATE pg_catalog.pg_constraint SET convalidated=false WHERE conrelid='public.mixer_browser_oidc_attempts'::regclass AND contype='f'"},
      {"deferred FK","ALTER TABLE public.mixer_browser_oidc_attempts ALTER CONSTRAINT mixer_browser_oidc_attempts_browser_id_fkey DEFERRABLE INITIALLY DEFERRED"},
      {"same-named custom equality","CREATE OPERATOR public.= (LEFTARG=text,RIGHTARG=text,FUNCTION=pg_catalog.texteq); UPDATE pg_catalog.pg_constraint SET conpfeqop=ARRAY[(SELECT oid FROM pg_catalog.pg_operator WHERE oprnamespace='public'::regnamespace AND oprname='=')] WHERE conrelid='public.mixer_authz_families'::regclass AND confrelid='public.mixer_authz_principals'::regclass"},
      {"extra index","CREATE INDEX relation_extra_index ON public.mixer_browser_sessions(status)"},
      {"missing partial index","DROP INDEX public.mixer_browser_one_attempt"},
      {"partial index explicit name","ALTER INDEX public.mixer_browser_one_attempt RENAME TO relation_renamed_partial"},
      {"invalid index","UPDATE pg_catalog.pg_index SET indisvalid=false WHERE indexrelid='public.mixer_browser_one_attempt'::regclass"},
      {"index checkxmin","UPDATE pg_catalog.pg_index SET indcheckxmin=true WHERE indexrelid='public.mixer_browser_one_attempt'::regclass"},
      {"disabled user trigger","ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER mixer_browser_integrity"},
      {"user trigger explicit name","ALTER TRIGGER mixer_browser_integrity ON public.mixer_browser_sessions RENAME TO relation_wrong_trigger"},
      {"disabled child RI","DO $x$ DECLARE n name; BEGIN SELECT tgname INTO n FROM pg_catalog.pg_trigger WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal AND tgtype=5 LIMIT 1; EXECUTE format('ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER %I',n); END $x$"},
      {"disabled parent RI","DO $x$ DECLARE n name; BEGIN SELECT tgname INTO n FROM pg_catalog.pg_trigger WHERE tgrelid='public.mixer_browser_sessions'::regclass AND tgisinternal AND tgtype=9 LIMIT 1; EXECUTE format('ALTER TABLE public.mixer_browser_sessions DISABLE TRIGGER %I',n); END $x$"},
      {"changed trigger body","UPDATE pg_catalog.pg_proc SET prosrc=prosrc||E'\\n-- changed' WHERE oid='public.mixer_browser_integrity()'::regprocedure"},
      {"changed trigger configuration","ALTER FUNCTION public.mixer_browser_integrity() SET search_path=public"},
      {"trigger PUBLIC execution","GRANT EXECUTE ON FUNCTION public.mixer_browser_integrity() TO PUBLIC"},
      {"extra permissive policy","CREATE POLICY relation_extra ON public.mixer_authz_profiles FOR SELECT TO PUBLIC USING(true)"},
      {"extra restrictive policy","CREATE POLICY relation_extra ON public.mixer_authz_profiles AS RESTRICTIVE FOR SELECT TO PUBLIC USING(true)"},
      {"policy false to true","ALTER POLICY scoped_lock ON public.mixer_authz_profiles WITH CHECK(true)"},
      {"policy false to NULL","UPDATE pg_catalog.pg_policy SET polwithcheck=NULL WHERE polrelid='public.mixer_authz_profiles'::regclass AND polname='scoped_lock'"},
      {"writer policy to PUBLIC","ALTER POLICY mixer_browser_read ON public.mixer_browser_sessions TO PUBLIC"},
      {"writer extra table UPDATE","GRANT UPDATE ON public.mixer_browser_sessions TO browser_writer"},
      {"writer immutable column UPDATE","GRANT UPDATE(id) ON public.mixer_browser_sessions TO browser_writer"},
      {"lifecycle direct SELECT","GRANT SELECT ON public.mixer_browser_sessions TO browser_lifecycle"},
      {"ordinary browser SELECT","GRANT SELECT ON public.mixer_browser_sessions TO browser_ordinary"},
      {"PUBLIC relation SELECT","GRANT SELECT ON public.mixer_browser_sessions TO PUBLIC"},
      {"third-party role SELECT","GRANT SELECT ON public.mixer_browser_sessions TO representation_extra"},
      {"writer grant option","GRANT SELECT ON public.mixer_browser_sessions TO browser_writer WITH GRANT OPTION"},
      {"missing writer INSERT","REVOKE INSERT ON public.mixer_browser_sessions FROM browser_writer"},
      {"external membership SELECT","GRANT SELECT ON public.mixer_authz_memberships TO browser_writer"},
      {"external membership column UPDATE","GRANT UPDATE(principal_id) ON public.mixer_authz_memberships TO browser_writer"},
      {"external writable view","CREATE VIEW public.relation_view AS SELECT principal_id FROM public.mixer_authz_memberships; GRANT UPDATE ON public.relation_view TO browser_writer"},
      {"external sequence USAGE","CREATE SEQUENCE public.relation_seq; GRANT USAGE ON SEQUENCE public.relation_seq TO browser_writer"},
      {"schema CREATE escape","GRANT CREATE ON SCHEMA public TO browser_writer"},
      {"role membership escape","GRANT browser_writer TO browser_lifecycle"},
      {"disabled FORCE RLS","ALTER TABLE public.mixer_browser_sessions NO FORCE ROW LEVEL SECURITY"},
      {"extra browser view any schema","CREATE SCHEMA relation_escape; CREATE VIEW relation_escape.mixer_browser_shadow AS SELECT 1 AS n"},
      {"relation owner","ALTER TABLE public.mixer_browser_sessions OWNER TO browser_admin"},
      {"inheritance edge","CREATE TABLE public.relation_inherited() INHERITS(public.mixer_browser_sessions)"}
    ]
    major=System.get_env("RELATION_MAJOR")
    mutations=if major=="17",do: mutations++[{"PG17 application MAINTAIN","GRANT MAINTAIN ON public.mixer_browser_sessions TO browser_writer"}],else: mutations
    acl65=Enum.map_join(1..65,";",fn i->"CREATE ROLE relation_acl_"<>Integer.to_string(i) end)<>
      ";GRANT SELECT ON public.mixer_browser_sessions TO "<>Enum.map_join(1..65,",",fn i->"relation_acl_"<>Integer.to_string(i) end)
    escaped_names=Enum.map(0..63,fn i->String.duplicate("\\",60)<>String.pad_leading(Integer.to_string(i),3,"0") end)
    quoted=fn name->"\""<>name<>"\"" end
    create=Enum.map_join(escaped_names,";",fn name->"CREATE ROLE "<>quoted.(name) end)
    escaped_sql=fn s->"'"<>String.replace(s,"'","''")<>"'" end
    acl16=create<>";UPDATE pg_catalog.pg_class SET relacl=ARRAY(SELECT pg_catalog.makeaclitem(g.oid,r.oid,'SELECT',false) FROM pg_catalog.pg_roles g CROSS JOIN pg_catalog.pg_roles r WHERE g.rolname=ANY(ARRAY["<>
      Enum.map_join(escaped_names,",",escaped_sql)<>"]::text[]) AND r.rolname="<>escaped_sql.(hd(escaped_names))<>") WHERE oid='public.mixer_browser_sessions'::regclass"
    mutations=mutations++[{"ACL 65 entry scalar cap",acl65},{"ACL 16KiB scalar cap",acl16}]
    Enum.each(mutations,fn {name,sql}->attack(name,sql) end)
    record("automatic constraint and backing-index rename equivalence",fn ->
      assert(RelationProbe.Admin.transaction(fn ->
        sql(RelationProbe.Admin,"ALTER TABLE public.mixer_browser_sessions RENAME CONSTRAINT mixer_browser_sessions_pkey TO relation_automatic_key")
        sql(RelationProbe.Admin,"SET LOCAL SESSION AUTHORIZATION browser_lifecycle");policy(RelationProbe.Admin)
        assert(check(RelationProbe.Admin)===:relation_surface_verified)
        RelationProbe.Admin.rollback(:expected_probe)
      end,log: false)==={:error,:expected_probe})
    end)
    record("actual rewrite clears admitted bigint fast defaults",fn ->
      assert(RelationProbe.Admin.transaction(fn ->
        sql(RelationProbe.Admin,"ALTER TABLE public.mixer_authz_profiles ALTER COLUMN state_revision TYPE bigint USING state_revision+0; ALTER TABLE public.mixer_authz_bindings ALTER COLUMN revision TYPE bigint USING revision+0")
        sql(RelationProbe.Admin,"SET LOCAL SESSION AUTHORIZATION browser_lifecycle");policy(RelationProbe.Admin)
        assert(check(RelationProbe.Admin)===:relation_surface_verified)
        RelationProbe.Admin.rollback(:expected_probe)
      end,log: false)==={:error,:expected_probe})
    end)
    record("pre-deparse oversized node rejects without NULL equivalence",fn ->
      predicates=Enum.map_join(1..500," AND ",fn _->"octet_length(id)=16" end)
      attack("oversized source node","ALTER TABLE public.mixer_browser_sessions DROP CONSTRAINT mixer_browser_sessions_id_check; ALTER TABLE public.mixer_browser_sessions ADD CHECK("<>predicates<>")")
    end)
    # Current policy is independently read on the checked-out session.
    for {name,setting}<-[{"JIT enabled","SET LOCAL jit=on"},{"search path","SET LOCAL search_path=public"},
      {"statement policy","SET LOCAL statement_timeout='4s'"},{"lock policy","SET LOCAL lock_timeout='1s'"},
      {"bytea output","SET LOCAL bytea_output=escape"}] do
      record("transaction policy: "<>name,fn ->
        assert(RelationProbe.Lifecycle.transaction(fn ->
          policy(RelationProbe.Lifecycle);sql(RelationProbe.Lifecycle,setting)
          unavailable(fn ->check(RelationProbe.Lifecycle) end)
        end,log: false)==={:ok,:ok})
      end)
    end
    # Capture a clean actual result set once; fault replays never alter the oracle.
    {:ok,wire}=Agent.start_link(fn ->nil end,name: RelationProbe.WireRepo)
    :ok=Ecto.Repo.Registry.associate(wire,RelationProbe.WireRepo,
      %{pid: wire,telemetry: {RelationProbe.WireRepo,false,[]},sql: RelationProbe.WireSQL,opts: [],log_stacktrace_mfa: nil})
    try do
      Process.put(:probe_index,0);Process.put(:probe_capture,[])
      assert(RelationProbe.Lifecycle.transaction(fn ->
        policy(RelationProbe.Lifecycle);check(RelationProbe.WireRepo)
      end,log: false)==={:ok,:relation_surface_verified})
      calls=Process.get(:probe_capture)|>Enum.reverse()
      Process.put(:probe_baseline,calls)
      record("actual captured family count",fn ->assert(length(calls)==12) end)
      record("unmodified actual wire replay",fn ->assert(replay(-1,&{:ok,&1})===:relation_surface_verified) end)
      caps=[1,4,9,124,109,14,53,32,512,27,372,0]
      for {_,i}<-Enum.with_index(calls) do
        for {name,change}<-
          [{"cap plus one duplicate",fn r->%{r|rows: List.duplicate(List.first(r.rows)||[1],Enum.at(caps,i)+1),num_rows: Enum.at(caps,i)+1} end},
           {"NULL required field",fn r->
             case r.rows do
               [head|tail]->%{r|rows: [List.replace_at(head,0,nil)|tail]}
               []->%{r|rows: [[nil]],num_rows: 1}
             end end},
           {"wrong field name",fn r->%{r|columns: ["wrong"|tl(r.columns)]} end},
           {"wrong row count",fn r->%{r|num_rows: r.num_rows+1} end},
           {"malformed rows",fn r->%{r|rows: [%{}],num_rows: 1} end}] do
          record("wire family #{i}: "<>name,fn ->
            unavailable(fn ->replay(i,fn r->{:ok,change.(r)} end) end)
          end)
        end
        record("wire family #{i}: driver failure redacted",fn ->
          unavailable(fn ->replay(i,fn _->{:error,%RuntimeError{message: "SECRET-CATALOG-DIAGNOSTIC"}} end) end)
        end)
        record("wire family #{i}: cancellation redacted",fn ->
          unavailable(fn ->replay(i,fn _->exit({:timeout,"SECRET"}) end) end)
        end)
      end
      for {name,at,field,value}<-
        [{"unsupported major",0,"version",180000},{"NULL versus false",0,"jit",nil},
         {"wrong login",0,"login","untrusted"},{"NULL OID",1,"oid",nil},
         {"negative OID",1,"oid",-1},{"oversized role identifier",1,"name",String.duplicate("a",64)},
         {"oversized deparse output",4,"expression",String.duplicate("x",8193)},
         {"distinct node bound marker",4,"expression","__mixer_relation_bound__"},
         {"operator vector overrun",4,"pfeq",List.duplicate("pg_catalog.=:pg_catalog.text:pg_catalog.text",33)},
         {"policy role vector overrun",7,"roles",List.duplicate(0,5)}] do
        record("wire scalar: "<>name,fn ->
          unavailable(fn ->replay(at,fn r->
            column=Enum.find_index(r.columns,&(&1==field))
            [head|tail]=r.rows
            {:ok,%{r|rows: [List.replace_at(head,column,value)|tail]}}
          end) end)
        end)
      end
      record("aggregate decoded wire over 2MiB rejects with bounded individual scalars",fn ->
        unavailable(fn ->replay(6,fn r->
          at=Enum.find_index(r.columns,&(&1=="source"))
          {:ok,%{r|rows: Enum.map(r.rows,&List.replace_at(&1,at,String.duplicate("x",65536)))}}
        end) end)
      end)
      record("original remaining deadline checked after every query",fn ->
        for i<-0..11 do
          deadline=System.monotonic_time(:millisecond)+15
          unavailable(fn ->replay(i,fn r->Process.sleep(20);{:ok,r} end,deadline) end)
        end
      end)
      record("all query timeouts monotonically decrease without reset",fn ->
        assert(replay(-1,&{:ok,&1})===:relation_surface_verified)
        values=Process.get(:probe_timeouts)|>Enum.reverse()
        assert(Enum.all?(Enum.chunk_every(values,2,1,:discard),fn [a,b]->a>=b end))
      end)
    after
      Agent.stop(wire)
    end
    baseline()
    checks=Process.get(:probe_checks)|>Enum.reverse()
    path=Path.join(System.fetch_env!("RELATION_OUTPUT"),"checks.json")
    File.write!(Path.join(System.fetch_env!("RELATION_OUTPUT"),"mutation-effects.json"),Jason.encode!(Enum.reverse(Process.get(:probe_effects,[])),pretty: true)<>"\n")
    File.write!(path,Jason.encode!(%{checks: checks,passed: length(checks),live_mutations: length(mutations)+1},pretty: true)<>"\n")
    IO.puts("passed #{length(checks)} standalone methods; #{length(mutations)+1} actual mutations")
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
