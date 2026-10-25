defmodule MixerStoredSnapshotIndependentReview do
  use ExUnit.Case, async: false
  alias MixerHosted.BrowserAuth.{StoredSnapshot, Vault}
  @error {:error, :snapshot_unavailable}
  @max 9_007_199_254_740_991
  @browser ~w(id cookie_digest status epoch revision generation csrf_digest created_at last_seen_at absolute_expires_at idle_expires_at expected_profile_id expected_profile_version initial_config_digest config_digest profile_id profile_version principal_id family_id credential_ref credential_revision audit_sequence)
  @vault ~w(browser_id epoch session_revision vault_generation ciphertext_version envelope_kind key_id iv tag ciphertext)
  @attempt ~w(state_digest browser_id browser_epoch browser_revision cookie_digest generation config_digest profile_id profile_version issuer client_id redirect_uri return_route nonce_digest created_at expires_at status claim_digest claimed_at claim_expires_at completion_reason ciphertext_version key_id iv tag ciphertext)
  @cipher ~w(key_id iv tag ciphertext)
  @claim ~w(claim_digest claimed_at claim_expires_at)
  @links ~w(profile_id profile_version principal_id family_id credential_ref credential_revision)

  defp bytes(value, count \\ 32), do: :binary.copy(<<value>>, count)
  defp hex(value), do: "\\x" <> Base.encode16(value, case: :lower)
  defp token(value), do: Base.url_encode64(bytes(value), padding: false)
  defp key, do: elem(Vault.key("independent.key-v1", bytes(198)), 1)

  # Independent public context assembled before and without calling the decoder.
  defp session_context(kind, completed \\ false) do
    %{
      purpose: kind, browser_id: bytes(171, 16), cookie_digest: bytes(if(completed, do: 174, else: 172)),
      csrf_digest: :crypto.hash(:sha256, token(if(completed, do: 176, else: 175))),
      epoch: if(completed, do: 5, else: 4), revision: if(completed, do: 5, else: 4),
      generation: token(if(completed, do: 178, else: 177)), vault_generation: if(completed, do: 5, else: 4),
      config_digest: bytes(179), profile_id: "human/é", profile_version: 7,
      principal_id: if(kind == :active, do: "person/42"),
      family_id: if(kind == :active, do: "browser_" <> token(180)),
      credential_ref: if(kind == :active, do: "credential/42"),
      credential_revision: if(kind == :active, do: 1)
    }
  end

  defp attempt_context do
    c = session_context(:preauth)
    %{purpose: :attempt, state_digest: bytes(181), browser_id: c.browser_id, cookie_digest: c.cookie_digest,
      epoch: c.epoch, revision: c.revision, generation: c.generation, config_digest: c.config_digest,
      profile_id: c.profile_id, profile_version: c.profile_version, issuer: "https://issuer.example.test/realm",
      client_id: "browser-client", redirect_uri: "https://console.example.test/auth/callback", expires_at: 490}
  end

  defp ciphertext(context, plain) do
    {:ok, value} = Vault.seal(key(), context, plain)
    %{"ciphertext_version" => value.version, "key_id" => value.key_id, "iv" => hex(value.iv),
      "tag" => hex(value.tag), "ciphertext" => hex(value.ciphertext)}
  end

  defp fixture(kind \\ :preauth, status \\ nil) do
    completed = status == "completed"
    c = session_context(kind, completed)
    csrf = token(if(completed, do: 176, else: 175))
    plain = if kind == :active, do: %Vault.Active{csrf: csrf, access_token: "bearer-body=="}, else: %Vault.Preauth{csrf: csrf}
    browser = %{"id" => hex(c.browser_id), "cookie_digest" => hex(c.cookie_digest), "status" => Atom.to_string(kind),
      "epoch" => c.epoch, "revision" => c.revision, "generation" => c.generation, "csrf_digest" => hex(c.csrf_digest),
      "created_at" => 200, "last_seen_at" => if(completed, do: 230, else: 220), "absolute_expires_at" => 600,
      "idle_expires_at" => 550, "expected_profile_id" => c.profile_id, "expected_profile_version" => c.profile_version,
      "initial_config_digest" => hex(c.config_digest), "config_digest" => hex(c.config_digest),
      "profile_id" => if(kind == :active, do: c.profile_id), "profile_version" => if(kind == :active, do: c.profile_version),
      "principal_id" => c.principal_id, "family_id" => c.family_id, "credential_ref" => c.credential_ref,
      "credential_revision" => c.credential_revision, "audit_sequence" => if(completed, do: 7, else: 6)}
    vault = Map.merge(ciphertext(c, plain), %{"browser_id" => hex(c.browser_id), "epoch" => c.epoch,
      "session_revision" => c.revision, "vault_generation" => c.vault_generation, "envelope_kind" => Atom.to_string(kind)})
    a = attempt_context()
    attempt = if status do
      row = Map.merge(ciphertext(a, %Vault.Verifier{verifier: token(182)}), %{
        "state_digest" => hex(a.state_digest), "browser_id" => hex(a.browser_id), "browser_epoch" => a.epoch,
        "browser_revision" => a.revision, "cookie_digest" => hex(a.cookie_digest), "generation" => a.generation,
        "config_digest" => hex(a.config_digest), "profile_id" => a.profile_id, "profile_version" => a.profile_version,
        "issuer" => a.issuer, "client_id" => a.client_id, "redirect_uri" => a.redirect_uri, "return_route" => "workspace",
        "nonce_digest" => hex(bytes(183)), "created_at" => 210, "expires_at" => a.expires_at,
        "status" => status, "claim_digest" => nil, "claimed_at" => nil, "claim_expires_at" => nil, "completion_reason" => nil})
      case status do
        "pending" -> row
        "provider_rejected" -> Enum.reduce(@cipher, row, &Map.put(&2, &1, nil)) |> Map.put("completion_reason", status)
        _ -> Enum.reduce(@cipher, row, &Map.put(&2, &1, nil)) |> Map.merge(%{
          "claim_digest" => hex(bytes(184)), "claimed_at" => 220, "claim_expires_at" => 280,
          "completion_reason" => if(completed, do: "completed")})
      end
    end
    %{"browser" => browser, "vault" => vault, "attempt" => attempt}
  end

  defp variants do
    for kind <- [:preauth, :active], status <- [nil, "pending", "claimed", "provider_rejected"] do
      {kind, status, fixture(kind, status)}
    end ++ [{:active, "completed", fixture(:active, "completed")}]
  end

  test "independently extracted SQL column names exactly equal every public row shape" do
    lines = System.fetch_env!("SNAPSHOT_REVIEW_COLUMNS") |> File.read!() |> String.split("\n", trim: true)
    actual = Map.new(lines, fn line -> [kind, names] = String.split(line, "\t"); {kind, String.split(names, ",")} end)
    assert actual == %{"browser" => @browser, "vault" => @vault, "attempt" => @attempt}
    assert Enum.sort(Map.keys(fixture()["browser"])) == Enum.sort(@browser)
    assert Enum.sort(Map.keys(fixture()["vault"])) == Enum.sort(@vault)
    assert Enum.sort(Map.keys(fixture(:preauth, "pending")["attempt"])) == Enum.sort(@attempt)
  end

  test "all9 live public result variants derive exact preexisting contexts and open real custody" do
    for {kind, status, input} <- variants() do
      assert {:ok, result} = StoredSnapshot.decode(input)
      assert result.session_envelope.context == session_context(kind, status == "completed")
      assert {:ok, plain} = Vault.open(key(), result.session_envelope.context, result.session_envelope.sealed)
      assert plain.csrf == token(if(status == "completed", do: 176, else: 175))
      assert result.browser["id"] == bytes(171, 16)
      if status == "pending" do
        assert result.attempt_envelope.context == attempt_context()
        assert {:ok, %Vault.Verifier{verifier: verifier}} = Vault.open(key(), result.attempt_envelope.context, result.attempt_envelope.sealed)
        assert verifier == token(182)
        assert result.attempt["nonce_digest"] == bytes(183)
      else
        assert result.attempt_envelope == nil
      end
      assert result.attempt == nil or result.attempt["status"] == status
    end
  end

  test "every missing field extra field wrong map-key type and null object fails closed across all states" do
    for {_kind, _status, input} <- variants(), path <- [[], ["browser"], ["vault"], ["attempt"]] do
      object = if path == [], do: input, else: get_in(input, path)
      if is_map(object) do
        replace = fn new -> if path == [], do: new, else: put_in(input, path, new) end
        for name <- Map.keys(object), do: assert(StoredSnapshot.decode(replace.(Map.delete(object, name))) == @error)
        for value <- [false, 1, 1.0, [], "private-sentinel", %{}, Map.put(object, "future", "private-sentinel"),
          Map.put(object, :unknown, true), Map.put(object, :__struct__, StoredSnapshot), Map.new(object, fn {_k, v} -> {:unknown, v} end)] do
          assert StoredSnapshot.decode(replace.(value)) == @error
        end
        if path != ["attempt"], do: assert(StoredSnapshot.decode(replace.(nil)) == @error)
      end
    end
    for input <- [nil, %{}, false, [], "private-sentinel", 0, %{"browser" => nil, "vault" => nil, "attempt" => nil}],
      do: assert(StoredSnapshot.decode(input) == @error)
    assert {:ok, empty_attempt} = StoredSnapshot.decode(put_in(fixture(:active, "pending"), ["attempt"], nil))
    assert empty_attempt.attempt == nil and empty_attempt.attempt_envelope == nil
  end

  test "canonical lowercase bytea and exact raw widths are enforced for every returned bytea" do
    for {_kind, _status, input} <- variants(), row <- ~w(browser vault attempt), is_map(input[row]),
        {field, value} <- input[row], is_binary(value) and String.starts_with?(value, "\\x") do
      raw = Base.decode16!(String.slice(value, 2..-1//1), case: :lower)
      malformed = [nil, 1, [], raw, "", "\\x", "\\X" <> String.slice(value, 2..-1//1),
        "0x" <> String.slice(value, 2..-1//1), "\\x" <> String.duplicate("A", byte_size(raw) * 2),
        value <> "0", value <> "gg", String.replace_suffix(value, String.last(value), "g")]
      for bad <- malformed, do: assert(StoredSnapshot.decode(put_in(input, [row, field], bad)) == @error, "#{row}.#{field}")
      unless field == "ciphertext" do
        assert StoredSnapshot.decode(put_in(input, [row, field], value <> "00")) == @error
        assert StoredSnapshot.decode(put_in(input, [row, field], hex(binary_part(raw, 0, byte_size(raw) - 1)))) == @error
      end
    end
    for row <- ~w(vault attempt) do
      for size <- [1, 8192] do
        assert {:ok, result} = StoredSnapshot.decode(put_in(fixture(:preauth, "pending"), [row, "ciphertext"], hex(bytes(190, size))))
        envelope = if row == "vault", do: result.session_envelope, else: result.attempt_envelope
        assert Vault.open(key(), envelope.context, envelope.sealed) == {:error, :vault_unavailable}
      end
      assert StoredSnapshot.decode(put_in(fixture(:preauth, "pending"), [row, "ciphertext"], hex(bytes(190, 8193)))) == @error
    end
  end

  test "browser and vault links never silently cross records profiles epochs revisions or envelope kinds" do
    for kind <- [:preauth, :active] do
      input = fixture(kind, "pending")
      for {path, value} <- [
        {["vault", "browser_id"], hex(bytes(191, 16))}, {["vault", "epoch"], 5}, {["vault", "session_revision"], 5},
        {["vault", "epoch"], 4.0}, {["vault", "session_revision"], 4.0}, {["vault", "vault_generation"], 0},
        {["vault", "ciphertext_version"], 2}, {["vault", "ciphertext_version"], 1.0},
        {["vault", "envelope_kind"], "erased"}, {["vault", "envelope_kind"], if(kind == :active, do: "preauth", else: "active")},
        {["vault", "key_id"], "private/sentinel"}, {["browser", "expected_profile_id"], "foreign"},
        {["browser", "expected_profile_version"], 8}, {["browser", "audit_sequence"], 3}] do
        assert StoredSnapshot.decode(put_in(input, path, value)) == @error
      end
      for status <- [nil, "expired", "revoked", "future", :active],
        do: assert(StoredSnapshot.decode(put_in(input, ["browser", "status"], status)) == @error)
      for name <- @links do
        bad = if kind == :active, do: nil, else: "retained"
        assert StoredSnapshot.decode(put_in(input, ["browser", name], bad)) == @error
      end
    end
  end

  test "attempt begin linkage and completion rotation are separately checked" do
    for status <- ~w(pending claimed provider_rejected completed) do
      kind = if status == "completed", do: :active, else: :preauth
      input = fixture(kind, status)
      for {name, bad} <- [{"browser_id", hex(bytes(191, 16))}, {"config_digest", hex(bytes(191))},
        {"profile_id", "foreign"}, {"profile_version", 8}, {"profile_version", 7.0},
        {"browser_epoch", 3}, {"browser_revision", 3}, {"browser_epoch", 4.0},
        {"return_route", "https://evil.example.test"}, {"ciphertext_version", 1.0}, {"ciphertext_version", 2}] do
        assert StoredSnapshot.decode(put_in(input, ["attempt", name], bad)) == @error
      end
      if status == "completed" do
        for name <- ~w(cookie_digest generation) do
          assert StoredSnapshot.decode(put_in(input, ["attempt", name], input["browser"][name])) == @error
        end
        assert StoredSnapshot.decode(put_in(input, ["browser", "status"], "preauth")) == @error
      else
        for {name, bad} <- [{"cookie_digest", hex(bytes(191))}, {"generation", token(191)}],
          do: assert(StoredSnapshot.decode(put_in(input, ["attempt", name], bad)) == @error)
      end
      for status <- ~w(failed superseded expired future),
        do: assert(StoredSnapshot.decode(put_in(input, ["attempt", "status"], status)) == @error)
    end
  end

  test "consumed verifier ciphertext erasure and claim fields are exact in every public state" do
    for kind <- [:preauth, :active], field <- @claim ++ ["completion_reason"] do
      assert StoredSnapshot.decode(put_in(fixture(kind, "pending"), ["attempt", field], "retained")) == @error
    end
    for status <- ~w(claimed provider_rejected completed) do
      input = fixture(if(status == "completed", do: :active, else: :preauth), status)
      for field <- @cipher do
        assert StoredSnapshot.decode(put_in(input, ["attempt", field], fixture(:preauth, "pending")["attempt"][field])) == @error
        assert StoredSnapshot.decode(update_in(input, ["attempt"], &Map.delete(&1, field))) == @error
      end
      if status == "provider_rejected" do
        for field <- @claim,
          do: assert(StoredSnapshot.decode(put_in(input, ["attempt", field], fixture(:preauth, "claimed")["attempt"][field])) == @error)
        for bad <- [nil, "completed", "future"],
          do: assert(StoredSnapshot.decode(put_in(input, ["attempt", "completion_reason"], bad)) == @error)
      else
        for field <- @claim, do: assert(StoredSnapshot.decode(put_in(input, ["attempt", field], nil)) == @error)
        for {field, bad} <- [{"claimed_at", 209}, {"claimed_at", 220.0}, {"claim_expires_at", 220},
          {"claim_expires_at", 281}, {"claim_expires_at", 491}, {"claim_expires_at", @max + 1},
          {"completion_reason", if(status == "completed", do: nil, else: "completed")}] do
          assert StoredSnapshot.decode(put_in(input, ["attempt", field], bad)) == @error
        end
      end
    end
  end

  test "bounded metadata and timestamps preserve type and required ordering" do
    for kind <- [:preauth, :active] do
      input = fixture(kind, "pending")
      for path <- [["browser", "epoch"], ["browser", "revision"], ["browser", "audit_sequence"],
        ["vault", "vault_generation"], ["attempt", "browser_epoch"], ["attempt", "browser_revision"]],
        bad <- [-1, 0, 4.0, "4", true, @max + 1] do
        assert StoredSnapshot.decode(put_in(input, path, bad)) == @error
      end
      for path <- [["browser", "expected_profile_version"], ["attempt", "profile_version"]],
        bad <- [-1, 0, 7.0, 2_147_483_648] do
        assert StoredSnapshot.decode(put_in(input, path, bad)) == @error
      end
      for {path, limit} <- [{["browser", "expected_profile_id"], 128}, {["attempt", "issuer"], 2048},
        {["attempt", "client_id"], 256}, {["attempt", "redirect_uri"], 2048}],
        bad <- ["", nil, <<255>>, "nul" <> <<0>>, String.duplicate("é", div(limit, 2) + 1)] do
        assert StoredSnapshot.decode(put_in(input, path, bad)) == @error
      end
      for {field, bad} <- [{"created_at", -1}, {"created_at", 221}, {"last_seen_at", 199},
        {"last_seen_at", 550}, {"idle_expires_at", 220}, {"idle_expires_at", 601},
        {"absolute_expires_at", 549}, {"absolute_expires_at", @max + 1}] do
        assert StoredSnapshot.decode(put_in(input, ["browser", field], bad)) == @error
      end
      for {field, bad} <- [{"created_at", 199}, {"created_at", 490}, {"created_at", 210.0},
        {"expires_at", 210}, {"expires_at", 511}, {"expires_at", @max + 1}] do
        assert StoredSnapshot.decode(put_in(input, ["attempt", field], bad)) == @error
      end
    end
    for field <- ~w(principal_id family_id credential_ref),
        bad <- [nil, "", <<255>>, "nul" <> <<0>>, String.duplicate("a", if(field == "credential_ref", do: 257, else: 129))],
      do: assert(StoredSnapshot.decode(put_in(fixture(:active), ["browser", field], bad)) == @error)
  end

  test "all64 trailing base64url choices isolate browser and saved generation canonicality" do
    for {last, index} <- Enum.with_index(~c"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_") do
      generation = String.duplicate("A", 42) <> <<last>>
      input = put_in(fixture(), ["browser", "generation"], generation)
      assert match?({:ok, _}, StoredSnapshot.decode(input)) == (rem(index, 4) == 0)
      completed = put_in(fixture(:active, "completed"), ["attempt", "generation"], generation)
      assert match?({:ok, _}, StoredSnapshot.decode(completed)) == (rem(index, 4) == 0)
    end
  end

  test "decode never supplies authentication freshness key provenance or current verifier evidence" do
    input = fixture(:active, "pending")
    for path <- [["vault", "iv"], ["vault", "tag"], ["vault", "ciphertext"],
      ["attempt", "iv"], ["attempt", "tag"], ["attempt", "ciphertext"]] do
      value = get_in(input, path)
      <<prefix::binary-size(2), first, tail::binary>> = value
      changed = prefix <> <<if(first == ?0, do: ?1, else: ?0)>> <> tail
      assert {:ok, result} = StoredSnapshot.decode(put_in(input, path, changed))
      envelope = if hd(path) == "vault", do: result.session_envelope, else: result.attempt_envelope
      assert Vault.open(key(), envelope.context, envelope.sealed) == {:error, :vault_unavailable}
    end
    assert {:ok, result} = StoredSnapshot.decode(input)
    assert result.browser["absolute_expires_at"] == 600
    assert {:ok, _} = StoredSnapshot.decode(put_in(input, ["attempt", "issuer"], "bounded-operator-text"))
    assert {:ok, _} = StoredSnapshot.decode(put_in(input, ["browser", "initial_config_digest"], hex(bytes(191))))
  end

  test "Inspect redacts result and envelope and every malformed public error is fixed" do
    assert StoredSnapshot.__info__(:functions) == [__struct__: 0, __struct__: 1, decode: 1]
    assert {:ok, result} = StoredSnapshot.decode(fixture(:active, "pending"))
    assert inspect(result) == "#MixerHosted.BrowserAuth.StoredSnapshot<...>"
    assert inspect(result.session_envelope) == "#MixerHosted.BrowserAuth.StoredSnapshot.Envelope<...>"
    assert inspect(result.attempt_envelope) == "#MixerHosted.BrowserAuth.StoredSnapshot.Envelope<...>"
    for malformed <- [nil, self(), make_ref(), fn -> raise "private-sentinel" end, <<255>>, :error, []],
      do: assert(StoredSnapshot.decode(malformed) == @error)
  end
end
