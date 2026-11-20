defmodule MixerHosted.Repo.Migrations.AddLocalReleasePublicationAction do
  use Ecto.Migration

  def up do
    execute("""
    ALTER TABLE public.mixer_release_publications
    ADD COLUMN action text NOT NULL DEFAULT 'publish',
    ADD CONSTRAINT mixer_release_publication_action CHECK (
      action = 'publish' OR (action IN ('promote','rollback') AND previous_sequence IS NOT NULL)
    )
    """)
  end

  def down do
    execute("LOCK TABLE public.mixer_release_publications IN ACCESS EXCLUSIVE MODE")

    execute("""
    DO $body$ BEGIN
      IF EXISTS (SELECT 1 FROM public.mixer_release_publications WHERE action <> 'publish') THEN
        RAISE EXCEPTION 'release ledger contains committed promotions or rollbacks';
      END IF;
    END $body$
    """)

    execute("ALTER TABLE public.mixer_release_publications DROP COLUMN action")
  end
end
