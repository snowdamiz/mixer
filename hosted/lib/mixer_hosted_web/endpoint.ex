defmodule MixerHostedWeb.Endpoint do
  use Phoenix.Endpoint, otp_app: :mixer_hosted

  plug(Plug.RequestId)
  plug(MixerHostedWeb.BrowserLoginHTTP, :ordinary)
  plug(Plug.Head)
  plug(MixerHostedWeb.Router)
end
