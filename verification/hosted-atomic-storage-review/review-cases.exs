  # Independently authored reviewer cases. Inserted into the frozen specimen's
  # existing test module solely to reuse its synthetic input/setup helpers.
  # "Observed limitation" cases preserve actual unsupported behavior explicitly;
  # their success must not be interpreted as product qualification.
  defp review_raw(c, o) do
    upload(c, o, MixerAtomicStoragePreflight.ReviewRaw)
  end

  defp review_raw_attempt(overrides) do
    o = opts(overrides)
    try do
      Context.enter(fn c ->
        bind(c, Context, o)
        review_raw(c, o)
      end)
    rescue
      e -> {:rejected, inspect(e.__struct__), Exception.message(e)}
    end
  end

  defp review_wait_for_runtime_lock do
    args = ["-h", System.fetch_env!("MXAS_SOCKET"), "-U", "preflight_owner", "-d", "atomic_preflight", "-At", "-c", "SELECT count(*) FROM pg_stat_activity WHERE usename='mxas_runtime' AND datname='atomic_preflight' AND wait_event_type='Lock' AND state='active' AND query LIKE '%mixer_hosted_release.upload_v1%'"]
    waiting = Enum.reduce_while(1..12, false, fn _, _ ->
      case System.cmd("psql", args, stderr_to_stdout: true) do
        {"1\n", 0} -> {:halt, true}
        _ -> Process.sleep(5); {:cont, false}
      end
    end)
    {waiting, args}
  end

  test "R01 null, fractional, NaN and unbounded completion fail closed in actual SQL" do
    for input <- [nil, "99.5", "NaN", "Infinity", "9007199254740992"] do
      assert {:rejected, _, _} = review_raw_attempt(input_authenticated_at: input)
      assert counts() == [0, 0, 0, "0"]
    end
    observe("review_completion_malformed", %{null_fraction_nan_infinity_overmax_rejected: true})
  end

  test "R02 zero is a numeric value rather than absence; stale zero is rejected" do
    assert {:rejected, _, _} = review_raw_attempt(input_authenticated_at: 0)
    sql("UPDATE mixer_authz.fixture_clock SET now_s=0")
    o = opts()
    assert {:ok, [201, _, _, false]} = Context.enter(fn c ->
      bind(c, Context, o)
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','0',true)", [], log: false)
      changed = %{c | authentication_completed_at: 0}
      result = upload(changed, o)
      # Restore the outer invocation's original immutable field before its guard.
      Repo.query!("SELECT set_config('mixer_atomic.authentication_completed_at','99',true)", [], log: false)
      result
    end)
    assert scalar("SELECT display_json->'actor'->>10 FROM mixer_hosted_release.audit_events") == "0"
    observe("review_zero_completion", %{stale_zero_rejected: true, zero_is_valid_when_fresh_and_bound: true, trusted_raw_sql_fixture_only: true})
  end

  test "R03 observed limitation: SQL specimen accepts noninteger and NaN token expiry" do
    for {expiry, key} <- [{"10000.5", "fraction"}, {"NaN", "nan"}, {"9007199254740992", "over53"}] do
      assert {:ok, [status, _, _, false]} = review_raw_attempt(expires: expiry, key: key)
      assert status in [200, 201]
    end
    observe("review_expiry_validation_gap", %{fractional: "10000.5", nan: "NaN", over_integer53: "9007199254740992", all_accepted_by_specimen: true, required_product_fix: "validate finite integer expiry 0..2^53-1 before cast and inside SQL"})
  end

  test "R04 current expiry is reread after blocked head lock before cached result" do
    assert {:ok, _} = attempt(expires: 140)
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
        send(parent, :review_head_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=140")
        after
          1000 -> raise "review holder release absent"
        end
      end)
    end)
    assert_receive :review_head_locked
    waiter = Task.async(fn -> attempt(expires: 140) end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_expiry_after_wait", %{cached_result_denied_after_clock_advanced: true, actual_runtime_lock_wait_confirmed: waiting, psql_argv: argv, completion_still_within_age45: true})
  end

  test "R05 completion age is reread after blocked head lock before cached result" do
    assert {:ok, _} = attempt()
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_hosted_release.tenant_heads FOR UPDATE")
        send(parent, :review_age_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=145")
        after
          1000 -> raise "review holder release absent"
        end
      end)
    end)
    assert_receive :review_age_locked
    waiter = Task.async(fn -> attempt() end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_completion_after_wait", %{cached_result_denied_after_age46: true, actual_runtime_lock_wait_confirmed: waiting, psql_argv: argv, token_still_unexpired: true})
  end

  test "R06 observed limitation: malformed stored idempotent material is returned verbatim" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.idempotency SET status=599,response=convert_to('altered','UTF8')")
    assert {:ok, [599, "altered", event, true]} = attempt()
    assert Decimal.equal?(event, 1)
    observe("review_idempotency_material_gap", %{changed_status_and_body_returned: true, runtime_can_change_rows: false, product_constraints_and_linkage_pending: true})
  end

  test "R07 observed limitation: idempotency event FK does not establish original-event linkage" do
    assert {:ok, _} = attempt(key: "first")
    assert {:ok, _} = attempt(key: "second")
    sql("UPDATE mixer_hosted_release.idempotency SET event_id=2 WHERE key='first'")
    assert {:ok, [201, body, event, true]} = attempt(key: "first")
    assert Decimal.equal?(event, 2)
    assert Jason.decode!(body)["event_id"] == "1"
    observe("review_idempotency_event_gap", %{response_event_id: "1", returned_event_id: "2", wrong_existing_event_accepted: true, immutable_runtime_rows: true})
  end

  test "R08 observed limitation: missing nullable display key and extra replacement bypass closed shape" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=(display_json-'source_ip')||'{\"unexpected\":null}'::jsonb")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8')")
    assert {:ok, [200, _, _, false]} = attempt(key: "next")
    observe("review_closed_display_gap", %{same_count_extra_and_missing_null_accepted: true, known_partial_decoder_only: true})
  end

  test "R09 observed limitation: noncanonical decimal display spelling has identical CBOR" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{actor,4}','\"01\"'::jsonb)")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8')")
    assert {:ok, [200, _, _, false]} = attempt(key: "next")
    observe("review_canonical_display_gap", %{leading_zero_integer_accepted: true, full_closed_decoder_pending: true})
  end

  test "R10 observed limitation: terminal predecessor edge is not checked against predecessor" do
    assert {:ok, _} = attempt(key: "first")
    assert {:ok, _} = attempt(key: "second")
    sql("UPDATE mixer_hosted_release.audit_events SET previous_hash=decode(repeat('ab',32),'hex'),display_json=jsonb_set(display_json,'{previous_hash}',to_jsonb(repeat('ab',32))) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET event_cbor=mixer_hosted_release.event_from_display(display_json) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET event_hash=mixer_hosted_release.hash_domain('mixer.hosted.audit.v1',event_cbor) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET display_json=jsonb_set(display_json,'{hash}',to_jsonb(encode(event_hash,'hex'))) WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.audit_events SET display_bytes=convert_to(display_json::text,'UTF8') WHERE event_id=2")
    sql("UPDATE mixer_hosted_release.tenant_heads SET audit_hash=(SELECT event_hash FROM mixer_hosted_release.audit_events WHERE event_id=2)")
    assert {:ok, [200, _, _, false]} = attempt(key: "third")
    observe("review_predecessor_edge_gap", %{coherent_wrong_predecessor_accepted: true, documented_historical_verification_pending: true})
  end

  test "R11 observed limitation: artifact creation event lacks typed immutable linkage" do
    assert {:ok, _} = attempt()
    sql("UPDATE mixer_hosted_release.artifacts SET created_event=999")
    assert {:ok, [200, _, _, false]} = attempt(key: "next")
    observe("review_artifact_creation_link_gap", %{nonexistent_creation_event_accepted: true, complete_row_constraints_pending: true})
  end

  test "R12 private helper SQL identities owner ACL and type field ordering are captured" do
    rows = sql("SELECT p.oid::regprocedure::text,r.rolname,p.prosecdef,p.provolatile::text,p.proparallel::text,p.proleakproof,coalesce(p.proconfig,ARRAY[]::text[]),p.proacl::text FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname IN ('mixer_authz','mixer_hosted_release') ORDER BY p.oid::regprocedure::text").rows
    for [identity, owner, definer, volatility, parallel, leak, config, _acl] <- rows do
      assert "search_path=pg_catalog" in config
      refute leak
      if definer do
        assert owner in ["mxas_resolver", "mxas_writer"]
        assert volatility == "v"
        assert parallel == "u"
        assert "row_security=on" in config
      else
        assert owner == "mxas_schema"
        assert volatility == "i"
        assert identity =~ "mixer_hosted_release."
      end
    end
    denied = for helper <- ["u(numeric)", "b(bytea)", "t(text)", "a(bytea[])", "hash_domain(text,bytea)", "target(mixer_hosted_release.upload_input)", "hx(text)", "event_from_display(jsonb)"] do
      allowed = scalar("SELECT has_function_privilege('mxas_runtime',$1,'EXECUTE')", ["mixer_hosted_release." <> helper])
      refute allowed
      helper
    end
    fields = sql("SELECT a.attnum,a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_type t ON t.typrelid=a.attrelid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='mixer_hosted_release' AND t.typname='call_context' AND a.attnum>0 ORDER BY a.attnum").rows
    assert List.last(fields) == [9, "authentication_completed_at", "numeric"]
    observe("review_actual_catalog", %{functions: rows, runtime_private_helpers_denied: denied, call_context_fields: fields, product_manifest_conceptual_names_are_not_this_DDL: true})
  end

  test "R13 independent randomized uint64 encodings agree with SQL and Elixir" do
    vectors = Jason.decode!(File.read!("review-uint64-vectors.json"))
    for %{"decimal" => n, "cbor_hex" => expected} <- vectors do
      assert scalar("SELECT encode(mixer_hosted_release.u($1::text::numeric),'hex')", [n]) == expected
      assert Codec.hex(Codec.encode(String.to_integer(n))) == expected
    end
    observe("review_uint64_independent", %{vector_count: length(vectors), exact_integer_python_reference: true})
  end

  test "R14 local corrupt object is never collected while outcome remains uncertain" do
    root = Path.join(System.fetch_env!("MXAS_BLOBS"), "review-corrupt-uncertain")
    {store, reference} = Blob.stage(Blob.open(root), "review-material")
    "sha256:" <> name = reference
    path = Path.join(root, name)
    File.chmod!(path, 0o600)
    File.write!(path, "altered")
    assert Blob.reconcile(store, MapSet.new(), true) == store
    assert File.exists?(path)
    assert_raise ArgumentError, fn -> Blob.open(root) end
    observe("review_blob_uncertainty", %{corruption_detected: true, uncertain_collection_preserved_file: true, offline_recovery_required: true})
  end

  test "R15 missing policy row rolls back without treating empty shared lock as success" do
    sql("DELETE FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid", [@one])
    assert {:rejected, _, _} = attempt()
    assert counts() == [0, 0, 0, "0"]
    sql("INSERT INTO mixer_authz.fixture_policy VALUES($1::text::uuid,'developer',true,1)", [@one])
    observe("review_missing_lock", %{missing_row_denied: true, no_partial_effects: true})
  end

  test "R16 every immutable artifact value is compared on new-key identical upload" do
    assert {:ok, _} = attempt()
    for {column, expression} <- [{"signed_document", "convert_to('{ }','UTF8')"}, {"signature", "decode(repeat('01',64),'hex')"}, {"payload_size", "2"}, {"blob_ref", "'sha256:'||repeat('01',32)"}] do
      original = scalar("SELECT " <> column <> " FROM mixer_hosted_release.artifacts")
      sql("UPDATE mixer_hosted_release.artifacts SET " <> column <> "=" <> expression)
      assert {:rejected, _, _} = attempt(key: "changed-" <> column)
      sql("UPDATE mixer_hosted_release.artifacts SET " <> column <> "=$1", [original])
    end
    assert counts() == [1, 1, 1, "1"]
    observe("review_material_compare", %{signed_signature_size_reference_corruption_rejected: true})
  end

  test "R17 composite numeric20 scale0 rounds invalid fractional input before a body guard" do
    sql("CREATE TYPE mixer_hosted_release.review_numeric_typmod AS (expires_at numeric(20,0),authentication_completed_at numeric(20,0))")
    rows = sql("SELECT (v).expires_at::text,(v).authentication_completed_at::text,trunc((v).expires_at)=(v).expires_at,trunc((v).authentication_completed_at)=(v).authentication_completed_at FROM (SELECT ROW(149.5::numeric,-0.1::numeric)::mixer_hosted_release.review_numeric_typmod AS v) s").rows
    assert rows == [["150", "0", true, true]]
    fields = sql("SELECT a.attname,format_type(a.atttypid,a.atttypmod) FROM pg_attribute a JOIN pg_type t ON t.typrelid=a.attrelid JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='mixer_hosted_release' AND t.typname='review_numeric_typmod' AND a.attnum>0 ORDER BY a.attnum").rows
    observe("review_numeric_typmod_rounding", %{raw_inputs: ["149.5", "-0.1"], post_cast: rows, catalog_fields: fields, trunc_guard_after_cast_can_miss_invalid_input: true, product_recommendation: "unconstrained numeric context inputs plus explicit finite integer 0..2^53-1 guards"})
    sql("DROP TYPE mixer_hosted_release.review_numeric_typmod")
  end

  test "R18 unconstrained numeric entry guard rejects nonfinite fractional negative and overrange" do
    for {input, expected} <- [{nil, false}, {"NaN", false}, {"Infinity", false}, {"-Infinity", false}, {"-0.1", false}, {"99.5", false}, {"9007199254740992", false}, {"0", true}, {"9007199254740991", true}] do
      assert scalar("SELECT coalesce($1::text::numeric >= 0 AND $1::text::numeric <= 9007199254740991 AND trunc($1::text::numeric) = $1::text::numeric,false)", [input]) == expected
    end
    observe("review_finite_seconds_oracle", %{unconstrained_numeric_guard_checked: true, valid_zero_and_max: true, null_nonfinite_fraction_negative_overmax_rejected: true})
  end

  test "R19 observed limitation: expiry is not refreshed after later blocking SQL before insert" do
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("LOCK TABLE mixer_authz.fixture_fault IN ACCESS EXCLUSIVE MODE")
        send(parent, :review_late_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_clock SET now_s=140")
        after
          1000 -> raise "review late holder release absent"
        end
      end)
    end)
    assert_receive :review_late_locked
    waiter = Task.async(fn -> attempt(expires: 140) end)
    args = ["-h", System.fetch_env!("MXAS_SOCKET"), "-U", "preflight_owner", "-d", "atomic_preflight", "-At", "-c", "SELECT count(*) FROM pg_locks WHERE relation='mixer_authz.fixture_fault'::regclass AND NOT granted"]
    blocked = Enum.reduce_while(1..15, false, fn _, _ ->
      case System.cmd("psql", args, stderr_to_stdout: true) do
        {"1\n", 0} -> {:halt, true}
        _ -> Process.sleep(5); {:cont, false}
      end
    end)
    send(holder.pid, :release)
    Task.await(holder)
    result = Task.await(waiter)
    assert blocked
    assert {:ok, [201, _, _, false]} = result
    assert scalar("SELECT now_s::text FROM mixer_authz.fixture_clock") == "140"
    assert scalar("SELECT display_json->'decision'->>0 FROM mixer_hosted_release.audit_events") == "100"
    observe("review_expiry_before_effect_gap", %{actual_relation_lock_wait_confirmed: true, lock_relation: "mixer_authz.fixture_fault", psql_argv: args, expiry: "140", clock_at_insert: "140", event_decision_time: "100", inserted_after_expiry: true, completion_still_within_age45: true, product_fresh_time_before_persistence_required: true})
  end

  test "R20 policy is read after confirmed shared lock wait before cached result" do
    assert {:ok, _} = attempt()
    parent = self()
    holder = Task.async(fn ->
      AdminRepo.transaction(fn ->
        sql("SELECT * FROM mixer_authz.fixture_policy WHERE actor=$1::text::uuid FOR UPDATE", [@one])
        send(parent, :review_policy_locked)
        receive do
          :release -> sql("UPDATE mixer_authz.fixture_policy SET active=false,revision=2 WHERE actor=$1::text::uuid", [@one])
        after
          1000 -> raise "review policy holder release absent"
        end
      end)
    end)
    assert_receive :review_policy_locked
    waiter = Task.async(fn -> attempt() end)
    {waiting, argv} = review_wait_for_runtime_lock()
    send(holder.pid, :release)
    Task.await(holder)
    assert waiting
    assert {:rejected, _, _} = Task.await(waiter)
    assert counts() == [1, 1, 1, "1"]
    observe("review_policy_after_wait", %{actual_runtime_lock_wait_confirmed: waiting, revoked_cached_result_denied: true, psql_argv: argv})
  end
