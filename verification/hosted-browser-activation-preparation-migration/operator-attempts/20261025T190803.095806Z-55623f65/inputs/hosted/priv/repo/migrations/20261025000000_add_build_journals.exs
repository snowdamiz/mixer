defmodule MixerHosted.Repo.Migrations.AddBuildJournals do
  use Ecto.Migration

  def change do
    create table(:mixer_builds, primary_key: false) do
      add(:id, :uuid, primary_key: true)
      add(:organization_id, :text, null: false)
      add(:project_id, :text, null: false)
      add(:application_id, :text, null: false)
      add(:build_id, :text, null: false)
      add(:platform, :text, null: false)
      add(:request_key, :text, null: false)
      add(:revision, :bigint, null: false)
      add(:journal, :map, null: false)
      timestamps(type: :utc_datetime_usec)
    end

    create(
      unique_index(:mixer_builds, [
        :organization_id,
        :project_id,
        :application_id,
        :build_id,
        :platform
      ])
    )

    create(
      unique_index(:mixer_builds, [
        :organization_id,
        :project_id,
        :application_id,
        :platform,
        :request_key
      ])
    )

    for field <- [:organization_id, :project_id, :application_id, :build_id, :request_key] do
      create(
        constraint(:mixer_builds, "mixer_builds_#{field}_bytes",
          check: "octet_length(#{field}) BETWEEN 1 AND 128"
        )
      )
    end

    create(
      constraint(:mixer_builds, :mixer_builds_platform, check: "platform IN ('ios', 'android')")
    )

    create(constraint(:mixer_builds, :mixer_builds_revision, check: "revision BETWEEN 0 AND 32"))

    create(
      constraint(:mixer_builds, :mixer_builds_journal_object,
        check: "jsonb_typeof(journal) = 'object'"
      )
    )
  end
end
