defmodule MixerHosted.Repo.Migrations.AddBrowserSessions do
  use Ecto.Migration
  alias MixerHosted.BrowserAuth.StorageSchema

  # Inert installation: no roles/logins, credentials, role grants, write policies,
  # provider or application startup. Reviewed operator provisioning is separate.
  def up, do: Enum.each(StorageSchema.statements(), &execute/1)
  def down, do: Enum.each(StorageSchema.rollback_statements(), &execute/1)
end
