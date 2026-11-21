defmodule MixerHosted.Releases.EnvironmentPromotion.Storage do
  @moduledoc false

  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.Releases.EnvironmentPromotion.Command.{Evidence, SourcePublication}
  alias MixerHosted.Releases.EnvironmentPromotion.Direction
  alias MixerHosted.Releases.Publication

  @bindings "public.mixer_stage_promotion_bindings"
  @scope_fields ~w(organization_id project_id application_id)
  @targets for side <- [:source, :destination], platform <- [:ios, :android], do: {side, platform}
  @route_fields ~w(direction_id writer_role) ++
                  @scope_fields ++
                  ~w(source_environment_id destination_environment_id) ++
                  Enum.flat_map(@targets, fn {side, platform} ->
                    ["#{side}_#{platform}_runtime_sha256", "#{side}_#{platform}_channel"]
                  end)
  @binding_fields @route_fields ++
                    ~w(idempotency_key request_sha256 principal_id reason) ++
                    Enum.flat_map(@targets, fn {side, platform} ->
                      ["#{side}_#{platform}_sequence", "#{side}_#{platform}_artifact_sha256"]
                    end)

  def check!(repo) do
    Session.query!(repo, "LOCK TABLE #{@bindings} IN ACCESS SHARE MODE")

    [[safe?]] =
      Session.query!(repo, """
      SELECT c.relkind='r' AND c.relpersistence='p' AND c.relrowsecurity AND c.relforcerowsecurity
        AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
        AND NOT pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER')
        AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'DELETE,TRUNCATE,REFERENCES,TRIGGER')
        AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'UPDATE,REFERENCES')
        AND NOT pg_catalog.has_column_privilege(current_user,c.oid,'recorded_at','INSERT')
        AND (SELECT count(*) FROM pg_catalog.pg_proc p
             WHERE p.oid IN (
               'public.mixer_stage_promotion_admit(text)'::regprocedure,
               'public.mixer_stage_promotion_source(text,numeric,numeric)'::regprocedure)
               AND p.proowner=c.relowner AND p.prosecdef
               AND p.proconfig=ARRAY['search_path=pg_catalog']::text[]
               AND NOT EXISTS (SELECT 1 FROM pg_catalog.aclexplode(
                 COALESCE(p.proacl,pg_catalog.acldefault('f',p.proowner))) a WHERE a.grantee=0)) = 2
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
      WHERE c.oid='#{@bindings}'::regclass
      """).rows

    unless safe?, do: repo.rollback(:authorization_unavailable)
  end

  def admit(repo, id, %Direction{} = direction) do
    coordinates = coordinates(direction)
    fields = Enum.join(@route_fields, ",")

    case Session.query!(repo, "SELECT #{fields} FROM public.mixer_stage_promotion_admit($1)", [id]).rows do
      [[^id, writer | ^coordinates]] -> {:ok, [id, writer | coordinates]}
      _ -> {:error, :invalid_promotion}
    end
  end

  def source(repo, id, %{ios: ios, android: android}) do
    case Session.query!(
           repo,
           """
           SELECT platform, sequence, artifact_sha256, signed_assignment_bytes,
                  signed_manifest_bytes, payload, payload_sha256
           FROM public.mixer_stage_promotion_source($1,$2,$3)
           ORDER BY platform COLLATE "C"
           """,
           [id, Decimal.new(ios), Decimal.new(android)]
         ).rows do
      [["android" | android_row], ["ios" | ios_row]] ->
        with {:ok, ios} <- source_publication(ios_row),
             {:ok, android} <- source_publication(android_row) do
          {:ok, %{ios: ios, android: android}}
        end

      _ ->
        {:error, :release_not_found}
    end
  end

  def binding(repo, id, key) do
    case Session.query!(
           repo,
           """
           SELECT request_sha256, principal_id, destination_ios_sequence, destination_android_sequence
           FROM #{@bindings} WHERE direction_id=$1 AND idempotency_key=$2
           """,
           [id, key]
         ).rows do
      [[fingerprint, principal, ios, android]] ->
        %{
          fingerprint: fingerprint,
          principal: principal,
          sequences: %{ios: ios, android: android}
        }

      [] ->
        nil
    end
  end

  def insert!(repo, route, verified, %{
        key: key,
        reason: reason,
        principal: principal,
        fingerprint: fingerprint
      }) do
    publication_keys =
      Enum.flat_map(@targets, fn {side, platform} ->
        assignment = verified[platform][side].assignment.assignment
        [Decimal.new(assignment["sequence"]), assignment["artifact_sha256"]]
      end)

    fields = Enum.join(@binding_fields, ",")
    slots = 1..length(@binding_fields) |> Enum.map_join(",", &"$#{&1}")

    %{num_rows: 1} =
      Session.query!(
        repo,
        "INSERT INTO #{@bindings} (#{fields}) VALUES (#{slots})",
        route ++ [key, fingerprint, principal, reason] ++ publication_keys
      )

    :ok
  end

  def publication(repo, target_filter, sequence),
    do: repo.get_by!(Publication, [{:sequence, sequence} | target_filter])

  defp source_publication([sequence, digest, assignment, manifest, payload, payload_digest]) do
    if sha256(payload) == payload_digest do
      {:ok,
       %SourcePublication{
         sequence: Decimal.to_integer(sequence),
         artifact_sha256: digest,
         evidence: %Evidence{
           signed_manifest_bytes: manifest,
           signed_assignment_bytes: assignment,
           payload: payload
         }
       }}
    else
      {:error, :storage_unavailable}
    end
  end

  defp coordinates(%Direction{source: source, destination: destination} = direction) do
    scope = destination.ios.target.scope

    [
      scope.organization_id,
      scope.project_id,
      scope.application_id,
      source.ios.target.scope.environment_id,
      scope.environment_id
    ] ++
      Enum.flat_map(@targets, fn {side, platform} ->
        target = Map.fetch!(direction, side)[platform].target
        [target.runtime_sha256, target.channel]
      end)
  end

  def sha256(bytes), do: Base.encode16(:crypto.hash(:sha256, bytes), case: :lower)
end
