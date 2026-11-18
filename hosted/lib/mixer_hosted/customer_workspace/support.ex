defmodule MixerHosted.CustomerWorkspace.Support do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.BrowserAuth.ActiveWorkspace
  alias MixerHosted.BrowserAuth.ActiveWorkspace.Binding
  alias MixerHosted.CustomerWorkspace.Input
  alias MixerHosted.Repo

  @id ~r/\A[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\z/

  def parse(%{"operation" => "list", "organization_id" => org} = body)
      when map_size(body) == 2 do
    if Scope.identifier?(org), do: {:ok, {:support, org, :list}}, else: {:error, :invalid_request}
  end

  def parse(
        %{
          "operation" => "submit",
          "organization_id" => org,
          "request_id" => id,
          "subject" => subject,
          "message" => message
        } = body
      )
      when map_size(body) == 5 and is_binary(id) and byte_size(id) == 36 do
    if Scope.identifier?(org) and Regex.match?(@id, id) and
         valid_text?(subject, 120, ~r/[\x00-\x1f\x7f-\x9f]/u) and
         valid_text?(message, 1800, ~r/[\x00-\x08\x0b-\x1f\x7f-\x9f]/u) do
      {:ok, {:support, org, {:submit, id, subject, message}}}
    else
      {:error, :invalid_request}
    end
  end

  def parse(_), do: {:error, :invalid_request}

  def execute(%Binding{} = binding, {:support, org, action}) do
    with :ok <- Input.identity(binding.identity),
         false <- Repo.in_transaction?(),
         true <- Repo.get_dynamic_repo() === Repo do
      Repo.transaction(
        fn ->
          {%{principal_id: actor}, expires} = ActiveWorkspace.prepare_identity!(Repo, binding)
          Session.context!(Repo, organization_id: org)

          case Session.query!(Repo, "SELECT public.mixer_authz_lock_organization_heads()").rows do
            [[true]] -> :ok
            _ -> Repo.rollback(:not_found)
          end

          membership_expires = membership_expiry!(org, actor, expires)
          value = perform(action, org, actor)
          :ok = ActiveWorkspace.current!(binding)
          if System.system_time(:second) >= membership_expires, do: Repo.rollback(:not_found)
          value
        end,
        timeout: max(1, binding.lease.deadline - System.monotonic_time(:millisecond)),
        queue: false
      )
    else
      {:error, reason} -> {:error, reason}
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp valid_text?(text, limit, controls) do
    is_binary(text) and byte_size(text) in 1..limit and String.valid?(text) and
      String.trim(text) != "" and not Regex.match?(controls, text)
  end

  defp membership_expiry!(org, actor, expires) do
    sql = """
    SELECT max(least(coalesce(m.expires_at, $3), $3))
    FROM public.mixer_authz_memberships m
    JOIN public.mixer_authz_organizations o ON o.id=m.organization_id AND o.active
    WHERE m.organization_id=$1 AND m.principal_id=$2 AND m.project_id IS NULL
      AND m.project_binding='all_projects' AND m.active
      AND m.not_before<=extract(epoch FROM statement_timestamp())
      AND (m.expires_at IS NULL OR m.expires_at>extract(epoch FROM statement_timestamp()))
    """

    case query!(sql, [org, actor, expires]).rows do
      [[until]] when is_integer(until) -> until
      _ -> Repo.rollback(:not_found)
    end
  end

  @fields "request_id, subject, message, floor(extract(epoch FROM submitted_at))::bigint"

  defp perform(:list, org, actor) do
    sql = """
    SELECT #{@fields}
    FROM public.mixer_support_requests
    WHERE organization_id=$1 AND principal_id=$2
    ORDER BY submitted_at DESC, request_id DESC LIMIT 20
    """

    %{organization_id: org, requests: Enum.map(query!(sql, [org, actor]).rows, &entry/1)}
  end

  defp perform({:submit, id, subject, message}, org, actor) do
    # Serialize retries and the daily limit for this actor in this organization.
    query!(
      """
      SELECT pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(
        pg_catalog.jsonb_build_array('mixer-support', $1::text, $2::text)::text, 0))
      """,
      [org, actor]
    )

    sql = """
    SELECT #{@fields} FROM public.mixer_support_requests
    WHERE organization_id=$1 AND principal_id=$2 AND request_id=$3
    """

    request =
      case query!(sql, [org, actor, id]).rows do
        [[^id, ^subject, ^message, _] = row] -> entry(row)
        [] -> insert!(org, actor, id, subject, message)
        [_] -> Repo.rollback(:conflict)
      end

    %{organization_id: org, request: request}
  end

  defp insert!(org, actor, id, subject, message) do
    sql = """
    INSERT INTO public.mixer_support_requests (organization_id, principal_id, request_id, subject, message)
    SELECT $1, $2, $3, $4, $5 WHERE (
      SELECT count(*) FROM public.mixer_support_requests
      WHERE organization_id=$1 AND principal_id=$2
        AND submitted_at >= statement_timestamp() - interval '24 hours'
    ) < 10
    RETURNING #{@fields}
    """

    case query!(sql, [org, actor, id, subject, message]).rows do
      [row] -> entry(row)
      [] -> Repo.rollback(:quota_exceeded)
    end
  end

  defp entry([id, subject, message, submitted_at]),
    do: %{id: id, subject: subject, message: message, submitted_at: submitted_at}

  defp query!(sql, params) do
    Ecto.Adapters.SQL.query!(Repo, sql, params,
      timeout: 5000,
      queue: false,
      log: false,
      telemetry_event: nil
    )
  end
end
