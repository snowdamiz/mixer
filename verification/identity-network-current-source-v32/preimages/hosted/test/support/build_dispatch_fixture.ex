defmodule MixerHosted.Test.BuildDispatchFixture do
  @moduledoc false
  @behaviour MixerHosted.Builds.Dispatch
  use GenServer
  alias MixerHosted.Builds.Dispatch.Observation

  def start_link(_), do: GenServer.start_link(__MODULE__, nil, name: __MODULE__)
  def reset, do: GenServer.call(__MODULE__, :reset)
  def mode(callback, mode), do: GenServer.call(__MODULE__, {:mode, callback, mode})
  def snapshot, do: GenServer.call(__MODULE__, :snapshot)
  def complete(id, result), do: GenServer.call(__MODULE__, {:complete, id, result})
  @impl true
  def query(request), do: call(:query, request)
  @impl true
  def ensure_started(request), do: call(:ensure_started, request)
  @impl true
  def stop(request), do: call(:stop, request)

  defp call(callback, request) do
    # Records DB visibility in the transport process, outside the coordinator transaction.
    {:ok, current} =
      MixerHosted.Builds.Storage.read(
        Map.take(request.ref, [
          :organization_id,
          :project_id,
          :application_id,
          :build_id,
          :platform
        ])
      )

    visibility = %{
      state: current.build.state,
      revision: current.record.revision,
      transaction?: MixerHosted.Repo.in_transaction?()
    }

    {reply, mode} = GenServer.call(__MODULE__, {:call, callback, request, visibility})

    case mode do
      :raise_after ->
        raise "synthetic callback crash after durable modeled effect"

      :timeout_after ->
        receive do
          :never -> reply
        end

      {:block_after, observer} ->
        send(observer, {:dispatch_blocked, self()})

        receive do
          :resume -> reply
        end

      :wrong_operation ->
        {:ok, %{elem(reply, 1) | operation_id: String.duplicate("0", 64)}}

      :wrong_ref ->
        {:ok, %{elem(reply, 1) | ref: %{request.ref | fence: request.ref.fence + 1}}}

      :invalid_result ->
        {:ok, %{elem(reply, 1) | status: {:completed, %{outcome: :succeeded}}}}

      _ ->
        reply
    end
  end

  @impl true
  def init(_), do: {:ok, fresh()}
  @impl true
  def handle_call(:reset, _, _), do: {:reply, :ok, fresh()}
  def handle_call(:snapshot, _, state), do: {:reply, state, state}

  def handle_call({:mode, callback, mode}, _, state),
    do: {:reply, :ok, %{state | modes: Map.put(state.modes, callback, mode)}}

  def handle_call({:complete, id, result}, _, state) do
    operations = Map.update!(state.operations, id, &%{&1 | status: {:completed, result}})
    {:reply, :ok, %{state | operations: operations}}
  end

  def handle_call({:call, callback, request, visibility}, _, state) do
    {mode, modes} = Map.pop(state.modes, callback, :normal)
    call = %{callback: callback, request: request, visibility: visibility}
    state = %{state | calls: state.calls ++ [call], modes: modes}

    if mode == :unavailable do
      {:reply, {{:error, :unavailable}, :normal}, state}
    else
      {reply, state} = operate(callback, request, state)
      {:reply, {reply, mode}, state}
    end
  end

  defp operate(callback, request, state) do
    previous = Map.get(state.operations, request.operation_id)
    version = {request.guard.epoch, request.guard.revision}

    cond do
      DateTime.compare(request.guard.expires_at, DateTime.utc_now()) != :gt ->
        {{:error, :stale}, state}

      previous != nil and
          (version < previous.version or previous.ref != request.ref or
             previous.spec != request.spec or previous.deadline_ms != request.deadline_ms) ->
        {{:error, :stale}, state}

      true ->
        {status, creations} =
          case {callback, previous} do
            {:query, nil} -> {:absent, 0}
            {:ensure_started, nil} -> {:running, 1}
            {:stop, nil} -> {{:stopped, String.duplicate("d", 64)}, 0}
            {:stop, %{status: :running}} -> {{:stopped, String.duplicate("d", 64)}, 0}
            {_, existing} -> {existing.status, 0}
          end

        operations =
          if status == :absent do
            state.operations
          else
            Map.put(state.operations, request.operation_id, %{
              ref: request.ref,
              spec: request.spec,
              deadline_ms: request.deadline_ms,
              version: version,
              status: status
            })
          end

        observation = %Observation{
          operation_id: request.operation_id,
          ref: request.ref,
          status: status
        }

        {{:ok, observation},
         %{state | operations: operations, creations: state.creations + creations}}
    end
  end

  defp fresh, do: %{operations: %{}, calls: [], creations: 0, modes: %{}}
end
