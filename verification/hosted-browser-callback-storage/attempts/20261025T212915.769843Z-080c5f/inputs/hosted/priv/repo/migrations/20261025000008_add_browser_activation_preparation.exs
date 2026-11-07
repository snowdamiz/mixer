defmodule MixerHosted.Repo.Migrations.AddBrowserActivationPreparation do
  use Ecto.Migration
  alias MixerHosted.BrowserAuth.ActivationPreparationSchema

  # Inert installation only. Existing-role upgrade and explicit V2 admission
  # selection are separate operator/application changes.
  def up, do: Enum.each(ActivationPreparationSchema.statements(), &execute/1)
  def down, do: Enum.each(ActivationPreparationSchema.rollback_statements(), &execute/1)
end
