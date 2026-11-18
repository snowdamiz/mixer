defmodule MixerHosted.Builds.ProcessorNotifier do
  @moduledoc "Admitted PostgreSQL transport for the fixed builds processor profile."
  @behaviour Oban.Notifier
  alias Postgrex.SimpleConnection, as: Simple
  @channels [:insert, :leader, :signal, :sonar]

  @impl Oban.Notifier
  def start_link(opts) do
    conf = Keyword.fetch!(opts, :conf)
    true = conf.name == Oban and conf.prefix == "public" and conf.repo == MixerHosted.Repo

    connection =
      conf
      |> Oban.Repo.config()
      |> Keyword.delete(:after_connect)
      |> Keyword.put(:name, Keyword.fetch!(opts, :name))
      |> Keyword.put(:auto_reconnect, true)
      |> Keyword.put(:sync_connect, false)

    Simple.start_link(
      __MODULE__.Connection,
      %{conf: conf, phase: :disconnected, generation: 0, backend_pid: nil},
      connection
    )
  end

  @impl Oban.Notifier
  def listen(server, channels), do: subscription(server, channels)
  @impl Oban.Notifier
  def unlisten(server, channels), do: subscription(server, channels)

  defp subscription(server, channels) do
    if is_list(channels) and Enum.all?(channels, &(&1 in @channels)),
      do: Simple.call(server, :ready),
      else: {:error, ArgumentError.exception("unsupported processor channel")}
  end

  @impl Oban.Notifier
  def notify(server, channel, payload) when channel in @channels do
    case Simple.call(server, :publish_context) do
      {:ok, conf} ->
        # This call executes in the original caller and its checked-out transaction.
        case Oban.Repo.query(
               conf,
               "SELECT pg_notify($1, payload) FROM json_array_elements_text($2::json) AS payload",
               ["public.oban_#{channel}", payload]
             ) do
          {:ok, _} -> :ok
          {:error, error} -> {:error, error}
        end

      {:error, _} = error ->
        error
    end
  end

  def notify(_server, _channel, _payload),
    do: {:error, ArgumentError.exception("unsupported processor channel")}
end

defmodule MixerHosted.Builds.ProcessorNotifier.Connection do
  @moduledoc false
  @behaviour Postgrex.SimpleConnection
  alias MixerHosted.Builds.ProcessorAdmission
  alias Postgrex.SimpleConnection, as: Simple
  @channels [:insert, :leader, :signal, :sonar]
  @listens ~s(LISTEN "public.oban_insert"; LISTEN "public.oban_leader"; LISTEN "public.oban_signal"; LISTEN "public.oban_sonar";)
  @impl true
  def notify(full_channel, payload, %{phase: :ready} = state) when is_binary(full_channel) do
    case Enum.find(@channels, &(full_channel == "public.oban_#{&1}")) do
      nil -> :ok
      channel -> Oban.Notifier.relay(state.conf, channel, payload)
    end
  end

  def notify(full_channel, _payload, _state) when is_binary(full_channel), do: :ok
  @impl Postgrex.SimpleConnection
  def init(state), do: {:ok, state}

  @impl Postgrex.SimpleConnection
  def handle_connect(state) do
    state = %{state | phase: :snapshot, generation: state.generation + 1, backend_pid: nil}
    {:query, "SET search_path=pg_catalog; " <> ProcessorAdmission.snapshot_sql(), state}
  end

  @impl Postgrex.SimpleConnection
  def handle_disconnect(state) do
    {:noreply,
     %{state | phase: :disconnected, generation: state.generation + 1, backend_pid: nil}}
  end

  @impl Postgrex.SimpleConnection
  def handle_result(
        [%Postgrex.Result{command: :set}, %Postgrex.Result{rows: [[raw]]}],
        %{phase: :snapshot} = state
      ) do
    snapshot = ProcessorAdmission.decode!(raw)
    state = %{state | backend_pid: snapshot["backend_pid"]}

    try do
      :ok = ProcessorAdmission.validate!(snapshot)
      event(:admitted, state)
      send(self(), {:listen_admitted, state.generation})
      {:noreply, %{state | phase: :admitted}}
    rescue
      _error ->
        event(:refused, state)
        {:noreply, %{state | phase: :refused}}
    end
  end

  def handle_result(results, %{phase: :listening} = state) when is_list(results) do
    true =
      length(results) == 4 and Enum.all?(results, &match?(%Postgrex.Result{command: :listen}, &1))

    event(:ready, state)
    {:noreply, %{state | phase: :ready}}
  end

  def handle_result(_error, state) do
    event(:refused, state)
    {:noreply, %{state | phase: :refused}}
  end

  @impl Postgrex.SimpleConnection
  def handle_info(
        {:listen_admitted, generation},
        %{generation: generation, phase: :admitted} = state
      ),
      do: {:query, @listens, %{state | phase: :listening}}

  def handle_info(_message, state), do: {:noreply, state}

  @impl Postgrex.SimpleConnection
  def handle_call(:ready, from, state) do
    Simple.reply(from, if(state.phase == :ready, do: :ok, else: unavailable()))
    {:noreply, state}
  end

  def handle_call(:publish_context, from, state) do
    Simple.reply(from, if(state.phase == :ready, do: {:ok, state.conf}, else: unavailable()))
    {:noreply, state}
  end

  def handle_call(:admission_status, from, state) do
    Simple.reply(from, Map.take(state, [:phase, :backend_pid, :generation]))
    {:noreply, state}
  end

  def handle_call(_message, from, state) do
    Simple.reply(
      from,
      {:error, ArgumentError.exception("unsupported processor notifier operation")}
    )

    {:noreply, state}
  end

  defp unavailable,
    do: {:error, RuntimeError.exception("processor notifier is not admitted and ready")}

  defp event(phase, state),
    do:
      :telemetry.execute(
        [:mixer_hosted, :processor_notifier, phase],
        %{},
        Map.take(state, [:backend_pid, :generation])
      )
end
