-- No retention deletion API. The tombstone is permanent for this identity.
CREATE FUNCTION mixer_build_operation_admissions_immutable() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'operation retention deletion is forbidden';
  END IF;
  IF ROW(NEW.operation_id, NEW.original_ref, NEW.original_spec, NEW.deadline_ms, NEW.record_id, NEW.created_at)
       IS DISTINCT FROM
     ROW(OLD.operation_id, OLD.original_ref, OLD.original_spec, OLD.deadline_ms, OLD.record_id, OLD.created_at)
     OR ROW(NEW.lease_epoch, NEW.journal_revision) < ROW(OLD.lease_epoch, OLD.journal_revision)
     OR (NEW.lease_epoch = OLD.lease_epoch AND NEW.owner_id <> OLD.owner_id)
     OR (OLD.admission_state = 'stop_intent' AND NEW.admission_state <> 'stop_intent')
     OR (OLD.admission_state = 'admitted' AND NEW.admission_state = 'unadmitted') THEN
    RAISE EXCEPTION 'immutable operation or monotonic admission violation';
  END IF;
  RETURN NEW;
END;
$$;
