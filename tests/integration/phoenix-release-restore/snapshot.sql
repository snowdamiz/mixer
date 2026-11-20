SELECT jsonb_build_object(
  'heads', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_release_heads r),
  'publications', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_release_publications r),
  'requests', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_release_cli_requests r),
  'artifactHeads', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_customer_artifact_heads r),
  'artifacts', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_customer_artifacts r),
  'audit', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_customer_audit_events r),
  'artifactReplay', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.mixer_customer_idempotency r),
  'migrations', (SELECT jsonb_agg(to_jsonb(r) ORDER BY to_jsonb(r)) FROM public.schema_migrations r)
)::text
