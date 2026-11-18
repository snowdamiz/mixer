defmodule MixerHosted.Repo.Migrations.AddWorkspaceApplicationRegistration do
  use Ecto.Migration

  alias MixerHosted.CustomerWorkspace.SelfServiceSchema

  def up, do: apply_definition(:up)
  def down, do: apply_definition(:down)

  defp apply_definition(direction) do
    Enum.each(SelfServiceSchema.application_registration_statements(direction), &execute/1)
  end
end
