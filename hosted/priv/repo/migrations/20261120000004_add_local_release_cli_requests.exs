defmodule MixerHosted.Repo.Migrations.AddLocalReleaseCLIRequests do
  use Ecto.Migration

  @artifact ~w(organization_id project_id application_id environment_id platform runtime_sha256)
  @head @artifact ++ ["channel"]
  @table "public.mixer_release_cli_requests"

  def up do
    head = Enum.join(@head, ",")
    artifact = Enum.join(@artifact, ",")
    bound = Enum.map_join(@head, " AND ", &"h.#{&1} = mixer_release_cli_requests.#{&1}")

    execute("""
    CREATE TABLE #{@table} (
      organization_id text NOT NULL, project_id text NOT NULL,
      application_id text NOT NULL, environment_id text NOT NULL,
      platform text NOT NULL, runtime_sha256 text NOT NULL, channel text NOT NULL,
      idempotency_key text NOT NULL CHECK (idempotency_key ~ '^[A-Za-z0-9_.:-]{1,128}$'),
      request_sha256 text NOT NULL CHECK (request_sha256 ~ '^[0-9a-f]{64}$'),
      principal_id text NOT NULL REFERENCES public.mixer_authz_principals(id),
      artifact_sha256 text NOT NULL,
      publication_sequence numeric,
      PRIMARY KEY (#{head},idempotency_key),
      FOREIGN KEY (#{head}) REFERENCES public.mixer_release_heads(#{head}),
      FOREIGN KEY (#{artifact},artifact_sha256)
        REFERENCES public.mixer_customer_artifacts(#{artifact},manifest_sha256),
      FOREIGN KEY (#{head},publication_sequence)
        REFERENCES public.mixer_release_publications(#{head},sequence)
    )
    """)

    execute("REVOKE ALL ON #{@table} FROM PUBLIC")
    execute("ALTER TABLE #{@table} ENABLE ROW LEVEL SECURITY")
    execute("ALTER TABLE #{@table} FORCE ROW LEVEL SECURITY")

    execute("""
    CREATE INDEX mixer_release_cli_validated_artifact ON #{@table} (#{head},artifact_sha256)
    WHERE publication_sequence IS NULL
    """)

    allowed = """
    current_setting('mixer.authz.action', true) = 'release.publish'
    AND EXISTS (SELECT 1 FROM public.mixer_release_heads h WHERE #{bound})
    """

    execute("""
    CREATE POLICY release_cli_read ON #{@table} FOR SELECT USING (#{allowed})
    """)

    execute("""
    CREATE POLICY release_cli_append ON #{@table} FOR INSERT WITH CHECK (
      #{allowed} AND principal_id = current_setting('mixer.authz.principal_id', true)
    )
    """)

    execute("""
    CREATE POLICY release_cli_owner_read ON #{@table} FOR SELECT USING (
      current_user = pg_catalog.pg_get_userbyid(
        (SELECT relowner FROM pg_catalog.pg_class WHERE oid = '#{@table}'::regclass))
    )
    """)
  end

  def down do
    execute("LOCK TABLE #{@table} IN ACCESS EXCLUSIVE MODE")

    execute("""
    DO $body$ BEGIN
      IF EXISTS (SELECT 1 FROM #{@table}) THEN
        RAISE EXCEPTION 'release CLI ledger contains committed requests';
      END IF;
    END $body$
    """)

    execute("DROP TABLE #{@table}")
  end
end
