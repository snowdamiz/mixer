defmodule MixerHosted.BrowserAuth.ActiveWorkspace do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.BrowserAuth.{ActiveCatalog, Protocol, RuntimeConfig, RuntimeOwner}
  alias MixerHosted.CustomerWorkspace.{SelfService, Support}
  alias MixerHosted.Identity.KeyOwner

  defmodule Binding do
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :browser, :identity, :key_lease, :expires]
    defstruct @enforce_keys
  end

  def enabled?(%RuntimeConfig{
        workspace_catalog: :workspace_v1,
        browser_config: %{scope: scope}
      }),
      do: RuntimeConfig.workspace_manage_scope?(scope)

  def enabled?(_), do: false

  def operation({:create_organization, display_name}),
    do: operation("create_organization", nil, display_name)

  def operation({:create_project, organization, display_name}) do
    if Scope.identifier?(organization),
      do: operation("create_project", organization, display_name),
      else: {:error, :invalid_request}
  end

  def operation({:admin, operation, organization, target, body})
      when operation in ~w(usage export set_member delete_project delete_organization) do
    valid_target =
      if operation in ~w(usage export delete_organization),
        do: is_nil(target),
        else: Scope.identifier?(target)

    if Scope.identifier?(organization) and valid_target and
         SelfService.valid_body?(operation, body),
       do: {:ok, {operation, organization, target, body}},
       else: {:error, :invalid_request}
  end

  def operation({:support, body}), do: Support.parse(body)

  def operation(_), do: {:error, :invalid_request}

  defp operation(name, organization, display_name) do
    body = %{"display_name" => display_name}

    if SelfService.valid_body?(name, body),
      do: {:ok, {name, organization, nil, body}},
      else: {:error, :invalid_request}
  end

  def run(lease, source, identity, csrf, headers, operation, key_lease, expires) do
    result =
      if enabled?(lease.runtime) and "mixer.workspace.manage" in identity.scopes and
           Protocol.verify_csrf(lease.runtime.browser_config, headers, csrf) == :ok do
        binding = %Binding{
          lease: lease,
          browser: source.browser,
          identity: identity,
          key_lease: key_lease,
          expires: expires
        }

        case operation do
          {:support, _, _} -> Support.execute(binding, operation)
          _ -> SelfService.execute_from_browser(binding, operation)
        end
      else
        {:error, :permission_denied}
      end

    {:ok, result}
  end

  def check_current!(repo, %Binding{} = b, %{principal_id: actor, family_id: family}) do
    :ok = current!(b)

    :function_surface_verified =
      ActiveCatalog.check_workspace_function_surface!(
        repo,
        b.lease.runtime.expected_roles,
        b.lease.deadline,
        RuntimeConfig.function_surface_version(b.lease.runtime)
      )

    browser = b.browser
    i = b.identity

    true = browser["principal_id"] === actor and browser["family_id"] === family

    %Postgrex.Result{rows: [[expires]]} =
      Ecto.Adapters.SQL.query!(
        repo,
        """
        SELECT public.mixer_browser_workspace_admit(
          $1::bytea,$2::bytea,$3::bigint,$4::text,$5::text,$6::text,$7::text,$8::integer,
          $9::text,$10::text,$11::text,$12::text,$13::bigint,$14::bigint,$15::text[])
        """,
        [
          browser["cookie_digest"],
          browser["config_digest"],
          browser["revision"],
          browser["generation"],
          actor,
          family,
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
        timeout: remaining!(b.lease),
        queue: false,
        log: false,
        telemetry_event: nil
      )

    true = expires === b.expires
    :ok = current!(b)
    expires
  end

  def current!(%Binding{} = b) do
    _ = remaining!(b.lease)
    true = System.system_time(:second) < b.expires
    :ok = RuntimeOwner.checkpoint(b.lease)
    :ok = KeyOwner.finish(KeyOwner, b.key_lease)
  end

  defp remaining!(lease) do
    remaining = lease.deadline - System.monotonic_time(:millisecond)
    true = remaining in 1..5000
    remaining
  end
end
