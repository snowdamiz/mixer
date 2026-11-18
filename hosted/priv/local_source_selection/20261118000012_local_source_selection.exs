defmodule MixerHosted.DevelopmentMigrations.LocalSourceSelection do
  use Ecto.Migration

  def up do
    Enum.each(MixerHosted.CustomerBuilds.LocalStarterSchema.statements(), &execute/1)
  end

  def down do
    execute("DROP FUNCTION public.mixer_local_starter_v1(text,text,jsonb,boolean)")
    execute("DROP TABLE public.mixer_local_starters")
  end
end
