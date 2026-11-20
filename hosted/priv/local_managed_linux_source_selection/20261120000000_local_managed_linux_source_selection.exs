defmodule MixerHosted.DevelopmentMigrations.LocalManagedLinuxSourceSelection do
  use Ecto.Migration

  def up do
    Enum.each(
      MixerHosted.CustomerBuilds.LocalStarterSchema.statements(:managed_linux_pair25),
      &execute/1
    )
  end

  def down do
    execute(
      "DROP FUNCTION public.mixer_managed_linux_pair25_starter_v1(text,text,jsonb,boolean,text,text)"
    )

    execute("DROP TABLE public.mixer_managed_linux_pair25_starters")
  end
end
