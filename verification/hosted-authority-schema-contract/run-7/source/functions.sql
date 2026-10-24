CREATE FUNCTION mixer_authz.validate_inputs(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1) RETURNS void LANGUAGE plpgsql IMMUTABLE PARALLEL UNSAFE SET search_path=pg_catalog AS $$
DECLARE sc text;
BEGIN
 IF NOT mixer_authz.bounded_text(i.profile_id,128) OR i.profile_version IS NULL OR i.profile_version<1 OR NOT mixer_authz.bounded_text(i.issuer,2048) OR NOT mixer_authz.bounded_text(i.subject,256) OR NOT mixer_authz.bounded_text(i.client_id,256) OR i.credential_sha256 IS NULL OR octet_length(i.credential_sha256)<>32 OR i.identity_class IS DISTINCT FROM 'human' OR NOT mixer_authz.finite_uint(i.issued_at,0,9007199254740991) OR NOT mixer_authz.finite_uint(i.expires_at,0,9007199254740991) OR NOT mixer_authz.finite_uint(i.authentication_completed_at,0,9007199254740991) OR i.issued_at>=i.expires_at OR i.authentication_completed_at>=i.expires_at OR i.scopes IS NULL OR cardinality(i.scopes)>3 OR array_ndims(i.scopes)>1 OR (cardinality(i.scopes)>0 AND array_lower(i.scopes,1)<>1) THEN RAISE EXCEPTION 'invalid identity' USING ERRCODE='42501';END IF;
 FOREACH sc IN ARRAY i.scopes LOOP IF sc IS NULL OR sc NOT IN ('mixer.artifact.read','mixer.artifact.upload','mixer.audit.read') THEN RAISE EXCEPTION 'invalid scopes' USING ERRCODE='42501';END IF;END LOOP;
 IF (SELECT count(DISTINCT x) FROM unnest(i.scopes) x)<>cardinality(i.scopes) THEN RAISE EXCEPTION 'duplicate scopes' USING ERRCODE='42501';END IF;
 IF t.action IS NULL OR t.action NOT IN ('artifact.read','artifact.upload','audit.read') OR NOT mixer_authz.valid_id(t.organization) OR NOT mixer_authz.valid_id(t.project) THEN RAISE EXCEPTION 'invalid action/tenant' USING ERRCODE='42501';END IF;
 IF t.action='audit.read' THEN
  IF t.app IS NOT NULL OR t.environment IS NOT NULL OR t.platform IS NOT NULL OR t.runtime_sha256 IS NOT NULL OR t.manifest_sha256 IS NOT NULL THEN RAISE EXCEPTION 'invalid audit target' USING ERRCODE='42501';END IF;
 ELSIF NOT mixer_authz.valid_id(t.app) OR NOT mixer_authz.valid_id(t.environment) OR t.platform IS NULL OR t.platform NOT IN ('ios','android') OR t.runtime_sha256 IS NULL OR octet_length(t.runtime_sha256)<>32 OR t.manifest_sha256 IS NULL OR octet_length(t.manifest_sha256)<>32 THEN RAISE EXCEPTION 'invalid artifact target' USING ERRCODE='42501';END IF;
END $$;
CREATE FUNCTION mixer_authz.assert_transaction(x mixer_authz.transaction_identity_v1) RETURNS void LANGUAGE plpgsql VOLATILE PARALLEL UNSAFE SET search_path=pg_catalog AS $$
BEGIN
 IF session_user<>'mixer_hosted_runtime' OR current_setting('role')<>'none' OR current_setting('transaction_isolation')<>'read committed' OR x.backend IS DISTINCT FROM pg_backend_pid() OR x.full_xid IS DISTINCT FROM pg_current_xact_id()::text OR x.database_name IS DISTINCT FROM current_database()::name OR x.runtime_role IS DISTINCT FROM session_user::name OR x.nonce IS NULL OR x.nonce !~ '^[0-9a-f]{64}$' OR x.nonce IS DISTINCT FROM nullif(current_setting('mixer_authz.invocation_nonce',true),'') OR x.deadline IS NULL OR NOT isfinite(x.deadline) OR x.deadline<=clock_timestamp() OR x.deadline>clock_timestamp()+interval '5 seconds' OR x.deadline::text IS DISTINCT FROM nullif(current_setting('mixer_authz.deadline',true),'') THEN RAISE EXCEPTION 'transaction context rejected' USING ERRCODE='42501';END IF;
END $$;
CREATE FUNCTION mixer_authz.lookup_admission(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.admission_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE a mixer_authz.admission_v1;
BEGIN
 PERFORM mixer_authz.assert_transaction(x);PERFORM mixer_authz.validate_inputs(i,t);
 SELECT b.principal_id,b.binding_id,c.family_id INTO a.principal_id,a.binding_id,a.family_id FROM mixer_authz.external_identity_bindings b JOIN mixer_authz.credential_references c ON (c.binding_id,c.principal_id,c.profile_id)=(b.binding_id,b.principal_id,b.profile_id) WHERE b.profile_id=i.profile_id AND b.issuer=i.issuer AND b.subject=i.subject AND b.registered_client=i.client_id AND b.identity_class=i.identity_class AND c.jti_sha256=i.credential_sha256 AND c.accepted_issued_at=i.issued_at AND c.accepted_expires_at=i.expires_at;
 IF NOT FOUND THEN RAISE EXCEPTION 'credential rejected' USING ERRCODE='42501';END IF;
 a.identity:=i;a.target:=t;a.transaction_identity:=x;RETURN a;
END $$;
CREATE FUNCTION mixer_authz.lock_admission_rows(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.admission_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE b mixer_authz.admission_v1;r mixer_authz.admission_v1:=a;
BEGIN
 b:=mixer_authz.lookup_admission(i,t,x);
 IF a.identity IS DISTINCT FROM i OR a.target IS DISTINCT FROM t OR a.transaction_identity IS DISTINCT FROM x OR ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(b.principal_id,b.binding_id,b.family_id) THEN RAISE EXCEPTION 'admission substitution' USING ERRCODE='42501';END IF;
 SELECT p.revision INTO r.profile_revision FROM mixer_authz.identity_trust_profiles p WHERE p.profile_id=i.profile_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT p.revision INTO r.principal_revision FROM mixer_authz.principals p WHERE p.principal_id=a.principal_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT f.revision INTO r.family_revision FROM mixer_authz.credential_families f WHERE f.family_id=a.family_id AND f.binding_id=a.binding_id AND f.principal_id=a.principal_id AND f.profile_id=i.profile_id FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT h.revision INTO r.organization_revision FROM mixer_authz.organization_authorization_heads h WHERE h.organization=t.organization FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 SELECT h.revision INTO r.project_revision FROM mixer_authz.project_authorization_heads h WHERE (h.organization,h.project)=(t.organization,t.project) FOR SHARE;IF NOT FOUND THEN RAISE EXCEPTION 'lock row missing' USING ERRCODE='42501';END IF;
 -- Reassert immutable lookup after all locks. No capability is returned.
 b:=mixer_authz.lookup_admission(i,t,x);
 IF ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(b.principal_id,b.binding_id,b.family_id) THEN RAISE EXCEPTION 'mapping changed' USING ERRCODE='42501';END IF;
 r.lock_statement_at:=statement_timestamp();RETURN r;
END $$;
CREATE FUNCTION mixer_authz.recheck_current(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.decision_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE locked mixer_authz.admission_v1;d mixer_authz.decision_v1;p mixer_authz.identity_trust_profiles;pr mixer_authz.principals;f mixer_authz.credential_families;now_s numeric;members mixer_authz.membership_witness_v1[];eligible boolean;visible boolean;needed text;
BEGIN
 IF a.lock_statement_at IS NULL OR NOT isfinite(a.lock_statement_at) OR a.lock_statement_at>=statement_timestamp() THEN RAISE EXCEPTION 'separate lock statement required' USING ERRCODE='42501';END IF;
 -- Writer recheck NEVER acquires a lock: caller already holds canonical locks.
 locked:=mixer_authz.lookup_admission(i,t,x);
 IF a.identity IS DISTINCT FROM i OR a.target IS DISTINCT FROM t OR a.transaction_identity IS DISTINCT FROM x OR ROW(a.principal_id,a.binding_id,a.family_id) IS DISTINCT FROM ROW(locked.principal_id,locked.binding_id,locked.family_id) THEN RAISE EXCEPTION 'admission substitution' USING ERRCODE='42501';END IF;
 SELECT pp.revision,qq.revision,ff.revision,oh.revision,ph.revision INTO locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision FROM mixer_authz.identity_trust_profiles pp CROSS JOIN mixer_authz.principals qq CROSS JOIN mixer_authz.credential_families ff CROSS JOIN mixer_authz.organization_authorization_heads oh CROSS JOIN mixer_authz.project_authorization_heads ph WHERE pp.profile_id=i.profile_id AND qq.principal_id=a.principal_id AND ff.family_id=a.family_id AND oh.organization=t.organization AND (ph.organization,ph.project)=(t.organization,t.project);
 IF NOT FOUND OR ROW(a.profile_revision,a.principal_revision,a.family_revision,a.organization_revision,a.project_revision) IS DISTINCT FROM ROW(locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision) THEN RAISE EXCEPTION 'revision substitution/change' USING ERRCODE='42501';END IF;
 PERFORM mixer_authz.assert_transaction(x);
 -- This VOLATILE internal statement obtains fresh READ COMMITTED current state.
 SELECT pp.* INTO STRICT p FROM mixer_authz.identity_trust_profiles pp WHERE pp.profile_id=i.profile_id;
 SELECT qq.* INTO STRICT pr FROM mixer_authz.principals qq WHERE qq.principal_id=a.principal_id;
 SELECT ff.* INTO STRICT f FROM mixer_authz.credential_families ff WHERE ff.family_id=a.family_id;
 now_s:=floor(extract(epoch FROM clock_timestamp()));
 IF NOT mixer_authz.finite_uint(now_s,0,9007199254740991) OR NOT p.enabled OR p.current_version<>i.profile_version OR ROW(p.issuer,p.client_id,p.identity_class) IS DISTINCT FROM ROW(i.issuer,i.client_id,i.identity_class) OR pr.kind<>'human' OR pr.status<>'active' OR f.status<>'active' OR i.issued_at<pr.valid_after OR i.issued_at<f.valid_after OR now_s>=i.expires_at OR i.authentication_completed_at<now_s-45 OR i.authentication_completed_at>now_s+30 OR EXISTS(SELECT 1 FROM mixer_authz.credential_denials den WHERE den.binding_id=a.binding_id AND den.jti_sha256=i.credential_sha256) THEN RAISE EXCEPTION 'current credential rejected' USING ERRCODE='42501';END IF;
 d.principal_id:=a.principal_id;d.binding_id:=a.binding_id;d.family_id:=a.family_id;d.decision_at:=now_s;d.profile_revision:=locked.profile_revision;d.principal_revision:=locked.principal_revision;d.family_revision:=locked.family_revision;d.organization_revision:=locked.organization_revision;d.project_revision:=locked.project_revision;d.memberships:=ARRAY[]::mixer_authz.membership_witness_v1[];
 IF NOT EXISTS(SELECT 1 FROM mixer_authz.organizations o JOIN mixer_authz.projects pj USING(organization) WHERE o.organization=t.organization AND pj.project=t.project AND o.status='active' AND pj.status='active') OR (t.action<>'audit.read' AND NOT EXISTS(SELECT 1 FROM mixer_authz.applications ap JOIN mixer_authz.environments en USING(organization,project,app) WHERE (ap.organization,ap.project,ap.app,en.environment)=(t.organization,t.project,t.app,t.environment) AND ap.status='active' AND en.status='active')) THEN d.outcome:='not_found';RETURN d;END IF;
 SELECT array_agg(ROW(m.lifecycle_id,m.role,m.revision)::mixer_authz.membership_witness_v1 ORDER BY m.lifecycle_id) INTO members FROM (SELECT allm.* FROM (SELECT om.lifecycle_id,om.role,om.revision FROM mixer_authz.organization_memberships om WHERE om.principal_id=a.principal_id AND om.organization=t.organization AND om.project_binding='organization_wide' AND om.status='active' AND (om.not_before IS NULL OR om.not_before<=now_s) AND (om.expires_at IS NULL OR now_s<om.expires_at) UNION ALL SELECT pm.lifecycle_id,pm.role,pm.revision FROM mixer_authz.project_memberships pm WHERE pm.principal_id=a.principal_id AND (pm.organization,pm.project)=(t.organization,t.project) AND pm.status='active' AND (pm.not_before IS NULL OR pm.not_before<=now_s) AND (pm.expires_at IS NULL OR now_s<pm.expires_at)) allm ORDER BY allm.lifecycle_id LIMIT 65) m;
 IF cardinality(members)>64 THEN d.outcome:='authorization_unavailable';RETURN d;END IF;
 visible:=coalesce(cardinality(members)>0,false);IF NOT visible THEN d.outcome:='not_found';RETURN d;END IF;
 d.memberships:=members;
 SELECT bool_or(m.role IN ('owner','administrator','developer') OR (t.action<>'artifact.upload' AND m.role IN ('release_manager','viewer'))) INTO eligible FROM unnest(members) m;
 needed:=CASE t.action WHEN 'artifact.read' THEN 'mixer.artifact.read' WHEN 'artifact.upload' THEN 'mixer.artifact.upload' WHEN 'audit.read' THEN 'mixer.audit.read' END;
 d.outcome:=CASE WHEN eligible AND needed=ANY(i.scopes) THEN 'allowed' ELSE 'forbidden' END;
 IF floor(extract(epoch FROM clock_timestamp()))<>now_s THEN RAISE EXCEPTION 'decision clock advanced; retry fresh' USING ERRCODE='42501';END IF;
 PERFORM mixer_authz.assert_transaction(x);RETURN d;
END $$;

CREATE FUNCTION mixer_authz.decide_current(i mixer_authz.verified_identity_v1,t mixer_authz.target_v1,a mixer_authz.admission_v1,x mixer_authz.transaction_identity_v1) RETURNS mixer_authz.decision_v1 LANGUAGE plpgsql VOLATILE SECURITY DEFINER PARALLEL UNSAFE SET search_path=pg_catalog SET row_security=on AS $$
DECLARE locked mixer_authz.admission_v1;
BEGIN
 IF a.lock_statement_at IS NULL OR NOT isfinite(a.lock_statement_at) OR a.lock_statement_at>=statement_timestamp() THEN RAISE EXCEPTION 'separate lock statement required' USING ERRCODE='42501';END IF;
 -- Admission proves actual cardinality by acquiring every lock again. No tenant head yet.
 locked:=mixer_authz.lock_admission_rows(i,t,a,x);
 IF ROW(a.profile_revision,a.principal_revision,a.family_revision,a.organization_revision,a.project_revision) IS DISTINCT FROM ROW(locked.profile_revision,locked.principal_revision,locked.family_revision,locked.organization_revision,locked.project_revision) THEN RAISE EXCEPTION 'revision substitution/change' USING ERRCODE='42501';END IF;
 RETURN mixer_authz.recheck_current(i,t,a,x);
END $$;
