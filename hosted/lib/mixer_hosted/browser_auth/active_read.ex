defmodule MixerHosted.BrowserAuth.ActiveRead do
  @moduledoc false
  alias MixerHosted.BrowserAuth.{
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

  def effect!({:admit, s, i}, deadline) do
    query!(
      "SELECT public.mixer_browser_current_active_load($1::bytea,$2::bytea,$3::bigint,ROW($4::text,$5::integer,$6::text,$7::text,$8::text,$9::text,$10::bigint,$11::bigint,$12::text[])::public.mixer_browser_access_evidence)",
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
      ],
      deadline
    )
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
      true = s.attempt === nil and s.attempt_envelope === nil

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
               {:ok, expires} <- Store.active_read(lease, {:admit, source, identity}),
               :ok <- RuntimeOwner.checkpoint(lease),
               :ok <- KeyOwner.finish(KeyOwner, key_lease),
               {:ok, value} <- value(operation, token, csrf, source, expires),
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

  defp value(:session, _token, csrf, s, expires),
    do: {:ok, {:authenticated, csrf, s.browser["revision"], s.browser["generation"], expires}}

  defp value({:workspace, request}, token, _csrf, _s, _expires) do
    MixerHostedWeb.BrowserWorkspaceDispatcher.dispatch(token, request, %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
    })
  end

  defp value({:build, selection}, token, _csrf, _source, _expires) do
    MixerHostedWeb.BrowserBuildDispatcher.dispatch(token, selection, %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
    })
  end

  defp value({:build_catalog, request}, token, _csrf, _source, _expires) do
    MixerHostedWeb.BrowserBuildCatalogDispatcher.dispatch(token, request, %{
      request_id: Base.encode16(:crypto.strong_rand_bytes(16), case: :lower)
    })
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
