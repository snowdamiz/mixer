defmodule MixerHosted.BrowserAuth.CallbackStore do
  @moduledoc false
  alias MixerHosted.BrowserAuth.{
    CallbackLifecycle,
    ActivationPreparation,
    LifecycleRepo,
    StoredSnapshot,
    Vault,
    Protocol,
    RuntimeOwner
  }

  alias CallbackLifecycle.{Claim, Activate, Result}

  def valid?(lease, {:claim, %Claim{lease: lease} = c}), do: claim?(c)
  def valid?(lease, {:fail, %Claim{lease: lease} = c}), do: claim?(c)

  def valid?(lease, {:activate, %Activate{claim: %Claim{lease: lease} = c} = d}) do
    claim?(c) and Enum.all?([d.cookie, d.csrf, d.generation], &Protocol.token?/1) and
      is_binary(d.family) and String.starts_with?(d.family, "browser_") and
      Protocol.token?(String.replace_prefix(d.family, "browser_", "")) and
      d.identity.__struct__ === MixerHosted.Identity.VerifiedIdentity and
      d.identity.profile_id === lease.runtime.browser_config.profile_id and
      d.identity.profile_version === lease.runtime.browser_config.profile_version
  end

  def valid?(_, _), do: false

  defp claim?(c) do
    s = c.source
    a = s.attempt
    b = s.browser
    l = c.lease
    config = l.runtime.browser_config

    is_binary(c.digest) and byte_size(c.digest) === 32 and is_integer(c.expires_at) and
      c.expires_at <= a["expires_at"] and System.system_time(:second) < c.expires_at and
      b["status"] === "preauth" and a["status"] === "pending" and
      b["config_digest"] === l.runtime.configuration_digest and
      b["initial_config_digest"] === l.runtime.configuration_digest and
      a["profile_id"] === config.profile_id and a["profile_version"] === config.profile_version and
      a["issuer"] === config.issuer and a["client_id"] === config.client_id and
      a["redirect_uri"] === config.redirect_uri and
      s.session_envelope.context.purpose === :preauth and
      match?(
        {:ok, %Vault.Preauth{}},
        Vault.open(l.runtime.custody.key, s.session_envelope.context, s.session_envelope.sealed)
      )
  end

  def effect!({:claim, c}, deadline) do
    query!(
      "SELECT public.mixer_browser_claim($1::bytea,$2::bytea,$3::bytea,$4::bigint,$5::bytea,$6::bigint,$7::text)",
      prefix(c) ++ [c.source.browser["revision"], c.digest, c.expires_at, request()],
      deadline
    )
  end

  def effect!({:fail, c}, deadline) do
    query!(
      "SELECT public.mixer_browser_fail_claim($1::bytea,$2::bytea,$3::bytea,$4::bytea,$5::text,$6::text)",
      prefix(c) ++ [c.digest, "session_failed", request()],
      deadline
    )
  end

  def effect!({:activate, d}, deadline) do
    c = d.claim
    i = d.identity
    lease = c.lease
    args = prefix(c) ++ [c.digest, c.source.browser["revision"]] ++ evidence(i)

    raw =
      query!(
        "SELECT public.mixer_browser_prepare_activation($1::bytea,$2::bytea,$3::bytea,$4::bytea,$5::bigint,ROW($6::text,$7::integer,$8::text,$9::text,$10::text,$11::text,$12::bigint,$13::bigint,$14::text[])::public.mixer_browser_access_evidence)",
        args,
        deadline
      )

    {:ok, prep} = ActivationPreparation.decode(raw)
    claimed!(c, prep.snapshot)
    expires = min(min(i.expires_at, d.id_expires_at), System.system_time(:second) + 900)
    old = prep.snapshot.session_envelope.context

    context = %{
      old
      | purpose: :active,
        cookie_digest: hash(d.cookie),
        csrf_digest: hash(d.csrf),
        epoch: old.epoch + 1,
        revision: old.revision + 1,
        generation: d.generation,
        vault_generation: old.vault_generation + 1,
        principal_id: prep.principal_id,
        family_id: d.family,
        credential_ref: i.credential_ref,
        credential_revision: 1
    }

    {:ok, sealed} =
      Vault.seal(lease.runtime.custody.key, context, %Vault.Active{
        csrf: d.csrf,
        access_token: d.access_token
      })

    :ok = RuntimeOwner.checkpoint(lease)

    raw =
      query!(
        "SELECT public.mixer_browser_activate($1::bytea,$2::bytea,$3::bytea,$4::bytea,$5::bigint,ROW($6::text,$7::integer,$8::text,$9::text,$10::text,$11::text,$12::bigint,$13::bigint,$14::text[],$15::bigint,$16::bigint,$17::bigint)::public.mixer_browser_verified,$18::bytea,$19::bytea,$20::text,$21::text,$22::bigint,ROW($23::text,$24::bytea,$25::bytea,$26::bytea)::public.mixer_browser_cipher,$27::text)",
        args ++
          [
            prep.profile_revision,
            prep.binding_revision,
            prep.principal_revision,
            context.cookie_digest,
            context.csrf_digest,
            d.generation,
            d.family,
            expires,
            sealed.key_id,
            sealed.iv,
            sealed.tag,
            sealed.ciphertext,
            request()
          ],
        deadline
      )

    {raw, context, sealed, expires}
  end

  def decode!({:claim, c}, raw) do
    {:ok, s} = StoredSnapshot.decode(raw)
    claimed!(c, s)
    s
  end

  def decode!({:fail, _}, true), do: true

  def decode!({:activate, d}, {raw, context, sealed, expires}) do
    {:ok, s} = StoredSnapshot.decode(raw)
    true = s.session_envelope.context === context and s.session_envelope.sealed === sealed
    true = s.browser["status"] === "active" and s.attempt["status"] === "completed"

    true =
      s.browser["absolute_expires_at"] === expires and s.browser["idle_expires_at"] === expires

    true = s.attempt["claim_digest"] === d.claim.digest
    true = System.system_time(:second) < expires

    {:ok, %Vault.Active{csrf: csrf, access_token: access}} =
      Vault.open(d.claim.lease.runtime.custody.key, context, sealed)

    true = csrf === d.csrf and access === d.access_token
    %Result{cookie: d.cookie, csrf: d.csrf, generation: d.generation, expires_at: expires}
  end

  defp claimed!(c, s) do
    source = c.source

    true =
      s.browser === %{source.browser | "audit_sequence" => source.browser["audit_sequence"] + 1}

    true = s.session_envelope === source.session_envelope and s.attempt_envelope === nil
    a = s.attempt

    true =
      a === %{
        source.attempt
        | "status" => "claimed",
          "claim_digest" => c.digest,
          "claimed_at" => a["claimed_at"],
          "claim_expires_at" => c.expires_at,
          "key_id" => nil,
          "iv" => nil,
          "tag" => nil,
          "ciphertext" => nil
      }

    true =
      a["claimed_at"] >= c.lease.started_at and a["claimed_at"] <= System.system_time(:second)

    true = System.system_time(:second) < c.expires_at
    :ok
  end

  defp evidence(i),
    do: [
      i.profile_id,
      i.profile_version,
      i.issuer,
      i.subject,
      i.client_id,
      i.credential_ref,
      i.issued_at,
      i.expires_at,
      i.scopes
    ]

  defp prefix(c),
    do: [
      c.source.browser["cookie_digest"],
      c.source.attempt["state_digest"],
      c.lease.runtime.configuration_digest
    ]

  defp query!(sql, params, deadline) do
    true = System.monotonic_time(:millisecond) < deadline

    %{command: :select, rows: [[raw]], num_rows: 1, messages: []} =
      Ecto.Adapters.SQL.query!(LifecycleRepo, sql, params,
        timeout: max(1, deadline - System.monotonic_time(:millisecond)),
        deadline: deadline,
        queue: false,
        log: false,
        telemetry_event: nil
      )

    true = System.monotonic_time(:millisecond) < deadline
    raw
  end

  defp hash(v), do: :crypto.hash(:sha256, v)
  defp request, do: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
end
