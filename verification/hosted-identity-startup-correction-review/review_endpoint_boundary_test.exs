defmodule MixerHosted.Identity.ReviewEndpointBoundaryTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Identity.{Manifest, StartupConfig, StartupFixture}

  setup_all do
    {:ok, roots: StartupFixture.standard_roots()}
  end

  defp entry(host, path) do
    %{
      profile: %{
        profile_id: "review-boundary",
        profile_version: 1,
        issuer: "https://issuer.review.invalid",
        audience: "review",
        client_id: "review",
        identity_class: :human,
        enabled: true
      },
      jwks_endpoint: %{host: host, port: 443, path: path},
      transport: :hosted_https
    }
  end

  defp check(host, path, accepted, roots) do
    raw =
      StartupFixture.envelope()
      |> put_in(["profiles", Access.at(0), "jwks_endpoint", "host"], host)
      |> put_in(["profiles", Access.at(0), "jwks_endpoint", "path"], path)
      |> Jason.encode!()

    env = %{"MIXER_IDENTITY_MODE" => "configured", "MIXER_IDENTITY_CONFIG" => raw}

    if accepted do
      candidate = entry(host, path)
      assert {:ok, %{"review-boundary" => ^candidate}} = Manifest.validate([candidate])
      assert StartupConfig.load!(env, :api, roots).mode == :configured
    else
      assert {:error, :invalid_manifest} = Manifest.validate([entry(host, path)])

      assert_raise ArgumentError, "invalid identity startup: configuration", fn ->
        StartupConfig.load!(env, :api, roots)
      end
    end
  end

  test "all ASCII bytes preserve exact middle-label and path grammar", %{roots: roots} do
    for byte <- 0..127 do
      host_allowed = byte in ?a..?z or byte in ?0..?9 or byte in [?-, ?.]
      path_allowed = host_allowed or byte in ?A..?Z or byte in [?_, ?~, ?., ?/]
      check("a" <> <<byte>> <> "b.review.invalid", "/keys", host_allowed, roots)
      check("keys.review.invalid", "/a" <> <<byte>> <> "b", path_allowed, roots)
    end
  end

  test "all terminal ASCII controls and Unicode newline separators fail closed", %{roots: roots} do
    tails =
      Enum.map(Enum.to_list(0..31) ++ [127], &<<&1>>) ++
        ["\u0085", "\u2028", "\u2029", "\uFEFF", "\n\n", "\r\n\n"]

    for tail <- tails do
      check("keys.review.invalid" <> tail, "/keys", false, roots)
      check("keys.review.invalid", "/keys" <> tail, false, roots)
    end
  end

  test "LF cannot terminate an intermediate hostname label", %{roots: roots} do
    for host <- ["keys\n.review.invalid", "keys.review\n.invalid", "a\n.b\n.c", "a\n\n.b"] do
      check(host, "/keys", false, roots)
    end
  end

  test "LF within maximum byte bounds rejects alongside exact valid controls", %{roots: roots} do
    label = String.duplicate("a", 62)

    host252 =
      Enum.join(
        [
          String.duplicate("a", 63),
          String.duplicate("b", 63),
          String.duplicate("c", 63),
          String.duplicate("d", 60)
        ],
        "."
      )

    path2047 = "/" <> String.duplicate("a", 2046)
    assert byte_size(host252) == 252
    assert byte_size(path2047) == 2047

    for host <- [label, host252] do
      check(host, "/keys", true, roots)
      check(host <> "\n", "/keys", false, roots)
    end

    check("keys.review.invalid", path2047, true, roots)
    check("keys.review.invalid", path2047 <> "\n", false, roots)
  end
end
