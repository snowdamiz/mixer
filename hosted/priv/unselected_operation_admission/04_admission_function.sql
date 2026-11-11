CREATE FUNCTION mixer_build_operation_admit(
  p_action text, p_id text, p_ref bytea, p_spec bytea, p_deadline bigint,
  p_record uuid, p_epoch bigint, p_revision bigint, p_owner text, p_expires timestamptz
) RETURNS TABLE(outcome text, admission_state text, lease_epoch bigint, journal_revision bigint)
LANGUAGE plpgsql AS $$
DECLARE
  saved mixer_build_operation_admissions%ROWTYPE;
  at_time timestamptz;
  inserted boolean := false;
  next_state text;
BEGIN
  -- Scope is data, not authority. No SECURITY DEFINER, RLS or provenance claim.
  IF p_action IS NULL OR p_action NOT IN ('query', 'ensure', 'stop')
     OR p_id IS NULL OR p_id !~ '^[0-9a-f]{64}$'
     OR p_ref IS NULL OR p_spec IS NULL OR p_record IS NULL
     OR p_deadline IS NULL OR p_deadline < 0
     OR p_epoch IS NULL OR p_epoch <= 0
     OR p_revision IS NULL OR p_revision NOT BETWEEN 0 AND 32
     OR p_owner IS NULL OR length(p_owner) NOT BETWEEN 1 AND 128
     OR p_expires IS NULL THEN
    RETURN QUERY SELECT 'invalid_request', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  -- A per-key transaction lock also covers absent keys. Hash collisions only
  -- serialize unrelated keys; exact primary-key/payload comparisons decide identity.
  PERFORM pg_advisory_xact_lock(hashtextextended('mixer-build-admission:' || p_id, 0));
  SELECT * INTO saved FROM mixer_build_operation_admissions AS a
    WHERE a.operation_id = p_id FOR UPDATE;
  at_time := clock_timestamp(); -- after every potentially blocking lock

  IF p_expires <= at_time THEN
    RETURN QUERY SELECT 'stale', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;
  IF FOUND THEN
    IF ROW(saved.original_ref, saved.original_spec, saved.deadline_ms, saved.record_id)
       IS DISTINCT FROM ROW(p_ref, p_spec, p_deadline, p_record) THEN
      RETURN QUERY SELECT 'identity_conflict', NULL::text, NULL::bigint, NULL::bigint;
      RETURN;
    END IF;
    IF ROW(p_epoch, p_revision) < ROW(saved.lease_epoch, saved.journal_revision)
       OR (p_epoch = saved.lease_epoch AND p_owner <> saved.owner_id) THEN
      RETURN QUERY SELECT 'stale', NULL::text, NULL::bigint, NULL::bigint;
      RETURN;
    END IF;
  END IF;

  -- Stop and query remain supported after the immutable operation deadline:
  -- the coordinator must be able to fence a timed-out operation. Neither launches.
  IF p_action = 'ensure' AND p_deadline <= floor(extract(epoch FROM at_time) * 1000)::bigint THEN
    RETURN QUERY SELECT 'deadline_expired', NULL::text, NULL::bigint, NULL::bigint;
    RETURN;
  END IF;

  IF saved.operation_id IS NULL THEN
    INSERT INTO mixer_build_operation_admissions
      (operation_id, original_ref, original_spec, deadline_ms, record_id,
       lease_epoch, journal_revision, owner_id, admission_state)
    VALUES (p_id, p_ref, p_spec, p_deadline, p_record, p_epoch, p_revision, p_owner, 'unadmitted')
    RETURNING * INTO saved;
    inserted := true;
  END IF;

  next_state := CASE
    WHEN saved.admission_state = 'stop_intent' OR p_action = 'stop' THEN 'stop_intent'
    WHEN p_action = 'ensure' THEN 'admitted'
    ELSE saved.admission_state END;

  UPDATE mixer_build_operation_admissions AS a
    SET lease_epoch = p_epoch, journal_revision = p_revision, owner_id = p_owner,
        admission_state = next_state, updated_at = at_time
    WHERE a.operation_id = p_id;

  RETURN QUERY SELECT
    CASE
      WHEN p_action = 'query' THEN 'read'
      WHEN p_action = 'stop' AND saved.admission_state <> 'stop_intent' THEN 'stop_recorded'
      WHEN p_action = 'stop' THEN 'stop_replay'
      WHEN saved.admission_state = 'stop_intent' THEN 'fenced'
      WHEN saved.admission_state = 'admitted' THEN 'admission_replay'
      ELSE 'admission_recorded' END,
    next_state, p_epoch, p_revision;
END;
$$;
