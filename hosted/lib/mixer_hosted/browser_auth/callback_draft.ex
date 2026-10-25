defmodule MixerHosted.BrowserAuth.CallbackDraft do
  @moduledoc false

  defmodule Discovery do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :cookie_digest, :state_digest]
    defstruct @enforce_keys
  end

  defmodule Claim do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :source, :verifier, :claim_secret, :claim_expires_at]
    defstruct @enforce_keys
  end

  defmodule Reject do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :source]
    defstruct @enforce_keys
  end
end
