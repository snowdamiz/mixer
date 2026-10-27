defmodule MixerHostedWeb.BrowserWorkspaceDispatcher.CaptureAdapter do
  @moduledoc false
  @behaviour Plug.Conn.Adapter

  @maximum_body_bytes 262_144

  def new, do: {__MODULE__, %{sends: 0}}

  @impl true
  def read_req_body(state, _options), do: {:ok, "", state}

  @impl true
  def send_resp(%{sends: 0} = state, status, headers, body) when map_size(state) == 1 do
    # Measure iodata before allocating its binary representation. Invalid iodata
    # and every unsupported response mode fail with the same fixed local reason.
    size = IO.iodata_length(body)

    if size > @maximum_body_bytes, do: unavailable!()
    body = IO.iodata_to_binary(body)
    {:ok, body, %{sends: 1, status: status, headers: headers, body: body}}
  rescue
    _ -> unavailable!()
  end

  def send_resp(_, _, _, _), do: unavailable!()

  @impl true
  def send_file(_, _, _, _, _, _), do: unavailable!()
  @impl true
  def send_chunked(_, _, _), do: unavailable!()
  @impl true
  def chunk(_, _), do: unavailable!()
  @impl true
  def upgrade(_, _, _), do: unavailable!()
  @impl true
  def inform(_, _, _), do: unavailable!()
  @impl true
  def push(_, _, _), do: unavailable!()
  @impl true
  def get_peer_data(_), do: %{address: {0, 0, 0, 0}, port: 0, ssl_cert: nil}
  @impl true
  def get_sock_data(_), do: %{address: {0, 0, 0, 0}, port: 0}
  @impl true
  def get_ssl_data(_), do: nil
  @impl true
  def get_http_protocol(_), do: :local_capture

  defp unavailable!, do: raise(ArgumentError, "local response unavailable")
end
