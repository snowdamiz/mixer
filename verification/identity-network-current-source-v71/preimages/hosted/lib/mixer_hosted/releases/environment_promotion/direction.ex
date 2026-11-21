defmodule MixerHosted.Releases.EnvironmentPromotion.Direction do
  @moduledoc """
  One ordered source-to-destination route from operator provisioning.

  Resolve this input from trusted configuration. Each side carries both
  enrolled platform targets, including channel, installed host policy and
  target-scoped roots with raw Ed25519 public keys.
  """

  alias MixerHosted.Releases.EnvironmentPromotion.Command

  defmodule Enrollment do
    @moduledoc "An exact provisioned target and its v3 verification policy."

    alias MixerHosted.Releases.Target

    @enforce_keys [:target, :host, :roots]
    defstruct @enforce_keys

    @type t :: %__MODULE__{
            target: Target.t(),
            host: map(),
            roots: [map()]
          }
  end

  @enforce_keys [:source, :destination]
  defstruct @enforce_keys

  @type t :: %__MODULE__{
          source: Command.platforms(Enrollment.t()),
          destination: Command.platforms(Enrollment.t())
        }
end
