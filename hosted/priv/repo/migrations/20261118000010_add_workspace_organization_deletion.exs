defmodule MixerHosted.Repo.Migrations.AddWorkspaceOrganizationDeletion do
  use Ecto.Migration

  alias MixerHosted.CustomerWorkspace.SelfServiceSchema

  # Upgrading an already provisioned database requires authority over both the
  # workspace-writer-owned function and the relation-owner-owned count and tables.
  def up, do: apply_definition(:up)
  def down, do: apply_definition(:down)

  defp apply_definition(direction) do
    Enum.each(SelfServiceSchema.organization_deletion_statements(direction), &execute/1)
  end
end
