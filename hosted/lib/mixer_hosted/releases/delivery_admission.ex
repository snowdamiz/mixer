defmodule MixerHosted.Releases.DeliveryAdmission do
  @moduledoc false
  use GenServer, restart: :temporary

  alias MixerHosted.Releases.DeliveryRepo

  @sql """
  SELECT current_user = $1::text AND session_user = current_user AND rolcanlogin
    AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication)
  FROM pg_catalog.pg_roles WHERE rolname = current_user
  """

  def start_link(role), do: GenServer.start_link(__MODULE__, role)

  @impl true
  def init(role) do
    # Only startup waits for the first usable checkout. HTTP reads still fail fast.
    case DeliveryRepo.query(@sql, [role], timeout: 5_000, queue: true, log: false) do
      {:ok, %{rows: [[true]]}} -> :ignore
      _ -> {:stop, :local_release_delivery_admission_refused}
    end
  end
end
