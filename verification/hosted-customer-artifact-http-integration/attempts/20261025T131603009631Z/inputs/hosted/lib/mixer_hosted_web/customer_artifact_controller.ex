defmodule MixerHostedWeb.CustomerArtifactController do
  @moduledoc """
  HTTP representations for already authenticated customer artifact operations.

  Production routes initialize with an operation atom and always use the real
  CustomerArtifacts facade. Keyword initialization is a trusted test composition
  seam; neither headers nor request parameters select a facade or a clock.
  """
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.CustomerArtifacts
  alias MixerHostedWeb.Plugs.CustomerArtifactRequest, as: Request

  @impl true
  def init(operation) when operation in [:upload, :read, :audit],
    do: %{operation: operation, facade: CustomerArtifacts, request: Request.init(operation)}

  def init(opts) when is_list(opts) do
    unless Keyword.keyword?(opts) and
             Enum.all?(Keyword.keys(opts), &(&1 in [:operation, :facade, :clock])) and
             length(Keyword.keys(opts)) == length(Enum.uniq(Keyword.keys(opts))) do
      raise ArgumentError, "invalid customer artifact controller options"
    end

    operation = Keyword.fetch!(opts, :operation)
    facade = Keyword.fetch!(opts, :facade)

    unless is_atom(facade) and Code.ensure_loaded?(facade) and
             Enum.all?([upload_at: 6, read: 4, audit: 5], fn {f, a} ->
               function_exported?(facade, f, a)
             end),
           do: raise(ArgumentError, "invalid customer artifact facade")

    request = opts |> Keyword.take([:operation, :clock]) |> Request.init()
    %{operation: operation, facade: facade, request: request}
  end

  def init(_), do: raise(ArgumentError, "invalid customer artifact controller operation")

  @impl true
  def call(conn, %{operation: operation, facade: facade, request: options}) do
    conn = Request.call(conn, options)
    if conn.halted, do: conn, else: dispatch(conn, operation, facade)
  end

  defp dispatch(conn, operation, facade) do
    request = conn.assigns.customer_artifact_request
    identity = conn.assigns.verified_identity

    result =
      case operation do
        :upload ->
          facade.upload_at(
            identity,
            request.route,
            request.digest,
            request.key,
            request.bytes,
            request.metadata
          )

        :read ->
          facade.read(identity, request.route, request.digest, request.metadata)

        :audit ->
          facade.audit(
            identity,
            request.route,
            request.page.after,
            request.page.limit,
            request.metadata
          )
      end

    respond(conn, operation, request.digest, result)
  rescue
    _ -> Request.reject(conn, :storage_unavailable)
  catch
    :throw, _ -> Request.reject(conn, :storage_unavailable)
  end

  defp respond(conn, :upload, digest, {:ok, %{status: status, manifest_sha256: digest}})
       when status in [200, 201],
       do: json(conn, status, %{artifact_sha256: digest, immutable: true})

  defp respond(conn, :read, digest, {:ok, %{manifest_sha256: digest, envelope_bytes: bytes}})
       when is_binary(bytes),
       do: conn |> put_resp_content_type("application/json") |> send_resp(200, bytes)

  defp respond(conn, :audit, _, {:ok, %{events: events, next_after_sequence: next}})
       when is_list(events) and is_integer(next),
       do: json(conn, 200, %{events: events, next: next})

  defp respond(conn, _, _, {:error, reason}), do: Request.reject(conn, reason)
  defp respond(conn, _, _, _), do: Request.reject(conn, :storage_unavailable)

  defp json(conn, status, value),
    do:
      conn |> put_resp_content_type("application/json") |> send_resp(status, Jason.encode!(value))
end
