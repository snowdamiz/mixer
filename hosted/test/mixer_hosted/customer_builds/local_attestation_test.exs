defmodule MixerHosted.CustomerBuilds.LocalAttestationTest do
  use ExUnit.Case, async: false

  alias MixerHosted.CustomerBuilds.{AttestationRepo, LocalAttestation}
  alias MixerHosted.RuntimeConfig
  alias MixerHostedWeb.Endpoint

  @password "MIXER_LOCAL_NATIVE_ATTESTATION_PASSWORD"
  @key "MIXER_LOCAL_NATIVE_ATTESTATION_PUBLIC_SPKI_BASE64"
  @writer "mixer_native_attestation_writer"
  @base %{
    "MIXER_HOSTED_ROLE" => "api",
    "MIXER_PROCESSOR_PROFILE" => "builds_v1",
    "MIXER_DATABASE_HOST" => "db.fixture.example",
    "MIXER_DATABASE_NAME" => "mixer_fixture",
    "MIXER_DATABASE_USER" => "api_fixture",
    "MIXER_DATABASE_PASSWORD" => "api-fixture",
    "MIXER_BUILD_CREATE_ENABLED" => "true",
    "MIXER_BUILD_CREATE_PASSWORD" => "create-fixture",
    "MIXER_SECRET_KEY_BASE" => String.duplicate("fixture-", 8),
    "MIXER_NATIVE_RETAINED_ROOT" => "/fixture/retained",
    "MIXER_HTTP_PORT" => "59709"
  }

  setup do
    {key, _} = :crypto.generate_key(:eddsa, :ed25519)
    spki = <<0x302A300506032B6570032100::96, key::binary>>

    %{
      hosted: RuntimeConfig.load!(@base),
      spki: spki,
      enabled: %{@password => "attest-fixture", @key => Base.encode64(spki)}
    }
  end

  test "default startup adds no writer pool", %{hosted: hosted} do
    assert LocalAttestation.configure!(%{}, hosted, :disabled) == hosted
    assert LocalAttestation.children(hosted, :disabled, hosted.endpoint) == []
  end

  test "an enrolled key and dedicated password add a single verified TLS connection", ctx do
    configured = LocalAttestation.configure!(ctx.enabled, ctx.hosted, :disabled)
    assert configured.database_connection_bound == ctx.hosted.database_connection_bound + 1
    assert configured.repo == ctx.hosted.repo
    assert configured.native_attestation.origin == "http://127.0.0.1:59709"
    assert configured.native_attestation.public_spki_der == ctx.spki
    endpoint = [adapter: Bandit.PhoenixAdapter] ++ configured.endpoint

    assert [{AttestationRepo, options}] =
             LocalAttestation.children(configured, :disabled, endpoint)

    assert options ==
             Keyword.merge(ctx.hosted.repo,
               username: @writer,
               password: "attest-fixture",
               pool_size: 1
             )

    assert options[:ssl][:verify] == :verify_peer
    refute inspect(configured) =~ "attest-fixture"
    refute inspect(configured.native_attestation) =~ "attest-fixture"

    for {key, value} <- [
          {:startup, {configured, :disabled}},
          {:role, :api},
          {:identity_startup, configured.identity_startup},
          {MixerHosted.Repo, configured.repo},
          {Oban, configured.oban},
          {Endpoint, endpoint}
        ] do
      put_config(key, value)
    end

    assert {AttestationRepo, options} in MixerHosted.Application.children({configured, :disabled})
    assert {:error, :authorization_unavailable} = LocalAttestation.configuration()
  end

  test "rejects partial or invalid trust and reused credentials", ctx do
    for env <- [
          Map.delete(ctx.enabled, @key),
          Map.delete(ctx.enabled, @password),
          Map.put(ctx.enabled, @key, Base.encode64(<<0::352>>)),
          Map.put(ctx.enabled, @key, ctx.enabled[@key] <> "\n"),
          Map.put(ctx.enabled, @password, ""),
          Map.put(ctx.enabled, @password, <<0>>),
          Map.put(ctx.enabled, @password, @base["MIXER_DATABASE_PASSWORD"]),
          Map.put(ctx.enabled, @password, @base["MIXER_BUILD_CREATE_PASSWORD"])
        ] do
      assert_raise ArgumentError, fn ->
        LocalAttestation.configure!(env, ctx.hosted, :disabled)
      end
    end

    delivery =
      {%{}, %{repo: [username: "mixer_release_delivery", password: ctx.enabled[@password]]}}

    assert_raise ArgumentError, fn ->
      LocalAttestation.configure!(ctx.enabled, ctx.hosted, delivery)
    end

    foreign_role = %{ctx.hosted | repo: Keyword.put(ctx.hosted.repo, :username, @writer)}

    assert_raise ArgumentError, fn ->
      LocalAttestation.configure!(ctx.enabled, foreign_role, :disabled)
    end
  end

  test "requires the retained API profile and its exact HTTP listener", ctx do
    for hosted <- [
          %{ctx.hosted | role: :processor},
          %{ctx.hosted | native: nil},
          %{ctx.hosted | endpoint: put_in(ctx.hosted.endpoint, [:http, :ip], {0, 0, 0, 0})}
        ] do
      assert_raise ArgumentError, fn ->
        LocalAttestation.configure!(ctx.enabled, hosted, :disabled)
      end
    end

    configured = LocalAttestation.configure!(ctx.enabled, ctx.hosted, :disabled)
    endpoint = [adapter: Bandit.PhoenixAdapter] ++ configured.endpoint

    for invalid <- [
          configured.endpoint,
          put_in(endpoint[:http][:port], 59_710),
          put_in(endpoint[:http][:transport_options], ip: {0, 0, 0, 0}),
          Keyword.put(endpoint, :https, [])
        ] do
      assert_raise ArgumentError, fn ->
        LocalAttestation.children(configured, :disabled, invalid)
      end
    end

    put_config(:native_development_attestation, %{})

    assert_raise ArgumentError, fn ->
      LocalAttestation.children(configured, :disabled, endpoint)
    end
  end

  defp put_config(key, value) do
    previous = Application.fetch_env(:mixer_hosted, key)
    Application.put_env(:mixer_hosted, key, value)

    on_exit(fn ->
      case previous do
        {:ok, value} -> Application.put_env(:mixer_hosted, key, value)
        :error -> Application.delete_env(:mixer_hosted, key)
      end
    end)
  end
end
