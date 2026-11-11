defmodule MixerHosted.BrowserAuth.BuildScopeTest do
  use ExUnit.Case, async: false

  test "signed build scope preserves the old projection and closed refusals" do
    alias MixerHosted.Identity.{AccessTokenVerifier, TrustSnapshot}
    {:ok, _} = Application.ensure_all_started(:jose)
    now = System.system_time(:second)

    profile = %{
      profile_id: "r1128-verifier",
      profile_version: 1,
      issuer: "https://issuer.fixture.invalid",
      audience: "mixer-api",
      client_id: "console",
      identity_class: :human,
      enabled: true
    }

    key = JOSE.JWK.generate_key({:rsa, 2048})

    public =
      key
      |> JOSE.JWK.to_public()
      |> JOSE.JWK.to_map()
      |> elem(1)
      |> Map.merge(%{"kid" => "r1128", "alg" => "RS256", "use" => "sig"})

    {:ok, snapshot} =
      TrustSnapshot.new(profile, Jason.encode!(%{"keys" => [public]}), now - 1, now + 299)

    base = %{
      "iss" => profile.issuer,
      "aud" => profile.audience,
      "sub" => "subject-1",
      "client_id" => profile.client_id,
      "jti" => "r1128-scope-control",
      "iat" => now - 1,
      "exp" => now + 120
    }

    sign = fn claims ->
      JOSE.JWS.sign(key, Jason.encode!(claims), %{
        "alg" => "RS256",
        "kid" => "r1128",
        "typ" => "at+jwt"
      })
      |> JOSE.JWS.compact()
      |> elem(1)
    end

    verify = fn scope ->
      AccessTokenVerifier.verify(sign.(Map.put(base, "scope", scope)), now, snapshot)
    end

    old = ~w(mixer.artifact.read mixer.artifact.upload mixer.audit.read mixer.workspace.read)
    {:ok, original} = verify.(Enum.join(Enum.reverse(old), " "))
    true = original.scopes == old

    {:ok, extended} =
      verify.(Enum.join(["mixer.build.read", "owner", "mixer.build.*" | Enum.reverse(old)], " "))

    true = extended.scopes == old ++ ["mixer.build.read"]

    true =
      Map.delete(Map.from_struct(original), :scopes) ==
        Map.delete(Map.from_struct(extended), :scopes)

    {:ok, %{scopes: ["mixer.build.read"]}} =
      verify.("owner mixer.build.read mixer.build.read.extra MIXER.build.read")

    {:ok, %{scopes: []}} = verify.("owner mixer.build.* mixer.build.read.extra MIXER.build.read")

    malformed = [
      nil,
      [],
      "",
      " mixer.build.read",
      "mixer.build.read ",
      "mixer.build.read  owner",
      "mixer.build.read mixer.build.read",
      "mixer.build.read\towner",
      "mixer.build.read\nowner",
      "mixer.build.read\\owner",
      "mixer.build.read\"owner",
      "snow☃",
      String.duplicate("a", 1025),
      Enum.map_join(1..33, " ", &"s#{&1}")
    ]

    for scope <- malformed, do: {:error, :unauthenticated} = verify.(scope)
    token = sign.(Map.put(base, "scope", "mixer.workspace.read mixer.build.read"))

    for bad <- ["Bearer " <> token, token <> ".", String.duplicate("a", 4090)],
        do: {:error, :unauthenticated} = AccessTokenVerifier.verify(bad, now, snapshot)

    for patch <- [
          %{"iss" => "https://wrong.invalid"},
          %{"aud" => "wrong"},
          %{"client_id" => "wrong"},
          %{"exp" => now},
          %{"iat" => now + 31}
        ],
        do:
          {:error, :unauthenticated} =
            AccessTokenVerifier.verify(
              sign.(Map.merge(Map.put(base, "scope", "mixer.build.read"), patch)),
              now,
              snapshot
            )

    {:ok, disabled} =
      TrustSnapshot.new(
        %{profile | enabled: false},
        Jason.encode!(%{"keys" => [public]}),
        now - 1,
        now + 299
      )

    {:error, :unauthenticated} = AccessTokenVerifier.verify(token, now, disabled)
  end
end
