defmodule MixerHosted.BrowserAuth.ActiveRead do
  @moduledoc false
  alias MixerHosted.Authorization.Postgres.Session

  alias MixerHosted.BrowserAuth.{
    ActiveCatalog,
    Config,
    Store,
    RuntimeOwner,
    PreauthDraft,
    StoredSnapshot,
    Vault,
    LifecycleRepo
  }

  alias MixerHosted.Identity.{
    ConfiguredVerifier,
    Admission,
    KeyOwner,
    AccessTokenVerifier,
    TrustSnapshot
  }

  defmodule Completion do
    @derive {Inspect, only: []}
    @enforce_keys [:receipt, :permit, :key_lease]
    defstruct @enforce_keys
  end

  def valid?(lease, {:discover, %PreauthDraft.Load{lease: lease, cookie_digest: digest}}),
    do: is_binary(digest) and byte_size(digest) == 32

  def valid?(lease, {:admit, source, %MixerHosted.Identity.VerifiedIdentity{} = i}) do
    source.browser["status"] === "active" and
      i.profile_id === lease.runtime.browser_config.profile_id and
      i.profile_version === lease.runtime.browser_config.profile_version and
      i.identity_class === :human
  end

  def valid?(_, _), do: false

  def effect!({:discover, input}, deadline),
    do:
      query!(
        "SELECT public.mixer_browser_load($1::bytea,$2::bytea)",
        [input.cookie_digest, input.lease.runtime.configuration_digest],
        deadline
      )

  @current_sql "SELECT public.mixer_browser_current_active_load($1::bytea,$2::bytea,$3::bigint,ROW($4::text,$5::integer,$6::text,$7::text,$8::text,$9::text,$10::bigint,$11::bigint,$12::text[])::public.mixer_browser_access_evidence)"

  def effect!({:admit, s, i}, deadline), do: query!(@current_sql, current_args(s, i), deadline)

  defp current_args(s, i) do
    [
      s.browser["cookie_digest"],
      s.browser["config_digest"],
      s.browser["revision"],
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
  end

  def decode!({:discover, _}, nil), do: nil

  def decode!({:discover, input}, raw) do
    {:ok, s} = StoredSnapshot.decode(raw)
    b = s.browser
    c = s.session_envelope.context
    config = input.lease.runtime.browser_config

    true =
      b["cookie_digest"] === input.cookie_digest and
        b["config_digest"] === input.lease.runtime.configuration_digest and
        b["initial_config_digest"] === input.lease.runtime.configuration_digest and
        b["expected_profile_id"] === config.profile_id and
        b["expected_profile_version"] === config.profile_version

    true =
      c.browser_id === b["id"] and c.cookie_digest === b["cookie_digest"] and
        c.csrf_digest === b["csrf_digest"] and
        c.config_digest === b["config_digest"] and c.epoch === b["epoch"] and
        c.revision === b["revision"] and c.generation === b["generation"]

    true = c.profile_id === config.profile_id and c.profile_version === config.profile_version
    true = Atom.to_string(c.purpose) === b["status"] and b["status"] in ["preauth", "active"]

    if c.purpose === :active do
      true =
        c.principal_id === b["principal_id"] and c.family_id === b["family_id"] and
          c.credential_ref === b["credential_ref"] and
          c.credential_revision === b["credential_revision"]
    else
      :ok = pending_source!(s, config)

      true =
        Enum.all?(
          [c.principal_id, c.family_id, c.credential_ref, c.credential_revision],
          &is_nil/1
        )
    end

    s
  end

  def decode!({:admit, source, i}, raw) do
    true = is_map(raw) and map_size(raw) == 3 and raw["version"] === 1
    {:ok, ^source} = StoredSnapshot.decode(raw["snapshot"])
    expires = raw["expires_at"]

    true =
      is_integer(expires) and expires <= i.expires_at and
        expires <= source.browser["absolute_expires_at"] and
        expires <= source.browser["idle_expires_at"] and System.system_time(:second) < expires

    expires
  end

  defp pending_source!(%StoredSnapshot{attempt: nil, attempt_envelope: nil}, _), do: :ok

  defp pending_source!(%StoredSnapshot{} = s, config) do
    a = s.attempt
    b = s.browser
    e = s.attempt_envelope

    c = %{
      purpose: :attempt,
      state_digest: a["state_digest"],
      browser_id: b["id"],
      cookie_digest: b["cookie_digest"],
      epoch: b["epoch"],
      revision: b["revision"],
      generation: b["generation"],
      config_digest: b["config_digest"],
      profile_id: config.profile_id,
      profile_version: config.profile_version,
      issuer: config.issuer,
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      expires_at: a["expires_at"]
    }

    true = e.context === c
    true = raw?(a["state_digest"], 32) and raw?(a["nonce_digest"], 32)
    true = a["created_at"] >= b["created_at"] and a["created_at"] <= System.system_time(:second)
    true = a["expires_at"] > a["created_at"] and a["expires_at"] <= a["created_at"] + 300
    true = a["expires_at"] <= min(b["absolute_expires_at"], b["idle_expires_at"])
    true = a === attempt_fields(c, e.sealed, a["nonce_digest"], a["created_at"])
    :ok
  end

  defp attempt_fields(c, sealed, nonce_digest, created_at) do
    %{
      "state_digest" => c.state_digest,
      "browser_id" => c.browser_id,
      "browser_epoch" => c.epoch,
      "browser_revision" => c.revision,
      "cookie_digest" => c.cookie_digest,
      "generation" => c.generation,
      "config_digest" => c.config_digest,
      "profile_id" => c.profile_id,
      "profile_version" => c.profile_version,
      "issuer" => c.issuer,
      "client_id" => c.client_id,
      "redirect_uri" => c.redirect_uri,
      "return_route" => "workspace",
      "nonce_digest" => nonce_digest,
      "created_at" => created_at,
      "expires_at" => c.expires_at,
      "status" => "pending",
      "claim_digest" => nil,
      "claimed_at" => nil,
      "claim_expires_at" => nil,
      "completion_reason" => nil,
      "ciphertext_version" => 1,
      "key_id" => sealed.key_id,
      "iv" => bytea_hex(sealed.iv),
      "tag" => bytea_hex(sealed.tag),
      "ciphertext" => bytea_hex(sealed.ciphertext)
    }
  end

  defp raw?(value, size), do: is_binary(value) and byte_size(value) == size
  defp bytea_hex(value), do: "\\x" <> Base.encode16(value, case: :lower)

  def run(lease, source, operation) do
    config = lease.runtime.browser_config
    e = source.session_envelope

    with :active <- e.context.purpose,
         {:ok, %Vault.Active{csrf: csrf, access_token: token}} <-
           Vault.open(lease.runtime.custody.key, e.context, e.sealed),
         true <- :crypto.hash_equals(e.context.csrf_digest, :crypto.hash(:sha256, csrf)),
         {:ok, identity} <-
           ConfiguredVerifier.authenticate(
             KeyOwner,
             config.profile_id,
             token,
             System.system_time(:second)
           ),
         true <-
           identity.profile_id === config.profile_id and
             identity.profile_version === config.profile_version and
             identity.issuer === config.issuer and identity.client_id === config.client_id and
             identity.identity_class === :human and "mixer.workspace.read" in identity.scopes,
         {:ok, permit} <- Admission.acquire(KeyOwner, config.profile_id) do
      retained =
        try do
          with {:ok, key_lease} <-
                 KeyOwner.checkout(KeyOwner, permit, System.system_time(:second)),
               p = TrustSnapshot.profile(key_lease.snapshot),
               true <-
                 p.profile_id === config.profile_id and
                   p.profile_version === config.profile_version and p.issuer === config.issuer and
                   p.client_id === config.client_id and p.audience === config.api_audience,
               {:ok, ^identity} <-
                 AccessTokenVerifier.verify(
                   token,
                   System.system_time(:second),
                   key_lease.snapshot
                 ),
               :ok <- KeyOwner.finish(KeyOwner, key_lease),
               {:ok, expires} <- Store.active_read(lease, {:admit, source, identity}, operation),
               :ok <- RuntimeOwner.checkpoint(lease),
               :ok <- KeyOwner.finish(KeyOwner, key_lease),
               {:ok, value} <-
                 value(operation, token, csrf, source, expires, lease, identity, key_lease),
               :ok <- KeyOwner.finish(KeyOwner, key_lease),
               receipt = RuntimeOwner.active_receipt(lease, expires, value),
               true <- is_struct(receipt, PreauthDraft.Publication) do
            %Completion{receipt: receipt, permit: permit, key_lease: key_lease}
          else
            {:error, %Store.Failure{}} = error -> error
            _ -> Store.failure(:commit, :committed)
          end
        rescue
          _ -> Store.failure(:commit, :unknown)
        catch
          _, _ -> Store.failure(:commit, :unknown)
        end

      case retained do
        %Completion{} ->
          retained

        error ->
          KeyOwner.release(KeyOwner, permit)
          Admission.release(permit)
          error
      end
    else
      _ -> Store.failure(:admission, :not_started)
    end
  end

  def final_check(%Completion{key_lease: l}), do: KeyOwner.finish(KeyOwner, l)

  def release(%Completion{permit: p}) do
    KeyOwner.release(KeyOwner, p)
    Admission.release(p)
  end

  defp value({:create, input, key, headers}, _token, csrf, source, expires, lease, identity, kl),
    do:
      MixerHosted.BrowserAuth.ActiveCreate.run(
        lease,
        source,
        identity,
        csrf,
        headers,
        input,
        key,
        kl,
        expires
      )

  defp value(
         {:workspace_create, operation, headers},
         _token,
         csrf,
         source,
         expires,
         lease,
         identity,
         key_lease
       ),
       do:
         MixerHosted.BrowserAuth.ActiveWorkspace.run(
           lease,
           source,
           identity,
           csrf,
           headers,
           operation,
           key_lease,
           expires
         )

  defp value({:release_head, target}, _token, _csrf, _source, _expires, _lease, identity, _kl),
    do: {:ok, MixerHosted.Releases.BrowserHead.read(identity, target)}

  defp value(
         {:release_publish, target, bytes, key, reason},
         _token,
         _csrf,
         source,
         expires,
         lease,
         identity,
         kl
       ) do
    if Config.scope_profile(lease.runtime.browser_config.scope) ==
         :release_operator and
         "mixer.release.publish" in identity.scopes do
      current! = fn repo ->
        check_release_session!(repo, lease, kl, source, identity, expires)
      end

      {:ok,
       MixerHosted.Releases.publish(identity, {:signed, target, bytes, current!}, key, reason)}
    else
      {:ok, {:error, :permission_denied}}
    end
  end

  defp value(operation, token, csrf, source, expires, _lease, _identity, _kl),
    do: value(operation, token, csrf, source, expires)

  defp value(:session, _token, csrf, s, expires),
    do: {:ok, {:authenticated, csrf, s.browser["revision"], s.browser["generation"], expires}}

  defp value({:workspace, request}, token, _csrf, _s, _expires) do
    MixerHostedWeb.BrowserWorkspaceDispatcher.dispatch(token, request, %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
    })
  end

  defp value({:build, selection, kind}, token, _csrf, _source, _expires) do
    MixerHostedWeb.BrowserBuildDispatcher.dispatch(
      token,
      selection,
      %{
        request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
      },
      kind
    )
  end

  defp value({:build_catalog, request}, token, _csrf, _source, _expires) do
    MixerHostedWeb.BrowserBuildCatalogDispatcher.dispatch(token, request, %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
    })
  end

  defp check_release_session!(repo, lease, kl, source, identity, expires) do
    :ok = RuntimeOwner.checkpoint(lease)
    :ok = KeyOwner.finish(KeyOwner, kl)

    Session.query!(repo, "SET LOCAL search_path = pg_catalog")
    Session.query!(repo, "SET LOCAL bytea_output = 'hex'")

    :function_surface_verified =
      ActiveCatalog.check_release_function_surface!(
        repo,
        lease.runtime.expected_roles,
        lease.deadline
      )

    # The same active read now takes its shared session/authority locks on the
    # writer transaction itself. Those locks live through the ledger commit.
    [[raw]] =
      Session.query!(
        repo,
        @current_sql,
        current_args(source, identity)
      ).rows

    ^expires = decode!({:admit, source, identity}, raw)
    true = System.system_time(:second) < expires
    :ok = KeyOwner.finish(KeyOwner, kl)
    RuntimeOwner.checkpoint(lease)
  end

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
end
