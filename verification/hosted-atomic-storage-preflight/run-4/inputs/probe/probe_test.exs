ExUnit.start(autorun: false,seed: 0,max_cases: 1,timeout: 15_000,trace: true)
alias MixerAtomicStoragePreflight.{Repo,OtherRepo,AdminRepo,ProxyRepo}
{:ok,_}=Agent.start_link(fn -> %{} end,name: PreflightObservations)
config=[socket_dir: System.fetch_env!("MXAS_SOCKET"),username: "mxas_runtime",database: "atomic_preflight",pool_size: 1,timeout: 5_000,connect_timeout: 2_000,log: false]
{:ok,_}=Repo.start_link(config)
{:ok,_}=OtherRepo.start_link(config)
{:ok,_}=AdminRepo.start_link(Keyword.put(config,:username,"preflight_owner"))
{:ok,proxy_pid}=ProxyRepo.start_link(Keyword.put(config,:socket_dir,System.fetch_env!("MXAS_PROXY")))
Process.unlink(proxy_pid)

defmodule MixerAtomicStoragePreflight.ProbeTest do
 use ExUnit.Case,async: false
 alias MixerAtomicStoragePreflight.{Repo,OtherRepo,AdminRepo,ProxyRepo,Context,OtherContext,ProxyContext,Codec,Blob}
 @one "00000000-0000-0000-0000-000000000001"
 @two "00000000-0000-0000-0000-000000000002"
 @request "00000000-0000-0000-0000-000000000030"
 defp sql(q,p \\ []),do: AdminRepo.query!(q,p,log: false)
 defp scalar(q,p \\ []),do: sql(q,p).rows |> hd() |> hd()
 defp observe(k,v),do: Agent.update(PreflightObservations,&Map.put(&1,k,v))
 defp opts(o \\ []) do
  canonical=Keyword.get(o,:canonical,<<0>>);payload=Keyword.get(o,:payload,<<1>>)
  defaults=[actor: @one,key: "k",runtime: <<0::256>>,canonical: canonical,manifest: :crypto.hash(:sha256,canonical),signed: "{}",signature: <<0::512>>,payload_hash: :crypto.hash(:sha256,payload),payload_size: byte_size(payload),app: "a",environment: "e",platform: "ios",body: "body",reason: "",source_ip: nil,asserted_display: nil,expires: 10000]
  Keyword.merge(defaults,o)
 end
 defp bind(ctx,mod,o) do
  values=[o[:actor],o[:app],o[:environment],o[:platform],Codec.hex(o[:runtime]),Codec.hex(o[:manifest]),Integer.to_string(o[:expires])]
  mod.query!(ctx,"SELECT set_config('mixer_atomic.actor',$1,true),set_config('mixer_atomic.app',$2,true),set_config('mixer_atomic.environment',$3,true),set_config('mixer_atomic.platform',$4,true),set_config('mixer_atomic.runtime',$5,true),set_config('mixer_atomic.manifest',$6,true),set_config('mixer_atomic.expires',$7,true),set_config('mixer_atomic.action','artifact.upload',true)",values)
 end
 defp upload(ctx,o,mod \\ Context) do
  deadline=DateTime.add(DateTime.utc_now(),ctx.deadline_ms-System.monotonic_time(:millisecond),:millisecond)
  hash=Keyword.get(o,:request_hash,:crypto.hash(:sha256,"POST /v3/private/artifacts"<><<0>><>o[:body]))
  args=[Keyword.get(o,:sql_backend,ctx.backend_pid),Keyword.get(o,:sql_xid,ctx.transaction_id),Keyword.get(o,:sql_database,ctx.database),Keyword.get(o,:runtime_role,ctx.db_role),Keyword.get(o,:nonce,ctx.nonce),Keyword.get(o,:deadline,deadline),Keyword.get(o,:input_actor,o[:actor]),Integer.to_string(o[:expires]),o[:app],o[:environment],o[:platform],o[:runtime],o[:manifest],o[:canonical],o[:signed],o[:signature],o[:payload_hash],Integer.to_string(o[:payload_size]),Keyword.get(o,:blob_ref,"sha256:"<>Codec.hex(o[:payload_hash])),o[:key],o[:body],hash,o[:reason],@request,o[:source_ip],o[:asserted_display]]
  mod.query!(ctx,"SELECT x.* FROM mixer_hosted_release.upload_v1(ROW($1,$2,$3,$4,$5,$6,$7::text::uuid,$8::text::numeric)::mixer_hosted_release.call_context,ROW('o','p',$9,$10,$11,$12,$13,$14,$15,$16,$17,$18::text::numeric,$19)::mixer_hosted_release.upload_input,ROW($20,'/v3/private/artifacts',$21,$22,$23,$24::text::uuid,$25,$26)::mixer_hosted_release.upload_request) AS x",args).rows |> hd()
 end
 defp attempt(overrides \\ [],mod \\ Context) do
  o=opts(overrides)
  try do
   mod.enter(fn c -> bind(c,mod,o);upload(c,o,mod) end)
  rescue e -> {:rejected,inspect(e.__struct__),Exception.message(e)} end
 end
 defp counts do
  Enum.map(["artifacts","audit_events","idempotency"],fn t->scalar("SELECT count(*) FROM mixer_hosted_release."<>t) end)++[scalar("SELECT last_event::text FROM mixer_hosted_release.tenant_heads")]
 end
 defp rejected(o,mod \\ Context) do
  assert {:rejected,_,_}=attempt(o,mod)
 end
 setup do
  sql("TRUNCATE mixer_hosted_release.artifacts,mixer_hosted_release.audit_events,mixer_hosted_release.idempotency")
  sql("UPDATE mixer_authz.fixture_policy SET role='developer',active=true,revision=1")
  sql("UPDATE mixer_authz.fixture_clock SET now_s=100")
  sql("UPDATE mixer_authz.fixture_fault SET boundary=''")
  sql("UPDATE mixer_hosted_release.tenant_heads SET last_event=0,audit_hash=''::bytea,state_hash=mixer_hosted_release.hash_domain('mixer.hosted.state.v1',mixer_hosted_release.a(ARRAY[mixer_hosted_release.u(1),mixer_hosted_release.t('o'),mixer_hosted_release.t('p')]))")
  :ok
 end
 test "01 complete routine returns original bytes and runtime context survives definer transition" do
  assert {:ok,[201,body,id,false]}=attempt()
  assert Decimal.equal?(id,1)
  assert body=="{\"manifest_sha256\":\""<>Codec.hex(:crypto.hash(:sha256,<<0>>))<>"\",\"event_id\":\"1\"}"
  assert counts()==[1,1,1,"1"]
  assert {:ok,[201,^body,^id,true]}=attempt()
  assert counts()==[1,1,1,"1"]
  observe("legitimate_definer_transition",%{runtime: "mxas_runtime",writer: "mxas_writer",same_backend_xid_nonce: true,context_revalidated_after: true})
 end
 test "02 runtime direct INSERT UPDATE DELETE TRUNCATE all private domain tables denied" do
  for table <- ~w(artifacts audit_events idempotency tenant_heads), verb <- ["INSERT INTO #{table} DEFAULT VALUES","UPDATE #{table} SET organization=organization","DELETE FROM #{table}","TRUNCATE #{table}"] do
   statement=String.replace(verb,table,"mixer_hosted_release."<>table)
   assert_raise Postgrex.Error,fn -> Repo.query!(statement) end
  end
  assert counts()==[0,0,0,"0"]
 end
 test "03 FORCE RLS manifest exact safe roles and no owner resolver writer SET ROLE paths" do
  assert scalar("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity")==7
  assert sql("SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb,rolreplication,rolcanlogin FROM pg_roles WHERE rolname LIKE 'mxas_%' ORDER BY rolname").rows |> Enum.all?(fn [_n,s,b,c,d,r,_l]->not(s or b or c or d or r) end)
  for role <- ~w(mxas_schema mxas_resolver mxas_writer) do
   assert scalar("SELECT pg_has_role('mxas_runtime',$1,'MEMBER')",[role])==false
   assert_raise Postgrex.Error,fn -> Repo.query!("SET ROLE "<>role) end
  end
  assert scalar("SELECT has_database_privilege('mxas_runtime',current_database(),'TEMP')")==false
  assert scalar("SELECT has_schema_privilege('mxas_runtime','mixer_hosted_release','CREATE')")==false
  assert scalar("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') AND p.prosecdef")==3
  assert Repo.query!("SELECT count(*) FROM mixer_hosted_release.artifacts").rows==[[0]]
  assert_raise Postgrex.Error,fn -> Repo.query!("SELECT * FROM mixer_authz.fixture_policy") end
  assert_raise Postgrex.Error,fn -> Repo.query!("SELECT * FROM mixer_hosted_release.idempotency") end
 end
 test "04 forged actor rejects before any writes" do rejected(input_actor: @two);assert counts()==[0,0,0,"0"] end
 test "05 wrong signed target rejects" do
  o=opts();assert_raise Postgrex.Error,fn->Context.enter(fn c->bind(c,Context,o);upload(c,Keyword.put(o,:app,"other")) end)end
  assert counts()==[0,0,0,"0"]
 end
 test "06 wrong request hash rejects" do rejected(request_hash: <<0::256>>);assert counts()==[0,0,0,"0"] end
 test "07 asserted wrong audit display rejects" do rejected(asserted_display: %{"hash"=>"forged"});assert counts()==[0,0,0,"0"] end
 test "08 wrong nonce runtime role backend fullxid database and stale transaction deny" do
  rejected(nonce: String.duplicate("f",64));rejected(runtime_role: "mxas_writer");rejected(sql_backend: -1);rejected(sql_xid: "1");rejected(sql_database: "other")
  for {field,value} <- [backend_pid: -1,transaction_id: "1",database: "other"] do
   o=opts();assert_raise MixerAtomicStoragePreflight.Rejected,fn->Context.enter(fn c->bind(c,Context,o);upload(Map.put(c,field,value),o) end)end
  end
  assert {:ok,closed}=Context.enter(& &1)
  assert_raise MixerAtomicStoragePreflight.Rejected,fn -> upload(closed,opts()) end
  assert counts()==[0,0,0,"0"]
 end
 test "09 foreign session denied even when deliberately granted fixture EXECUTE" do
  {:ok,conn}=Postgrex.start_link(socket_dir: System.fetch_env!("MXAS_SOCKET"),username: "mxas_foreign",database: "atomic_preflight")
  assert_raise Postgrex.Error,fn->Postgrex.query!(conn,"SELECT mixer_hosted_release.upload_v1(NULL,NULL,NULL)",[])end
  GenServer.stop(conn)
 end
 test "10 current authorization before idempotent cached result" do
  assert {:ok,_}=attempt()
  sql("UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid",[@one])
  rejected([]);assert counts()==[1,1,1,"1"]
 end
 test "11 expiry before idempotency rejects even identical original key" do
  assert {:ok,_}=attempt(expires: 101)
  sql("UPDATE mixer_authz.fixture_clock SET now_s=101")
  rejected(expires: 101);assert counts()==[1,1,1,"1"]
 end
 test "12 principal action target and hash conflicts do not disclose cached bytes" do
  assert {:ok,_}=attempt()
  rejected(actor: @two);rejected(body: "different")
  sql("UPDATE mixer_hosted_release.idempotency SET action='release.publish'");rejected([])
  sql("UPDATE mixer_hosted_release.idempotency SET action='artifact.upload',target='00'::bytea");rejected([])
  assert counts()==[1,1,1,"1"]
 end
 test "13 new key identical artifact audits success with no state delta" do
  assert {:ok,_}=attempt();first=scalar("SELECT state_hash FROM mixer_hosted_release.tenant_heads")
  assert {:ok,[200,_,_,false]}=attempt(key: "new")
  assert counts()==[1,2,2,"2"]
  assert scalar("SELECT state_hash FROM mixer_hosted_release.tenant_heads")==first
  assert scalar("SELECT previous_state=current_state FROM mixer_hosted_release.audit_events WHERE event_id=2")
 end
 test "14 immutable conflict cannot append a success" do
  assert {:ok,_}=attempt();rejected(key: "new",signed: "{ }");assert counts()==[1,1,1,"1"]
 end
 test "15 rollback after every persistence boundary has no partial event or id gap" do
  for boundary <- ~w(artifact audit idempotency head) do
   sql("UPDATE mixer_authz.fixture_fault SET boundary=$1",[boundary]);rejected([]);assert counts()==[0,0,0,"0"]
  end
  sql("UPDATE mixer_authz.fixture_fault SET boundary=''");assert {:ok,[201,_,id,false]}=attempt();assert Decimal.equal?(id,1)
 end
 test "16 initial head event hash display and previous links corruption deny" do
  sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash='01'::bytea");rejected([])
  sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=''::bytea")
  assert {:ok,_}=attempt()
  original=sql("SELECT event_cbor,event_hash,previous_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events").rows |> hd()
  for mutation <- ["event_cbor='01'::bytea","event_hash='01'::bytea","previous_hash='01'::bytea","display_json=jsonb_set(display_json,'{action}','\"forged\"'),display_bytes=convert_to(jsonb_set(display_json,'{action}','\"forged\"')::text,'UTF8')","display_bytes='01'::bytea"] do
   sql("UPDATE mixer_hosted_release.audit_events SET "<>mutation);rejected(key: "new")
   sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=$1,event_hash=$2,previous_hash=$3,display_json=$4,display_bytes=$5",original)
  end
  assert counts()==[1,1,1,"1"]
 end
 test "17 concurrent same key different principals has one success and one hidden conflict" do
  parent=self()
  holder=Task.async(fn->AdminRepo.transaction(fn->sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE");send(parent,:locked);receive do :release->:ok end end)end)
  assert_receive :locked
  a=Task.async(fn->send(parent,:started);attempt([],Context)end)
  b=Task.async(fn->send(parent,:started);attempt([actor: @two],OtherContext)end)
  assert_receive :started;assert_receive :started;Process.sleep(70);send(holder.pid,:release);Task.await(holder)
  results=[Task.await(a),Task.await(b)]
  assert Enum.count(results,&match?({:ok,[201,_,_,false]},&1))==1
  assert Enum.count(results,&match?({:rejected,_,_},&1))==1
  assert counts()==[1,1,1,"1"]
  observe("different_principal_race",%{successes: 1,conflicts: 1,events: 1})
 end
 test "18 concurrent new keys identical artifact produce insert and unchanged success" do
  a=Task.async(fn->attempt([key: "a"],Context)end);b=Task.async(fn->attempt([key: "b"],OtherContext)end)
  results=[Task.await(a),Task.await(b)]
  assert Enum.sort(Enum.map(results,fn {:ok,[status,_,_,false]}->status end))==[200,201]
  assert counts()==[1,2,2,"2"]
  assert scalar("SELECT previous_state=current_state FROM mixer_hosted_release.audit_events WHERE event_id=2")
 end
 test "19 lock timeout rolls back; postwait current policy revocation denies" do
  parent=self();holder=Task.async(fn->AdminRepo.transaction(fn->sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE");send(parent,:locked);receive do :release->:ok after 1000->:ok end end)end)
  assert_receive :locked;start=System.monotonic_time(:millisecond);rejected([]);elapsed=System.monotonic_time(:millisecond)-start
  assert elapsed>=240 and elapsed<1000;send(holder.pid,:release);Task.await(holder);assert counts()==[0,0,0,"0"]
  observe("lock_timeout_ms",elapsed)
 end
 test "20 PostgreSQL commit acknowledgement dropped then database restart and exact retry" do
  root=Path.join(System.fetch_env!("MXAS_BLOBS"),"uncertain")
  {staged,reference}=Blob.stage(Blob.open(root),<<1>>)
  o=opts(blob_ref: reference);result=try do
   ProxyContext.enter(fn c->bind(c,ProxyContext,o);r=upload(c,o,ProxyContext);File.write!(System.fetch_env!("MXAS_ARM"),"armed");r end)
  rescue e->{:storage_unavailable,inspect(e.__struct__)}end
  assert match?({:storage_unavailable,_},result) or result=={:error,:rollback}
  # Proxy drops only PostgreSQL's completed COMMIT reply; caller receives no success.
  assert counts()==[1,1,1,"1"]
  assert Blob.reconcile(staged,MapSet.new(),true)==staged
  assert Blob.read(Blob.open(root),reference)==<<1>>
  original=sql("SELECT status,response,event_id FROM mixer_hosted_release.idempotency").rows |> hd()
  {stop,0}=System.cmd("pg_ctl",["-D",System.fetch_env!("MXAS_PGDATA"),"stop","-m","fast","-w"])
  {start,0}=System.cmd("pg_ctl",["-D",System.fetch_env!("MXAS_PGDATA"),"-l",System.fetch_env!("MXAS_PGLOG"),"-o","-k #{System.fetch_env!("MXAS_SOCKET")} -c listen_addresses='' -c unix_socket_permissions=0700 -c max_connections=12 -c log_statement=all","start","-w"])
  Process.sleep(350)
  recovered=Enum.reduce_while(1..40,nil,fn _,_ ->
   case attempt() do
    {:ok,_}=success->{:halt,success}
    {:rejected,"DBConnection.ConnectionError",_}->Process.sleep(50);{:cont,nil}
    other->{:halt,other}
   end
  end)
  assert {:ok,[status,body,event,true]}=recovered
  assert [status,body,event]==original
  assert Blob.read(Blob.open(root),reference)==<<1>>
  assert counts()==[1,1,1,"1"]
  observe("uncertain_commit_restart",%{client_result: inspect(result),stop_output: stop,start_output: start,exact_original_retry: true,no_duplicate_event: true})
 end
 test "21 six supported roles and closed supported actions only" do
  for {role,allowed} <- [{"owner",true},{"administrator",true},{"developer",true},{"release_manager",false},{"viewer",false},{"billing_manager",false},{"publisher",false}] do
   sql("UPDATE mixer_authz.fixture_policy SET role=$1",[role])
   if allowed,do: assert(match?({:ok,_},attempt(key: role))),else: rejected(key: role)
  end
  o=opts();assert_raise Postgrex.Error,fn->Context.enter(fn c->bind(c,Context,o);Context.query!(c,"SELECT set_config('mixer_atomic.action','release.publish',true)");upload(c,o)end)end
 end
 test "22 SQL and independent Elixir uint64 encoding hand vectors all widths" do
  for {n,h} <- [{0,"00"},{23,"17"},{24,"1818"},{255,"18ff"},{256,"190100"},{65535,"19ffff"},{65536,"1a00010000"},{4294967295,"1affffffff"},{4294967296,"1b0000000100000000"},{18446744073709551615,"1bffffffffffffffff"}] do
   assert Codec.hex(Codec.encode(n))==h
   assert scalar("SELECT encode(mixer_hosted_release.u($1::text::numeric),'hex')",[Integer.to_string(n)])==h
  end
  for n <- [-1,18446744073709551616] do
   assert_raise ArgumentError,fn->Codec.encode(n)end
   assert_raise Postgrex.Error,fn->sql("SELECT mixer_hosted_release.u($1::text::numeric)",[Integer.to_string(n)])end
  end
  assert Codec.hex(Codec.encode([1,nil,Codec.b(<<>>),""]))=="8401f64060"
 end
 test "23 every stored display field reconstructs identical audit bytes and standard hash" do
  assert {:ok,_}=attempt(reason: "line\n雪",source_ip: "127.0.0.1")
  [bytes,hash,d,display]=sql("SELECT event_cbor,event_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events").rows |> hd()
  assert Codec.encode(Codec.from_display(d))==bytes
  assert Codec.hash("mixer.hosted.audit.v1",bytes)==hash
  assert Jason.decode!(display)==d
  assert Codec.unhex(d["hash"])==hash
  observe("display_and_cbor",%{event_hex: Codec.hex(bytes),event_hash: Codec.hex(hash),display_bytes: display})
 end
 test "24 request body exact6MiB and over plus signed and canonical64KiB edges" do
  assert {:ok,_}=attempt(body: :binary.copy(" ",6291456))
  rejected(key: "over",body: :binary.copy(" ",6291457))
  assert {:ok,_}=attempt(key: "signedmax",canonical: <<1>>,signed: :binary.copy(" ",65536))
  rejected(key: "signedover",canonical: <<2>>,signed: :binary.copy(" ",65537))
  assert {:ok,_}=attempt(key: "cborlimit",canonical: :binary.copy(<<3>>,65536))
  rejected(key: "cborover",canonical: :binary.copy(<<4>>,65537))
 end
 test "25 reason512 UTF8 and key128 exact plus over" do
  assert {:ok,_}=attempt(key: String.duplicate("k",128),reason: String.duplicate("é",256))
  rejected(key: String.duplicate("k",129));rejected(key: "next",reason: String.duplicate("é",256)<>"a")
  rejected(key: "");rejected(key: "illegal space");rejected(key: "ip",source_ip: String.duplicate("1",46))
 end
 test "26 payload metadata min max oneover and blob digest binding" do
  rejected(payload_size: 0);assert {:ok,_}=attempt(payload_size: 4194304)
  rejected(key: "maxplus",payload_size: 4194305);rejected(key: "blob",blob_ref: "sha256:"<>String.duplicate("f",64))
  rejected(key: "sig",signature: <<0::504>>);rejected(key: "hash",manifest: <<0::256>>)
 end
 test "27 event id uint64 exhaustion fails closed no wrap or partial write" do
  assert {:ok,_}=attempt();sql("UPDATE mixer_hosted_release.tenant_heads SET last_event=18446744073709551615")
  rejected(key: "next");assert counts()==[1,1,1,"18446744073709551615"]
 end
 test "28 fixed codec totalbytes boundary, no ambiguous maps floats negative booleans" do
  assert byte_size(Codec.encode(String.duplicate("a",16381)))==16384
  assert_raise ArgumentError,fn->Codec.encode(String.duplicate("a",16382))end
  for v <- [%{},true,false,-1,1.5,{:bytes,1},<<255>>] do assert_raise ArgumentError,fn->Codec.encode(v)end end
 end
 test "29 bounded local immutable blob stage reopen corruption and orphan cleanup" do
  root=Path.join(System.fetch_env!("MXAS_BLOBS"),"one");s=Blob.open(root)
  {s,ref}=Blob.stage(s,<<1>>);{same,^ref}=Blob.stage(s,<<1>>);assert same==s
  assert Blob.open(root)==s;assert Blob.read(s,ref)==<<1>>
  {s,orphan}=Blob.stage(s,<<2>>);assert Blob.reconcile(s,MapSet.new([ref]),true)==s
  s=Blob.reconcile(s,MapSet.new([ref]),false);assert s.count==1
  assert_raise File.Error,fn->Blob.read(s,orphan)end
  path=Path.join(root,String.replace_prefix(ref,"sha256:",""));File.chmod!(path,0o600);File.write!(path,<<3>>)
  assert_raise ArgumentError,fn->Blob.open(root)end
  assert_raise ArgumentError,fn->Blob.stage(s,<<1>>)end
 end
 test "30 local blob size count and total quota exact then oneover" do
  root=Path.join(System.fetch_env!("MXAS_BLOBS"),"quota");s=Blob.open(root)
  assert_raise ArgumentError,fn->Blob.stage(s,<<>>)end
  assert_raise ArgumentError,fn->Blob.stage(s,:binary.copy(<<0>>,4194305))end
  s=Enum.reduce(0..3,s,fn n,s->{next,_}=Blob.stage(s,:binary.copy(<<n>>,4194304));next end)
  assert s.bytes==16777216;assert Blob.open(root)==s
  assert_raise ArgumentError,fn->Blob.stage(s,<<9>>)end
  root2=Path.join(System.fetch_env!("MXAS_BLOBS"),"count")
  s=Enum.reduce(0..7,Blob.open(root2),fn n,s->{next,_}=Blob.stage(s,<<n>>);next end)
  assert s.count==8;assert_raise ArgumentError,fn->Blob.stage(s,<<9>>)end
 end
 test "31 closed codec depth nodes container and max output exact and oneover" do
  nested=Enum.reduce(1..16,0,fn _,v->[v] end)
  assert is_binary(Codec.encode(nested));assert_raise ArgumentError,fn->Codec.encode([nested])end
  assert is_binary(Codec.encode(List.duplicate(0,256)));assert_raise ArgumentError,fn->Codec.encode(List.duplicate(0,257))end
  # 1 outer + 15*(1+256) + 1 inner +239 leaves =4096 items.
  exact=List.duplicate(List.duplicate(0,256),15)++[List.duplicate(0,239)]
  assert is_binary(Codec.encode(exact));assert_raise ArgumentError,fn->Codec.encode(List.duplicate(List.duplicate(0,256),15)++[List.duplicate(0,240)])end
  assert byte_size(Codec.encode(String.duplicate("a",65533),65536))==65536
  assert_raise ArgumentError,fn->Codec.encode(String.duplicate("a",65534),65536)end
 end
 test "32 exact response bytes page row and encoded total bounds admission four then busy" do
  alias MixerAtomicStoragePreflight.Bounds
  assert byte_size(Bounds.response(:binary.copy("a",4096)))==4096
  assert_raise ArgumentError,fn->Bounds.response(:binary.copy("a",4097))end
  assert byte_size(Bounds.body(:binary.copy("a",6291456)))==6291456
  assert_raise ArgumentError,fn->Bounds.body(:binary.copy("a",6291457))end
  {hundred,_}=Bounds.page(List.duplicate("{}",101),100);assert length(hundred)==100
  assert_raise ArgumentError,fn->Bounds.page([],101)end
  assert_raise ArgumentError,fn->Bounds.page([],0)end
  for n <- [32768,32769] do
    row="\""<>String.duplicate("a",n-2)<>"\""
    if n==32768,do: assert(match?({[_],_},Bounds.page([row],1))),else: assert_raise(ArgumentError,fn->Bounds.page([row],1)end)
  end
  rows=List.duplicate("\""<>String.duplicate("a",32766)<>"\"",100)
  {chosen,encoded}=Bounds.page(rows,100);assert length(chosen)==7;assert byte_size(encoded)<=262144
  # Choose a small exact encoded ceiling; one byte less removes the row.
  row="{}";reserved=byte_size("{\"events\":[],\"next\":null}")+2+18
  assert match?({["{}"],_},Bounds.page([row,row],1,reserved))
  assert match?({[],_},Bounds.page([row,row],1,reserved-1))
  {:ok,gate}=Bounds.admission_start();refs=Enum.map(1..4,fn _->{:ok,r}=Bounds.admit(gate);r end)
  assert Bounds.admit(gate)==:busy;Bounds.release(gate,hd(refs));assert {:ok,_}=Bounds.admit(gate);Agent.stop(gate)
 end

 test "33 policy changes during blocking lock are freshly denied before cache" do
  assert {:ok,_}=attempt()
  parent=self()
  holder=Task.async(fn->AdminRepo.transaction(fn->sql("SELECT * FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid FOR UPDATE",[@one]);send(parent,:policy_locked);receive do :revoke->sql("UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid",[@one])end end)end)
  assert_receive :policy_locked
  waiting=Task.async(fn->send(parent,:writer_starting);attempt()end)
  assert_receive :writer_starting;Process.sleep(80);send(holder.pid,:revoke);Task.await(holder)
  assert {:rejected,_,_}=Task.await(waiting);assert counts()==[1,1,1,"1"]
  observe("post_lock_fresh_policy",%{cached_original_exists: true,waited_on_policy_writer: true,revoked_result_denied: true})
 end
 test "34 hand authored event state and exact display golden vectors" do
  golden=File.read!("golden-vectors.json") |> Jason.decode!()
  assert {:ok,_}=attempt()
  [cbor,event_hash,display,display_bytes]=sql("SELECT event_cbor,event_hash,display_json,display_bytes FROM mixer_hosted_release.audit_events").rows |> hd()
  assert Codec.hex(cbor)==golden["event"]["cbor_hex"]
  assert Codec.hex(event_hash)==golden["event"]["sha256"]
  assert Codec.hash("mixer.hosted.audit.v1",Codec.unhex(golden["event"]["cbor_hex"]))==event_hash
  assert Codec.hash("mixer.hosted.state.v1",Codec.unhex(golden["initial"]["cbor_hex"]))==Codec.unhex(golden["initial"]["sha256"])
  assert Codec.hash("mixer.hosted.state.v1",Codec.unhex(golden["transition"]["cbor_hex"]))==Codec.unhex(golden["transition"]["sha256"])
  assert scalar("SELECT encode(state_hash,'hex') FROM mixer_hosted_release.tenant_heads")==golden["transition"]["sha256"]
  assert display==golden["expected_display"]
  assert display_bytes==golden["expected_display_bytes_utf8"]
  assert Codec.encode(Codec.from_display(display))==cbor
 end
 test "35 SET ROLE self changes role setting and is rejected inside writer" do
  o=opts()
  assert_raise Postgrex.Error,fn->Context.enter(fn c->bind(c,Context,o);Context.query!(c,"SET LOCAL ROLE mxas_runtime");upload(c,o)end)end
  assert counts()==[0,0,0,"0"]
 end
 test "36 stage before locks failed transaction leaves bounded orphan; reopen partial crash fails closed" do
  root=Path.join(System.fetch_env!("MXAS_BLOBS"),"orphan")
  {s,ref}=Blob.stage(Blob.open(root),<<8>>)
  assert not Repo.in_transaction?()
  sql("UPDATE mixer_authz.fixture_fault SET boundary='audit'")
  rejected(payload: <<8>>,blob_ref: ref)
  assert counts()==[0,0,0,"0"];assert Blob.read(Blob.open(root),ref)==<<8>>
  assert Blob.reconcile(s,MapSet.new(),true).count==1
  assert Blob.reconcile(s,MapSet.new(),false).count==0
  # Simulated process death during exclusive file creation leaves incomplete immutable bytes.
  partial=Path.join(root,Codec.hex(:crypto.hash(:sha256,<<1,2>>)))
  File.write!(partial,<<1>>)
  assert_raise ArgumentError,fn->Blob.open(root)end
 end

end
result=ExUnit.run()
summary=%{total: result.total,failures: result.failures,skipped: result.skipped,excluded: result.excluded}
File.write!(System.fetch_env!("MXAS_RESULTS"),Jason.encode!(%{summary: summary,observations: Agent.get(PreflightObservations,& &1)},pretty: true))
System.halt(if result.failures==0,do: 0,else: 1)
