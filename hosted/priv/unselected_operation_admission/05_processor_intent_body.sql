DECLARE
  build public.mixer_builds%ROWTYPE;
  reservation public.mixer_build_reservations%ROWTYPE;
  lease public.mixer_build_coordinator_leases%ROWTYPE;
  started jsonb;
  ref jsonb;
  last_event text;
  deadline_ms bigint;
  expected_id text;
BEGIN
  IF current_setting('transaction_isolation') <> 'read committed'
     OR p_action IS NULL OR p_action NOT IN ('ensure', 'stop')
     OR p_ref IS NULL OR octet_length(p_ref) NOT BETWEEN 1 AND 4096
     OR p_spec IS NULL OR octet_length(p_spec) NOT BETWEEN 1 AND 8192 THEN
    RETURN QUERY SELECT 'invalid_request', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  -- Match Admission's row lock order. The journal and guard cannot change
  -- between validation and the permanent operation write.
  SELECT * INTO build FROM public.mixer_builds WHERE id = p_record FOR UPDATE;
  SELECT * INTO reservation FROM public.mixer_build_reservations WHERE build_record_id = p_record FOR UPDATE;
  SELECT * INTO lease FROM public.mixer_build_coordinator_leases WHERE build_record_id = p_record FOR UPDATE;

  IF build.id IS NULL OR build.revision IS DISTINCT FROM p_revision
     OR reservation.held IS DISTINCT FROM true OR reservation.terminal_event_id IS NOT NULL
     OR reservation.organization_id IS DISTINCT FROM build.organization_id
     OR reservation.platform IS DISTINCT FROM build.platform
     OR lease.owner_id IS NULL OR lease.owner_id IS DISTINCT FROM p_owner
     OR lease.epoch IS DISTINCT FROM p_epoch
     OR lease.expires_at IS NULL OR lease.expires_at IS DISTINCT FROM (p_expires AT TIME ZONE 'UTC')
     OR p_expires <= clock_timestamp() THEN
    RETURN QUERY SELECT 'stale', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  last_event := build.journal->'events'->-1->'event'->>'type';
  SELECT e INTO started
    FROM jsonb_array_elements(build.journal->'events') WITH ORDINALITY AS events(e, position)
    WHERE e->'event'->>'type' = 'start'
    ORDER BY position DESC LIMIT 1;
  ref := started->'event'->'ref';
  deadline_ms := (started->>'now_ms')::bigint + (build.journal->'creation'->'policy'->>'timeout_ms')::bigint;
  IF deadline_ms IS NULL OR deadline_ms IS DISTINCT FROM p_deadline
     OR (p_action = 'ensure' AND last_event IS DISTINCT FROM 'start')
     OR (p_action = 'stop' AND (last_event IS NULL OR last_event NOT IN ('cancel', 'expire')))
     OR ref IS DISTINCT FROM jsonb_build_object(
       'organization_id', build.organization_id, 'project_id', build.project_id,
       'application_id', build.application_id, 'build_id', build.build_id, 'platform', build.platform,
       'attempt', reservation.attempt, 'fence', reservation.worker_fence)
     OR ref IS DISTINCT FROM p_ref_scope
     OR build.journal->'creation'->'spec' IS DISTINCT FROM p_spec_scope THEN
    RETURN QUERY SELECT 'stale', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  -- Dispatch hashes compact JSON. Quote each string independently so IDs with
  -- punctuation or Unicode retain their exact bytes.
  expected_id := encode(sha256(convert_to('["mixer-build-operation-v1",' ||
    to_json(build.id::text)::text || ',' || to_json(build.organization_id)::text || ',' ||
    to_json(build.project_id)::text || ',' || to_json(build.application_id)::text || ',' ||
    to_json(build.build_id)::text || ',' || to_json(build.platform)::text || ',' ||
    reservation.attempt::text || ',' || reservation.worker_fence::text || ']', 'UTF8')), 'hex');
  IF expected_id IS DISTINCT FROM p_id THEN
    RETURN QUERY SELECT 'identity_conflict', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  -- Keep legacy deterministic term bytes for storage compatibility. The
  -- projections, journal, and live lease above determine operation authority.
  -- The primitive checks time again after acquiring its operation key lock.
  RETURN QUERY SELECT * FROM public.mixer_build_operation_admit(
    p_action, expected_id, p_ref, p_spec, deadline_ms, build.id, lease.epoch,
    build.revision::bigint, lease.owner_id, p_expires);
END;
