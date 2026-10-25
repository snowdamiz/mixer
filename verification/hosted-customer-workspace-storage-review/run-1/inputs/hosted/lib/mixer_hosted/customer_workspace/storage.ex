defmodule MixerHosted.CustomerWorkspace.Storage do
  @moduledoc false
  alias MixerHosted.Authorization.{Policy, Scope}
  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Authorization.Transaction.Context
  alias MixerHosted.CustomerWorkspace.Input

  @key {__MODULE__, :active}
  @roles ~w(owner administrator developer release_manager billing_manager viewer)
  @settings ~w(profile_id profile_version issuer subject client_id identity_class credential_ref organization_id project_id application_id environment_id principal_id family_id action transaction_marker token_issued_at token_expires_at required_scope phase directory_mode)

  def read(identity, kind, organization, page, repo) do
    if not is_nil(Process.get(@key)) or Context.active?() or repo.in_transaction?() do
      {:error, :authorization_unavailable}
    else
      owned_read(identity, kind, organization, page, repo)
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp owned_read(identity, kind, organization, page, repo) do
    state = %{
      owner: self(),
      repo: repo,
      dynamic_repo: repo.get_dynamic_repo(),
      deadline: System.monotonic_time(:millisecond) + 5_000,
      admitted_at: System.system_time(:second)
    }

    Process.put(@key, state)

    case repo.transaction(fn -> run!(identity, kind, organization, page, state) end,
           timeout: 5_000,
           queue: false
         ) do
      {:ok, result} -> {:ok, result}
      {:error, reason} when reason in [:unauthenticated, :not_found] -> {:error, reason}
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  after
    Process.delete(@key)
  end

  defp run!(identity, kind, organization, page, state) do
    repo = state.repo
    linkage = Session.prepare_identity!(repo, Policy.identity_key(identity))

    intended = [
      directory_mode: kind,
      organization_id: organization,
      project_id: nil,
      application_id: nil,
      environment_id: nil,
      action: "workspace.read",
      required_scope: "mixer.workspace.read",
      phase: "directory",
      transaction_marker: Base.encode16(:crypto.strong_rand_bytes(32), case: :lower),
      token_issued_at: Integer.to_string(identity.issued_at),
      token_expires_at: Integer.to_string(identity.expires_at)
    ]

    Session.context!(repo, intended)
    binding = connection!(repo)
    initial_identity = identity!(repo, identity, linkage, fresh_time!(state, state.admitted_at))

    organization_row = if kind == "projects", do: requested_organization!(repo, organization)
    candidates = candidates!(repo, kind, organization, page)
    selected = if organization_row, do: [organization_row | candidates], else: candidates
    ids = selected |> Enum.flat_map(& &1.witnesses) |> Enum.uniq() |> Enum.sort()
    witnesses = witnesses!(repo, ids, linkage.principal_id, fresh_time!(state, state.admitted_at))
    lock_selected!(repo, selected, witnesses, intended)
    check_binding!(state, binding)

    # All resource and witness queries below are new READ COMMITTED statements
    # after the final bounded lock wait. Freeze witnesses; never substitute an
    # unlocked newly granted membership or retry a changed selection.
    now = fresh_time!(state, state.admitted_at)
    if identity!(repo, identity, linkage, now) !== initial_identity, do: unavailable!(repo)
    current = reread!(repo, kind, organization, selected)
    fresh_witnesses = witnesses!(repo, ids, linkage.principal_id, now)
    if fresh_witnesses !== witnesses, do: unavailable!(repo)
    check_resources!(repo, current, fresh_witnesses, kind, organization)

    final_time = fresh_time!(state, now)
    if identity!(repo, identity, linkage, final_time) !== initial_identity, do: unavailable!(repo)
    final_witnesses = witnesses!(repo, ids, linkage.principal_id, final_time)
    if final_witnesses !== witnesses, do: unavailable!(repo)
    check_resources!(repo, current, final_witnesses, kind, organization)
    result = result(kind, organization, candidates, current, final_witnesses, page.limit)
    Session.finish!(repo)
    check_binding!(state, binding)
    # Re-evaluate the locked snapshots against actual time after all SQL. One
    # boundary change permits a second local check; a second change fails closed.
    final_time!(state, identity, linkage, initial_identity, final_witnesses, final_time, 2)
    result
  end

  defp requested_organization!(repo, organization) do
    case organization_candidates(repo, "o.id = $1", [organization], 1) do
      [row] -> row
      _ -> repo.rollback(:not_found)
    end
  end

  defp candidates!(repo, "organizations", _, page) do
    organization_candidates(
      repo,
      "($1::text IS NULL OR o.id COLLATE \"C\" > $1 COLLATE \"C\")",
      [page.after],
      page.limit + 1
    )
  end

  defp candidates!(repo, "projects", organization, page) do
    Session.query!(
      repo,
      """
      SELECT p.id, p.display_name, ARRAY(
        SELECT w.id FROM (
          SELECT DISTINCT ON (m.role COLLATE "C") m.id, m.role
          FROM public.mixer_authz_memberships m
          WHERE m.organization_id = p.organization_id
            AND ((m.project_binding = 'all_projects' AND m.project_id IS NULL)
              OR (m.project_binding = 'exact_project' AND m.project_id = p.id))
          ORDER BY m.role COLLATE "C", m.id COLLATE "C") w ORDER BY w.role COLLATE "C")
      FROM public.mixer_authz_projects p
      WHERE p.organization_id = $1 AND p.active
        AND ($2::text IS NULL OR p.id COLLATE "C" > $2 COLLATE "C")
      ORDER BY p.id COLLATE "C" LIMIT $3
      """,
      [organization, page.after, page.limit + 1]
    ).rows
    |> Enum.map(fn [id, name, ids] -> row(organization, id, name, ids, :project) end)
  end

  defp organization_candidates(repo, condition, params, limit) do
    Session.query!(
      repo,
      """
      SELECT o.id, o.display_name, COALESCE(NULLIF(ARRAY(
        SELECT w.id FROM (
          SELECT DISTINCT ON (m.role COLLATE "C") m.id, m.role
          FROM public.mixer_authz_memberships m
          WHERE m.organization_id = o.id AND m.project_id IS NULL
          ORDER BY m.role COLLATE "C", m.id COLLATE "C") w ORDER BY w.role COLLATE "C"), '{}'::text[]),
        ARRAY(SELECT m.id FROM public.mixer_authz_memberships m WHERE m.organization_id = o.id
          ORDER BY m.id COLLATE "C" LIMIT 1))
      FROM public.mixer_authz_organizations o WHERE o.active AND (#{condition})
      ORDER BY o.id COLLATE "C" LIMIT $#{length(params) + 1}
      """,
      params ++ [limit]
    ).rows
    |> Enum.map(fn [id, name, ids] -> row(id, id, name, ids, :organization) end)
  end

  defp row(organization, id, name, ids, kind),
    do: %{organization_id: organization, id: id, display_name: name, witnesses: ids, kind: kind}

  defp lock_selected!(repo, rows, witnesses, intended) do
    organizations = rows |> Enum.map(& &1.organization_id) |> Enum.uniq() |> Enum.sort()

    projects =
      for(row <- rows, row.kind == :project, do: {row.organization_id, row.id}) ++
        for {_id, m} <- witnesses, m.project_id, do: {m.organization_id, m.project_id}

    for org <- organizations do
      Session.context!(repo,
        directory_mode: nil,
        phase: "directory_lock",
        organization_id: org,
        project_id: nil,
        application_id: nil,
        environment_id: nil
      )

      lock!(repo, "organization_heads")
    end

    for {org, project} <- projects |> Enum.uniq() |> Enum.sort() do
      Session.context!(repo,
        directory_mode: nil,
        phase: "directory_lock",
        organization_id: org,
        project_id: project,
        application_id: nil,
        environment_id: nil
      )

      lock!(repo, "project_heads")
    end

    Session.context!(repo, intended)
  end

  defp lock!(repo, table) do
    if Session.query!(repo, "SELECT public.mixer_authz_lock_#{table}()").rows != [[true]],
      do: unavailable!(repo)
  end

  defp witnesses!(repo, [], _, _), do: %{}

  defp witnesses!(repo, ids, principal, now) do
    result =
      Session.query!(
        repo,
        """
        SELECT id, principal_id, organization_id, project_id, project_binding, role,
          active, not_before, expires_at, revision
        FROM public.mixer_authz_memberships WHERE id = ANY($1::text[]) ORDER BY id COLLATE "C"
        """,
        [ids]
      ).rows
      |> Map.new(fn [id, actor, org, project, binding, role, active, start, finish, revision] ->
        valid =
          Scope.identifier?(id) and Scope.identifier?(actor) and Scope.identifier?(org) and
            actor == principal and role in @roles and active and start <= now and
            (is_nil(finish) or finish > now) and
            ((is_nil(project) and binding in ["organization_only", "all_projects"]) or
               (Scope.identifier?(project) and binding == "exact_project"))

        if not valid, do: unavailable!(repo)

        {id,
         %{
           id: id,
           principal_id: actor,
           organization_id: org,
           project_id: project,
           project_binding: binding,
           role: role,
           active: active,
           not_before: start,
           expires_at: finish,
           revision: revision
         }}
      end)

    if Enum.sort(Map.keys(result)) != ids, do: unavailable!(repo)
    result
  end

  defp reread!(repo, kind, organization, selected) do
    orgs = selected |> Enum.filter(&(&1.kind == :organization))
    projects = selected |> Enum.filter(&(&1.kind == :project))

    org_rows =
      Session.query!(
        repo,
        "SELECT id, display_name FROM public.mixer_authz_organizations WHERE active AND id = ANY($1::text[])",
        [Enum.map(orgs, & &1.id)]
      ).rows

    project_rows =
      if kind == "projects",
        do:
          Session.query!(
            repo,
            "SELECT id, display_name FROM public.mixer_authz_projects WHERE active AND organization_id = $1 AND id = ANY($2::text[])",
            [organization, Enum.map(projects, & &1.id)]
          ).rows,
        else: []

    names =
      Map.new(
        Enum.map(org_rows, fn [id, name] -> {{:organization, id}, name} end) ++
          Enum.map(project_rows, fn [id, name] -> {{:project, id}, name} end)
      )

    if map_size(names) != length(selected), do: unavailable!(repo)
    Enum.map(selected, fn row -> %{row | display_name: Map.fetch!(names, {row.kind, row.id})} end)
  end

  defp check_resources!(repo, rows, witnesses, _kind, _organization) do
    Enum.each(rows, fn row ->
      if not Scope.identifier?(row.id) or not Scope.identifier?(row.organization_id) or
           not Input.display_name?(row.display_name) or row.witnesses == [],
         do: unavailable!(repo)

      Enum.each(row.witnesses, fn id ->
        m = Map.fetch!(witnesses, id)

        if m.organization_id != row.organization_id or
             (row.kind == :project and
                not (m.project_binding == "all_projects" or
                       (m.project_binding == "exact_project" and m.project_id == row.id))),
           do: unavailable!(repo)
      end)
    end)
  end

  defp result(kind, organization, candidates, current, witnesses, limit) do
    lookup = Map.new(current, &{{&1.kind, &1.id}, &1})

    items =
      candidates
      |> Enum.take(limit)
      |> Enum.map(fn original ->
        row = Map.fetch!(lookup, {original.kind, original.id})
        members = Enum.map(row.witnesses, &Map.fetch!(witnesses, &1))

        roles =
          members
          |> Enum.filter(&(kind == "projects" or is_nil(&1.project_id)))
          |> Enum.map(& &1.role)
          |> Enum.uniq()
          |> Enum.sort()

        if kind == "organizations",
          do: %{id: row.id, display_name: row.display_name, organization_roles: roles},
          else: %{
            organization_id: organization,
            id: row.id,
            display_name: row.display_name,
            roles: roles
          }
      end)

    cursor =
      if length(candidates) > limit,
        do: Input.cursor(kind, organization, List.last(items).id),
        else: nil

    if kind == "organizations",
      do: %{organizations: items, next_cursor: cursor},
      else: %{projects: items, next_cursor: cursor}
  end

  defp identity!(repo, i, linkage, now) do
    sql = """
    SELECT p.id, p.version, p.issuer, p.client_id, p.identity_class, p.active, p.state_revision,
      b.subject, b.principal_id, b.identity_class, b.active, b.revision,
      a.id, a.identity_class, a.active, a.not_before, a.revision,
      c.reference, c.principal_id, c.family_id, c.active, c.not_before, c.expires_at, c.revision,
      f.id, f.principal_id, f.active, f.not_before, f.expires_at, f.revision
    FROM public.mixer_authz_profiles p CROSS JOIN public.mixer_authz_bindings b
    CROSS JOIN public.mixer_authz_principals a CROSS JOIN public.mixer_authz_credentials c
    CROSS JOIN public.mixer_authz_families f
    """

    evidence = Session.one!(repo, sql, [], :unauthenticated)
    validate_identity!(repo, i, linkage, evidence, now)
  end

  defp validate_identity!(repo, i, linkage, evidence, now) do
    [
      profile,
      version,
      issuer,
      client,
      "human",
      true,
      _profile_revision,
      subject,
      principal,
      "human",
      true,
      _binding_revision,
      principal_id,
      "human",
      true,
      principal_start,
      _principal_revision,
      reference,
      credential_principal,
      family,
      true,
      credential_start,
      credential_end,
      _credential_revision,
      family_id,
      family_principal,
      true,
      family_start,
      family_end,
      _family_revision
    ] = evidence

    if profile != i.profile_id or version != i.profile_version or issuer != i.issuer or
         client != i.client_id or subject != i.subject or reference != i.credential_ref or
         Enum.any?(
           [principal, principal_id, credential_principal, family_principal],
           &(&1 != linkage.principal_id)
         ) or
         family != linkage.family_id or family_id != linkage.family_id or
         i.issued_at < max(principal_start, max(credential_start, family_start)) or
         Enum.any?([principal_start, credential_start, family_start], &(&1 > now)) or
         Enum.any?([credential_end, family_end], &(not is_nil(&1) and &1 <= now)) or
         i.expires_at <= now or i.issued_at > now + 30,
       do: repo.rollback(:unauthenticated)

    evidence
  rescue
    MatchError -> repo.rollback(:unauthenticated)
  end

  defp final_time!(state, identity, linkage, evidence, witnesses, previous, remaining) do
    now = fresh_time!(state, previous)
    validate_identity!(state.repo, identity, linkage, evidence, now)

    Enum.each(witnesses, fn {_id, m} ->
      if m.not_before > now or (not is_nil(m.expires_at) and m.expires_at <= now),
        do: unavailable!(state.repo)
    end)

    final = fresh_time!(state, now)

    cond do
      final == now ->
        :ok

      remaining > 1 ->
        final_time!(state, identity, linkage, evidence, witnesses, now, remaining - 1)

      true ->
        unavailable!(state.repo)
    end
  end

  defp fresh_time!(state, previous) do
    now = System.system_time(:second)

    if now < previous or now < state.admitted_at or
         System.monotonic_time(:millisecond) >= state.deadline,
       do: unavailable!(state.repo)

    now
  end

  defp connection!(repo) do
    fields = Enum.map_join(@settings, ",", &"current_setting('mixer.authz.#{&1}', true)")

    Session.one!(
      repo,
      "SELECT pg_backend_pid(), pg_current_xact_id()::text, current_user::text, session_user::text, " <>
        fields,
      [],
      :authorization_unavailable
    )
  end

  defp check_binding!(state, binding) do
    if Process.get(@key) !== state or self() != state.owner or Context.active?() or
         state.repo.get_dynamic_repo() != state.dynamic_repo or not state.repo.in_transaction?() or
         connection!(state.repo) !== binding,
       do: unavailable!(state.repo)
  end

  defp unavailable!(repo), do: repo.rollback(:authorization_unavailable)
end
