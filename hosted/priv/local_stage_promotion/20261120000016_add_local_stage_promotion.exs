defmodule MixerHosted.Repo.Migrations.AddLocalStagePromotion do
  use Ecto.Migration

  @directions "public.mixer_stage_promotion_directions"
  @bindings "public.mixer_stage_promotion_bindings"
  @publications "public.mixer_release_publications"
  @environments "public.mixer_authz_environments"
  @enrollments "public.mixer_release_delivery_enrollments"
  @admit "public.mixer_stage_promotion_admit"
  @source "public.mixer_stage_promotion_source"
  @scope ~w(organization_id project_id application_id)
  @targets for side <- ~w(source destination), platform <- ~w(ios android), do: {side, platform}
  @coordinates ~w(environment_id platform runtime_sha256 channel)
  @publication_key @scope ++ @coordinates ++ ~w(sequence artifact_sha256)
  @route_key ~w(direction_id writer_role) ++
               @scope ++
               ~w(source_environment_id destination_environment_id) ++
               Enum.flat_map(@targets, fn {side, platform} ->
                 ["#{side}_#{platform}_runtime_sha256", "#{side}_#{platform}_channel"]
               end)

  def up do
    execute("""
    DO $body$
    BEGIN
      IF (SELECT count(*) FROM pg_catalog.pg_class c
          JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
          WHERE c.oid IN ('#{@publications}'::regclass, '#{@environments}'::regclass,
              '#{@enrollments}'::regclass, 'public.mixer_release_heads'::regclass,
              'public.mixer_customer_artifacts'::regclass)
            AND c.relrowsecurity AND c.relforcerowsecurity AND r.rolname=current_user
            AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls) <> 5 THEN
        RAISE EXCEPTION 'stage promotion requires the restricted ledger and authorization owner';
      END IF;
    END
    $body$
    """)

    route_types =
      Enum.map_join(@route_key, ",\n", fn
        "direction_id" ->
          "direction_id text NOT NULL CHECK (direction_id ~ '^[A-Za-z0-9_.-]{1,128}$')"

        "writer_role" ->
          "writer_role name NOT NULL"

        field ->
          "#{field} text NOT NULL"
      end)

    execute("""
    CREATE TABLE #{@directions} (
      #{route_types},
      active boolean NOT NULL DEFAULT true,
      PRIMARY KEY (direction_id),
      UNIQUE (#{csv(@route_key)}),
      CHECK (source_environment_id <> destination_environment_id)
    )
    """)

    protect(@directions)

    execute("""
    CREATE POLICY stage_direction_owner ON #{@directions} TO CURRENT_USER USING (true)
    """)

    execute("""
    CREATE UNIQUE INDEX mixer_stage_promotion_publication_key
      ON #{@publications} (#{csv(@publication_key)})
    """)

    references =
      Enum.map_join(@targets, ",\n", fn {side, platform} ->
        key =
          coordinates(side, platform) ++ attributes(side, platform, ~w(sequence artifact_sha256))

        prefix = "#{side}_#{platform}"

        """
        #{prefix}_platform text GENERATED ALWAYS AS ('#{platform}') STORED,
        #{prefix}_sequence numeric NOT NULL,
        #{prefix}_artifact_sha256 text NOT NULL,
        FOREIGN KEY (#{csv(key)}) REFERENCES #{@publications} (#{csv(@publication_key)})
        """
      end)

    execute("""
    CREATE TABLE #{@bindings} (
      #{route_types},
      idempotency_key text NOT NULL CHECK (idempotency_key ~ '^[A-Za-z0-9_.:-]{1,128}$'),
      request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
      principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
      reason text NOT NULL CHECK (octet_length(reason) BETWEEN 1 AND 512),
      recorded_at timestamp(6) with time zone NOT NULL DEFAULT statement_timestamp(),
      PRIMARY KEY (direction_id, idempotency_key),
      FOREIGN KEY (#{csv(@route_key)}) REFERENCES #{@directions} (#{csv(@route_key)}),
      #{references},
      #{destination_unique("ios")},
      #{destination_unique("android")}
    )
    """)

    protect(@bindings)
    create_admission()
    create_source_reader()
    create_binding_policies()
    require_binding()
  end

  def down, do: raise("stage promotion requires a forward migration preserving its bindings")

  defp create_admission do
    # Add owner-only visibility for the other end of a provisioned direction.
    # The normal release and authorization policies keep the destination scope.
    source_environment = """
    current_user <> session_user
      AND current_setting('mixer.authz.action',true) = 'release.publish'
      AND current_setting('mixer.authz.phase',true) = 'effect'
      AND EXISTS (
        SELECT 1 FROM #{@directions} d
        WHERE d.active AND d.writer_role=session_user
          AND (d.organization_id,d.project_id,d.application_id,d.source_environment_id)
            = (mixer_authz_environments.organization_id,mixer_authz_environments.project_id,
               mixer_authz_environments.application_id,mixer_authz_environments.id)
          AND (d.organization_id,d.project_id,d.application_id,d.destination_environment_id)
            = (current_setting('mixer.authz.organization_id',true),
               current_setting('mixer.authz.project_id',true),
               current_setting('mixer.authz.application_id',true),
               current_setting('mixer.authz.environment_id',true))
      )
    """

    execute("""
    CREATE POLICY stage_source_environment ON #{@environments}
      FOR SELECT TO CURRENT_USER USING (#{source_environment})
    """)

    execute("""
    CREATE POLICY stage_source_environment_lock ON #{@environments}
      FOR UPDATE TO CURRENT_USER USING (#{source_environment}) WITH CHECK (false)
    """)

    enrolled_targets =
      Enum.map_join(@targets, ",\n", fn {side, platform} ->
        "(d.#{side}_environment_id,'#{platform}',d.#{side}_#{platform}_runtime_sha256,d.#{side}_#{platform}_channel)"
      end)

    execute("""
    CREATE FUNCTION #{@admit}(route text) RETURNS SETOF #{@directions}
    LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $body$
    DECLARE
      d #{@directions}%ROWTYPE;
    BEGIN
      SELECT * INTO d FROM #{@directions}
        WHERE direction_id=route AND active AND writer_role=session_user
          AND current_user<>session_user
        FOR SHARE;
      IF NOT FOUND OR NOT public.mixer_release_publish_allowed(
        d.organization_id,d.project_id,d.application_id,d.destination_environment_id
      ) THEN
        RETURN;
      END IF;

      IF (SELECT count(*) FROM (
        SELECT e.id FROM #{@environments} e
        WHERE (e.organization_id,e.project_id,e.application_id)
            = (d.organization_id,d.project_id,d.application_id)
          AND e.id IN (d.source_environment_id,d.destination_environment_id) AND e.active
        ORDER BY e.id COLLATE "C" FOR SHARE OF e
      ) AS locked_environments) <> 2 THEN
        RETURN;
      END IF;

      IF (SELECT count(*) FROM (
        SELECT e.platform FROM #{@enrollments} e
        WHERE (e.organization_id,e.project_id,e.application_id)
            = (d.organization_id,d.project_id,d.application_id)
          AND e.reader_role='mixer_release_delivery'
          AND (e.environment_id,e.platform,e.runtime_sha256,e.channel) IN (#{enrolled_targets})
        ORDER BY e.environment_id COLLATE "C",e.platform COLLATE "C" FOR SHARE OF e
      ) AS locked_enrollments) <> 4 THEN
        RETURN;
      END IF;

      RETURN NEXT d;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@admit}(text) FROM PUBLIC")
  end

  defp create_source_reader do
    execute("""
    CREATE FUNCTION #{@source}(route text, ios_sequence numeric, android_sequence numeric)
    RETURNS TABLE(platform text, sequence numeric, artifact_sha256 text,
                  signed_assignment_bytes bytea, signed_manifest_bytes bytea, payload bytea,
                  payload_sha256 text)
    LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = pg_catalog AS $body$
      SELECT p.platform,p.sequence,p.artifact_sha256,p.signed_assignment_bytes,
             a.signed_manifest_bytes,a.payload,a.payload_sha256
      FROM #{@admit}(route) d
      JOIN #{@publications} p
        ON (p.organization_id,p.project_id,p.application_id,p.environment_id)
           = (d.organization_id,d.project_id,d.application_id,d.source_environment_id)
        AND (p.platform,p.runtime_sha256,p.channel,p.sequence) IN (
          ('ios',d.source_ios_runtime_sha256,d.source_ios_channel,ios_sequence),
          ('android',d.source_android_runtime_sha256,d.source_android_channel,android_sequence))
      JOIN public.mixer_customer_artifacts a
        ON (a.organization_id,a.project_id,a.application_id,a.environment_id,a.platform,
            a.runtime_sha256,a.manifest_sha256)
         = (p.organization_id,p.project_id,p.application_id,p.environment_id,p.platform,
            p.runtime_sha256,p.artifact_sha256)
      WHERE p.action IN ('publish','stage_promote')
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@source}(text,numeric,numeric) FROM PUBLIC")
  end

  defp create_binding_policies do
    visible = """
    current_user=session_user AND writer_role=session_user
      AND public.mixer_release_publish_allowed(
        organization_id,project_id,application_id,destination_environment_id)
    """

    execute("CREATE POLICY stage_binding_read ON #{@bindings} FOR SELECT USING (#{visible})")

    publications =
      Enum.map_join(~w(ios android), " AND ", fn platform ->
        """
        EXISTS (
          SELECT 1 FROM #{@publications} p
          WHERE #{bound_publication(platform)}
            AND p.action='stage_promote'
            AND (p.principal_id,p.idempotency_key,p.reason)
              = (mixer_stage_promotion_bindings.principal_id,
                 mixer_stage_promotion_bindings.idempotency_key,mixer_stage_promotion_bindings.reason)
        )
        """
      end)

    execute("""
    CREATE POLICY stage_binding_append ON #{@bindings} FOR INSERT WITH CHECK (
      #{visible} AND principal_id=current_setting('mixer.authz.principal_id',true)
      AND EXISTS (SELECT 1 FROM #{@admit}(direction_id)) AND #{publications}
    )
    """)

    execute("""
    CREATE FUNCTION public.mixer_stage_promotion_immutable() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      RAISE EXCEPTION 'stage bindings are immutable' USING ERRCODE = '23514';
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION public.mixer_stage_promotion_immutable() FROM PUBLIC")

    execute("""
    CREATE TRIGGER stage_binding_immutable BEFORE UPDATE OR DELETE ON #{@bindings}
    FOR EACH ROW EXECUTE FUNCTION public.mixer_stage_promotion_immutable()
    """)
  end

  defp require_binding do
    # Retain the ordinary action checks and allow the first stage promotion
    # to create a destination publication with no predecessor.
    execute("""
    ALTER TABLE #{@publications} DROP CONSTRAINT mixer_release_publication_action,
      ADD CONSTRAINT mixer_release_publication_action CHECK (
        (action IN ('publish','stage_promote')
          OR (action IN ('promote','rollback') AND previous_sequence IS NOT NULL))
          AND health_activated IS NULL AND health_pending IS NULL AND health_adverse_signals IS NULL
        OR (action = 'halt' AND previous_sequence IS NOT NULL AND rollout_basis_points = 0
          AND health_activated IS NOT NULL AND health_pending IS NOT NULL
          AND health_adverse_signals IS NOT NULL)
      )
    """)

    binding_match =
      Enum.map_join(~w(ios android), " OR ", fn platform ->
        bound_publication(platform)
        |> String.replace("p.", "NEW.")
      end)

    execute("""
    CREATE FUNCTION public.mixer_stage_promotion_require_binding() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog AS $body$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM #{@bindings} AS mixer_stage_promotion_bindings
                     WHERE #{binding_match}) THEN
        RAISE EXCEPTION 'stage publication requires a dual-platform binding' USING ERRCODE = '23514';
      END IF;
      RETURN NULL;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION public.mixer_stage_promotion_require_binding() FROM PUBLIC")

    execute("""
    CREATE CONSTRAINT TRIGGER stage_publication_requires_binding AFTER INSERT ON #{@publications}
    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.action='stage_promote')
    EXECUTE FUNCTION public.mixer_stage_promotion_require_binding()
    """)
  end

  defp protect(table) do
    execute("REVOKE ALL ON #{table} FROM PUBLIC")
    execute("ALTER TABLE #{table} ENABLE ROW LEVEL SECURITY")
    execute("ALTER TABLE #{table} FORCE ROW LEVEL SECURITY")
  end

  defp attributes(side, platform, fields), do: Enum.map(fields, &"#{side}_#{platform}_#{&1}")

  defp coordinates(side, platform) do
    @scope ++ ["#{side}_environment_id"] ++ attributes(side, platform, tl(@coordinates))
  end

  defp destination_unique(platform) do
    fields = coordinates("destination", platform) ++ ["destination_#{platform}_sequence"]
    "UNIQUE (#{csv(fields)})"
  end

  defp bound_publication(platform) do
    fields =
      coordinates("destination", platform) ++
        attributes("destination", platform, ~w(sequence artifact_sha256))

    "(#{csv(@publication_key, "p.")}) = (#{csv(fields, "mixer_stage_promotion_bindings.")})"
  end

  defp csv(fields, prefix \\ ""), do: Enum.map_join(fields, ",", &(prefix <> &1))
end
