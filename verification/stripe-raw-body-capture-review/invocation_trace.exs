defmodule CaptureReview.InvocationTrace do
  use GenServer
  def start_link, do: GenServer.start_link(__MODULE__, %{}, name: __MODULE__)
  def init(state), do: {:ok, state}
  def begin do
    :ok = GenServer.call(__MODULE__, {:begin, self()})
    1 = :erlang.trace(self(), true, [:call, {:tracer, Process.whereis(__MODULE__)}])
  end
  def finish do
    ref = :erlang.trace_delivered(self())
    receive do
      {:trace_delivered, pid, ^ref} when pid == self() -> :ok
    after
      1000 -> raise "signature invocation trace delivery failed"
    end
    1 = :erlang.trace(self(), false, [:call])
    GenServer.call(__MODULE__, {:take, self()})
  end
  def handle_call({:begin, pid}, _from, state), do: {:reply, :ok, Map.put(state, pid, [])}
  def handle_call({:take, pid}, _from, state), do: {:reply, Map.fetch!(state, pid) |> Enum.reverse(), Map.delete(state, pid)}
  def handle_info({:trace, pid, :call, {MixerHosted.Billing.WebhookSignature, :verify, [body, headers, secrets, now]}}, state) do
    item = %{bodySHA256: Base.encode16(:crypto.hash(:sha256, body), case: :lower), bodyBytes: byte_size(body), signatureValues: headers, secretCount: length(secrets), utc: now}
    {:noreply, Map.update!(state, pid, &[item | &1])}
  end
end

{:ok, _} = CaptureReview.InvocationTrace.start_link()
1 = :erlang.trace_pattern({MixerHosted.Billing.WebhookSignature, :verify, 4}, true, [:local])
