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

  defmodule Begin do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [
      :lease,
      :source,
      :context,
      :sealed,
      :attempt_context,
      :attempt_sealed,
      :state,
      :nonce,
      :verifier,
      :csrf,
      :url
    ]
    defstruct @enforce_keys
  end

  defmodule Authorization do
    @moduledoc "Private begin-login URL only; this never proves an authenticated identity."
    @derive {Inspect, only: []}
    @enforce_keys [:url, :expires_at]
    defstruct @enforce_keys
  end

  defmodule Publication do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:checked_wall, :expires_at, :value]
    defstruct @enforce_keys
  end

  defmodule Preauth do
    @moduledoc "Private preauthentication data only. This never proves an authenticated identity."
    @derive {Inspect, only: []}
    @enforce_keys [:cookie, :csrf, :expires_at, :source]
    defstruct @enforce_keys
  end
end
