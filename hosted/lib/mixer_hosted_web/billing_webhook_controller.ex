defmodule MixerHostedWeb.BillingWebhookController do
  use Phoenix.Controller, formats: [:json]
  alias MixerHosted.Billing.{WebhookInbox, WebhookTransport}
  alias MixerHosted.Repo

  def accept(conn, _params) do
    # A nested admission result is provisional until its caller commits. This
    # HTTP boundary owns the outer transaction and refuses ambient transactions.
    if Repo.in_transaction?() do
      respond(conn, 503, "unavailable")
    else
      case MixerHostedWeb.BillingWebhookEndpoint.configuration() do
        {:ok, config} ->
          capture_and_admit(conn, config)

        _ ->
          respond(conn, 503, "unavailable")
      end
    end
  end

  defp capture_and_admit(conn, config) do
    case WebhookTransport.capture(conn) do
      {:ok, captured, latest} ->
        case WebhookInbox.admit(captured, config) do
          {:ok, status, _} when status in [:accepted, :duplicate] ->
            respond(latest, 200, "accepted")

          {:error, :event_conflict} ->
            respond(latest, 409, "conflict")

          {:error, reason}
          when reason in [:invalid_signature, :invalid_event, :wrong_scope, :unsupported_event] ->
            respond(latest, 400, "rejected")

          {:error, _} ->
            respond(latest, 503, "unavailable")
        end

      {:error, _, latest} ->
        respond(latest, 400, "rejected")
    end
  end

  defp respond(conn, status, body) do
    conn
    |> Plug.Conn.put_resp_header("cache-control", "no-store")
    |> Plug.Conn.send_resp(status, body)
  end
end
