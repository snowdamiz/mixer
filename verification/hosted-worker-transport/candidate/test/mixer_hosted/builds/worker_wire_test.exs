defmodule MixerHosted.Builds.WorkerWireTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Builds.{WorkerWire, Dispatch}
  alias MixerHosted.Test.WorkerData

  defp config,
    do: %{
      environment_id: "development",
      pool_id: "native",
      controller_id: "controller-1",
      platforms: [:ios, :android]
    }

  test "exact int64 and microsecond request binding with nonce-independent immutable digest" do
    r = WorkerData.request()
    assert {:ok, bytes, expected} = WorkerWire.encode(:query, r, config())
    v = Jason.decode!(bytes)
    assert v["ref"]["fence"] == "9223372036854775807"
    assert v["guard"]["epoch"] == "9223372036854775807"
    assert v["deadline_ms"] == "9223372036854775807"

    assert v["guard"]["expires_at_us"] ==
             Integer.to_string(DateTime.to_unix(r.guard.expires_at, :microsecond))

    assert {:ok, _, other} = WorkerWire.encode(:query, r, config())
    assert other["request_id"] != expected["request_id"]
    assert other["immutable_sha256"] == expected["immutable_sha256"]

    assert {:ok, %Dispatch.Observation{ref: ref, status: :absent}} =
             WorkerWire.decode(
               Jason.encode!(Map.put(expected, "observation", %{"status" => "absent"})),
               expected
             )

    assert ref === r.ref
  end

  test "all exact echoes, duplicate and escaped-equivalent keys reject" do
    {:ok, _, e} = WorkerWire.encode(:query, WorkerData.request(), config())
    base = Map.put(e, "observation", %{"status" => "running"})

    for key <- Map.keys(e) do
      assert {:error, :uncertain} =
               WorkerWire.decode(Jason.encode!(Map.put(base, key, "wrong")), e)
    end

    raw = Jason.encode!(base)

    assert {:error, :uncertain} =
             WorkerWire.decode(
               String.replace(
                 raw,
                 "\"status\":\"running\"",
                 "\"status\":\"running\",\"st\\u0061tus\":\"absent\""
               ),
               e
             )

    assert {:error, :uncertain} = WorkerWire.decode(Jason.encode!(Map.put(base, "extra", 1)), e)

    assert {:error, :uncertain} =
             WorkerWire.decode(String.replace(raw, "\"version\":1", "\"version\":1.0"), e)
  end

  test "bounded JSON lexical envelope precedes decoding" do
    assert :error =
             WorkerWire.object(
               "{\"x\":" <> String.duplicate("[", 9) <> "0" <> String.duplicate("]", 9) <> "}",
               32_768
             )

    assert :error =
             WorkerWire.object("{\"x\":\"" <> String.duplicate("a", 8_193) <> "\"}", 32_768)

    assert :error =
             WorkerWire.object(
               "{\"x\":[" <> Enum.join(List.duplicate("0", 513), ",") <> "]}",
               32_768
             )

    assert :error = WorkerWire.object("{" <> <<255>> <> "}", 32_768)
  end

  test "invalid request identity, scope and integer ranges fail closed" do
    r = WorkerData.request()

    assert {:error, :invalid_request} =
             WorkerWire.encode(:query, %{r | operation_id: String.duplicate("f", 64)}, config())

    assert {:error, :invalid_request} =
             WorkerWire.encode(:query, %{r | ref: %{r.ref | project_id: "elsewhere"}}, config())

    assert {:error, :invalid_request} = WorkerWire.encode(:query, %{r | deadline_ms: 0}, config())
    assert {:error, :invalid_request} = WorkerWire.encode(:unknown, r, config())

    for value <- ["+1", "01", "-1", "1e3", "9223372036854775808", 1, 1.0] do
      assert :error = WorkerWire.decimal(value, 1, 9_223_372_036_854_775_807)
    end
  end

  test "terminal results match existing lifecycle artifact and classification contract" do
    {:ok, _, e} = WorkerWire.encode(:stop, WorkerData.request(), config())

    for {code, result} <- [
          {"stale", :stale},
          {"unavailable", :unavailable},
          {"uncertain", :uncertain}
        ] do
      assert {:error, ^result} =
               WorkerWire.decode(
                 Jason.encode!(Map.put(e, "observation", %{"status" => "error", "code" => code})),
                 e
               )
    end

    artifact_kinds =
      ~w(unsigned_native_binary guest_artifact resource_inventory debug_symbols compatibility_report sbom provenance)

    artifacts =
      Enum.with_index(artifact_kinds, fn kind, i ->
        %{
          "kind" => kind,
          "sha256" => String.duplicate(Integer.to_string(i), 64),
          "size_bytes" => "9223372036854775807"
        }
      end)

    result = %{"outcome" => "succeeded", "artifacts" => artifacts}

    reply = fn r ->
      Jason.encode!(Map.put(e, "observation", %{"status" => "completed", "result" => r}))
    end

    assert {:ok,
            %Dispatch.Observation{
              status: {:completed, %{outcome: :succeeded, artifacts: converted}}
            }} = WorkerWire.decode(reply.(result), e)

    assert length(converted) == 7

    assert {:error, :uncertain} =
             WorkerWire.decode(reply.(%{result | "artifacts" => tl(artifacts)}), e)

    failure = %{
      "outcome" => "failed",
      "class" => "compiler",
      "code" => "worker_lost",
      "diagnostic_sha256" => String.duplicate("a", 64)
    }

    assert {:error, :uncertain} = WorkerWire.decode(reply.(failure), e)
    assert {:ok, _} = WorkerWire.decode(reply.(%{failure | "code" => "compiler_error"}), e)
  end
end
