defmodule MixerHosted.CustomerWorkspace.SelfService do
  @moduledoc "Bounded free workspace lifecycle; caller identity never supplies owner authority."
  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.BrowserAuth.{ActiveWorkspace, Installation, RuntimeConfig, WorkspaceCatalog}
  alias MixerHosted.BrowserAuth.ActiveWorkspace.Binding
  alias MixerHosted.CustomerBuilds.Selection
  alias MixerHosted.CustomerWorkspace.Input

  @operations ~w(create_organization create_project set_member usage export delete_project delete_organization register_application)
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

  def execute_from_browser(%Binding{} = binding, {operation, organization, target, body})
      when operation in @operations do
    execute_operation(
      binding.identity,
      operation,
      organization,
      target,
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
         true <- permitted_browser?(browser, runtime, operation) do
      deadline =
        if browser, do: browser.lease.deadline, else: System.monotonic_time(:millisecond) + 5000

      repo.transaction(
        fn ->
          expires = admission_expiry!(repo, browser, identity)

          %{connection_id: backend} =
            Session.query!(repo, "SELECT pg_catalog.set_config('search_path','pg_catalog',true)")

          {_writer, application_registration?} =
            WorkspaceCatalog.check!(repo, runtime.expected_roles, deadline, backend)

          if operation == "register_application" and not application_registration?,
            do: repo.rollback(:authorization_unavailable)

          [[value]] =
            Session.query!(
              repo,
              "SELECT public.mixer_workspace_self_service_v1($1,$2,$3,$4::jsonb,$5,$6)",
              [operation, organization, target, body, identity.issued_at, expires]
            ).rows

          value =
            case value do
              %{"plan" => "free"} = usage when operation == "usage" and not is_nil(browser) ->
                Map.put(
                  usage,
                  "can_administer",
                  browser_owner?(repo, organization, identity, expires)
                )

              value ->
                value
            end

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

  defp permitted_browser?(%Binding{lease: %{runtime: runtime}}, runtime, "register_application"),
    do: ActiveWorkspace.application_registration_enabled?(runtime)

  defp permitted_browser?(_, _, "register_application"), do: false
  defp permitted_browser?(nil, _runtime, _operation), do: true

  defp permitted_browser?(%Binding{lease: %{runtime: runtime}}, runtime, _operation),
    do: ActiveWorkspace.enabled?(runtime)

  defp permitted_browser?(_, _, _), do: false

  defp admission_expiry!(repo, nil, identity) do
    Session.prepare_identity!(repo, Policy.identity_key(identity))
    identity.expires_at
  end

  defp admission_expiry!(repo, %Binding{} = browser, _identity) do
    {_linkage, expires} = ActiveWorkspace.prepare_identity!(repo, browser)
    expires
  end

  # Usage already holds the organization head lock. Read the caller's current
  # membership under the existing directory RLS policy, with no new grant.
  defp browser_owner?(repo, organization, identity, expires) do
    Session.context!(repo,
      directory_mode: "projects",
      action: "workspace.read",
      required_scope: "mixer.workspace.read",
      phase: "directory",
      token_issued_at: Integer.to_string(identity.issued_at),
      token_expires_at: Integer.to_string(expires)
    )

    [[owner]] =
      Session.query!(
        repo,
        """
        SELECT EXISTS (
          SELECT 1 FROM public.mixer_authz_memberships
          WHERE organization_id=$1 AND project_id IS NULL
            AND project_binding='all_projects' AND role='owner'
        )
        """,
        [organization]
      ).rows

    owner
  end

  def valid_body?(op, %{"display_name" => name} = body)
      when op in ~w(create_organization create_project) do
    map_size(body) == 1 and is_binary(name) and byte_size(name) in 1..128 and
      String.valid?(name) and String.trim(name) != "" and
      Enum.all?(String.to_charlist(name), &(&1 >= 32 and &1 not in 127..159))
  end

  def valid_body?("set_member", %{"role" => role} = body),
    do: map_size(body) == 1 and role in ~w(administrator developer viewer)

  def valid_body?("register_application", %{"application_id" => app} = body),
    do: map_size(body) == 1 and Selection.id?(app)

  def valid_body?(op, body) when op in ~w(usage export delete_project delete_organization),
    do: body == %{}

  def valid_body?(_, _), do: false
end
