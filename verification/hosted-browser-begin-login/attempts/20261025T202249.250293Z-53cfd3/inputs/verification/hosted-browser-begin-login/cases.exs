      alias MixerHosted.BrowserAuth.{StoredSnapshot, Vault}
      metadata = @metadata
      {:ok, p} = RuntimeOwner.bootstrap(metadata)
      record("fixed begin commits before private URL and exact OIDC state nonce S256 ciphertext agreement", fn ->
        before = p.source
        {:ok, result} = RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)
        assert(match?(%PreauthDraft.Authorization{}, result))
        u = URI.parse(result.url)
        q = URI.decode_query(u.query)
        assert(Map.keys(q) |> Enum.sort() == ~w(client_id code_challenge code_challenge_method nonce redirect_uri response_mode response_type scope state))
        assert(result.url |> byte_size() <= 8192)
        assert(u.scheme <> "://" <> u.host <> u.path === config.authorization_endpoint)
        assert(q["client_id"] === config.client_id and q["redirect_uri"] === config.redirect_uri)
        assert(q["response_type"] === "code" and q["response_mode"] === "query")
        assert(q["scope"] === "openid mixer.workspace.read" and q["code_challenge_method"] === "S256")
        s = BeginControls.snapshot(p)
        assert(s.browser === %{before.browser | "epoch" => 2, "revision" => 2, "audit_sequence" => 2})
        assert(s.attempt["state_digest"] === :crypto.hash(:sha256, q["state"]))
        assert(s.attempt["nonce_digest"] === :crypto.hash(:sha256, q["nonce"]))
        assert(result.expires_at === p.expires_at and s.attempt["expires_at"] === result.expires_at)
        {:ok, %Vault.Verifier{verifier: verifier}} = Vault.open(custody.key,s.attempt_envelope.context,s.attempt_envelope.sealed)
        {:ok, challenge} = Protocol.pkce_challenge(verifier)
        assert(q["code_challenge"] === challenge)
        assert(length(Enum.uniq([q["state"], q["nonce"], verifier])) === 3)
        {:ok, %Vault.Preauth{csrf: csrf}} = Vault.open(custody.key,s.session_envelope.context,s.session_envelope.sealed)
        assert(csrf === p.csrf)
        durable = Jason.encode!(BeginControls.durable())
        for secret <- [p.cookie,p.csrf,q["state"],q["nonce"],verifier], do: assert(not String.contains?(durable,secret))
        assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
        Process.put(:first_url,result.url)
      end)

      record("pending replacement supersedes old cipher and publishes independent fresh request", fn ->
        old = BeginControls.snapshot(p)
        old_q = URI.parse(Process.get(:first_url)).query |> URI.decode_query()
        {:ok, result} = RuntimeOwner.begin_login(p.cookie, BeginControls.headers(p), :workspace, metadata)
        q = URI.parse(result.url).query |> URI.decode_query()
        s = BeginControls.snapshot(p)
        assert(s.browser["epoch"] === 3 and s.browser["revision"] === 3)
        assert(s.session_envelope.context.vault_generation === 3)
        assert(q["state"] !== old_q["state"] and q["nonce"] !== old_q["nonce"] and q["code_challenge"] !== old_q["code_challenge"])
        %{rows: [["superseded","superseded",nil,nil,nil,nil]]} = sql(PreauthFixture.Admin,"SELECT status,completion_reason,key_id,iv,tag,ciphertext FROM public.mixer_browser_oidc_attempts WHERE state_digest=$1",[old.attempt["state_digest"]])
      end)

      record("ordinary load remains fail closed for valid pending source", fn ->
        before = BeginControls.durable()
        unavailable(RuntimeOwner.load(p.cookie))
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :storage_ready)
      end)

      record("raw supplied cookie must equal parsed header cookie before mutation", fn ->
        {:ok, other} = RuntimeOwner.bootstrap(metadata)
        before = BeginControls.durable()
        bad = [{"cookie","__Host-mixer-session=" <> other.cookie},{"origin",config.public_origin},{"x-mixer-csrf",p.csrf}]
        unavailable(RuntimeOwner.begin_login(p.cookie,bad,:workspace,metadata))
        assert(BeginControls.durable() === before)
      end)

      record("duplicate raw headers cookie ambiguity bearer aliases and malformed input cause no mutation", fn ->
        h = BeginControls.headers(p)
        before = BeginControls.durable()
        for headers <- [h ++ [{"Origin",config.public_origin}],h ++ [{"X-Mixer-Csrf",p.csrf}],h ++ [{"Cookie","x=y"}],h ++ [{"Authorization","Bearer synthetic"}],Map.new(h),[{"cookie","__Host-mixer-session=" <> p.cookie <> "; __Host-mixer-session=" <> p.cookie}]] do
          unavailable(RuntimeOwner.begin_login(p.cookie,headers,:workspace,metadata))
        end
        assert(BeginControls.durable() === before)
      end)

      record("exact Origin and recovered canonical CSRF checked without durable effects", fn ->
        before = BeginControls.durable()
        for h <- [BeginControls.headers(p,"https://console.example.invalid/"),BeginControls.headers(p,"https://other.example.invalid"),List.keyreplace(BeginControls.headers(p),"x-mixer-csrf",0,{"x-mixer-csrf",Protocol.random_token()}),List.keydelete(BeginControls.headers(p),"origin",0)] do
          unavailable(RuntimeOwner.begin_login(p.cookie,h,:workspace,metadata))
        end
        assert(BeginControls.durable() === before)
      end)

      record("closed metadata return route and absent malformed cookie deny without write", fn ->
        before = BeginControls.durable()
        for m <- [%{},%{request_id: String.duplicate("A",32)},%{request_id: metadata.request_id,extra: true},nil], do: unavailable(RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,m))
        for route <- [:login,"workspace","/workspace",nil], do: unavailable(RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),route,metadata))
        for cookie <- [nil,"",String.duplicate("a",42),Protocol.random_token()], do: unavailable(RuntimeOwner.begin_login(cookie,BeginControls.headers(p),:workspace,metadata))
        assert(BeginControls.durable() === before)
      end)

      record("public result and internal drafts redact URL state verifier source and live owner status", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        {:ok,r} = RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata)
        printed = inspect(d) <> inspect(r) <> inspect(:sys.get_status(RuntimeOwner))
        for secret <- [r.url,d.state,d.nonce,d.verifier,p.cookie,p.csrf,custody.key.bytes], do: assert(not String.contains?(printed,secret))
        assert(release(lease) === :ok)
      end)

      record("bad or mismatched URL denied before mutating transaction", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        before = BeginControls.durable()
        for url <- [d.url <> "&extra=1",String.duplicate("x",8193),"https://other.example.invalid/authorize"], do: unavailable(Store.begin_login(%{d|url: url},metadata))
        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record("all new session and verifier cipher fields authenticate before mutating effects", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        before = BeginControls.durable()
        for field <- [:key_id,:iv,:tag,:ciphertext] do
          bad = case field do :key_id -> "different-key"; :iv -> :binary.copy(<<19>>,12); :tag -> :binary.copy(<<19>>,16); :ciphertext -> <<19>> end
          unavailable(Store.begin_login(%{d|sealed: Map.put(d.sealed,field,bad)},metadata))
          unavailable(Store.begin_login(%{d|attempt_sealed: Map.put(d.attempt_sealed,field,bad)},metadata))
        end
        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record("new attempt metadata and state nonce verifier substitutions fail before effects", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        before = BeginControls.durable()
        for {field,value} <- [state: Protocol.random_token(),nonce: Protocol.random_token(),verifier: Protocol.random_token(),csrf: Protocol.random_token()] do
          unavailable(Store.begin_login(Map.put(d,field,value),metadata))
        end
        for {field,value} <- [issuer: "https://other.example.invalid",client_id: "different",redirect_uri: "https://other.example.invalid/auth/callback",epoch: d.attempt_context.epoch+1,expires_at: d.attempt_context.expires_at+1,profile_version: 8] do
          unavailable(Store.begin_login(%{d|attempt_context: Map.put(d.attempt_context,field,value)},metadata))
        end
        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record("all produced browser source fields compared before commit and rollback on mismatch", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        before = BeginControls.durable()
        for {field,value} <- [{"last_seen_at",s.browser["last_seen_at"]+1},{"audit_sequence",s.browser["audit_sequence"]+1},{"absolute_expires_at",s.browser["absolute_expires_at"]+1},{"idle_expires_at",s.browser["idle_expires_at"]-1}] do
          altered = %{s|browser: Map.put(s.browser,field,value)}
          unavailable(Store.begin_login(%{d|source: altered},metadata))
          assert(BeginControls.durable() === before)
        end
        assert(release(lease) === :ok)
      end)

      record("pending source verifier AEAD authentication fails closed with no mutation", fn ->
        s = BeginControls.snapshot(p)
        tag = s.attempt_envelope.sealed.tag
        # The admin is fixture authority only; restore exact cipher bytes after
        # the attempted request, with no schema or helper modification.
        sql(PreauthFixture.Admin,"UPDATE public.mixer_browser_oidc_attempts SET tag=$2 WHERE state_digest=$1",[s.attempt["state_digest"],:binary.copy(<<9>>,16)])
        before = BeginControls.durable()
        unavailable(RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata))
        assert(BeginControls.durable() === before)
        sql(PreauthFixture.Admin,"UPDATE public.mixer_browser_oidc_attempts SET tag=$2 WHERE state_digest=$1",[s.attempt["state_digest"],tag])
      end)

      record("same source revision concurrency has one URL winner one closed CAS loser and no retry", fn ->
        {:ok, c} = RuntimeOwner.bootstrap(metadata)
        results = BeginControls.concurrent(c,metadata) |> Enum.map(&elem(&1,1))
        assert(Enum.count(results,&match?({:ok,%PreauthDraft.Authorization{}},&1)) === 1)
        assert(Enum.count(results,&match?({:error,%Store.Failure{}},&1)) === 1)
        s = BeginControls.snapshot(c)
        assert(s.browser["revision"] === 2 and s.browser["audit_sequence"] === 2)
        assert(map_size(:sys.get_state(RuntimeOwner).operations) === 0)
      end)

      record("foreign caller cannot consume copied begin lease or invoke typed Store", fn ->
        {lease,s} = BeginControls.discover(p)
        d = BeginControls.draft(lease,s,p.csrf)
        before = BeginControls.durable()
        parent = self()
        pid = spawn(fn -> send(parent,{:foreign_begin,self(),Store.begin_login(d,metadata)}) end)
        receive do {:foreign_begin,^pid,r} -> unavailable(r) after 1500 -> raise "foreign begin missing" end
        preserved(lease)
        assert(BeginControls.durable() === before)
        assert(release(lease) === :ok)
      end)

      record("single original deadline includes encrypted discovery commit and pre-mutation work", fn ->
        before = BeginControls.durable()
        started = System.monotonic_time(:millisecond)
        r = BeginControls.held_n(Store,:discover_begin,1,1,fn -> RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata) end,fn -> Process.sleep(5100) end)
        unavailable(r)
        assert(System.monotonic_time(:millisecond)-started >= 5000)
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        owner(runtime)
      end)

      record("deferred mutating COMMIT rejection returns no URL and restores exact durable source", fn ->
        before = BeginControls.durable()
        r = try do
          BeginControls.held_n(RelationCatalog,:check_relation_surface!,3,2,fn -> RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata) end,fn -> BeginControls.install_deferred("RAISE EXCEPTION 'synthetic deferred denial' USING ERRCODE='23514'") end)
        after BeginControls.remove_deferred() end
        unavailable(r)
        assert(match?({:error,%Store.Failure{phase: :commit,outcome: :rolled_back}},r))
        assert(BeginControls.durable() === before)
        settings_restored()
      end)

      record("lost backend during mutating COMMIT is unknown clears readiness and never retries", fn ->
        before = BeginControls.durable()
        r = try do
          BeginControls.held_n(RelationCatalog,:check_relation_surface!,3,2,fn -> RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata) end,fn -> BeginControls.install_deferred("PERFORM pg_catalog.pg_terminate_backend(pg_catalog.pg_backend_pid())") end)
        after BeginControls.remove_deferred() end
        unavailable(r)
        assert(match?({:error,%Store.Failure{phase: :commit,outcome: :unknown}},r))
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        settings_restored()
        owner(runtime)
      end)

      record("deferred mutating COMMIT wait uses the same five second entry deadline", fn ->
        before = BeginControls.durable()
        started = System.monotonic_time(:millisecond)
        r = try do
          BeginControls.held_n(RelationCatalog,:check_relation_surface!,3,2,fn -> RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata) end,fn -> BeginControls.install_deferred("PERFORM pg_catalog.pg_sleep(7)") end)
        after BeginControls.remove_deferred() end
        unavailable(r)
        assert(System.monotonic_time(:millisecond)-started >= 4500 and System.monotonic_time(:millisecond)-started < 7000)
        assert(match?({:error,%Store.Failure{phase: :commit}},r))
        assert(BeginControls.durable() === before)
        assert(RuntimeOwner.status().phase === :unavailable)
        settings_restored()
        owner(runtime)
      end)

      record("known committed mutation with default identity PID loss withholds authorization URL", fn ->
        before = BeginControls.snapshot(p)
        r = BeginControls.held_n(LifecycleRepo,:transaction,2,2,fn -> RuntimeOwner.begin_login(p.cookie,BeginControls.headers(p),:workspace,metadata) end,fn ->
          assert(BeginControls.snapshot(p).browser["revision"] === before.browser["revision"]+1)
          GenServer.stop(identity_pid)
        end)
        unavailable(r)
        assert(match?({:error,%Store.Failure{phase: :commit,outcome: :committed}},r))
        assert(RuntimeOwner.status().phase === :unavailable)
        assert(BeginControls.snapshot(p).browser["revision"] === before.browser["revision"]+1)
      end)
