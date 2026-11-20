defmodule MixerHosted.Repo.Migrations.AddLocalReleaseHaltHealth do
  use Ecto.Migration

  @table "public.mixer_release_publications"
  @max_uint64 18_446_744_073_709_551_615
  @prior_actions """
  action = 'publish' OR (action IN ('promote','rollback') AND previous_sequence IS NOT NULL)
  """

  def up do
    execute("""
    ALTER TABLE #{@table}
      ADD COLUMN health_activated numeric CHECK (
        health_activated BETWEEN 0 AND #{@max_uint64} AND health_activated = trunc(health_activated)
      ),
      ADD COLUMN health_pending numeric CHECK (
        health_pending BETWEEN 0 AND #{@max_uint64} AND health_pending = trunc(health_pending)
      ),
      ADD COLUMN health_adverse_signals numeric CHECK (
        health_adverse_signals BETWEEN 1 AND #{@max_uint64}
        AND health_adverse_signals = trunc(health_adverse_signals)
      ),
      DROP CONSTRAINT mixer_release_publication_action,
      ADD CONSTRAINT mixer_release_publication_action CHECK (
        ((#{@prior_actions}) AND health_activated IS NULL
          AND health_pending IS NULL AND health_adverse_signals IS NULL)
        OR (action = 'halt' AND previous_sequence IS NOT NULL AND rollout_basis_points = 0
          AND health_activated IS NOT NULL AND health_pending IS NOT NULL
          AND health_adverse_signals IS NOT NULL)
      )
    """)
  end

  def down do
    execute("LOCK TABLE #{@table} IN ACCESS EXCLUSIVE MODE")

    execute("""
    DO $body$ BEGIN
      IF EXISTS (SELECT 1 FROM #{@table} WHERE action = 'halt') THEN
        RAISE EXCEPTION 'release ledger contains committed health halts';
      END IF;
    END $body$
    """)

    execute("""
    ALTER TABLE #{@table}
      DROP CONSTRAINT mixer_release_publication_action,
      DROP COLUMN health_activated,
      DROP COLUMN health_pending,
      DROP COLUMN health_adverse_signals,
      ADD CONSTRAINT mixer_release_publication_action CHECK (#{@prior_actions})
    """)
  end
end
