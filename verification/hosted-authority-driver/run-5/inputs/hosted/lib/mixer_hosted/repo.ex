defmodule MixerHosted.Repo do
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end
