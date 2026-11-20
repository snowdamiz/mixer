\set ON_ERROR_STOP on

-- Run as the local ledger administrator with -v release_job_id=<job-id>.
-- Allow one more attempt on the same discarded release job.
UPDATE mixer_release_jobs.oban_jobs
SET state = 'available', scheduled_at = now(), discarded_at = NULL,
    max_attempts = attempt + 1
WHERE id = :'release_job_id'::bigint
  AND queue = 'releases' AND worker = 'MixerHosted.Releases.ReleaseJobs.Materialize'
  AND state = 'discarded' AND attempt >= max_attempts AND attempt < 2147483647
RETURNING id, attempt, max_attempts;
