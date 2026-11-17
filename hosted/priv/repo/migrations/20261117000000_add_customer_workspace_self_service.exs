defmodule MixerHosted.Repo.Migrations.AddCustomerWorkspaceSelfService do
  use Ecto.Migration

  alias MixerHosted.BrowserAuth.ActiveWorkspaceSchema
  alias MixerHosted.CustomerWorkspace.SelfServiceSchema

  def up, do: Enum.each(SelfServiceSchema.statements(), &execute/1)

  def down do
    execute(ActiveWorkspaceSchema.rollback_statement())
    Enum.each(SelfServiceSchema.rollback_statements(), &execute/1)
  end
end
