defmodule MixerHosted.CustomerBuilds do
  @moduledoc "Private customer build operations with server-owned authorization and storage."
  alias MixerHosted.CustomerBuilds.{Context, Policy, Selection}

  def inputs(identity, input), do: MixerHosted.CustomerBuilds.Inputs.run(identity, input)

  def create(identity, input, key),
    do: MixerHosted.CustomerBuilds.Create.run(identity, input, key)

  @doc "Attaches a verified local iOS development envelope under dedicated build write authority."
  def attach_native_development_attestation(identity, selection, envelope),
    do: MixerHosted.CustomerBuilds.AttachNativeAttestation.run(identity, selection, envelope)

  def read(identity, selection, kind \\ nil) do
    with :ok <- Policy.request(identity),
         {:ok, s} <- Selection.new(selection),
         do: Context.read(identity, s, kind)
  end
end
