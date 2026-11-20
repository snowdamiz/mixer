defmodule MixerHosted.DevelopmentMigrations.LocalAndroidSourceSelection do
  use Ecto.Migration

  def up do
    Enum.each(MixerHosted.CustomerBuilds.LocalStarterSchema.statements(:android), &execute/1)
  end

  def down do
    execute("DROP FUNCTION public.mixer_local_android_starter_v1(text,text,jsonb,boolean,text)")
    execute("DROP TABLE public.mixer_local_android_starters")
  end
end
