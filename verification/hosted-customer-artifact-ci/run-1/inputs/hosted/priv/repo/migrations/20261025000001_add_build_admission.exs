defmodule MixerHosted.Repo.Migrations.AddBuildAdmission do
  use Ecto.Migration

  def change do
    create table(:mixer_build_capacities, primary_key: false) do
      add(:organization_id, :text, primary_key: true)
      add(:platform, :text, primary_key: true)
      add(:limit, :integer, null: false)
      add(:revision, :bigint, null: false)
    end

    create(
      constraint(:mixer_build_capacities, :mixer_build_capacities_bounds,
        check:
          "octet_length(organization_id) BETWEEN 1 AND 128 AND platform IN ('ios', 'android') AND \"limit\" BETWEEN 0 AND 10000 AND revision >= 0"
      )
    )

    create(unique_index(:mixer_builds, [:id, :organization_id, :platform]))

    create table(:mixer_build_reservations, primary_key: false) do
      add(:build_record_id, :uuid, primary_key: true)
      add(:organization_id, :text, null: false)
      add(:platform, :text, null: false)
      add(:attempt, :integer, null: false)
      add(:worker_fence, :bigint, null: false)
      add(:held, :boolean, null: false)
      add(:terminal_event_id, :text)
    end

    execute(
      "ALTER TABLE mixer_build_reservations ADD CONSTRAINT mixer_build_reservations_build_scope_fkey FOREIGN KEY (build_record_id, organization_id, platform) REFERENCES mixer_builds (id, organization_id, platform)",
      "ALTER TABLE mixer_build_reservations DROP CONSTRAINT mixer_build_reservations_build_scope_fkey"
    )

    execute(
      "ALTER TABLE mixer_build_reservations ADD CONSTRAINT mixer_build_reservations_capacity_fkey FOREIGN KEY (organization_id, platform) REFERENCES mixer_build_capacities (organization_id, platform)",
      "ALTER TABLE mixer_build_reservations DROP CONSTRAINT mixer_build_reservations_capacity_fkey"
    )

    create(index(:mixer_build_reservations, [:organization_id, :platform], where: "held"))

    create(
      constraint(:mixer_build_reservations, :mixer_build_reservations_bounds,
        check:
          "attempt BETWEEN 1 AND 5 AND worker_fence >= 1 AND ((held AND terminal_event_id IS NULL) OR (NOT held AND terminal_event_id IS NOT NULL AND octet_length(terminal_event_id) BETWEEN 1 AND 128))"
      )
    )

    create table(:mixer_build_coordinator_leases, primary_key: false) do
      add(
        :build_record_id,
        references(:mixer_build_reservations,
          column: :build_record_id,
          type: :uuid,
          on_delete: :restrict
        ),
        primary_key: true
      )

      add(:owner_id, :text)
      add(:epoch, :bigint, null: false)
      add(:expires_at, :utc_datetime_usec)
    end

    create(
      constraint(:mixer_build_coordinator_leases, :mixer_build_coordinator_leases_bounds,
        check:
          "epoch >= 1 AND ((owner_id IS NULL AND expires_at IS NULL) OR (owner_id IS NOT NULL AND octet_length(owner_id) BETWEEN 1 AND 128 AND expires_at IS NOT NULL))"
      )
    )
  end
end
