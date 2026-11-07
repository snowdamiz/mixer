defmodule MixerHosted.Repo.Migrations.AddBuildAggregateLimits do
  use Ecto.Migration

  def up do
    create table(:mixer_build_fleet_capacity, primary_key: false) do
      add(:id, :text, primary_key: true)
      add(:limit, :integer, null: false, default: 0)
      add(:revision, :bigint, null: false, default: 0)
      add(:configured, :boolean, null: false, default: false)
    end

    create(
      constraint(:mixer_build_fleet_capacity, :mixer_build_fleet_capacity_bounds,
        check:
          "id = 'fleet' AND \"limit\" BETWEEN 0 AND 10000 AND revision >= 0 AND (configured OR (\"limit\" = 0 AND revision = 0))"
      )
    )

    create table(:mixer_build_fleet_platform_capacities, primary_key: false) do
      add(:platform, :text, primary_key: true)
      add(:limit, :integer, null: false, default: 0)
      add(:revision, :bigint, null: false, default: 0)
      add(:configured, :boolean, null: false, default: false)
    end

    create(
      constraint(
        :mixer_build_fleet_platform_capacities,
        :mixer_build_fleet_platform_capacities_bounds,
        check:
          "platform IN ('ios', 'android') AND \"limit\" BETWEEN 0 AND 10000 AND revision >= 0 AND (configured OR (\"limit\" = 0 AND revision = 0))"
      )
    )

    create table(:mixer_build_organization_capacities, primary_key: false) do
      add(:organization_id, :text, primary_key: true)
      add(:limit, :integer, null: false, default: 0)
      add(:revision, :bigint, null: false, default: 0)
      add(:configured, :boolean, null: false, default: false)
    end

    create(
      constraint(
        :mixer_build_organization_capacities,
        :mixer_build_organization_capacities_bounds,
        check:
          "octet_length(organization_id) BETWEEN 1 AND 128 AND \"limit\" BETWEEN 0 AND 10000 AND revision >= 0 AND (configured OR (\"limit\" = 0 AND revision = 0))"
      )
    )

    execute("INSERT INTO mixer_build_fleet_capacity (id) VALUES ('fleet')")

    execute(
      "INSERT INTO mixer_build_fleet_platform_capacities (platform) VALUES ('ios'), ('android')"
    )

    execute(
      "INSERT INTO mixer_build_organization_capacities (organization_id) SELECT DISTINCT organization_id FROM mixer_build_capacities"
    )

    create(index(:mixer_build_reservations, [:platform], where: "held"))
  end

  def down do
    drop(index(:mixer_build_reservations, [:platform], where: "held"))
    drop(table(:mixer_build_organization_capacities))
    drop(table(:mixer_build_fleet_platform_capacities))
    drop(table(:mixer_build_fleet_capacity))
  end
end
