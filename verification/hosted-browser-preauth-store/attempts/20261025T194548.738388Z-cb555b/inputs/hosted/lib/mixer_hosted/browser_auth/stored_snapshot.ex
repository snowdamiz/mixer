defmodule MixerHosted.BrowserAuth.StoredSnapshot do
  @moduledoc """
  Decodes the closed JSONB results of the ordinary browser lifecycle helpers.

  This is data validation, never session authentication or database provenance.
  A successful decode proves neither freshness nor a current identity. The owner
  must admit the database topology, compare its request/configuration, claim
  state atomically, open the vault, and use the current identity verifier.
  """
  alias MixerHosted.BrowserAuth.Vault

  defmodule Envelope do
    @moduledoc "Exact public context and authenticated ciphertext; Inspect is redacted."
    @derive {Inspect, only: []}
    @enforce_keys [:context, :sealed]
    defstruct [:context, :sealed]
  end

  @derive {Inspect, only: []}
  @enforce_keys [:browser, :attempt, :session_envelope, :attempt_envelope]
  defstruct [:browser, :attempt, :session_envelope, :attempt_envelope]

  @max_integer 9_007_199_254_740_991
  @browser_fields ~w(id cookie_digest status epoch revision generation csrf_digest
    created_at last_seen_at absolute_expires_at idle_expires_at expected_profile_id
    expected_profile_version initial_config_digest config_digest profile_id profile_version
    principal_id family_id credential_ref credential_revision audit_sequence)
  @vault_fields ~w(browser_id epoch session_revision vault_generation ciphertext_version
    envelope_kind key_id iv tag ciphertext)
  @attempt_fields ~w(state_digest browser_id browser_epoch browser_revision cookie_digest
    generation config_digest profile_id profile_version issuer client_id redirect_uri
    return_route nonce_digest created_at expires_at status claim_digest claimed_at
    claim_expires_at completion_reason ciphertext_version key_id iv tag ciphertext)
  @link_fields ~w(profile_id profile_version principal_id family_id credential_ref credential_revision)
  @cipher_fields ~w(key_id iv tag ciphertext)
  @claim_fields ~w(claim_digest claimed_at claim_expires_at)

  @doc "Accepts only live public snapshots, with canonical PostgreSQL hex bytea strings."
  def decode(input) do
    exact!(input, ~w(browser vault attempt))
    browser = browser!(input["browser"])
    envelope = session!(input["vault"], browser)
    {attempt, attempt_envelope} = attempt!(input["attempt"], browser)

    {:ok,
     %__MODULE__{
       browser: browser,
       attempt: attempt,
       session_envelope: envelope,
       attempt_envelope: attempt_envelope
     }}
  rescue
    _ -> {:error, :snapshot_unavailable}
  catch
    _, _ -> {:error, :snapshot_unavailable}
  end

  defp browser!(raw) do
    exact!(raw, @browser_fields)

    b =
      bytes_fields!(raw, [
        {"id", 16},
        {"cookie_digest", 32},
        {"csrf_digest", 32},
        {"initial_config_digest", 32},
        {"config_digest", 32}
      ])

    require!(b["status"] in ["preauth", "active"])
    require!(Enum.all?(~w(epoch revision audit_sequence), &positive?(b[&1])))
    require!(b["audit_sequence"] >= b["revision"])
    require!(token?(b["generation"]))

    require!(
      Enum.all?(~w(created_at last_seen_at absolute_expires_at idle_expires_at), &time?(b[&1]))
    )

    require!(b["created_at"] <= b["last_seen_at"])
    require!(b["last_seen_at"] < b["idle_expires_at"])
    require!(b["idle_expires_at"] <= b["absolute_expires_at"])
    require!(text?(b["expected_profile_id"], 128) and version?(b["expected_profile_version"]))

    if b["status"] == "preauth" do
      require!(Enum.all?(@link_fields, &is_nil(b[&1])))
    else
      require!(b["profile_id"] == b["expected_profile_id"])
      require!(b["profile_version"] === b["expected_profile_version"])
      require!(text?(b["principal_id"], 128) and text?(b["family_id"], 128))
      require!(text?(b["credential_ref"], 256) and positive?(b["credential_revision"]))
    end

    b
  end

  defp session!(raw, b) do
    exact!(raw, @vault_fields)
    v = bytes_fields!(raw, [{"browser_id", 16}])
    require!(v["browser_id"] == b["id"])
    require!(v["epoch"] === b["epoch"] and v["session_revision"] === b["revision"])
    require!(positive?(v["vault_generation"]))
    require!(v["envelope_kind"] == b["status"])

    context = %{
      purpose: if(b["status"] == "preauth", do: :preauth, else: :active),
      browser_id: b["id"],
      cookie_digest: b["cookie_digest"],
      csrf_digest: b["csrf_digest"],
      epoch: b["epoch"],
      revision: b["revision"],
      generation: b["generation"],
      vault_generation: v["vault_generation"],
      config_digest: b["config_digest"],
      profile_id: b["expected_profile_id"],
      profile_version: b["expected_profile_version"],
      principal_id: b["principal_id"],
      family_id: b["family_id"],
      credential_ref: b["credential_ref"],
      credential_revision: b["credential_revision"]
    }

    envelope!(v, context)
  end

  defp attempt!(nil, _), do: {nil, nil}

  defp attempt!(raw, b) do
    exact!(raw, @attempt_fields)

    a =
      bytes_fields!(raw, [
        {"state_digest", 32},
        {"browser_id", 16},
        {"cookie_digest", 32},
        {"config_digest", 32},
        {"nonce_digest", 32}
      ])

    require!(a["status"] in ["pending", "claimed", "provider_rejected", "completed"])
    require!(a["browser_id"] == b["id"] and a["config_digest"] == b["config_digest"])
    require!(a["profile_id"] == b["expected_profile_id"])
    require!(a["profile_version"] === b["expected_profile_version"])
    require!(positive?(a["browser_epoch"]) and positive?(a["browser_revision"]))
    require!(token?(a["generation"]) and a["return_route"] == "workspace")
    require!(text?(a["issuer"], 2048) and text?(a["client_id"], 256))
    require!(text?(a["redirect_uri"], 2048) and a["ciphertext_version"] === 1)
    require!(time?(a["created_at"]) and time?(a["expires_at"]))
    require!(a["created_at"] >= b["created_at"] and a["expires_at"] > a["created_at"])
    require!(a["expires_at"] - a["created_at"] <= 300)

    if a["status"] == "completed" do
      require!(b["status"] == "active")
      require!(a["browser_epoch"] + 1 == b["epoch"])
      require!(a["browser_revision"] + 1 == b["revision"])
      require!(a["cookie_digest"] != b["cookie_digest"] and a["generation"] != b["generation"])
    else
      require!(a["browser_epoch"] == b["epoch"] and a["browser_revision"] == b["revision"])
      require!(a["cookie_digest"] == b["cookie_digest"] and a["generation"] == b["generation"])
    end

    attempt_state!(a)
  end

  defp attempt_state!(%{"status" => "pending"} = a) do
    require!(Enum.all?(@claim_fields, &is_nil(a[&1])) and is_nil(a["completion_reason"]))

    context = %{
      purpose: :attempt,
      state_digest: a["state_digest"],
      browser_id: a["browser_id"],
      cookie_digest: a["cookie_digest"],
      epoch: a["browser_epoch"],
      revision: a["browser_revision"],
      generation: a["generation"],
      config_digest: a["config_digest"],
      profile_id: a["profile_id"],
      profile_version: a["profile_version"],
      issuer: a["issuer"],
      client_id: a["client_id"],
      redirect_uri: a["redirect_uri"],
      expires_at: a["expires_at"]
    }

    {a, envelope!(a, context)}
  end

  defp attempt_state!(a) do
    require!(Enum.all?(@cipher_fields, &is_nil(a[&1])))

    if a["status"] == "provider_rejected" do
      require!(Enum.all?(@claim_fields, &is_nil(a[&1])))
      require!(a["completion_reason"] == "provider_rejected")
      {a, nil}
    else
      a = bytes_fields!(a, [{"claim_digest", 32}])
      require!(time?(a["claimed_at"]) and time?(a["claim_expires_at"]))
      require!(a["claimed_at"] >= a["created_at"])
      require!(a["claim_expires_at"] > a["claimed_at"])
      require!(a["claim_expires_at"] <= a["expires_at"])
      require!(a["claim_expires_at"] - a["claimed_at"] <= 60)
      expected = if a["status"] == "completed", do: "completed", else: nil
      require!(a["completion_reason"] == expected)
      {a, nil}
    end
  end

  defp envelope!(row, context) do
    require!(row["ciphertext_version"] === 1)
    # Vault owns the exact versioned context and key identifier contract.
    {:ok, _aad} = Vault.associated_data(row["key_id"], context)

    %Envelope{
      context: context,
      sealed: %Vault.Sealed{
        version: 1,
        key_id: row["key_id"],
        iv: bytes!(row["iv"], 12, 12),
        tag: bytes!(row["tag"], 16, 16),
        ciphertext: bytes!(row["ciphertext"], 1, 8192)
      }
    }
  end

  defp exact!(value, fields) do
    require!(is_map(value) and map_size(value) == length(fields))
    require!(Enum.all?(fields, &Map.has_key?(value, &1)))
    value
  end

  defp bytes_fields!(row, fields) do
    Enum.reduce(fields, row, fn {field, size}, result ->
      Map.update!(result, field, &bytes!(&1, size, size))
    end)
  end

  defp bytes!("\\x" <> hex, minimum, maximum)
       when byte_size(hex) >= minimum * 2 and byte_size(hex) <= maximum * 2 do
    {:ok, bytes} = Base.decode16(hex, case: :lower)
    require!(byte_size(bytes) >= minimum and byte_size(bytes) <= maximum)
    bytes
  end

  defp bytes!(_, _, _), do: raise(ArgumentError, "invalid snapshot")
  defp require!(true), do: :ok
  defp require!(_), do: raise(ArgumentError, "invalid snapshot")
  defp time?(value), do: is_integer(value) and value in 0..@max_integer
  defp positive?(value), do: is_integer(value) and value in 1..@max_integer
  defp version?(value), do: is_integer(value) and value in 1..2_147_483_647

  defp text?(value, maximum),
    do:
      is_binary(value) and byte_size(value) in 1..maximum and String.valid?(value) and
        :binary.match(value, <<0>>) == :nomatch

  defp token?(value) when is_binary(value) and byte_size(value) == 43 do
    case Base.url_decode64(value, padding: false) do
      {:ok, bytes} when byte_size(bytes) == 32 ->
        Base.url_encode64(bytes, padding: false) == value

      _ ->
        false
    end
  end

  defp token?(_), do: false
end
