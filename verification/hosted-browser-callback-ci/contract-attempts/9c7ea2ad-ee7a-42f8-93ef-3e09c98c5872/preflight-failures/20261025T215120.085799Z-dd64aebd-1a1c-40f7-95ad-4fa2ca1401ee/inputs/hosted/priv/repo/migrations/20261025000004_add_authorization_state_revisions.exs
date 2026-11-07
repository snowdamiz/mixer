defmodule MixerHosted.Repo.Migrations.AddAuthorizationStateRevisions do
  use Ecto.Migration

  # Baseline for this newly introduced schema. This does not reconstruct history
  # or implement the future controlled, audited lifecycle writer.
  def up do
    execute("""
    ALTER TABLE public.mixer_authz_profiles
      ADD COLUMN state_revision bigint NOT NULL DEFAULT 1
      CHECK (state_revision BETWEEN 1 AND 9007199254740991)
    """)

    execute("""
    ALTER TABLE public.mixer_authz_bindings
      ADD COLUMN revision bigint NOT NULL DEFAULT 1
      CHECK (revision BETWEEN 1 AND 9007199254740991)
    """)
  end

  def down do
    execute("ALTER TABLE public.mixer_authz_bindings DROP COLUMN revision")
    execute("ALTER TABLE public.mixer_authz_profiles DROP COLUMN state_revision")
  end
end
