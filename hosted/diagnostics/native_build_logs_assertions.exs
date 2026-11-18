defmodule MixerHosted.Diagnostics.NativeBuildLogsAssertions do
  @moduledoc """
  Assertions for a root-owned ordinary HTTP fixture. Pass a two-argument GET
  function taking the path and request headers. It must return status, headers,
  and body from the real Phoenix endpoint using OrdinaryBrowserStartupFixture.http/3.
  """
  import ExUnit.Assertions

  @path "/console-api/v1/build-logs"

  def assert_pending!(get, headers, selection) do
    assert_error(get.(path(selection), headers), 404, "not_found")
  end

  def assert_closed!(get, headers, selection, state, attempt) do
    url = path(selection)
    assert_error(get.(url, []), 401, "unauthenticated")
    assert_error(get.(url <> "&build_id=duplicate", headers), 400, "invalid_request")

    for key <- [:source_sha256, :toolchain_lock_sha256, :build_definition_sha256] do
      original = Map.fetch!(selection, key)
      changed = if original == String.duplicate("0", 64), do: "1", else: "0"
      other = Map.put(selection, key, String.duplicate(changed, 64))
      assert_error(get.(path(other), headers), 404, "not_found")
    end

    for key <- [:organization_id, :project_id, :application_id, :build_id] do
      other = Map.update!(selection, key, &(&1 <> "-unselected"))
      assert_error(get.(path(other), headers), 404, "not_found")
    end

    response = get.(url, headers)
    assert response.status == 200
    assert "cache-control: no-store" in response.headers
    assert byte_size(response.body) <= 2_048

    assert %{"buildLogs" => logs} = decoded = Jason.decode!(response.body)
    assert map_size(decoded) == 1

    expected_selection =
      Map.new(selection, fn {key, value} ->
        [first | tail] = key |> Atom.to_string() |> String.split("_")
        {first <> Enum.map_join(tail, "", &String.capitalize/1), value}
      end)

    assert Map.take(logs, Map.keys(expected_selection)) == expected_selection
    assert logs["state"] == state
    assert logs["attempt"] == attempt
    assert is_integer(logs["revision"]) and logs["revision"] > 0

    assert [
             %{
               "event" => "compiler_finished",
               "exitCode" => compiler_exit,
               "stdoutBytes" => stdout_bytes,
               "stderrBytes" => stderr_bytes,
               "tailTruncated" => truncated,
               "phases" => phases
             } = compiler,
             %{"event" => "build_command_finished", "exitCode" => cli_exit} = command
           ] = logs["events"]

    assert map_size(compiler) == 6
    assert map_size(command) == 2
    assert is_integer(compiler_exit)
    assert is_integer(cli_exit)
    assert is_integer(stdout_bytes) and stdout_bytes >= 0
    assert is_integer(stderr_bytes) and stderr_bytes >= 0
    assert is_boolean(truncated)
    assert is_list(phases) and Enum.all?(phases, &(&1 in ~w(compile link package)))

    if state == "native_succeeded" do
      assert {compiler_exit, cli_exit} == {0, 0}
      assert stdout_bytes + stderr_bytes > 0
    end

    expected_keys =
      Map.keys(expected_selection) ++
        ~w(revision state attempt maxAttempts failureCode workerCompletionPending events)

    assert Enum.sort(Map.keys(logs)) == Enum.sort(expected_keys)

    logs
  end

  def assert_storage_refused!(get, headers, selection) do
    assert_error(get.(path(selection), headers), 503, "authorization_unavailable")
  end

  defp path(selection), do: @path <> "?" <> URI.encode_query(selection)

  defp assert_error(response, status, code) do
    assert response.status == status
    assert "cache-control: no-store" in response.headers
    assert %{"error" => %{"code" => ^code} = error} = decoded = Jason.decode!(response.body)
    assert map_size(decoded) == 1
    assert Map.keys(error) -- ~w(code message) == []
  end
end
