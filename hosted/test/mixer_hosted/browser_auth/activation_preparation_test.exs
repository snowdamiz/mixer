defmodule MixerHosted.BrowserAuth.ActivationPreparationTest do
  use ExUnit.Case, async: true
  import ExUnit.CaptureLog
  alias MixerHosted.BrowserAuth.{ActivationPreparation, StoredSnapshot, Vault}

  @error {:error, :session_unavailable}
  @max_integer 9_007_199_254_740_991
  @csrf Base.url_encode64(:binary.copy(<<11>>, 32), padding: false)
  @verifier Base.url_encode64(:binary.copy(<<12>>, 32), padding: false)
  @generation Base.url_encode64(:binary.copy(<<13>>, 32), padding: false)
  @replacement Base.url_encode64(:binary.copy(<<14>>, 32), padding: false)
  @revision_fields ~w(profile_revision binding_revision principal_revision)

  defp raw(byte, size \\ 32), do: :binary.copy(<<byte>>, size)
  defp hex(bytes), do: "\\x" <> Base.encode16(bytes, case: :lower)

  defp key do
    {:ok, key} = Vault.key("preparation-fixture-key", raw(42))
    key
  end

  defp context(kind) do
    %{
      purpose: kind,
      browser_id: raw(1, 16),
      cookie_digest: raw(2),
      csrf_digest: :crypto.hash(:sha256, @csrf),
      epoch: 2,
      revision: 2,
      generation: @generation,
      vault_generation: 2,
      config_digest: raw(3),
      profile_id: "human-main",
      profile_version: 1,
      principal_id: if(kind == :active, do: "old-principal"),
      family_id: if(kind == :active, do: "old-family"),
      credential_ref: if(kind == :active, do: "old-credential"),
      credential_revision: if(kind == :active, do: 1)
    }
  end

  defp cipher(context, plaintext) do
    {:ok, sealed} = Vault.seal(key(), context, plaintext)

    %{
      "ciphertext_version" => sealed.version,
      "key_id" => sealed.key_id,
      "iv" => hex(sealed.iv),
      "tag" => hex(sealed.tag),
      "ciphertext" => hex(sealed.ciphertext)
    }
  end

  defp fixture(kind \\ :preauth) do
    c = context(kind)

    plaintext =
      if kind == :preauth,
        do: %Vault.Preauth{csrf: @csrf},
        else: %Vault.Active{csrf: @csrf, access_token: "fixture.access-token.secret"}

    browser = %{
      "id" => hex(c.browser_id),
      "cookie_digest" => hex(c.cookie_digest),
      "status" => Atom.to_string(kind),
      "epoch" => c.epoch,
      "revision" => c.revision,
      "generation" => c.generation,
      "csrf_digest" => hex(c.csrf_digest),
      "created_at" => 100,
      "last_seen_at" => 101,
      "absolute_expires_at" => 1000,
      "idle_expires_at" => 700,
      "expected_profile_id" => c.profile_id,
      "expected_profile_version" => c.profile_version,
      "initial_config_digest" => hex(c.config_digest),
      "config_digest" => hex(c.config_digest),
      "profile_id" => if(kind == :active, do: c.profile_id),
      "profile_version" => if(kind == :active, do: c.profile_version),
      "principal_id" => c.principal_id,
      "family_id" => c.family_id,
      "credential_ref" => c.credential_ref,
      "credential_revision" => c.credential_revision,
      "audit_sequence" => c.revision
    }

    vault =
      Map.merge(cipher(c, plaintext), %{
        "browser_id" => hex(c.browser_id),
        "epoch" => c.epoch,
        "session_revision" => c.revision,
        "vault_generation" => c.vault_generation,
        "envelope_kind" => Atom.to_string(kind)
      })

    attempt = %{
      "state_digest" => hex(raw(4)),
      "browser_id" => hex(c.browser_id),
      "cookie_digest" => hex(c.cookie_digest),
      "browser_epoch" => c.epoch,
      "browser_revision" => c.revision,
      "generation" => c.generation,
      "config_digest" => hex(c.config_digest),
      "profile_id" => c.profile_id,
      "profile_version" => c.profile_version,
      "issuer" => "https://identity.example.test",
      "client_id" => "console-client",
      "redirect_uri" => "https://console.example.test/auth/callback",
      "return_route" => "workspace",
      "nonce_digest" => hex(raw(5)),
      "created_at" => 110,
      "expires_at" => 400,
      "status" => "claimed",
      "claim_digest" => hex(raw(6)),
      "claimed_at" => 120,
      "claim_expires_at" => 180,
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
      "principal_id" => "incoming-principal",
      "profile_revision" => 7,
      "binding_revision" => 11,
      "principal_revision" => 13
    }
  end

  defp pending(input) do
    a = input["snapshot"]["attempt"]

    context = %{
      purpose: :attempt,
      state_digest: raw(4),
      browser_id: raw(1, 16),
      cookie_digest: raw(2),
      epoch: 2,
      revision: 2,
      generation: @generation,
      config_digest: raw(3),
      profile_id: a["profile_id"],
      profile_version: a["profile_version"],
      issuer: a["issuer"],
      client_id: a["client_id"],
      redirect_uri: a["redirect_uri"],
      expires_at: a["expires_at"]
    }

    attempt =
      Map.merge(a, cipher(context, %Vault.Verifier{verifier: @verifier}))
      |> Map.merge(%{
        "status" => "pending",
        "claim_digest" => nil,
        "claimed_at" => nil,
        "claim_expires_at" => nil
      })

    put_in(input, ["snapshot", "attempt"], attempt)
  end

  defp provider_rejected(input) do
    update_in(input, ["snapshot", "attempt"], fn attempt ->
      Map.merge(attempt, %{
        "status" => "provider_rejected",
        "claim_digest" => nil,
        "claimed_at" => nil,
        "claim_expires_at" => nil,
        "completion_reason" => "provider_rejected"
      })
    end)
  end

  defp completed do
    input = fixture(:active)

    c = %{
      context(:active)
      | epoch: 3,
        revision: 3,
        vault_generation: 3,
        cookie_digest: raw(7),
        generation: @replacement
    }

    input
    |> update_in(["snapshot", "browser"], fn browser ->
      Map.merge(browser, %{
        "epoch" => c.epoch,
        "revision" => c.revision,
        "audit_sequence" => 4,
        "cookie_digest" => hex(c.cookie_digest),
        "generation" => c.generation
      })
    end)
    |> update_in(["snapshot", "vault"], fn vault ->
      Map.merge(vault, cipher(c, %Vault.Active{csrf: @csrf, access_token: "new.access-token"}))
      |> Map.merge(%{"epoch" => 3, "session_revision" => 3, "vault_generation" => 3})
    end)
    |> put_in(["snapshot", "attempt", "status"], "completed")
    |> put_in(["snapshot", "attempt", "completion_reason"], "completed")
  end

  test "claimed preauth and active projections retain the complete decoded snapshot" do
    for kind <- [:preauth, :active] do
      input = fixture(kind)
      assert {:ok, expected} = StoredSnapshot.decode(input["snapshot"])
      assert {:ok, %ActivationPreparation{} = decoded} = ActivationPreparation.decode(input)
      assert decoded.snapshot === expected
      assert decoded.snapshot.attempt["status"] == "claimed"
      assert decoded.snapshot.attempt_envelope == nil
      assert decoded.snapshot.attempt["claim_digest"] == raw(6)
      assert decoded.snapshot.session_envelope.context == context(kind)

      assert Map.from_struct(decoded) == %{
               version: 1,
               snapshot: expected,
               principal_id: "incoming-principal",
               profile_revision: 7,
               binding_revision: 11,
               principal_revision: 13
             }

      assert {:ok, plaintext} =
               Vault.open(
                 key(),
                 expected.session_envelope.context,
                 expected.session_envelope.sealed
               )

      assert plaintext.csrf == @csrf
    end
  end

  test "non-map and structurally unrelated inputs return only the session error" do
    for input <- [nil, true, false, 1, 1.0, "secret", [], [fixture()], {:ok, fixture()}, self()] do
      assert ActivationPreparation.decode(input) === @error
    end
  end

  test "every top-level field is required" do
    input = fixture()

    for field <- Map.keys(input) do
      assert ActivationPreparation.decode(Map.delete(input, field)) === @error
    end
  end

  test "extra keys atom aliases and forged structures fail closed" do
    input = fixture()

    for field <- ["extra", :extra, :__struct__, "__struct__", :version, :snapshot] do
      assert ActivationPreparation.decode(Map.put(input, field, "secret")) === @error
    end

    for field <- Map.keys(input) do
      alias_input = input |> Map.delete(field) |> Map.put(String.to_atom(field), input[field])
      assert ActivationPreparation.decode(alias_input) === @error
    end

    assert ActivationPreparation.decode(%{
             __struct__: ActivationPreparation,
             version: 1,
             snapshot: input["snapshot"],
             principal_id: input["principal_id"],
             profile_revision: 7,
             binding_revision: 11,
             principal_revision: 13
           }) === @error
  end

  test "version admits only exact integer one" do
    input = fixture()

    for value <- [nil, 0, -1, 2, 1.0, true, "1", :v1, [], %{}] do
      assert ActivationPreparation.decode(Map.put(input, "version", value)) === @error
    end
  end

  test "principal text rejects invalid types empty excess bytes NUL and malformed UTF8" do
    input = fixture()

    for value <- [
          nil,
          true,
          1,
          :principal,
          [],
          %{},
          "",
          String.duplicate("p", 129),
          String.duplicate("é", 65),
          "principal\0secret",
          <<0>>,
          <<255>>,
          <<195>>
        ] do
      assert ActivationPreparation.decode(Map.put(input, "principal_id", value)) === @error
    end
  end

  test "principal text follows existing byte-bound UTF8 semantics without normalization" do
    input = fixture()

    for value <- ["p", String.duplicate("p", 128), String.duplicate("é", 64), " ", "a\nb"] do
      assert {:ok, decoded} = ActivationPreparation.decode(Map.put(input, "principal_id", value))
      assert decoded.principal_id === value
    end
  end

  test "every provisional revision rejects non-positive unsafe and non-integer values" do
    input = fixture()

    for field <- @revision_fields,
        value <- [
          nil,
          0,
          -1,
          1.0,
          "1",
          true,
          [],
          %{},
          @max_integer + 1,
          1_000_000_000_000_000_000
        ] do
      assert ActivationPreparation.decode(Map.put(input, field, value)) === @error
    end
  end

  test "revision bounds are independent positive safe53 integers" do
    input = fixture()

    for field <- @revision_fields, value <- [1, @max_integer] do
      assert {:ok, decoded} = ActivationPreparation.decode(Map.put(input, field, value))
      assert Map.fetch!(decoded, String.to_existing_atom(field)) === value
    end
  end

  test "all nested object boundaries delegate exact-key and type admission" do
    input = fixture()

    for path <- [
          ["snapshot"],
          ["snapshot", "browser"],
          ["snapshot", "vault"],
          ["snapshot", "attempt"]
        ] do
      row = get_in(input, path)

      for field <- Map.keys(row) do
        assert ActivationPreparation.decode(put_in(input, path, Map.delete(row, field))) ===
                 @error
      end

      for value <- [
            nil,
            [],
            "secret",
            0,
            Map.put(row, "extra", "secret"),
            Map.put(row, :__struct__, StoredSnapshot)
          ] do
        assert ActivationPreparation.decode(put_in(input, path, value)) === @error
      end
    end

    assert {:ok, decoded} = StoredSnapshot.decode(input["snapshot"])
    assert ActivationPreparation.decode(Map.put(input, "snapshot", decoded)) === @error
  end

  test "valid snapshots with absent pending rejected or completed attempts are unavailable" do
    input = fixture()

    for candidate <- [
          put_in(input, ["snapshot", "attempt"], nil),
          pending(input),
          provider_rejected(input),
          completed()
        ] do
      assert {:ok, %StoredSnapshot{}} = StoredSnapshot.decode(candidate["snapshot"])
      assert ActivationPreparation.decode(candidate) === @error
    end
  end

  test "claimed attempt ciphertext must already be erased" do
    input = fixture()

    for field <- ~w(key_id iv tag ciphertext), value <- ["retained-secret", "", false] do
      assert ActivationPreparation.decode(put_in(input, ["snapshot", "attempt", field], value)) ===
               @error
    end

    assert ActivationPreparation.decode(
             put_in(input, ["snapshot", "attempt_envelope"], "retained-secret")
           ) === @error
  end

  test "nested browser vault and attempt disagreement is rejected" do
    input = fixture()

    for {path, value} <- [
          {["snapshot", "vault", "browser_id"], hex(raw(9, 16))},
          {["snapshot", "vault", "epoch"], 3},
          {["snapshot", "vault", "session_revision"], 3},
          {["snapshot", "vault", "envelope_kind"], "active"},
          {["snapshot", "attempt", "browser_id"], hex(raw(9, 16))},
          {["snapshot", "attempt", "browser_epoch"], 3},
          {["snapshot", "attempt", "browser_revision"], 3},
          {["snapshot", "attempt", "cookie_digest"], hex(raw(9))},
          {["snapshot", "attempt", "generation"], @replacement},
          {["snapshot", "attempt", "config_digest"], hex(raw(9))},
          {["snapshot", "attempt", "profile_id"], "other-profile"},
          {["snapshot", "attempt", "profile_version"], 2},
          {["snapshot", "attempt", "profile_version"], 1.0}
        ] do
      assert ActivationPreparation.decode(put_in(input, path, value)) === @error
    end
  end

  test "claimed attempt digest times completion and version remain closed" do
    input = fixture()

    for {field, value} <- [
          {"claim_digest", nil},
          {"claim_digest", hex(raw(6, 31))},
          {"claim_digest", "\\xAB"},
          {"claimed_at", 109},
          {"claimed_at", 120.0},
          {"claim_expires_at", 120},
          {"claim_expires_at", 181},
          {"claim_expires_at", 401},
          {"completion_reason", "completed"},
          {"status", "unclaimed"},
          {"ciphertext_version", 2},
          {"ciphertext_version", 1.0}
        ] do
      assert ActivationPreparation.decode(put_in(input, ["snapshot", "attempt", field], value)) ===
               @error
    end
  end

  test "malformed session ciphertext and bytea encodings map to the same error" do
    input = fixture()

    for {field, value} <- [
          {"iv", nil},
          {"iv", hex(raw(1, 11))},
          {"tag", hex(raw(1, 17))},
          {"tag", "\\x" <> String.duplicate("AB", 16)},
          {"ciphertext", "\\x"},
          {"ciphertext", hex(raw(1, 8193))},
          {"key_id", "invalid:key"},
          {"ciphertext_version", 2}
        ] do
      assert ActivationPreparation.decode(put_in(input, ["snapshot", "vault", field], value)) ===
               @error
    end
  end

  test "redacted Inspect reveals no snapshot principal revision or ciphertext metadata" do
    input = fixture(:active)
    assert {:ok, decoded} = ActivationPreparation.decode(input)
    inspected = inspect(decoded, limit: :infinity, printable_limit: :infinity)
    assert inspected == "#MixerHosted.BrowserAuth.ActivationPreparation<...>"

    for value <- [
          input["principal_id"],
          input["snapshot"]["browser"]["principal_id"],
          input["snapshot"]["browser"]["credential_ref"],
          @generation,
          @csrf,
          "preparation-fixture-key",
          input["snapshot"]["vault"]["ciphertext"],
          "profile_revision",
          "binding_revision",
          "principal_revision"
        ] do
      refute inspected =~ value
    end
  end

  test "failures return no supplied secrets and decoding emits no log messages" do
    input = fixture()
    secret = "decoder-error-secret"

    assert capture_log(fn ->
             for candidate <- [
                   Map.put(input, "principal_id", secret <> "\0"),
                   Map.put(input, "profile_revision", secret),
                   put_in(input, ["snapshot", "attempt", "ciphertext"], secret),
                   put_in(input, ["snapshot", "vault", "key_id"], secret <> ":"),
                   Map.put(input, "unknown", secret)
                 ] do
               assert ActivationPreparation.decode(candidate) === @error
               refute inspect(ActivationPreparation.decode(candidate)) =~ secret
             end
           end) == ""
  end

  test "shape acceptance authenticates neither ciphertext nor freshness" do
    input = put_in(fixture(), ["snapshot", "vault", "tag"], hex(raw(9, 16)))
    assert {:ok, decoded} = ActivationPreparation.decode(input)
    envelope = decoded.snapshot.session_envelope
    assert Vault.open(key(), envelope.context, envelope.sealed) == {:error, :vault_unavailable}
    assert decoded.snapshot.browser["absolute_expires_at"] == 1000
    assert decoded.snapshot.attempt["claim_expires_at"] == 180
  end

  test "provisional metadata is not bound to old active identity or owner-retained evidence" do
    input = fixture(:active)
    assert {:ok, decoded} = ActivationPreparation.decode(input)
    assert decoded.snapshot.browser["principal_id"] == "old-principal"
    assert decoded.principal_id == "incoming-principal"

    changed =
      input
      |> Map.put("principal_id", "other-provisional-principal")
      |> Map.put("profile_revision", 19)
      |> Map.put("binding_revision", 23)
      |> Map.put("principal_revision", 29)

    assert {:ok, other} = ActivationPreparation.decode(changed)
    assert other.snapshot === decoded.snapshot
    assert other.principal_id == "other-provisional-principal"
    assert other.profile_revision == 19
    assert other.binding_revision == 23
    assert other.principal_revision == 29
  end
end
