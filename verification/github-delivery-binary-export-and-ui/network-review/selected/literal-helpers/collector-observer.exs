
defmodule MixerIdentityNetworkCollector.Observer do
  use GenServer
  def init(_options) do
    {:ok, output} = File.open("/workspace/evidence/events.jsonl", [:write, :exclusive])
    {:ok, %{output: output, bytes: 0, total: 0, failures: 0, skipped: 0, excluded: 0, invalid: 0}}
  end
  defp record(value, state) do
    line = Jason.encode!(value) <> "\n"
    true = byte_size(line) < 1048576 and state.bytes + byte_size(line) < 2097152
    :ok = IO.binwrite(state.output, line)
    %{state | bytes: state.bytes + byte_size(line)}
  end
  def handle_cast({:suite_started, _}, state), do: {:noreply, record(%{event: "suite_started"}, state)}
  def handle_cast({:test_started, test}, state), do: {:noreply, record(%{event: "test_started", module: Atom.to_string(test.module), name: Atom.to_string(test.name)}, state)}
  def handle_cast({:test_finished, test}, state) do
    category = case test.state do nil -> nil; {kind, _} -> kind; _ -> :failed end
    state = %{state | total: state.total + 1}
    state = case category do
      nil -> state
      :skipped -> %{state | skipped: state.skipped + 1}
      :excluded -> %{state | excluded: state.excluded + 1}
      :invalid -> %{state | invalid: state.invalid + 1}
      _ -> %{state | failures: state.failures + 1}
    end
    {:noreply, record(%{event: "test_finished", module: Atom.to_string(test.module), name: Atom.to_string(test.name), state: if(test.state == nil, do: nil, else: inspect(test.state, limit: 100))}, state)}
  end
  def handle_cast({:suite_finished, _times}, state) do
    modules = for {module, path} <- :code.all_loaded() do
      path = if is_list(path), do: List.to_string(path), else: inspect(path)
      hash = if File.regular?(path), do: Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower), else: nil
      %{module: Atom.to_string(module), path: path, sha256: hash}
    end
    apps = for {app, _description, version} <- :application.loaded_applications(), do: %{application: Atom.to_string(app), version: to_string(version)}
    otp = Path.join([to_string(:code.root_dir()), "releases", to_string(:erlang.system_info(:otp_release)), "OTP_VERSION"])
    identity = %{modules: Enum.sort_by(modules, & &1.module), applications: Enum.sort_by(apps, & &1.application), elixir: System.version(), otp_patch: File.read!(otp) |> String.trim(), vm: to_string(:erlang.system_info(:system_version)), architecture: to_string(:erlang.system_info(:system_architecture)), crypto: inspect(:crypto.info_lib())}
    :ok = File.write!("/workspace/evidence/runtime.json", Jason.encode!(identity, pretty: true), [:exclusive])
    final = state |> Map.take([:total, :failures, :skipped, :excluded, :invalid]) |> Map.put(:event, "suite_finished")
    state = record(final, state)
    :ok = File.close(state.output)
    {:noreply, state}
  end
  def handle_cast(_event, state), do: {:noreply, state}
end
