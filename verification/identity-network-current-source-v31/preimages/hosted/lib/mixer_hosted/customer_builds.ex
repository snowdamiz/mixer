defmodule MixerHosted.CustomerBuilds do
  @moduledoc "Private current build read. No authority, Repo or operation is request selectable."
  alias MixerHosted.CustomerBuilds.{Context, Policy, Selection}

  def inputs(identity, input), do: MixerHosted.CustomerBuilds.Inputs.run(identity, input)

  def create(identity, input, key),
    do: MixerHosted.CustomerBuilds.Create.run(identity, input, key)

  def read(identity, selection) do
    with :ok <- Policy.request(identity),
         {:ok, s} <- Selection.new(selection),
         do: Context.read(identity, s)
  end
end
