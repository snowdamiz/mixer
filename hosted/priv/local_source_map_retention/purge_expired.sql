-- Run as the disposable local database administrator. Keep the publication
-- key and its original deadline so it cannot be retained again.
BEGIN;
SET LOCAL lock_timeout = '1s';
SET LOCAL statement_timeout = '5s';

WITH expired AS (
  SELECT organization_id, project_id, application_id, environment_id,
         platform, runtime_sha256, channel, sequence
  FROM public.mixer_release_source_maps
  WHERE map_bytes IS NOT NULL
    AND retain_until <= floor(extract(epoch FROM statement_timestamp()))
    AND (inet_server_addr() IS NULL OR inet_server_addr() IN ('127.0.0.1', '::1'))
  ORDER BY retain_until
  LIMIT 100
  FOR UPDATE SKIP LOCKED
), cleared AS (
  UPDATE public.mixer_release_source_maps AS maps
  SET map_bytes = NULL
  FROM expired
  WHERE (maps.organization_id,maps.project_id,maps.application_id,maps.environment_id,
         maps.platform,maps.runtime_sha256,maps.channel,maps.sequence)
      = (expired.organization_id,expired.project_id,expired.application_id,expired.environment_id,
         expired.platform,expired.runtime_sha256,expired.channel,expired.sequence)
  RETURNING 1
)
SELECT count(*) AS maps_cleared FROM cleared;

COMMIT;
