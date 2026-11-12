defmodule MixerHosted.CustomerBuildCatalog do
  @moduledoc "Private unselected build-purpose discovery with current authorization on every page."
  alias MixerHosted.CustomerBuildCatalog.{Input, Context}
  alias MixerHosted.CustomerBuilds.Policy
  def applications(identity, scope, page), do: read(:applications, identity, scope, page)
  def builds(identity, scope, page), do: read(:builds, identity, scope, page)

  defp read(kind, identity, scope, page) do
    with :ok <- Policy.request(identity),
         {:ok, input} <- Input.new(kind, scope, page),
         do: Context.read(identity, input)
  end
end
