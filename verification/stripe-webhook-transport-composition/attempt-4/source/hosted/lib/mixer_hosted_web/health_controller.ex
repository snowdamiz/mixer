defmodule MixerHostedWeb.HealthController do
  use Phoenix.Controller, formats: [:json]

  def live(conn, _params) do
    conn
    |> put_resp_header("cache-control", "no-store")
    |> json(%{status: "alive"})
  end
end
