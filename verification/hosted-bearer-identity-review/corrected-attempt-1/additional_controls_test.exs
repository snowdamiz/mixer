defmodule MixerHostedWeb.BearerIdentityCorrectionReviewTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.Plugs.BearerIdentity

  @now 1_800_000_000
  defmodule Verifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:correction_verified, token, now})
      Process.get(:correction_result)
    end
  end
  def clock, do: @now
  setup do
    identity = %VerifiedIdentity{
      profile_id: "correction-review", profile_version: 1, issuer: "https://correction.invalid",
      subject: "correction-review", client_id: "correction-review", credential_ref: "correction-review",
      issued_at: @now - 1, expires_at: @now + 30, identity_class: :human, scopes: []
    }
    Process.put(:correction_result, {:ok, identity})
    {:ok, opts: BearerIdentity.init(verifier: Verifier, clock: {__MODULE__, :clock, []}), identity: identity}
  end
  defp request(type), do: conn(:get, "/protected") |> put_req_header("authorization", "Bearer review-token") |> put_req_header("content-type", type)

  test "media type requires a nonempty subtype even when parameters are complete", %{opts: opts} do
    invalid = ["application/", "application/ ", "application/; charset=utf-8", ~s(application/; profile="one,two"), "application/; ;"]
    observations = for type <- invalid do
      result = request(type) |> BearerIdentity.call(opts)
      called = receive do {:correction_verified, _, _} -> true after 0 -> false end
      %{type: type, status: result.status, halted: result.halted, verifier_called: called}
    end
    assert Enum.all?(observations, &(&1.status == 400 and &1.halted and not &1.verifier_called)), inspect(observations)
  end

  test "quoted pairs validate every byte and reject dangling escapes or trailing syntax", %{opts: opts} do
    for byte <- 0..255 do
      type = "application/json; profile=\"prefix\\" <> <<byte>> <> "suffix\""
      result = request(type) |> BearerIdentity.call(opts)
      if byte == 9 or byte in 32..126 or byte >= 128 do
        refute result.halted, "legal quoted pair #{byte}"
        assert_received {:correction_verified, "review-token", @now}
      else
        assert result.status == 400, "illegal quoted pair #{byte}"
        refute_received {:correction_verified, _, _}
      end
    end
    for tail <- ["; profile=\"dangling\\", "; profile=\"escaped-closing\\\"", "; profile=\"ok\", application/json", "; profile=\"ok\"extra"] do
      result = request("application/json" <> tail) |> BearerIdentity.call(opts)
      assert result.status == 400
      refute_received {:correction_verified, _, _}
    end
  end

  test "multiple duplicate metadata values normalize on success and each denial family", %{opts: opts, identity: identity} do
    for {authorization, outcome, status} <- [
      {"Bearer review-token", {:ok, identity}, nil},
      {nil, {:ok, identity}, 401},
      {"Basic review-token", {:ok, identity}, 400},
      {"Bearer review-token", {:error, :unauthenticated}, 401},
      {"Bearer review-token", {:error, :identity_unavailable}, 503}
    ] do
      Process.put(:correction_result, outcome)
      headers = for name <- ["x-request-id", "cache-control", "content-type", "www-authenticate", "retry-after"], n <- 1..8, do: {name, "stale-value-number-#{n}-123456"}
      original = %{conn(:get, "/protected") | resp_headers: [{"x-review-preserved", "yes"} | headers]}
      original = if authorization, do: put_req_header(original, "authorization", authorization), else: original
      result = BearerIdentity.call(original, opts)
      assert result.status == status
      assert [id] = get_resp_header(result, "x-request-id")
      refute String.starts_with?(id, "stale-")
      assert get_resp_header(result, "cache-control") == ["no-store"]
      assert get_resp_header(result, "x-review-preserved") == ["yes"]
      if status do
        assert result.halted
        assert get_resp_header(result, "content-type") == ["application/json; charset=utf-8"]
        assert Jason.decode!(result.resp_body)["request_id"] == id
        assert get_resp_header(result, "retry-after") == if(status == 503, do: ["1"], else: [])
        expected_challenge = cond do
          status == 503 -> []
          status == 400 -> [~s(Bearer error="invalid_request")]
          is_nil(authorization) -> ["Bearer"]
          true -> [~s(Bearer error="invalid_token")]
        end
        assert get_resp_header(result, "www-authenticate") == expected_challenge
        refute Map.has_key?(result.assigns, :verified_identity)
      else
        refute result.halted
        assert result.assigns.verified_identity == identity
      end
      if authorization == "Bearer review-token", do: assert_received({:correction_verified, "review-token", @now})
    end
  end
end
