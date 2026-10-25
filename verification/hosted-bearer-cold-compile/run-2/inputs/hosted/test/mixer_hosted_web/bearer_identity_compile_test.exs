defmodule MixerHostedWeb.BearerIdentityCompileTest do
  use ExUnit.Case, async: false

  alias MixerHostedWeb.Plugs.BearerIdentity

  defmodule InitProbe do
    def init(options) do
      send(:persistent_term.get({__MODULE__, :owner}), :initializing_bearer)
      BearerIdentity.init(options)
    end

    def call(conn, options), do: BearerIdentity.call(conn, options)
  end

  test "pipeline initialization waits for verifier and clock in a cold parallel compile" do
    key = {InitProbe, :owner}
    :persistent_term.put(key, self())

    directory =
      Path.join(System.tmp_dir!(), "mixer-bearer-compile-#{System.unique_integer([:positive])}")

    File.mkdir!(directory)

    modules = [
      MixerHostedWeb.ColdCompileVerifier,
      MixerHostedWeb.ColdCompileClock,
      MixerHostedWeb.ColdCompilePipeline
    ]

    try do
      for module <- modules, do: refute(Code.loaded?(module))

      verifier = Path.join(directory, "verifier.ex")
      clock = Path.join(directory, "clock.ex")
      pipeline = Path.join(directory, "pipeline.ex")

      for {path, module, definitions} <- [
            {verifier, Enum.at(modules, 0),
             "def authenticate(_, _), do: {:error, :unauthenticated}"},
            {clock, Enum.at(modules, 1), "def now, do: System.system_time(:second)"}
          ] do
        File.write!(path, """
        defmodule #{inspect(module)} do
          send(:persistent_term.get(#{inspect(key)}), {:dependency_waiting, self()})
          receive do
            :continue -> :ok
          after
            5_000 -> raise "compile test dependency was not released"
          end
          #{definitions}
        end
        """)
      end

      File.write!(pipeline, """
      send(:persistent_term.get(#{inspect(key)}), {:pipeline_waiting, self()})
      receive do
        :continue -> :ok
      after
        5_000 -> raise "compile test pipeline was not released"
      end
      defmodule MixerHostedWeb.ColdCompilePipeline do
        use Plug.Builder
        plug #{inspect(InitProbe)}, verifier: MixerHostedWeb.ColdCompileVerifier,
          clock: {MixerHostedWeb.ColdCompileClock, :now, []}
      end
      """)

      task =
        Task.async(fn ->
          Kernel.ParallelCompiler.compile([verifier, clock, pipeline], return_diagnostics: true)
        end)

      assert_receive {:dependency_waiting, first}, 5_000
      assert_receive {:dependency_waiting, second}, 5_000
      assert_receive {:pipeline_waiting, caller}, 5_000
      send(caller, :continue)
      assert_receive :initializing_bearer, 5_000

      # Keep both dependencies in compilation until the plug has attempted init.
      # A load-only check returns an error here; the compiler-aware check waits.
      premature = Task.yield(task, 100)
      send(first, :continue)
      send(second, :continue)
      result = premature || Task.yield(task, 5_000) || Task.shutdown(task, :brutal_kill)
      assert premature == nil
      assert {:ok, {:ok, _, []}} = result

      conn = apply(Enum.at(modules, 2), :call, [Plug.Test.conn(:get, "/protected"), []])
      assert conn.status == 401
      assert conn.halted
      refute Map.has_key?(conn.assigns, :verified_identity)
    after
      :persistent_term.erase(key)
      File.rm_rf!(directory)

      for module <- Enum.reverse(modules) do
        :code.purge(module)
        :code.delete(module)
      end
    end
  end
end
