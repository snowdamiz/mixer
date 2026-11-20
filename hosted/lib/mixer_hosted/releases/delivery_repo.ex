defmodule MixerHosted.Releases.DeliveryRepo do
  @moduledoc false
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres, read_only: true
end
