defmodule MixerHosted.Repo.Migrations.AddLocalReleaseJobs do
  use Ecto.Migration

  @prefix "mixer_release_jobs"
  @processor "mixer_release_processor"
  @worker "MixerHosted.Releases.ReleaseJobs.Materialize"
  @jobs "#{@prefix}.oban_jobs"
  @peers "#{@prefix}.oban_peers"
  @offers "#{@prefix}.offer_materializations"
  @publications "public.mixer_release_publications"
  @heads "public.mixer_release_heads"
  @stamp "#{@prefix}.stamp_publication_v1"
  @sequence_parser "#{@prefix}.publication_sequence_v1"
  @writer_check "#{@prefix}.writer_can_enqueue_v1"
  @materialize "#{@prefix}.materialize_v1"
  @target ~w(organization_id project_id application_id environment_id platform runtime_sha256 channel)
  @key Enum.join(@target ++ ["sequence"], ",")
  @max_sequence "18446744073709551615"
  @queue "queue = 'releases' AND worker = '#{@worker}'"
  @live_processor "current_user = session_user AND session_user = '#{@processor}'"

  def up do
    execute("""
    DO $body$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles r
        WHERE r.rolname = current_user
          AND NOT (r.rolcanlogin OR r.rolsuper OR r.rolbypassrls)
          AND r.oid = (SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{@publications}'::regclass)
          AND r.oid = (SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{@heads}'::regclass)
      ) THEN
        RAISE EXCEPTION 'release jobs require the restricted release ledger owner';
      END IF;
    END
    $body$
    """)

    execute("CREATE SCHEMA #{@prefix}")
    Oban.Migration.up(prefix: @prefix, version: 14, create_schema: false)

    # A full transaction ID survives xid wraparound and also matches inserts
    # made inside savepoints. Existing publications keep NULL.
    execute("ALTER TABLE #{@publications} ADD COLUMN release_jobs_xact_id xid8")

    create_publication_stamp()

    execute("""
    CREATE TABLE #{@offers} (
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL, runtime_sha256 text NOT NULL, channel text NOT NULL,
      sequence numeric NOT NULL CHECK (sequence BETWEEN 1 AND #{@max_sequence} AND sequence = trunc(sequence)),
      signed_assignment_bytes bytea NOT NULL,
      artifact_sha256 text NOT NULL,
      rollout_basis_points integer NOT NULL,
      action text NOT NULL,
      PRIMARY KEY (#{@key})
    )
    """)

    for table <- [@jobs, @peers, @offers] do
      execute("ALTER TABLE #{table} ENABLE ROW LEVEL SECURITY")
      execute("ALTER TABLE #{table} FORCE ROW LEVEL SECURITY")
    end

    execute("REVOKE ALL ON SCHEMA #{@prefix} FROM PUBLIC")
    execute("REVOKE ALL ON ALL TABLES IN SCHEMA #{@prefix} FROM PUBLIC")
    execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA #{@prefix} FROM PUBLIC")

    execute("CREATE POLICY release_job_owner ON #{@jobs} TO CURRENT_USER USING (true)")
    execute("CREATE POLICY release_peer_owner ON #{@peers} TO CURRENT_USER USING (true)")

    execute(
      "CREATE POLICY release_offer_read ON #{@offers} FOR SELECT TO CURRENT_USER USING (true)"
    )

    execute(
      "CREATE POLICY release_offer_insert ON #{@offers} FOR INSERT TO CURRENT_USER WITH CHECK (true)"
    )

    # The ledger enforces one local target. The canonical sequence identifies a
    # single publication within that target and can be enqueued at most once.
    execute("""
    CREATE UNIQUE INDEX release_job_publication_sequence
    ON #{@jobs} ((args ->> 'sequence')) WHERE #{@queue}
    """)

    create_sequence_parser()
    create_writer_check()
    create_processor_policy()

    execute("""
    CREATE POLICY release_peer_processor ON #{@peers}
    USING (#{@live_processor} AND name = 'Oban')
    WITH CHECK (#{@live_processor} AND name = 'Oban')
    """)

    create_materializer()
  end

  def down do
    execute("LOCK TABLE #{@jobs}, #{@offers} IN ACCESS EXCLUSIVE MODE")

    execute("""
    DO $body$
    BEGIN
      IF EXISTS (SELECT 1 FROM #{@jobs}) OR EXISTS (SELECT 1 FROM #{@offers}) THEN
        RAISE EXCEPTION 'release jobs storage contains retained work';
      END IF;
    END
    $body$
    """)

    execute("DROP FUNCTION #{@materialize}(bigint,integer)")
    execute("DROP POLICY IF EXISTS release_job_writer_insert ON #{@jobs}")
    execute("DROP POLICY IF EXISTS release_job_writer_returning ON #{@jobs}")
    execute("DROP FUNCTION #{@writer_check}(jsonb)")
    execute("DROP FUNCTION #{@sequence_parser}(jsonb)")
    execute("DROP TRIGGER release_jobs_stamp ON #{@publications}")
    execute("DROP FUNCTION #{@stamp}()")
    execute("ALTER TABLE #{@publications} DROP COLUMN release_jobs_xact_id")
    execute("DROP TABLE #{@offers}")
    Oban.Migration.down(prefix: @prefix, version: 1)
    execute("DROP SCHEMA #{@prefix}")
  end

  defp create_publication_stamp do
    execute("""
    CREATE FUNCTION #{@stamp}() RETURNS trigger
    LANGUAGE plpgsql SET search_path = pg_catalog, pg_temp AS $body$
    BEGIN
      NEW.release_jobs_xact_id := pg_catalog.pg_current_xact_id();
      RETURN NEW;
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@stamp}() FROM PUBLIC")

    execute("""
    CREATE TRIGGER release_jobs_stamp BEFORE INSERT ON #{@publications}
    FOR EACH ROW EXECUTE FUNCTION #{@stamp}()
    """)
  end

  defp create_sequence_parser do
    execute("""
    CREATE FUNCTION #{@sequence_parser}(reference jsonb) RETURNS numeric
    LANGUAGE sql IMMUTABLE STRICT SET search_path = pg_catalog, pg_temp AS $body$
      SELECT CASE
        WHEN jsonb_typeof(reference) = 'object'
          AND (reference->'version')::text = '1'
          AND jsonb_typeof(reference->'sequence') = 'string'
          AND (reference->>'sequence') COLLATE pg_catalog."C" ~ '^[1-9][0-9]{0,19}$'
        THEN CASE WHEN (reference->>'sequence')::numeric <= #{@max_sequence}
          THEN (reference->>'sequence')::numeric END
      END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@sequence_parser}(jsonb) FROM PUBLIC")
  end

  defp create_writer_check do
    execute("""
    CREATE FUNCTION #{@writer_check}(reference jsonb) RETURNS boolean
    LANGUAGE sql STABLE SECURITY INVOKER SET search_path = pg_catalog, pg_temp AS $body$
      SELECT current_user = session_user AND EXISTS (
        SELECT 1 FROM #{@heads} h
        JOIN #{@publications} p USING (#{@key})
        WHERE h.writer_role = current_user
          AND p.release_jobs_xact_id = pg_current_xact_id_if_assigned()
          AND (reference->'version')::text = '1'
          AND #{exact_reference("reference", "p")}
      )
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@writer_check}(jsonb) FROM PUBLIC")
  end

  defp create_processor_policy do
    processor_row = "#{@live_processor} AND #{@queue}"

    execute("""
    CREATE POLICY release_job_processor_read ON #{@jobs} FOR SELECT USING (#{processor_row})
    """)

    execute("""
    CREATE POLICY release_job_processor_update ON #{@jobs} FOR UPDATE
    USING (#{processor_row}) WITH CHECK (#{processor_row})
    """)
  end

  defp create_materializer do
    execute("""
    CREATE FUNCTION #{@materialize}(job_id bigint, job_attempt integer) RETURNS text
    LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp AS $body$
    DECLARE
      reference pg_catalog.jsonb;
      publication_sequence pg_catalog.numeric;
      publication pg_catalog.record;
    BEGIN
      IF session_user <> '#{@processor}' OR job_id IS NULL OR job_id <= 0
          OR job_attempt IS NULL OR job_attempt <= 0 THEN
        RETURN 'invalid_publication_reference';
      END IF;

      -- Keep the executing attempt current through the projection write.
      SELECT args INTO reference FROM #{@jobs}
      WHERE id = job_id AND state = 'executing' AND attempt = job_attempt
        AND attempt <= max_attempts AND #{@queue}
      FOR SHARE;

      publication_sequence := #{@sequence_parser}(reference);
      IF publication_sequence IS NULL THEN
        RETURN 'invalid_publication_reference';
      END IF;

      SELECT #{qualified_target("p")}, p.sequence, p.signed_assignment_bytes,
        p.artifact_sha256, p.rollout_basis_points, p.action
      INTO publication
      FROM #{@publications} p
      WHERE (#{qualified_target("p")}) = (#{reference_target("reference")})
        AND p.sequence = publication_sequence AND p.release_jobs_xact_id IS NOT NULL
        AND #{exact_reference("reference", "p")};

      IF NOT FOUND THEN
        RETURN 'invalid_publication_reference';
      END IF;

      INSERT INTO #{@offers} (#{@key},signed_assignment_bytes,artifact_sha256,rollout_basis_points,action)
      VALUES (#{qualified_target("publication")}, publication.sequence,
        publication.signed_assignment_bytes, publication.artifact_sha256,
        publication.rollout_basis_points, publication.action)
      ON CONFLICT (#{@key}) DO NOTHING;

      IF FOUND OR EXISTS (
        SELECT 1 FROM #{@offers} o
        WHERE (#{qualified_target("o")},o.sequence) = (#{qualified_target("publication")},publication.sequence)
          AND (o.signed_assignment_bytes,o.artifact_sha256,o.rollout_basis_points,o.action)
            = (publication.signed_assignment_bytes,publication.artifact_sha256,publication.rollout_basis_points,publication.action)
      ) THEN
        RETURN 'ok';
      END IF;

      RAISE EXCEPTION 'release materialization differs from the retained publication' USING ERRCODE = '23514';
    END
    $body$
    """)

    execute("REVOKE ALL ON FUNCTION #{@materialize}(bigint,integer) FROM PUBLIC")
  end

  defp qualified_target(relation), do: Enum.map_join(@target, ",", &"#{relation}.#{&1}")
  defp reference_target(reference), do: Enum.map_join(@target, ",", &"#{reference}->>'#{&1}'")

  defp exact_reference(reference, relation) do
    fields = Enum.map_join(@target, ",", &"'#{&1}',#{relation}.#{&1}")

    "#{reference} = jsonb_build_object('version',1,#{fields},'sequence',trunc(#{relation}.sequence)::text)"
  end
end
