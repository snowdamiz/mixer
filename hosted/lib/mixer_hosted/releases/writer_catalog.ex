defmodule MixerHosted.Releases.WriterCatalog do
  @moduledoc false

  alias MixerHosted.Authorization.Postgres.Session
  alias MixerHosted.CustomerArtifacts.Topology

  @receipts "mixer_release_cli_requests"
  # Exact catalog projections of migrations 000004 and 000002 on PostgreSQL 16 and 17.
  @receipt_catalog_sha256 "ee990d52ca4de496c56e3745417faa82da0c4535fe8892221d3ebc9bffd4e2b7"
  @bound_artifact_sha256 "a176824eb681abebce1b7b21abe547c315c3efa6836271bd4655576d5f9d181a"

  def receipts_installed?(repo) do
    [[installed?]] =
      Session.query!(repo, "SELECT pg_catalog.to_regclass('public.#{@receipts}') IS NOT NULL").rows

    installed?
  end

  def check_receipts!(repo) do
    Session.query!(repo, "LOCK TABLE public.#{@receipts} IN ACCESS SHARE MODE")

    [[safe?]] =
      Session.query!(repo, """
      SELECT c.relkind='r' AND c.relpersistence='p' AND c.relrowsecurity AND c.relforcerowsecurity
        AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolbypassrls
        AND NOT pg_catalog.pg_has_role(current_user,c.relowner,'MEMBER')
        AND NOT pg_catalog.has_table_privilege(current_user,c.oid,'DELETE,TRUNCATE,REFERENCES,TRIGGER')
        AND NOT pg_catalog.has_any_column_privilege(current_user,c.oid,'UPDATE,REFERENCES')
      FROM pg_catalog.pg_class c JOIN pg_catalog.pg_roles r ON r.oid=c.relowner
      WHERE c.oid = 'public.#{@receipts}'::regclass
      """).rows

    exact? =
      with_catalog_path(repo, fn -> Topology.catalog_hash(repo, [@receipts]) end) ==
        @receipt_catalog_sha256

    unless safe? and exact?, do: repo.rollback(:authorization_unavailable)
  end

  def check_artifact!(repo) do
    unless with_catalog_path(repo, fn -> artifact_matches?(repo) end),
      do: repo.rollback(:authorization_unavailable)
  end

  defp artifact_matches?(repo) do
    [[safe?]] =
      Session.query!(
        repo,
        """
        SELECT EXISTS (
          SELECT 1 FROM pg_catalog.pg_proc p
          JOIN pg_catalog.pg_roles owner ON owner.oid=p.proowner
          JOIN pg_catalog.pg_class artifact ON artifact.oid='public.mixer_customer_artifacts'::regclass
          JOIN pg_catalog.pg_class head ON head.oid='public.mixer_release_heads'::regclass
          WHERE p.oid=pg_catalog.to_regprocedure(
            'public.mixer_release_bound_artifact(text,text,text,text,text,text,text,text)')
          AND p.prokind='f' AND p.prosupport=0 AND p.prosecdef
          AND p.proowner=artifact.relowner AND p.proowner=head.relowner
          AND NOT owner.rolcanlogin AND NOT owner.rolsuper AND NOT owner.rolbypassrls
          AND NOT pg_catalog.pg_has_role(current_user,owner.oid,'MEMBER')
          AND pg_catalog.has_function_privilege(current_user,p.oid,'EXECUTE')
          AND NOT EXISTS (
            SELECT 1 FROM pg_catalog.aclexplode(coalesce(p.proacl,pg_catalog.acldefault('f',p.proowner))) a
            WHERE a.grantee=0)
          AND pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(
            pg_catalog.pg_get_functiondef(p.oid),'UTF8')),'hex')=$1
          AND artifact.relkind='r' AND artifact.relrowsecurity AND artifact.relforcerowsecurity
          AND NOT pg_catalog.has_any_column_privilege(current_user,artifact.oid,'SELECT,INSERT,UPDATE,REFERENCES')
          AND NOT pg_catalog.has_table_privilege(current_user,artifact.oid,'DELETE,TRUNCATE,TRIGGER')
        )
        """,
        [@bound_artifact_sha256]
      ).rows

    safe? and Topology.catalog_matches?(repo) and Topology.immutable_function_matches?(repo)
  end

  # The deparser qualifies names based on search_path. Browser transactions
  # already pin a different path, which must be restored before their next check.
  defp with_catalog_path(repo, check) do
    [[previous]] = Session.query!(repo, "SHOW search_path").rows
    Session.query!(repo, "SET LOCAL search_path = pg_catalog, public")
    result = check.()
    Session.query!(repo, "SELECT pg_catalog.set_config('search_path',$1,true)", [previous])
    result
  end
end
