defmodule MixerHostedWeb.Router do
  use Phoenix.Router

  # This only reports process liveness. It neither queries PostgreSQL nor claims
  # that auth, workers, migrations, delivery, or a production service are ready.
  get("/health/live", MixerHostedWeb.HealthController, :live)
end
