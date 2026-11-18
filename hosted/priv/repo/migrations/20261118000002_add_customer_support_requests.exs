defmodule MixerHosted.Repo.Migrations.AddCustomerSupportRequests do
  use Ecto.Migration

  def up, do: Enum.each(MixerHosted.CustomerWorkspace.SupportSchema.statements(), &execute/1)

  def down, do: execute("DROP TABLE public.mixer_support_requests")
end
