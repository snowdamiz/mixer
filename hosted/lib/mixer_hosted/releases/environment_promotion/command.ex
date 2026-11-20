defmodule MixerHosted.Releases.EnvironmentPromotion.Command do
  @moduledoc """
  Signed inputs for one dual-platform environment promotion.

  The transaction supplies source evidence from the recorded publications
  and their stored artifacts. Destination evidence contains the independently
  signed destination documents and the exact payload bytes to be bound.
  """

  defmodule Evidence do
    @moduledoc "The original standalone v3 documents and raw artifact payload."

    @enforce_keys [:signed_manifest_bytes, :signed_assignment_bytes, :payload]
    defstruct @enforce_keys

    @type t :: %__MODULE__{
            signed_manifest_bytes: binary(),
            signed_assignment_bytes: binary(),
            payload: binary()
          }
  end

  defmodule SourcePublication do
    @moduledoc "A scoped ledger row's sequence and artifact digest together with its stored evidence."

    @enforce_keys [:sequence, :artifact_sha256, :evidence]
    defstruct @enforce_keys

    @type t :: %__MODULE__{
            sequence: pos_integer(),
            artifact_sha256: String.t(),
            evidence: Evidence.t()
          }
  end

  @enforce_keys [:source, :destination]
  defstruct @enforce_keys

  @type platforms(entry) :: %{ios: entry, android: entry}
  @type t :: %__MODULE__{
          source: platforms(SourcePublication.t()),
          destination: platforms(Evidence.t())
        }
end
