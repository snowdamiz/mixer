defmodule WorkerV2Support do
  import ExUnit.Assertions
  alias MixerHosted.Builds.{WorkerTransport, WorkerHTTPAdapter}
  alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}
  @marker {WorkerTransport, :ownership_v2}

  def eventually(fun, n \\ 300)

  def eventually(fun, n) when n > 0 do
    if fun.(),
      do: :ok,
      else:
        (
          Process.sleep(5)
          eventually(fun, n - 1)
        )
  end

  def eventually(_, 0), do: flunk("owned V2 resource failed to retire")
  def alive?(pid), do: is_pid(pid) and Process.alive?(pid)

  def resume(pid) do
    :erlang.resume_process(pid)
  catch
    _, _ -> :ok
  end

  def marker do
    {:present, :persistent_term.get(@marker)}
  rescue
    ArgumentError -> :missing
  end

  def retired?(s),
    do:
      not alive?(s.worker) and (s.raw == nil or Port.info(s.raw) == nil) and
        not alive?(s.connection)

  def fixture(material, mode \\ :normal) do
    {:ok, fixture} = WorkerTLSFixture.start_link({material, mode})
    Process.unlink(fixture)

    ExUnit.Callbacks.on_exit(fn ->
      if owner = Process.whereis(WorkerTransport) do
        try do
          GenServer.stop(owner, :normal, 1_000)
        catch
          _, _ -> Process.exit(owner, :kill)
        end
      end

      if guard = Process.whereis(WorkerTransport.RoleGuard) do
        try do
          state = :sys.get_state(guard, 200)

          Enum.each(Map.keys(state.flights), fn flight ->
            resume(flight)
            send(flight, :deadline)
          end)

          eventually(fn -> Enum.all?(Map.keys(state.flights), &(not alive?(&1))) end)
        catch
          _, _ -> :ok
        end

        if alive?(guard), do: Process.exit(guard, :kill)
      end

      if alive?(fixture) do
        eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
        info = WorkerTLSFixture.info(fixture)
        assert info.accepted == info.closed
        GenServer.stop(fixture)
      end
    end)

    fixture
  end

  def start(material, fixture, barriers \\ %{}) do
    result =
      WorkerTransport.start_fixture(
        WorkerData.config(material.ca),
        {127, 0, 0, 1},
        WorkerTLSFixture.info(fixture).port,
        barriers
      )

    case result do
      {:ok, owner} -> Process.unlink(owner)
      _ -> :ok
    end

    result
  end

  def starter(material, fixture, barriers) do
    recipient = self()

    spawn_monitor(fn ->
      Process.flag(:trap_exit, true)
      result = start(material, fixture, barriers)
      send(recipient, {:worker_v2_start_result, self(), result})
    end)
  end

  def request do
    receive do
      {:worker_fixture_request, handler} -> handler
    after
      2_000 -> flunk("TLS request was not observed")
    end
  end

  def flight(owner) do
    [flight] = Map.keys(:sys.get_state(owner).flights)
    {flight, :sys.get_state(flight)}
  end

  def clean(fixture, owner) do
    eventually(fn -> map_size(:sys.get_state(owner).flights) == 0 end)
    eventually(fn -> map_size(:sys.get_state(WorkerTransport.RoleGuard).flights) == 0 end)
    eventually(fn -> MapSet.size(WorkerTLSFixture.info(fixture).active) == 0 end)
  end

  def stop_clean(fixture, owner) do
    clean(fixture, owner)
    GenServer.stop(owner)

    eventually(fn ->
      Process.whereis(WorkerTransport.RoleGuard) == nil and marker() == :missing
    end)
  end

  def deny_replacement(material, fixture) do
    assert {:error, :unavailable} = start(material, fixture)
    assert {:error, :unavailable} = WorkerHTTPAdapter.query(WorkerData.request())
  end

  def note(name, value) do
    path = Path.join([__DIR__, "..", "..", "..", name <> ".json"]) |> Path.expand()
    File.write!(path, Jason.encode!(value, pretty: true) <> "\n")
  end
end

defmodule WorkerV2Case do
  use ExUnit.CaseTemplate

  using do
    quote do
      alias MixerHosted.Builds.{Dispatch, WorkerHTTPAdapter, WorkerTransport}
      alias MixerHosted.Test.{WorkerData, WorkerTLSFixture}
      import WorkerV2Support
    end
  end

  setup_all do
    material = MixerHosted.Test.WorkerTLSFixture.material()
    assert material.key_dir_removed
    {:ok, material: material}
  end
end
