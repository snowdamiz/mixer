defmodule MixerHosted.Identity.ReviewEndpointRegressionTest do
  use ExUnit.Case, async: true
  alias MixerHosted.Identity.{Manifest, StartupConfig, StartupFixture}

  for {field, value} <- [{"host", "keys.independent.invalid\n"}, {"path", "/keys\n"}] do
    @field field
    @value value
    test "Manifest rejects LF in endpoint #{field}" do
      entry = StartupFixture.entry() |> put_in(["jwks_endpoint", @field], @value)
      # Same explicit fixed conversion used by StartupConfig, with accepted enum atoms.
      profile =
        Map.new(entry["profile"], fn {k, v} ->
          key =
            %{
              "profile_id" => :profile_id,
              "profile_version" => :profile_version,
              "issuer" => :issuer,
              "audience" => :audience,
              "client_id" => :client_id,
              "identity_class" => :identity_class,
              "enabled" => :enabled
            }[k]

          {key, if(k == "identity_class", do: :human, else: v)}
        end)

      candidate = %{
        profile: profile,
        jwks_endpoint: %{
          host: entry["jwks_endpoint"]["host"],
          port: 443,
          path: entry["jwks_endpoint"]["path"]
        },
        transport: :hosted_https
      }

      assert {:error, :invalid_manifest} = Manifest.validate([candidate])
    end

    test "StartupConfig rejects LF in endpoint #{field}" do
      object =
        StartupFixture.envelope()
        |> put_in(["profiles", Access.at(0), "jwks_endpoint", @field], @value)

      env = %{
        "MIXER_IDENTITY_MODE" => "configured",
        "MIXER_IDENTITY_CONFIG" => Jason.encode!(object)
      }

      assert_raise ArgumentError, "invalid identity startup: configuration", fn ->
        StartupConfig.load!(env, :api, StartupFixture.standard_roots())
      end
    end
  end
end
