defmodule MixerHosted.CustomerBuilds do
  @moduledoc "Private current build read. No authority, Repo or operation is request selectable."
  alias MixerHosted.CustomerBuilds.{Context, Policy, Selection}

  def read(identity, selection) do
    with :ok <- Policy.request(identity),
         {:ok, s} <- Selection.new(selection),
         do: Context.read(identity, s)
  end
end
