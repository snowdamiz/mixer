DECLARE
  build public.mixer_builds%ROWTYPE;
  last_kind text;
  stamp bigint;
  epoch bigint;
  attempt integer;
  fence bigint;
BEGIN
  IF session_user <> 'mixer_build_create'
     OR public.mixer_customer_build_create_guard() IS DISTINCT FROM true THEN
    RETURN NULL;
  END IF;

  SELECT * INTO build FROM public.mixer_builds
  WHERE organization_id = current_setting('mixer.authz.organization_id',true)
    AND project_id = current_setting('mixer.authz.project_id',true)
    AND application_id = current_setting('mixer.authz.application_id',true)
    AND build_id = $1 AND platform = $2
    AND journal#>>'{creation,spec,source,sha256}' = $3
    AND journal#>>'{creation,spec,toolchain_lock_sha256}' = $4
    AND journal#>>'{creation,spec,build_definition_sha256}' = $5
  FOR UPDATE;
  IF NOT FOUND OR public.mixer_customer_build_create_guard() IS DISTINCT FROM true THEN
    RETURN NULL;
  END IF;

  IF EXISTS (SELECT 1 FROM jsonb_array_elements(build.journal->'events') e
             WHERE e->>'id' = 'customer:cancel'
               AND e->'event' = '{"type":"cancel","reason":"customer_requested"}'::jsonb) THEN
    RETURN jsonb_build_object('outcome','duplicate','record',to_jsonb(build));
  END IF;

  last_kind := COALESCE(build.journal#>>'{events,-1,event,type}', 'created');
  IF last_kind NOT IN ('created','retry','start','expire') THEN
    RETURN jsonb_build_object('outcome','conflict');
  END IF;

  epoch := floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint;
  stamp := greatest(epoch, COALESCE(build.journal#>>'{events,-1,now_ms}',
                                  build.journal#>>'{creation,now_ms}')::bigint);

  -- The coordinator derives the same attempt and fence from the journal.
  SELECT 1 + count(*) FILTER (WHERE e#>>'{event,type}' = 'retry'),
         2 + count(*) FILTER (WHERE e#>>'{event,type}' <> 'start')
  INTO attempt, fence FROM jsonb_array_elements(build.journal->'events') e;

  UPDATE public.mixer_builds
  SET revision = build.revision + 1, updated_at = clock_timestamp(),
      journal = jsonb_insert(build.journal, '{events,-1}', jsonb_build_object(
        'id','customer:cancel','now_ms',stamp,
        'event',jsonb_build_object('type','cancel','reason','customer_requested')), true)
  WHERE id = build.id AND revision = build.revision AND revision < 32
  RETURNING * INTO build;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'cancel revision unavailable';
  END IF;

  INSERT INTO public.oban_jobs (queue, worker, args, max_attempts)
  VALUES ('builds', 'MixerHosted.Builds.Coordinator',
          jsonb_build_object('organization_id',build.organization_id,
            'project_id',build.project_id,'application_id',build.application_id,
            'build_id',build.build_id,'platform',build.platform,'build_record_id',build.id,
            'revision',build.revision,'attempt',attempt,'fence',fence,'kind','cancel'),
          20);

  RETURN jsonb_build_object('outcome','applied','record',to_jsonb(build));
END
