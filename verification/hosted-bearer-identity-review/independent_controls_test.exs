defmodule MixerHostedWeb.BearerIdentityIndependentReviewTest do
  use ExUnit.Case, async: false
  import Plug.Conn
  import Plug.Test
  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.Plugs.BearerIdentity

  @now 1_800_000_000

  defmodule ReviewVerifier do
    @behaviour MixerHosted.Identity.Verifier
    def authenticate(token, now) do
      send(self(), {:review_verified, token, now})
      Process.get(:review_result)
    end
  end

  def clock, do: @now

  setup do
    identity = %VerifiedIdentity{
      profile_id: "review-profile", profile_version: 1, issuer: "https://review.invalid",
      subject: "review-subject", client_id: "review-client", credential_ref: "review-reference",
      issued_at: @now - 1, expires_at: @now + 30, identity_class: :human, scopes: []
    }
    Process.put(:review_result, {:ok, identity})
    opts = BearerIdentity.init(verifier: ReviewVerifier, clock: {__MODULE__, :clock, []})
    {:ok, identity: identity, opts: opts}
  end

  defp request(token \\ "valid-token", query \\ "") do
    conn(:get, "/protected" <> query) |> put_req_header("authorization", "Bearer " <> token)
  end

  test "each byte in an unpadded token has the declared alphabet", %{opts: opts} do
    alphabet = MapSet.new(:binary.bin_to_list("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~+/"))
    for byte <- 0..255 do
      token = "a" <> <<byte>> <> "b"
      result = request(token) |> BearerIdentity.call(opts)
      if MapSet.member?(alphabet, byte) do
        refute result.halted, "allowed byte #{byte}"
        assert_received {:review_verified, ^token, @now}
      else
        assert result.status == 400, "forbidden byte #{byte}"
        refute_received {:review_verified, _, _}
      end
    end
  end

  test "reserved query names reject every singly percent-encoded character", %{opts: opts, identity: identity} do
    for name <- ["access_token", "access_token[]", "access_token[value]"],
        index <- 0..(byte_size(name) - 1), hex_case <- [:lower, :upper] do
      <<head::binary-size(index), byte, tail::binary>> = name
      hex = Integer.to_string(byte, 16) |> String.pad_leading(2, "0")
      hex = if hex_case == :upper, do: String.upcase(hex), else: String.downcase(hex)
      query = "?ordinary=unchanged&" <> head <> "%" <> hex <> tail <> "=secret"
      result = request("valid-token", query) |> assign(:verified_identity, identity) |> BearerIdentity.call(opts)
      assert result.status == 400
      assert result.halted
      refute Map.has_key?(result.assigns, :verified_identity)
      refute_received {:review_verified, _, _}
    end
  end

  test "a legal quoted comma remains a single Content-Type", %{opts: opts} do
    result = request() |> put_req_header("content-type", ~s(application/json; profile="one,two")) |> BearerIdentity.call(opts)
    refute result.halted
    assert_received {:review_verified, "valid-token", @now}
  end

  test "malformed Content-Type parameters cannot hide a combined second media type", %{opts: opts} do
    values = [
      "application/json; charset=utf-8, application/x-www-form-urlencoded",
      "application/json; invalid-parameter",
      ~s(application/json; profile="unterminated)
    ]
    for value <- values do
      assert {:ok, "application", "json", _} = Plug.Conn.Utils.content_type(value)
      result = request() |> put_req_header("content-type", value) |> BearerIdentity.call(opts)
      assert result.status == 400, "accepted malformed Content-Type #{inspect(value)}"
      refute_received {:review_verified, _, _}
    end
  end

  test "duplicate upstream request IDs are replaced by one safe ID on denial", %{opts: opts} do
    original = %{conn(:get, "/protected") | resp_headers: [
      {"x-request-id", "upstream-first-request-12345"},
      {"x-request-id", "upstream-second-request-12345"}
    ]}
    result = BearerIdentity.call(original, opts)
    assert result.status == 401
    assert [id] = get_resp_header(result, "x-request-id")
    refute id in ["upstream-first-request-12345", "upstream-second-request-12345"]
    assert Jason.decode!(result.resp_body)["request_id"] == id
  end

  test "all stale challenge and retry values are removed before generic denial", %{opts: opts} do
    original = %{conn(:get, "/protected") | resp_headers: [
      {"www-authenticate", "stale-one"}, {"www-authenticate", "stale-two"},
      {"www-authenticate", "stale-three"}, {"retry-after", "77"}, {"retry-after", "88"}
    ]}
    result = BearerIdentity.call(original, opts)
    assert result.status == 401
    assert get_resp_header(result, "www-authenticate") == ["Bearer"]
    assert get_resp_header(result, "retry-after") == []
  end

  test "consecutive successes and failures never reuse stale identity", %{opts: opts, identity: identity} do
    first = request() |> assign(:verified_identity, %{identity | subject: "stale"}) |> BearerIdentity.call(opts)
    assert first.assigns.verified_identity == identity
    assert_received {:review_verified, "valid-token", @now}
    for outcome <- [{:error, :unauthenticated}, {:error, :identity_unavailable}, {:ok, %{subject: "forged"}}] do
      Process.put(:review_result, outcome)
      result = request() |> assign(:verified_identity, first.assigns.verified_identity) |> BearerIdentity.call(opts)
      assert result.status == if(outcome == {:error, :unauthenticated}, do: 401, else: 503)
      refute Map.has_key?(result.assigns, :verified_identity)
      assert_received {:review_verified, "valid-token", @now}
    end
  end
end
