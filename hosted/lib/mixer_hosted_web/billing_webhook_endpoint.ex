defmodule MixerHostedWeb.BillingWebhookEndpoint do
  @moduledoc """
  Dedicated private webhook entrypoint; never compose into the ordinary API BEAM.

  Explicit startup uses the frozen private transport profile. Trusted deployment
  code supplies :billing_webhook configuration with endpoint_id, account,
  livemode, secrets and a real reconciliation worker. No default worker exists.
  Customer-to-tenant binding belongs to that worker's trusted provider lookup.
  """
  @behaviour Plug
  alias MixerHosted.Billing.WebhookTransport

  def start_link do
    with {:ok, _config} <- configuration(),
         do: WebhookTransport.start_link(__MODULE__)
  end

  @doc false
  def configuration do
    case Application.get_env(:mixer_hosted, :billing_webhook) do
      %{endpoint_id: endpoint, account: account, livemode: mode, secrets: secrets, worker: worker} =
          config
      when is_binary(endpoint) and byte_size(endpoint) in 1..255 and
             (is_nil(account) or is_binary(account)) and is_boolean(mode) and is_atom(worker) ->
        if secrets?(secrets) and Code.ensure_loaded?(worker) and
             function_exported?(worker, :new, 1) and function_exported?(worker, :perform, 1),
           do: {:ok, config},
           else: {:error, :billing_disabled}

      _ ->
        {:error, :billing_disabled}
    end
  end

  defp secrets?([one]), do: secret?(one)
  defp secrets?([one, two]), do: secret?(one) and secret?(two) and one != two
  defp secrets?(_), do: false
  defp secret?(value), do: is_binary(value) and byte_size(value) in 16..256

  def init([]), do: []

  def call(conn, []) do
    try do
      MixerHostedWeb.BillingWebhookRouter.call(conn, [])
    after
      WebhookTransport.dispose()
    end
  end
end

defmodule MixerHostedWeb.BillingWebhookRouter do
  use Phoenix.Router
  post("/api/v1/webhooks/stripe", MixerHostedWeb.BillingWebhookController, :accept)
end
