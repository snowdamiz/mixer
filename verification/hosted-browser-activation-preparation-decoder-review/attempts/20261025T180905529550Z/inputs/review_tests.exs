ExUnit.start(autorun: false)

defmodule MixerActivationPreparationReviewFixture do
  @moduledoc false

  def bytea(size, byte), do: "\\x" <> Base.encode16(:binary.copy(<<byte>>, size), case: :lower)
  def token(byte), do: Base.url_encode64(:binary.copy(<<byte>>, 32), padding: false)

  def projection(kind \\ "preauth") do
    browser = %{
      "id" => bytea(16, 1),
      "cookie_digest" => bytea(32, 2),
      "status" => kind,
      "epoch" => 2,
      "revision" => 3,
      "generation" => token(3),
      "csrf_digest" => bytea(32, 4),
      "created_at" => 10,
      "last_seen_at" => 20,
      "absolute_expires_at" => 2_000,
      "idle_expires_at" => 1_000,
      "expected_profile_id" => "profile-review",
      "expected_profile_version" => 7,
      "initial_config_digest" => bytea(32, 5),
      "config_digest" => bytea(32, 6),
      "profile_id" => if(kind == "active", do: "profile-review"),
      "profile_version" => if(kind == "active", do: 7),
      "principal_id" => if(kind == "active", do: "old-principal-private-marker"),
      "family_id" => if(kind == "active", do: "old-family-private-marker"),
      "credential_ref" => if(kind == "active", do: "old-credential-private-marker"),
      "credential_revision" => if(kind == "active", do: 8),
      "audit_sequence" => 3
    }

    vault = %{
      "browser_id" => browser["id"],
      "epoch" => browser["epoch"],
      "session_revision" => browser["revision"],
      "vault_generation" => 4,
      "ciphertext_version" => 1,
      "envelope_kind" => kind,
      "key_id" => "private-key-marker",
      "iv" => bytea(12, 7),
      "tag" => bytea(16, 8),
      "ciphertext" => bytea(1, 9)
    }

    attempt = %{
      "state_digest" => bytea(32, 10),
      "browser_id" => browser["id"],
      "browser_epoch" => browser["epoch"],
      "browser_revision" => browser["revision"],
      "cookie_digest" => browser["cookie_digest"],
      "generation" => browser["generation"],
      "config_digest" => browser["config_digest"],
      "profile_id" => browser["expected_profile_id"],
      "profile_version" => browser["expected_profile_version"],
      "issuer" => "https://issuer.invalid/review",
      "client_id" => "client-review-private-marker",
      "redirect_uri" => "https://client.invalid/callback",
      "return_route" => "workspace",
      "nonce_digest" => bytea(32, 11),
      "created_at" => 20,
      "expires_at" => 120,
      "status" => "claimed",
      "claim_digest" => bytea(32, 12),
      "claimed_at" => 30,
      "claim_expires_at" => 50,
      "completion_reason" => nil,
      "ciphertext_version" => 1,
      "key_id" => nil,
      "iv" => nil,
      "tag" => nil,
      "ciphertext" => nil
    }

    %{
      "version" => 1,
      "snapshot" => %{"browser" => browser, "vault" => vault, "attempt" => attempt},
      "principal_id" => "new-principal-private-marker",
      "profile_revision" => 12,
      "binding_revision" => 13,
      "principal_revision" => 14
    }
  end

  def unclaimed(status) do
    input = projection()
    attempt = input["snapshot"]["attempt"]

    attempt =
      case status do
        :absent ->
          nil

        :pending ->
          Map.merge(attempt, %{
            "status" => "pending",
            "claim_digest" => nil,
            "claimed_at" => nil,
            "claim_expires_at" => nil,
            "key_id" => "pending-key-marker",
            "iv" => bytea(12, 13),
            "tag" => bytea(16, 14),
            "ciphertext" => bytea(1, 15)
          })

        :provider_rejected ->
          Map.merge(attempt, %{
            "status" => "provider_rejected",
            "claim_digest" => nil,
            "claimed_at" => nil,
            "claim_expires_at" => nil,
            "completion_reason" => "provider_rejected"
          })

        :completed ->
          input = projection("active")

          input["snapshot"]["attempt"]
          |> Map.merge(%{
            "status" => "completed",
            "browser_epoch" => 1,
            "browser_revision" => 2,
            "cookie_digest" => bytea(32, 16),
            "generation" => token(17),
            "completion_reason" => "completed"
          })
      end

    input = if status == :completed, do: projection("active"), else: input
    put_in(input, ["snapshot", "attempt"], attempt)
  end
end

defmodule MixerActivationPreparationDecoderReviewTest do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{ActivationPreparation, StoredSnapshot, Vault}
  alias MixerActivationPreparationReviewFixture, as: F

  @fields ~w(version snapshot principal_id profile_revision binding_revision principal_revision)
  @revisions ~w(profile_revision binding_revision principal_revision)
  @maximum 9_007_199_254_740_991
  @error {:error, :session_unavailable}

  test "preauth produces exactly the six typed fields and the actual complete snapshot" do
    input = F.projection()
    assert {:ok, expected} = StoredSnapshot.decode(input["snapshot"])
    assert {:ok, result} = ActivationPreparation.decode(input)
    assert result.__struct__ == ActivationPreparation

    assert Map.keys(Map.from_struct(result)) |> Enum.sort() ==
             Enum.sort(Enum.map(@fields, &String.to_existing_atom/1))

    assert result.version === 1
    assert result.snapshot === expected
    assert result.principal_id === input["principal_id"]
    assert result.profile_revision === 12
    assert result.binding_revision === 13
    assert result.principal_revision === 14
    assert result.snapshot.attempt["status"] === "claimed"
    assert result.snapshot.attempt_envelope === nil
    assert result.snapshot.session_envelope.__struct__ == StoredSnapshot.Envelope
    assert result.snapshot.session_envelope.sealed.__struct__ == Vault.Sealed
    assert result.snapshot.browser["id"] === :binary.copy(<<1>>, 16)
    assert result.snapshot.attempt["claim_digest"] === :binary.copy(<<12>>, 32)
  end

  test "active browser preserves old identity and accepts a different provisional incoming principal" do
    input = F.projection("active")
    assert {:ok, result} = ActivationPreparation.decode(input)
    assert result.snapshot.browser["principal_id"] == "old-principal-private-marker"
    assert result.principal_id == "new-principal-private-marker"
    refute result.principal_id == result.snapshot.browser["principal_id"]
    assert result.snapshot.session_envelope.context.principal_id == "old-principal-private-marker"
  end

  test "every closed field is mandatory" do
    for field <- @fields,
        do: assert(ActivationPreparation.decode(Map.delete(F.projection(), field)) == @error)
  end

  test "every atom alias and mixed-key replacement denies" do
    for field <- @fields do
      input = F.projection()
      value = Map.fetch!(input, field)

      assert ActivationPreparation.decode(
               input
               |> Map.delete(field)
               |> Map.put(String.to_existing_atom(field), value)
             ) == @error

      assert ActivationPreparation.decode(Map.put(input, String.to_existing_atom(field), value)) ==
               @error
    end
  end

  test "extra keys including purported authority deny" do
    for key <- [
          "extra",
          "__struct__",
          "ready",
          "authorized",
          "verified_identity",
          :__struct__,
          1,
          <<255>>
        ] do
      assert ActivationPreparation.decode(Map.put(F.projection(), key, true)) == @error
    end
  end

  test "nonmaps structs and decoded typed results deny" do
    assert {:ok, result} = ActivationPreparation.decode(F.projection())

    for input <- [
          nil,
          false,
          true,
          [],
          @fields,
          1,
          1.0,
          "{}",
          <<255>>,
          self(),
          make_ref(),
          fn -> :ok end,
          result,
          %Vault.Preauth{csrf: "private-marker"}
        ] do
      assert ActivationPreparation.decode(input) == @error
    end

    forged = Map.put(Map.delete(F.projection(), "version"), :__struct__, ActivationPreparation)
    assert ActivationPreparation.decode(forged) == @error
  end

  test "version requires exact integer one" do
    for value <- [nil, true, false, 0, -1, 2, 1.0, "1", <<1>>, [1], %{}] do
      assert ActivationPreparation.decode(Map.put(F.projection(), "version", value)) == @error
    end
  end

  test "each revision accepts one and positive safe53 maximum independently" do
    for field <- @revisions, value <- [1, @maximum] do
      input = Map.put(F.projection(), field, value)
      assert {:ok, decoded} = ActivationPreparation.decode(input)
      assert Map.fetch!(decoded, String.to_existing_atom(field)) === value
    end
  end

  test "each revision denies noninteger zero negative and safe53 overflow" do
    for field <- @revisions,
        value <- [
          nil,
          true,
          false,
          0,
          -1,
          @maximum + 1,
          :erlang.bsl(1, 128),
          1.0,
          "1",
          <<1>>,
          [1],
          %{}
        ] do
      assert ActivationPreparation.decode(Map.put(F.projection(), field, value)) == @error
    end
  end

  test "principal accepts exact byte boundaries without normalization or trimming" do
    for value <- [
          "x",
          String.duplicate("x", 128),
          String.duplicate("é", 64),
          String.duplicate("😀", 32),
          " ",
          "é"
        ] do
      assert {:ok, decoded} =
               ActivationPreparation.decode(Map.put(F.projection(), "principal_id", value))

      assert decoded.principal_id === value
    end
  end

  test "principal denies invalid text NUL and byte overflow" do
    for value <- [
          nil,
          true,
          1,
          1.0,
          [],
          %{},
          "",
          String.duplicate("x", 129),
          String.duplicate("é", 65),
          String.duplicate("😀", 33),
          <<0>>,
          "x\0y",
          "\0" <> String.duplicate("x", 127),
          <<255>>,
          <<192, 175>>,
          <<237, 160, 128>>,
          <<240, 159, 152>>
        ] do
      assert ActivationPreparation.decode(Map.put(F.projection(), "principal_id", value)) ==
               @error
    end
  end

  test "nested snapshot requires exact raw shape rather than typed snapshot or aliases" do
    input = F.projection()
    assert {:ok, snapshot} = StoredSnapshot.decode(input["snapshot"])

    for value <- [
          nil,
          false,
          [],
          "{}",
          %{},
          snapshot,
          %{
            browser: input["snapshot"]["browser"],
            vault: input["snapshot"]["vault"],
            attempt: input["snapshot"]["attempt"]
          }
        ] do
      assert ActivationPreparation.decode(Map.put(input, "snapshot", value)) == @error
    end

    for field <- ~w(browser vault attempt) do
      assert ActivationPreparation.decode(update_in(input["snapshot"], &Map.delete(&1, field))) ==
               @error

      assert ActivationPreparation.decode(
               update_in(input["snapshot"], &Map.put(&1, "extra", :secret))
             ) == @error
    end
  end

  test "all existing nested keys remain mandatory and atom aliases deny" do
    input = F.projection()

    for row <- ~w(browser vault attempt), {field, value} <- input["snapshot"][row] do
      assert ActivationPreparation.decode(
               update_in(input, ["snapshot", row], &Map.delete(&1, field))
             ) == @error

      renamed =
        input
        |> update_in(["snapshot", row], &Map.delete(&1, field))
        |> put_in(["snapshot", row, String.to_atom(field)], value)

      assert ActivationPreparation.decode(renamed) == @error

      assert ActivationPreparation.decode(put_in(input, ["snapshot", row, "extra"], true)) ==
               @error
    end
  end

  test "nested rows deny structs scalar containers and manufactured struct keys" do
    for row <- ~w(browser vault attempt),
        value <- [nil, false, [], "{}", %{}, %Vault.Preauth{csrf: "private-marker"}] do
      assert ActivationPreparation.decode(put_in(F.projection(), ["snapshot", row], value)) ==
               @error
    end

    for row <- ~w(browser vault attempt) do
      input = F.projection()
      forged = Map.put(input["snapshot"][row], :__struct__, StoredSnapshot)
      assert ActivationPreparation.decode(put_in(input, ["snapshot", row], forged)) == @error
    end
  end

  test "actual ordinary decoder accepts each unclaimed state but preparation denies it" do
    for status <- [:absent, :pending, :provider_rejected, :completed] do
      input = F.unclaimed(status)
      assert {:ok, _} = StoredSnapshot.decode(input["snapshot"])
      assert ActivationPreparation.decode(input) == @error
    end
  end

  test "claimed requires all cipher fields erased individually" do
    for {field, value} <- [
          {"key_id", "retained-key-marker"},
          {"iv", F.bytea(12, 7)},
          {"tag", F.bytea(16, 8)},
          {"ciphertext", F.bytea(1, 9)}
        ] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "attempt", field], value)
             ) == @error
    end
  end

  test "claimed digest time and completion fields preserve nested validation" do
    for {field, value} <- [
          {"claim_digest", nil},
          {"claim_digest", F.bytea(31, 12)},
          {"claimed_at", nil},
          {"claimed_at", 19},
          {"claim_expires_at", 30},
          {"claim_expires_at", 121},
          {"claim_expires_at", 91},
          {"completion_reason", "completed"},
          {"ciphertext_version", 2}
        ] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "attempt", field], value)
             ) == @error
    end
  end

  test "every session and attempt linkage mismatch denies" do
    mismatches = [
      {"vault", "browser_id", F.bytea(16, 30)},
      {"vault", "epoch", 3},
      {"vault", "session_revision", 4},
      {"vault", "envelope_kind", "active"},
      {"attempt", "browser_id", F.bytea(16, 31)},
      {"attempt", "browser_epoch", 3},
      {"attempt", "browser_revision", 4},
      {"attempt", "cookie_digest", F.bytea(32, 32)},
      {"attempt", "generation", F.token(33)},
      {"attempt", "config_digest", F.bytea(32, 34)},
      {"attempt", "profile_id", "wrong-profile"},
      {"attempt", "profile_version", 8}
    ]

    for {row, field, value} <- mismatches,
        do:
          assert(
            ActivationPreparation.decode(put_in(F.projection(), ["snapshot", row, field], value)) ==
              @error
          )
  end

  test "browser invariants and nonlive statuses deny through ordinary decoder" do
    for {field, value} <- [
          {"status", "revoked"},
          {"status", "expired"},
          {"status", "claimed"},
          {"created_at", 21},
          {"last_seen_at", 1_000},
          {"idle_expires_at", 2_001},
          {"audit_sequence", 2},
          {"principal_id", "unexpected-link"},
          {"epoch", 0},
          {"revision", @maximum + 1}
        ] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "browser", field], value)
             ) == @error
    end
  end

  test "canonical bytea and bounded session ciphertext are enforced" do
    for value <- [nil, "", "00", "\\x", "\\x0", "\\xGG", "\\xAA", <<9>>, F.bytea(8_193, 9)] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "vault", "ciphertext"], value)
             ) == @error
    end

    for size <- [1, 8_192] do
      assert {:ok, decoded} =
               ActivationPreparation.decode(
                 put_in(F.projection(), ["snapshot", "vault", "ciphertext"], F.bytea(size, 9))
               )

      assert byte_size(decoded.snapshot.session_envelope.sealed.ciphertext) == size
    end

    for {field, size} <- [{"iv", 11}, {"iv", 13}, {"tag", 15}, {"tag", 17}] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "vault", field], F.bytea(size, 7))
             ) == @error
    end
  end

  test "key IDs retain the actual Vault AAD contract" do
    for value <- [nil, "", "x/y", "x\0y", "é", String.duplicate("x", 129)] do
      assert ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "vault", "key_id"], value)
             ) == @error
    end

    assert {:ok, _} =
             ActivationPreparation.decode(
               put_in(F.projection(), ["snapshot", "vault", "key_id"], String.duplicate("a", 128))
             )
  end

  test "all errors are exact generic results and do not print secret inputs" do
    for input <- [
          nil,
          Map.put(F.projection(), "principal_id", "secret-invalid\0marker"),
          put_in(F.projection(), ["snapshot", "vault", "key_id"], "secret/invalid-marker")
        ] do
      output =
        ExUnit.CaptureIO.capture_io(fn ->
          assert ActivationPreparation.decode(input) === @error
        end)

      assert output == ""
    end
  end

  test "Inspect redacts typed result and independently inspected nested secret containers" do
    assert {:ok, decoded} = ActivationPreparation.decode(F.projection("active"))
    envelope = decoded.snapshot.session_envelope

    for term <- [decoded, decoded.snapshot, envelope, envelope.sealed] do
      rendered = inspect(term, limit: :infinity, printable_limit: :infinity)

      for marker <- [
            "old-principal",
            "new-principal",
            "old-family",
            "old-credential",
            "private-key-marker",
            "client-review",
            "ciphertext",
            "cookie_digest",
            "claim_digest",
            "profile_revision",
            "principal_revision"
          ] do
        refute String.contains?(rendered, marker)
      end
    end
  end

  test "shape-valid ciphertext is not decryption authentication or authority" do
    input = F.projection("active")
    assert {:ok, decoded} = ActivationPreparation.decode(input)
    assert {:ok, key} = Vault.key("private-key-marker", :binary.copy(<<42>>, 32))

    assert Vault.open(
             key,
             decoded.snapshot.session_envelope.context,
             decoded.snapshot.session_envelope.sealed
           ) == {:error, :vault_unavailable}

    refute Map.has_key?(decoded, :authenticated)
    refute Map.has_key?(decoded, :authorized)
    refute Map.has_key?(decoded, :ready)
  end

  test "shape-valid stale synthetic dates are accepted without a clock or current validity" do
    assert {:ok, decoded} = ActivationPreparation.decode(F.projection())
    assert decoded.snapshot.attempt["claim_expires_at"] == 50
    assert decoded.snapshot.browser["absolute_expires_at"] == 2_000
  end

  test "all provisional revisions and principal can vary without any owner-retained state" do
    input = F.projection("active")

    changed =
      Map.merge(input, %{
        "principal_id" => "entirely-other-incoming",
        "profile_revision" => 1,
        "binding_revision" => @maximum,
        "principal_revision" => 2
      })

    assert {:ok, a} = ActivationPreparation.decode(input)
    assert {:ok, b} = ActivationPreparation.decode(changed)
    assert a.snapshot === b.snapshot
    refute a.principal_id == b.principal_id
    assert b.profile_revision === 1
    assert b.binding_revision === @maximum
    assert b.principal_revision === 2
  end

  test "public surface has no startup configuration readiness or authority entrypoint" do
    assert ActivationPreparation.__info__(:functions) |> Enum.sort() == [
             __struct__: 0,
             __struct__: 1,
             decode: 1
           ]
  end

  test "decode has no process dictionary random-state environment or cwd effects" do
    before_dictionary = Process.get()
    before_environment = System.get_env()
    before_cwd = File.cwd!()

    for _ <- 1..20 do
      assert {:ok, _} = ActivationPreparation.decode(F.projection())
      assert ActivationPreparation.decode(Map.put(F.projection(), "version", 0)) == @error
    end

    assert Process.get() == before_dictionary
    assert System.get_env() == before_environment
    assert File.cwd!() == before_cwd
  end

  test "call trace observes only pure selected validators and runtime builtins" do
    inputs = [
      F.projection(),
      F.projection("active"),
      F.unclaimed(:pending),
      Map.put(F.projection(), "version", 0)
    ]

    parent = self()

    worker =
      spawn(fn ->
        receive do
          {:run, cases} ->
            results = Enum.map(cases, &ActivationPreparation.decode/1)
            send(parent, {:decoded, self(), results})

            receive do
              :finish -> :ok
            end
        end
      end)

    :erlang.trace_pattern({:_, :_, :_}, true, [:local])

    :erlang.trace_pattern(
      {ActivationPreparation, :decode, 1},
      [{:_, [], [{:return_trace}]}],
      [:local]
    )

    :erlang.trace(worker, true, [:call, {:tracer, self()}])
    send(worker, {:run, inputs})
    assert_receive {:decoded, ^worker, results}, 5_000
    assert [{:ok, _}, {:ok, _}, @error, @error] = results
    delivered = :erlang.trace_delivered(worker)
    assert_receive {:trace_delivered, ^worker, ^delivered}, 5_000
    :erlang.trace(worker, false, [:call])
    :erlang.trace_pattern({:_, :_, :_}, false, [:local])
    send(worker, :finish)
    calls = drain_calls(worker, [], 0)
    assert Enum.any?(calls, &match?({ActivationPreparation, :decode, _}, &1))
    assert Enum.any?(calls, &match?({StoredSnapshot, :decode, _}, &1))
    assert Enum.any?(calls, &match?({Vault, :associated_data, _}, &1))

    forbidden_modules = [
      System,
      File,
      IO,
      DateTime,
      NaiveDateTime,
      Time,
      Agent,
      GenServer,
      Supervisor,
      Application,
      Task,
      Port,
      Process,
      :file,
      :prim_file,
      :file_io_server,
      :gen_tcp,
      :gen_udp,
      :ssl,
      :httpc,
      :http,
      :inet,
      :socket,
      :os,
      :ets,
      :persistent_term,
      :application,
      :crypto,
      :rand,
      :calendar,
      :logger,
      Logger,
      MixerHosted.Repo
    ]

    for {module, function, args} <- calls do
      refute module in forbidden_modules,
             "unexpected effectful call #{inspect({module, function, length(args)})}"

      if module == :erlang do
        refute function in [
                 :system_time,
                 :monotonic_time,
                 :time_offset,
                 :timestamp,
                 :date,
                 :time,
                 :localtime,
                 :universaltime,
                 :put,
                 :erase,
                 :send,
                 :spawn,
                 :spawn_link,
                 :spawn_monitor,
                 :open_port,
                 :register,
                 :unregister,
                 :exit,
                 :halt,
                 :process_flag,
                 :load_nif,
                 :send_after,
                 :start_timer
               ]
      end
    end
  end

  defp drain_calls(worker, found, depth) do
    receive do
      {:trace, ^worker, :call, {ActivationPreparation, :decode, _} = call} ->
        drain_calls(worker, [call | found], depth + 1)

      {:trace, ^worker, :return_from, {ActivationPreparation, :decode, 1}, _} ->
        drain_calls(worker, found, depth - 1)

      {:trace, ^worker, :call, call} ->
        drain_calls(worker, if(depth > 0, do: [call | found], else: found), depth)
    after
      0 -> found
    end
  end
end

result = ExUnit.run()
IO.puts("MIXER_ACTIVATION_REVIEW_RESULT=" <> inspect(result, limit: :infinity))
System.halt(if result.failures == 0, do: 0, else: 1)
