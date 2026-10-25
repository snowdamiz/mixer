defmodule MixerHosted.BrowserAuth.PreauthDraft do
  @moduledoc false

  defmodule Lease do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:owner, :reference, :caller, :generation, :deadline, :started_at, :runtime]
    defstruct @enforce_keys
  end

  defmodule Bootstrap do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :context, :sealed, :cookie, :csrf, :expires_at]
    defstruct @enforce_keys
  end

  defmodule Load do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :cookie_digest]
    defstruct @enforce_keys
  end

  defmodule Preauth do
    @moduledoc "Private preauthentication data only. This never proves an authenticated identity."
    @derive {Inspect, only: []}
    @enforce_keys [:cookie, :csrf, :expires_at, :source]
    defstruct @enforce_keys
  end
end
