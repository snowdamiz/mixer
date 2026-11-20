defmodule MixerHosted.CustomerArtifacts.UploadRepo do
  @moduledoc false
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end
