defmodule MixerHosted.DevelopmentMigrations.CustomerBuildCreate do
  use Ecto.Migration

  def up do
    Enum.each(MixerHosted.CustomerBuilds.CreateSchema.statements(), &execute/1)
    Enum.each(MixerHosted.BrowserAuth.ActiveCreateSchema.statements(), &execute/1)
  end

  def down, do: raise("immutable development admission requires explicit retirement")
end
