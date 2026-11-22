defmodule MixerHostedWeb.L07LostAck do
  @moduledoc false
  @behaviour Plug
  import Plug.Conn

  @impl true
  def init(options), do: options

  @impl true
  def call(%Plug.Conn{method: "POST", scheme: :http, host: "127.0.0.1"} = conn, _options) do
    expected_host = "127.0.0.1:#{conn.port}"

    if get_req_header(conn, "host") == [expected_host] and
         String.ends_with?(conn.request_path, "/ios/native-development-attestation") do
      register_before_send(conn, &interrupt/1)
    else
      conn
    end
  end

  def call(conn, _options), do: conn

  defp interrupt(conn) do
    root = System.fetch_env!("PAIR25_RUN")
    arm = Path.join(root, "v74.lost-ack-arm.json")
    target = conn.request_path <> "?" <> conn.query_string
    {status, body} =
      if System.get_env("L07_V74_PREFLIGHT") == "1",
        do: {404, %{"error" => %{"code" => "not_found"}}},
        else: {201, %{"status" => "attached"}}

    with ^status <- conn.status,
         {:ok, ^body} <- conn.resp_body |> IO.iodata_to_binary() |> Jason.decode(),
         {:ok, raw} <- File.read(arm),
         %{"origin" => origin, "target" => ^target} <- Jason.decode!(raw),
         true <- origin == "http://127.0.0.1:#{conn.port}",
         {Bandit.Adapter, %Bandit.Adapter{transport: %Bandit.HTTP1.Socket{
           write_state: :unsent, socket: socket
         }}} <- conn.adapter,
         :ok <- File.rename(arm, Path.join(root, "v74.lost-ack-consumed.json")) do
      # The ordinary controller has returned from the writer transaction.
      # Shut down the write half before Bandit sends any status line or body.
      :ok = ThousandIsland.Socket.shutdown(socket, :write)
      evidence = Path.join(root, "v74.lost-ack-result.json")
      File.write!(evidence <> ".tmp", Jason.encode!(%{
        origin: origin, target: target, selectedHTTP: status, writeShutdown: true,
        adapterWriteState: "unsent"
      }), [:exclusive])
      File.rename!(evidence <> ".tmp", evidence)
      raise Bandit.TransportError, message: "L07 fixture suppressed one HTTP acknowledgement"
    else
      _ -> conn
    end
  end
end
