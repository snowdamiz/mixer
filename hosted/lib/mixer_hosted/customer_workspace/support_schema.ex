defmodule MixerHosted.CustomerWorkspace.SupportSchema do
  @moduledoc false

  def statements do
    [
      """
      CREATE TABLE public.mixer_support_requests (
        organization_id text NOT NULL,
        principal_id text NOT NULL,
        request_id text NOT NULL CHECK (request_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'),
        subject text NOT NULL CHECK (octet_length(subject) BETWEEN 1 AND 120),
        message text NOT NULL CHECK (octet_length(message) BETWEEN 1 AND 1800),
        submitted_at timestamptz NOT NULL DEFAULT statement_timestamp(),
        PRIMARY KEY (organization_id, principal_id, request_id)
      )
      """,
      """
      CREATE INDEX mixer_support_requests_recent ON public.mixer_support_requests
        (organization_id, principal_id, submitted_at DESC, request_id DESC)
      """,
      "REVOKE ALL ON public.mixer_support_requests FROM PUBLIC",
      "ALTER TABLE public.mixer_support_requests ENABLE ROW LEVEL SECURITY",
      "ALTER TABLE public.mixer_support_requests FORCE ROW LEVEL SECURITY",
      """
      CREATE POLICY support_submitter ON public.mixer_support_requests USING (
        organization_id = current_setting('mixer.authz.organization_id', true)
        AND principal_id = current_setting('mixer.authz.principal_id', true)
        AND EXISTS (
          SELECT 1 FROM public.mixer_authz_memberships m
          JOIN public.mixer_authz_organizations o ON o.id=m.organization_id AND o.active
          WHERE m.organization_id=mixer_support_requests.organization_id
            AND m.principal_id=mixer_support_requests.principal_id AND m.project_id IS NULL
            AND m.project_binding='all_projects' AND m.active
            AND m.not_before<=extract(epoch FROM statement_timestamp())
            AND (m.expires_at IS NULL OR m.expires_at>extract(epoch FROM statement_timestamp()))
        )
      )
      """
    ]
  end

  @doc "Grant the configured ordinary browser login access after migration."
  def grant_statement(ordinary_login) do
    true = Regex.match?(~r/\A[a-z_][a-z0-9_]{0,62}\z/, ordinary_login)
    true = ordinary_login != "public" and not String.starts_with?(ordinary_login, "pg_")

    ~s|GRANT SELECT, INSERT (organization_id, principal_id, request_id, subject, message) ON public.mixer_support_requests TO "#{ordinary_login}"|
  end
end
