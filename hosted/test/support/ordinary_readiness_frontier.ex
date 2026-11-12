defmodule MixerHosted.Test.OrdinaryReadinessFrontier do
  @moduledoc false
  @test MixerHosted.BrowserAuth.OrdinaryConsoleCatalogNavigationCookiePGJoinTest
  @table __MODULE__
  @budget {__MODULE__, :budget}
  @cases %{
    "test ordinary_console_catalog_navigation_cookie_pg_join": 1,
    "test ordinary disabled endpoint serves health and bearer but no browser owners or cookies": 2,
    "test processor and malformed installations refuse before any children; configured production stays closed": 3,
    "test ordinary mount preserves raw refusals and passes nonowned connections unchanged": 4,
    "test actual permanent child termination tears down browser siblings without restarting the temporary group": 5,
    "test runtime startup refusal unwinds lifecycle provider and ordinary siblings before Endpoint": 6,
    "test external Repo replacement cannot renew the retained owner or its old lease": 7,
    "test expired lease and unknown outcome remain latched until explicit application restart": 8,
    "test provider ticket retains PID and generation fences across whole-Application restart": 9
  }

  def begin!(@test) do
    :absent = :persistent_term.get(@budget, :absent)
    :persistent_term.put(@budget, :atomics.new(2, signed: false))
    ExUnit.Callbacks.on_exit(fn -> :persistent_term.erase(@budget) end)
    :ok
  end

  def open!(%{module: @test, test: test}) do
    :undefined = :ets.info(@table)
    @table = :ets.new(@table, [:named_table, :public, :set])
    true = :ets.insert(@table, {:active, Map.fetch!(@cases, test)})
    :ok
  end

  # No observer process, links, timers, SQL, values, messages or supplied PID.
  # The test owns its ETS activation; automatic ETS retirement ends activation.
  def record(stage, class, stack) do
    if self() === Process.whereis(MixerHosted.BrowserAuth.RuntimeOwner) do
      case :ets.lookup(@table, :active) do
        [{:active, case_number}] -> emit(case_number, stage, class, stack)
        _ -> :ok
      end
    end
    :ok
  rescue
    _ -> :ok
  catch
    _, _ -> :ok
  end

  defp emit(case_number, stage, class, stack) do
    budget = :persistent_term.get(@budget)
    if :atomics.add_get(budget, 1, 1) <= 64 do
      frames = stack |> Enum.filter(fn {module, _function, _arity_or_args, _location} ->
        module in [MixerHosted.BrowserAuth.RuntimeOwner, MixerHosted.BrowserAuth.Store,
          MixerHosted.BrowserAuth.ActiveCatalog, MixerHosted.BrowserAuth.RelationCatalog,
          MixerHosted.BrowserAuth.BuildCatalogAdmission]
      end) |> Enum.take(2) |> Enum.map(fn {_module, function, _arity_or_args, location} ->
        [location |> Keyword.get(:file, ~c"unknown") |> to_string() |> Path.basename(),
          Atom.to_string(function) |> String.slice(0, 32), Keyword.get(location, :line, 0)]
      end)
      # Never format exceptions, reasons, frame arguments, SQL or process state.
      class = if is_boolean(class), do: class,
        else: class |> Atom.to_string() |> String.replace_prefix("Elixir.", "") |> String.slice(0, 64)
      line = "R1478 " <> Jason.encode!(%{c: case_number, s: stage, k: class, f: frames}) <> "\n"
      if :atomics.add_get(budget, 2, byte_size(line)) <= 8192, do: IO.write(line)
    end
    :ok
  end
end
