defmodule MixerHosted.Billing.SubscriptionReadTransport do
  @moduledoc """
  Private, unselected server-owned Stripe subscription GET. No worker behaviour,
  application configuration, persistence or entitlement effects are supplied.
  Only trusted server setup may construct this handle or resolve its secret.
  """
  alias MixerHosted.Billing.ObservedSubscription
  alias MixerHosted.Identity.{BoundedTCP, DNSResolver, HTTPWireGuard}

  @origin "https://api.stripe.com"
  @version "2026-10-28.endive"
  @fields ~w(origin api_version account livemode secret_ref ca_roots resolvers connect_ms read_ms deadline_ms)a
  @derive {Inspect, only: []}
  @enforce_keys [:config, :secret_resolver]
  defstruct @enforce_keys
  @opaque t :: %__MODULE__{config: map(), secret_resolver: (binary() -> {:ok, binary()} | :error)}

  @spec new(map(), function()) :: {:ok, t()} | {:error, :configuration_rejected}
  def new(config, secret_resolver) when is_map(config) and is_function(secret_resolver, 1) do
    with true <- Enum.sort(Map.keys(config)) == Enum.sort(@fields),
         true <- config.origin === @origin and config.api_version === @version,
         true <- ObservedSubscription.id?(config.account, "acct_"),
         true <- is_boolean(config.livemode),
         true <- is_binary(config.secret_ref) and byte_size(config.secret_ref) in 1..128,
         true <- Regex.match?(~r/\A[A-Za-z0-9_:\/-]+\z/, config.secret_ref),
         true <- is_list(config.ca_roots) and length(config.ca_roots) in 1..256,
         true <- Enum.all?(config.ca_roots, &(is_binary(&1) and byte_size(&1) in 1..65_536)),
         true <- is_list(config.resolvers) and length(config.resolvers) in 1..4,
         true <- Enum.all?(config.resolvers, &resolver?/1),
         true <-
           Enum.all?(
             [config.connect_ms, config.read_ms, config.deadline_ms],
             &(is_integer(&1) and &1 in 1..5_000)
           ),
         true <- config.connect_ms <= config.deadline_ms and config.read_ms <= config.deadline_ms do
      {:ok, %__MODULE__{config: config, secret_resolver: secret_resolver}}
    else
      _ -> {:error, :configuration_rejected}
    end
  rescue
    _ -> {:error, :configuration_rejected}
  end

  def new(_, _), do: {:error, :configuration_rejected}

  defp resolver?({ip, port}) when is_tuple(ip) and is_integer(port) and port in 1..65_535 do
    :inet.is_ip_address(ip)
  end

  defp resolver?(_), do: false

  @spec read(t(), binary(), binary()) :: {:ok, ObservedSubscription.t()} | {:error, atom()}
  def read(%__MODULE__{config: c} = handle, subscription_id, customer_id) do
    deadline = now() + c.deadline_ms

    with :ok <- scope(subscription_id, customer_id),
         {:ok, ip} <- DNSResolver.resolve("api.stripe.com", c.resolvers, deadline) do
      connect(handle, subscription_id, customer_id, ip, 443, deadline)
    end
  end

  def read(_, _, _), do: {:error, :scope_rejected}

  # Compile-time fixture seam changes destination only, never URL, SNI, hostname,
  # certificate validation, request/decoder code or response policy.
  if Mix.env() == :test do
    def read_fixture(
          %__MODULE__{config: c} = handle,
          subscription_id,
          customer_id,
          {127, 0, 0, 1} = ip,
          port
        )
        when is_integer(port) and port in 1..65_535 do
      with :ok <- scope(subscription_id, customer_id),
           do: connect(handle, subscription_id, customer_id, ip, port, now() + c.deadline_ms)
    end
  end

  defp scope(subscription, customer) do
    if ObservedSubscription.id?(subscription, "sub_") and
         ObservedSubscription.id?(customer, "cus_"), do: :ok, else: {:error, :scope_rejected}
  end

  defp connect(handle, subscription, customer, ip, port, deadline) do
    BoundedTCP.with_watchdog(nil, deadline, fn ->
      do_connect(handle, subscription, customer, ip, port, deadline)
    end)
  rescue
    _ -> {:error, :transport_rejected}
  catch
    _, _ -> {:error, :transport_rejected}
  end

  defp do_connect(
         %{config: c, secret_resolver: resolve},
         subscription,
         customer,
         ip,
         port,
         deadline
       ) do
    # Resolution is trusted server code. No secret or raw network error is logged,
    # returned, attached to an exception, or retained in an observation.
    with {:ok, token} <- resolve_secret(resolve, c.secret_ref, deadline),
         true <- is_binary(token) and byte_size(token) in 1..512,
         true <- Regex.match?(~r/\A[A-Za-z0-9_\-]+\z/, token),
         true <- remaining(deadline) > 0 do
      opts = [
        hostname: "api.stripe.com",
        protocols: [:http1],
        mode: :passive,
        max_header_list_size: 10_240,
        transport_opts: [
          cb_info: {BoundedTCP, :tcp, :tcp_closed, :tcp_error, :tcp_passive},
          verify: :verify_peer,
          cacerts: c.ca_roots,
          timeout: min(c.connect_ms, remaining(deadline)),
          send_timeout: min(c.read_ms, remaining(deadline)),
          send_timeout_close: true,
          versions: [:"tlsv1.2", :"tlsv1.3"],
          recbuf: 16_384,
          buffer: 16_384,
          inet4: tuple_size(ip) == 4,
          inet6: tuple_size(ip) == 8,
          max_handshake_size: 65_536
        ]
      ]

      with {:ok, conn} <- Mint.HTTP.connect(:https, ip, port, opts) do
        try do
          headers = [
            {"authorization", "Bearer " <> token},
            {"stripe-account", c.account},
            {"stripe-version", c.api_version},
            {"accept", "application/json"},
            {"accept-encoding", "identity"},
            {"connection", "close"}
          ]

          with true <- remaining(deadline) > 0,
               {:ok, {^ip, ^port}} <- :ssl.peername(Mint.HTTP.get_socket(conn)),
               {:ok, next, ref} <-
                 Mint.HTTP.request(
                   conn,
                   "GET",
                   "/v1/subscriptions/" <> URI.encode_www_form(subscription),
                   headers,
                   nil
                 ),
               {:ok, body} <-
                 receive_loop(next, ref, HTTPWireGuard.new(), [], 0, deadline, c.read_ms),
               true <- remaining(deadline) > 0 do
            ObservedSubscription.decode(body, subscription, customer, c.livemode)
          else
            _ -> {:error, :response_rejected}
          end
        after
          Mint.HTTP.close(conn)
        end
      else
        _ -> {:error, :tls_rejected}
      end
    else
      _ -> {:error, :credential_unavailable}
    end
  end

  defp resolve_secret(resolve, reference, deadline) do
    task =
      Task.async(fn ->
        try do
          case resolve.(reference) do
            {:ok, token} when is_binary(token) -> {:ok, token}
            _ -> :error
          end
        rescue
          _ -> :error
        catch
          _, _ -> :error
        end
      end)

    case Task.yield(task, remaining(deadline)) || Task.shutdown(task, :brutal_kill) do
      {:ok, value} -> value
      _ -> :error
    end
  end

  defp receive_loop(conn, ref, wire, chunks, size, deadline, read_ms) do
    socket = Mint.HTTP.get_socket(conn)

    count =
      case wire.phase do
        {:length, n} when n > 0 -> min(n, 4_096)
        {:chunk, n} when n > 0 -> min(n, 4_096)
        :chunk_crlf -> 2
        _ -> 1
      end

    if remaining(deadline) > 0 do
      case :ssl.recv(socket, count, min(read_ms, remaining(deadline))) do
        {:ok, data} when byte_size(data) <= count ->
          with {:ok, wire} <- HTTPWireGuard.feed(wire, data),
               {:ok, conn, events} <- Mint.HTTP.stream(conn, {:ssl, socket, data}),
               {:ok, chunks, size, done} <- events(events, ref, chunks, size) do
            if done and wire.done,
              do: {:ok, IO.iodata_to_binary(Enum.reverse(chunks))},
              else: receive_loop(conn, ref, wire, chunks, size, deadline, read_ms)
          else
            _ -> {:error, :response_rejected}
          end

        {:error, :closed} ->
          with :close <- wire.phase,
               {:ok, _, events} <- Mint.HTTP.stream(conn, {:ssl_closed, socket}),
               {:ok, chunks, _, true} <- events(events, ref, chunks, size) do
            {:ok, IO.iodata_to_binary(Enum.reverse(chunks))}
          else
            _ -> {:error, :truncated_response}
          end

        _ ->
          {:error, :deadline_or_socket_error}
      end
    else
      {:error, :deadline}
    end
  end

  defp events(events, ref, chunks, size) do
    Enum.reduce_while(events, {:ok, chunks, size, false}, fn
      {:data, ^ref, data}, {:ok, chunks, size, done} when size + byte_size(data) <= 262_144 ->
        {:cont, {:ok, [:binary.copy(data) | chunks], size + byte_size(data), done}}

      {:done, ^ref}, {:ok, chunks, size, _} ->
        {:cont, {:ok, chunks, size, true}}

      {:status, ^ref, 200}, acc ->
        {:cont, acc}

      {:status, ^ref, status}, acc when status in 100..199 and status != 101 ->
        {:cont, acc}

      {:headers, ^ref, _}, acc ->
        {:cont, acc}

      _, _ ->
        {:halt, {:error, :response_rejected}}
    end)
  end

  defp now, do: System.monotonic_time(:millisecond)
  defp remaining(deadline), do: max(0, deadline - now())
end
