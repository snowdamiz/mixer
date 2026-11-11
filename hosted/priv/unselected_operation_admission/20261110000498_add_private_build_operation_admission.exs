defmodule MixerHosted.Repo.Migrations.AddPrivateBuildOperationAdmission do
  use Ecto.Migration

  @statements ~w(01_table.sql 02_immutable_function.sql 03_immutable_trigger.sql 04_admission_function.sql)

  # UNSELECTED: outside priv/repo/migrations and the closed reviewed list.
  def up do
    Enum.each(@statements, fn statement ->
      execute(File.read!(Path.join(__DIR__, statement)))
    end)
  end

  def down do
    raise "permanent operation identities require an explicit retention migration decision"
  end
end
