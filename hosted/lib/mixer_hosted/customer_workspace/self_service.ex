defmodule MixerHosted.CustomerWorkspace.SelfService do
  @moduledoc "Bounded free workspace lifecycle; caller identity never supplies owner authority."
  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.BrowserAuth.{ActiveWorkspace, Installation, RuntimeConfig, WorkspaceCatalog}
  alias MixerHosted.BrowserAuth.ActiveWorkspace.Binding
  alias MixerHosted.CustomerWorkspace.Input

  @operations ~w(create_organization create_project set_member usage export delete_project)
  @errors %{
    "unauthenticated" => :unauthenticated,
    "permission_denied" => :permission_denied,
    "not_found" => :not_found,
    "conflict" => :conflict,
    "quota_exceeded" => :quota_exceeded,
    "invalid_request" => :invalid_request
  }
  def execute(identity, operation, organization, target, body, repo \\ MixerHosted.Repo) do
    execute_operation(identity, operation, organization, target, body, repo, nil)
  end

  def create_from_browser(%Binding{} = binding, {operation, organization, body})
      when operation in ~w(create_organization create_project) do
    execute_operation(
      binding.identity,
      operation,
      organization,
      nil,
      body,
      MixerHosted.Repo,
      binding
    )
  end

  defp execute_operation(identity, operation, organization, target, body, repo, browser) do
    with :ok <- Input.identity(identity),
         true <- "mixer.workspace.manage" in identity.scopes,
         true <- operation in @operations,
         true <- is_nil(organization) or Scope.identifier?(organization),
         true <- is_nil(target) or Scope.identifier?(target),
         true <- valid_body?(operation, body),
         false <- Context.active?() or repo.in_transaction?(),
         true <- repo === MixerHosted.Repo and repo.get_dynamic_repo() === repo,
         {_, %Installation{runtime: %RuntimeConfig{workspace_catalog: :workspace_v1} = runtime}} <-
           Application.fetch_env!(:mixer_hosted, :startup),
         true <- permitted_browser?(browser, runtime) do
      deadline =
        if browser, do: browser.lease.deadline, else: System.monotonic_time(:millisecond) + 5000

      repo.transaction(
        fn ->
          linkage = Session.prepare_identity!(repo, Policy.identity_key(identity))

          %{connection_id: backend} =
            Session.query!(repo, "SELECT pg_catalog.set_config('search_path','pg_catalog',true)")

          _writer = WorkspaceCatalog.check!(repo, runtime.expected_roles, deadline, backend)
          expires = admission_expiry!(repo, browser, identity, linkage)

          [[value]] =
            Session.query!(
              repo,
              "SELECT public.mixer_workspace_self_service_v1($1,$2,$3,$4::jsonb,$5,$6)",
              [operation, organization, target, body, identity.issued_at, expires]
            ).rows

          :ok = Input.identity(identity)
          if browser, do: ActiveWorkspace.current!(browser)

          case value do
            %{"error" => reason} ->
              repo.rollback(Map.get(@errors, reason, :authorization_unavailable))

            value when is_map(value) ->
              value

            _ ->
              repo.rollback(:authorization_unavailable)
          end
        end,
        timeout: max(1, deadline - System.monotonic_time(:millisecond)),
        queue: false
      )
    else
      {:error, reason} -> {:error, reason}
      _ -> {:error, :permission_denied}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp permitted_browser?(nil, _runtime), do: true

  defp permitted_browser?(%Binding{lease: %{runtime: runtime}}, runtime),
    do: ActiveWorkspace.enabled?(runtime)

  defp permitted_browser?(_, _), do: false

  defp admission_expiry!(_repo, nil, identity, _linkage), do: identity.expires_at

  defp admission_expiry!(repo, %Binding{} = browser, _identity, linkage) do
    Session.query!(repo, "SET LOCAL bytea_output = 'hex'")
    ActiveWorkspace.check_current!(repo, browser, linkage)
  end

  def valid_body?(op, %{"display_name" => name} = body)
      when op in ~w(create_organization create_project) do
    map_size(body) == 1 and is_binary(name) and byte_size(name) in 1..128 and
      String.valid?(name) and String.trim(name) != "" and
      Enum.all?(String.to_charlist(name), &(&1 >= 32 and &1 not in 127..159))
  end

  def valid_body?("set_member", %{"role" => role} = body),
    do: map_size(body) == 1 and role in ~w(administrator developer viewer)

  def valid_body?(op, body) when op in ~w(usage export delete_project), do: body == %{}
  def valid_body?(_, _), do: false
end
