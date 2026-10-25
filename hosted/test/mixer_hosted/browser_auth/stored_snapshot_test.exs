defmodule MixerHosted.BrowserAuth.StoredSnapshotTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{StoredSnapshot, Vault}
  @error {:error, :snapshot_unavailable}
  @csrf Base.url_encode64(:binary.copy(<<11>>, 32), padding: false)
  @verifier Base.url_encode64(:binary.copy(<<12>>, 32), padding: false)
  @generation Base.url_encode64(:binary.copy(<<13>>, 32), padding: false)
  @replacement Base.url_encode64(:binary.copy(<<14>>, 32), padding: false)

  defp raw(byte, size \\ 32), do: :binary.copy(<<byte>>, size)
  defp hex(bytes), do: "\\x" <> Base.encode16(bytes, case: :lower)

  defp key do
    {:ok, value} = Vault.key("key-v1", raw(42))
    value
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
      principal_id: if(kind == :active, do: "person-1"),
      family_id: if(kind == :active, do: "browser_" <> @generation),
      credential_ref: if(kind == :active, do: "jti-1"),
      credential_revision: if(kind == :active, do: 1)
    }
  end

  defp cipher(context, plaintext) do
    {:ok, value} = Vault.seal(key(), context, plaintext)

    %{
      "ciphertext_version" => value.version,
      "key_id" => value.key_id,
      "iv" => hex(value.iv),
      "tag" => hex(value.tag),
      "ciphertext" => hex(value.ciphertext)
    }
  end

  defp fixture(kind \\ :preauth) do
    c = context(kind)

    plaintext =
      if kind == :preauth,
        do: %Vault.Preauth{csrf: @csrf},
        else: %Vault.Active{csrf: @csrf, access_token: "header.payload.signature"}

    browser = %{
      "id" => hex(c.browser_id),
      "cookie_digest" => hex(c.cookie_digest),
      "status" => Atom.to_string(kind),
      "epoch" => 2,
      "revision" => 2,
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
      "audit_sequence" => 2
    }

    vault =
      Map.merge(cipher(c, plaintext), %{
        "browser_id" => hex(c.browser_id),
        "epoch" => 2,
        "session_revision" => 2,
        "vault_generation" => 2,
        "envelope_kind" => Atom.to_string(kind)
      })

    %{"browser" => browser, "vault" => vault, "attempt" => nil}
  end

  defp pending(kind \\ :preauth) do
    c = context(kind)

    a = %{
      purpose: :attempt,
      state_digest: raw(4),
      browser_id: c.browser_id,
      cookie_digest: c.cookie_digest,
      epoch: 2,
      revision: 2,
      generation: c.generation,
      config_digest: c.config_digest,
      profile_id: c.profile_id,
      profile_version: c.profile_version,
      issuer: "https://id.example.test",
      client_id: "console-client",
      redirect_uri: "https://console.example.test/auth/callback",
      expires_at: 400
    }

    row = %{
      "state_digest" => hex(a.state_digest),
      "browser_id" => hex(a.browser_id),
      "cookie_digest" => hex(a.cookie_digest),
      "browser_epoch" => 2,
      "browser_revision" => 2,
      "generation" => a.generation,
      "config_digest" => hex(a.config_digest),
      "profile_id" => a.profile_id,
      "profile_version" => a.profile_version,
      "issuer" => a.issuer,
      "client_id" => a.client_id,
      "redirect_uri" => a.redirect_uri,
      "expires_at" => 400,
      "created_at" => 110,
      "return_route" => "workspace",
      "nonce_digest" => hex(raw(5)),
      "status" => "pending",
      "claim_digest" => nil,
      "claimed_at" => nil,
      "claim_expires_at" => nil,
      "completion_reason" => nil
    }

    Map.put(
      fixture(kind),
      "attempt",
      Map.merge(row, cipher(a, %Vault.Verifier{verifier: @verifier}))
    )
  end

  defp consumed(status, kind \\ :preauth) do
    input = pending(kind)
    row = Enum.reduce(~w(key_id iv tag ciphertext), input["attempt"], &Map.put(&2, &1, nil))
    row = Map.put(row, "status", status)

    row =
      if status == "provider_rejected" do
        Map.put(row, "completion_reason", "provider_rejected")
      else
        Map.merge(row, %{
          "claim_digest" => hex(raw(6)),
          "claimed_at" => 120,
          "claim_expires_at" => 180,
          "completion_reason" => if(status == "completed", do: "completed")
        })
      end

    Map.put(input, "attempt", row)
  end

  defp completed do
    input = consumed("completed", :active)
    # Activation rotates the browser and vault; attempt metadata retains begin values.
    c = %{
      context(:active)
      | epoch: 3,
        revision: 3,
        vault_generation: 3,
        cookie_digest: raw(7),
        generation: @replacement
    }

    browser =
      Map.merge(input["browser"], %{
        "epoch" => 3,
        "revision" => 3,
        "audit_sequence" => 4,
        "cookie_digest" => hex(c.cookie_digest),
        "generation" => c.generation
      })

    vault =
      Map.merge(
        input["vault"],
        cipher(c, %Vault.Active{csrf: @csrf, access_token: "header.payload.signature"})
      )
      |> Map.merge(%{"epoch" => 3, "session_revision" => 3, "vault_generation" => 3})

    %{input | "browser" => browser, "vault" => vault}
  end

  test "preauth and active PostgreSQL JSON decode to exact authenticated Vault contexts" do
    for kind <- [:preauth, :active] do
      assert {:ok, snapshot} = StoredSnapshot.decode(fixture(kind))
      assert snapshot.session_envelope.context == context(kind)

      assert {:ok, plaintext} =
               Vault.open(
                 key(),
                 snapshot.session_envelope.context,
                 snapshot.session_envelope.sealed
               )

      assert plaintext.csrf == @csrf
      assert snapshot.attempt == nil
      assert snapshot.attempt_envelope == nil
      assert snapshot.browser["id"] == raw(1, 16)
      refute inspect(snapshot) =~ @generation
      refute inspect(snapshot.session_envelope) =~ "key-v1"
    end
  end

  test "pending attempt uses saved begin values and authenticates a real verifier" do
    for kind <- [:preauth, :active] do
      assert {:ok, snapshot} = StoredSnapshot.decode(pending(kind))
      assert snapshot.attempt_envelope.context.revision == 2

      assert {:ok, %Vault.Verifier{verifier: @verifier}} =
               Vault.open(
                 key(),
                 snapshot.attempt_envelope.context,
                 snapshot.attempt_envelope.sealed
               )

      assert snapshot.attempt["nonce_digest"] == raw(5)
    end
  end

  test "claim and provider rejection retain only closed consumed metadata" do
    for kind <- [:preauth, :active], status <- ["claimed", "provider_rejected"] do
      assert {:ok, snapshot} = StoredSnapshot.decode(consumed(status, kind))
      assert snapshot.attempt["status"] == status
      assert snapshot.attempt_envelope == nil
      assert snapshot.session_envelope.context.revision == 2

      assert {:ok, _} =
               Vault.open(
                 key(),
                 snapshot.session_envelope.context,
                 snapshot.session_envelope.sealed
               )
    end
  end

  test "completed metadata binds old begin context to a newly rotated active browser" do
    assert {:ok, snapshot} = StoredSnapshot.decode(completed())
    assert snapshot.attempt["browser_revision"] == 2
    assert snapshot.session_envelope.context.revision == 3
    assert snapshot.attempt_envelope == nil

    assert {:ok, %Vault.Active{}} =
             Vault.open(
               key(),
               snapshot.session_envelope.context,
               snapshot.session_envelope.sealed
             )

    for {field, value} <- [
          {"browser_epoch", 3},
          {"browser_revision", 1},
          {"cookie_digest", hex(raw(7))},
          {"generation", @replacement}
        ] do
      assert StoredSnapshot.decode(put_in(completed(), ["attempt", field], value)) == @error
    end
  end

  test "all object boundaries reject missing unknown atom and structural fields" do
    input = pending()

    for path <- [[], ["browser"], ["vault"], ["attempt"]] do
      row = if path == [], do: input, else: get_in(input, path)
      replace = fn value -> if path == [], do: value, else: put_in(input, path, value) end

      for field <- Map.keys(row) do
        assert StoredSnapshot.decode(replace.(Map.delete(row, field))) == @error
      end

      for value <- [
            nil,
            [],
            "row",
            0,
            Map.put(row, "extra", true),
            Map.put(row, :status, "active"),
            Map.put(row, :__struct__, StoredSnapshot)
          ] do
        if path == ["attempt"] and value == nil do
          assert {:ok, _} = StoredSnapshot.decode(replace.(value))
        else
          assert StoredSnapshot.decode(replace.(value)) == @error
        end
      end
    end
  end

  test "canonical bytea excludes aliases wrong widths odd hex and unbounded ciphertext" do
    input = pending()

    for path <- [
          ["browser", "id"],
          ["browser", "cookie_digest"],
          ["browser", "csrf_digest"],
          ["browser", "initial_config_digest"],
          ["browser", "config_digest"],
          ["vault", "browser_id"],
          ["vault", "iv"],
          ["vault", "tag"],
          ["attempt", "state_digest"],
          ["attempt", "nonce_digest"]
        ] do
      for value <- [
            nil,
            1,
            "",
            "\\x0",
            "\\xGG",
            "\\xAB",
            "AB",
            raw(1),
            get_in(input, path) <> "00"
          ] do
        assert StoredSnapshot.decode(put_in(input, path, value)) == @error
      end
    end

    for value <- ["\\x", hex(raw(1, 8193)), "\\xabc", nil] do
      assert StoredSnapshot.decode(put_in(input, ["vault", "ciphertext"], value)) == @error
    end
  end

  test "browser state linkage counters profiles and times fail closed" do
    for {field, values} <- [
          {"status", ["revoked", "expired", "authenticated", nil]},
          {"epoch", [0, -1, 1.0, 9_007_199_254_740_992]},
          {"revision", [0, "2", 1.0]},
          {"audit_sequence", [1, -1, 2.0]},
          {"generation", ["", @generation <> "=", String.duplicate("A", 42) <> "B"]},
          {"expected_profile_id", [nil, "", "a\0b", <<255>>, String.duplicate("a", 129)]},
          {"expected_profile_version", [0, 1.0, 2_147_483_648]},
          {"created_at", [-1, 102]},
          {"last_seen_at", [99, 700]},
          {"idle_expires_at", [101, 1001]},
          {"absolute_expires_at", [699, 9_007_199_254_740_992]},
          {"principal_id", ["person-1"]},
          {"profile_version", [1]}
        ] do
      for value <- values,
          do:
            assert(StoredSnapshot.decode(put_in(fixture(), ["browser", field], value)) == @error)
    end

    for field <-
          ~w(profile_id profile_version principal_id family_id credential_ref credential_revision) do
      assert StoredSnapshot.decode(put_in(fixture(:active), ["browser", field], nil)) == @error
    end

    for {field, value} <- [
          {"profile_id", "other"},
          {"profile_version", 2},
          {"profile_version", 1.0},
          {"credential_ref", String.duplicate("x", 257)},
          {"credential_revision", 0}
        ] do
      assert StoredSnapshot.decode(put_in(fixture(:active), ["browser", field], value)) == @error
    end
  end

  test "vault metadata cannot be swapped or silently upgraded" do
    for {field, value} <- [
          {"browser_id", hex(raw(9, 16))},
          {"epoch", 3},
          {"session_revision", 3},
          {"epoch", 2.0},
          {"session_revision", 2.0},
          {"vault_generation", 0},
          {"ciphertext_version", 2},
          {"ciphertext_version", 1.0},
          {"envelope_kind", "active"},
          {"envelope_kind", "erased"},
          {"key_id", "a:b"}
        ] do
      assert StoredSnapshot.decode(put_in(fixture(), ["vault", field], value)) == @error
    end
  end

  test "attempt context cannot cross browser config identity or revision" do
    for {field, value} <- [
          {"browser_id", hex(raw(9, 16))},
          {"cookie_digest", hex(raw(9))},
          {"browser_epoch", 1},
          {"browser_revision", 3},
          {"config_digest", hex(raw(9))},
          {"profile_id", "other"},
          {"profile_version", 2},
          {"profile_version", 1.0},
          {"ciphertext_version", 1.0},
          {"generation", @replacement},
          {"return_route", "https://evil.test"},
          {"created_at", 99},
          {"expires_at", 411},
          {"expires_at", 110},
          {"issuer", "bad\0value"},
          {"client_id", String.duplicate("x", 257)},
          {"redirect_uri", <<255>>},
          {"status", "failed"},
          {"status", "superseded"}
        ] do
      assert StoredSnapshot.decode(put_in(pending(), ["attempt", field], value)) == @error
    end
  end

  test "claim metadata and ciphertext erasure are enforced for every returned state" do
    for field <- ~w(claim_digest claimed_at claim_expires_at completion_reason) do
      assert StoredSnapshot.decode(put_in(pending(), ["attempt", field], "unexpected")) == @error
    end

    for input <- [consumed("claimed"), consumed("provider_rejected"), completed()],
        field <- ~w(key_id iv tag ciphertext) do
      assert StoredSnapshot.decode(put_in(input, ["attempt", field], "retained")) == @error
    end

    for {field, value} <- [
          {"claim_digest", nil},
          {"claimed_at", 109},
          {"claim_expires_at", 120},
          {"claim_expires_at", 181},
          {"claim_expires_at", 401},
          {"completion_reason", "completed"}
        ] do
      assert StoredSnapshot.decode(put_in(consumed("claimed"), ["attempt", field], value)) ==
               @error
    end

    assert StoredSnapshot.decode(
             put_in(consumed("provider_rejected"), ["attempt", "claim_digest"], hex(raw(6)))
           ) == @error

    assert StoredSnapshot.decode(put_in(completed(), ["attempt", "completion_reason"], nil)) ==
             @error
  end

  test "decoding is not authentication: changed ciphertext requires cryptographic rejection" do
    input = put_in(fixture(), ["vault", "tag"], hex(raw(9, 16)))
    assert {:ok, snapshot} = StoredSnapshot.decode(input)

    assert Vault.open(key(), snapshot.session_envelope.context, snapshot.session_envelope.sealed) ==
             {:error, :vault_unavailable}

    # Timestamps deliberately remain historical. Fresh-time admission belongs to the owner/SQL.
    assert snapshot.browser["absolute_expires_at"] == 1000
  end
end
