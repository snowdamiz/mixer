defmodule MixerHostedWeb.LocalReleaseControllerTest do
  use ExUnit.Case, async: false

  import Plug.Conn
  import Plug.Test

  alias MixerHosted.Identity.VerifiedIdentity
  alias MixerHostedWeb.{Endpoint, LocalReleaseController}

  @loopback {127, 0, 0, 1}
  @ipv6_loopback {0, 0, 0, 0, 0, 0, 0, 1}
  @path "/v3/orgs/org-a/projects/project-a/apps/fieldlog/release-promotions"

  test "stage promotion rejects a listener bound to a different address" do
    start_endpoint!(true,
      thousand_island_options: [transport_options: [:inet6, {:ip, @ipv6_loopback}]]
    )

    assert Endpoint.config(:http)[:ip] == @loopback
    assert {:ok, {@ipv6_loopback, port}} = Endpoint.server_info(:http)
    assert port > 0

    assert stage_promotion().status == 404
  end

  test "stage promotion requires an active HTTP listener" do
    start_endpoint!(false)

    assert {:error, :no_server_found} = Endpoint.server_info(:http)
    assert stage_promotion().status == 404
  end

  test "stage promotion reaches body validation on the expected loopback listener" do
    start_endpoint!(true)

    assert {:ok, {@loopback, port}} = Endpoint.server_info(:http)
    assert port > 0
    assert %{status: 400, resp_body: body} = stage_promotion()
    assert %{"error" => %{"code" => "invalid_json"}} = Jason.decode!(body)
  end

  test "stage promotion rejects dot segments as direction IDs" do
    start_endpoint!(true)

    for id <- [".", ".."] do
      assert stage_promotion(id).status == 404
    end
  end

  defp start_endpoint!(server?, http_options \\ []) do
    assert {:ok, _} = Application.ensure_all_started(:bandit)
    original = Application.fetch_env!(:mixer_hosted, Endpoint)
    on_exit(fn -> Application.put_env(:mixer_hosted, Endpoint, original) end)

    config =
      Keyword.merge(original,
        server: server?,
        http: [ip: @loopback, port: 0] ++ http_options,
        https: false
      )

    Application.put_env(:mixer_hosted, Endpoint, config)
    start_supervised!(Endpoint)
  end

  defp stage_promotion(direction_id \\ "dev-to-stage") do
    identity = %VerifiedIdentity{
      profile_id: "profile",
      profile_version: 1,
      issuer: "https://issuer.example",
      subject: "operator",
      client_id: "client",
      credential_ref: "credential",
      issued_at: 1,
      expires_at: 2,
      identity_class: :human,
      scopes: ["mixer.release.publish"]
    }

    request = %{
      conn(:post, @path <> "/" <> direction_id, "{}")
      | remote_ip: @loopback,
        path_params: %{
          "organization_id" => "org-a",
          "project_id" => "project-a",
          "application_id" => "fieldlog",
          "direction_id" => direction_id
        }
    }

    request
    |> assign(:verified_identity, identity)
    |> put_req_header("content-type", "application/json")
    |> put_req_header("idempotency-key", "promotion-test")
    |> put_req_header("x-mixer-reason", "Verify listener admission")
    |> LocalReleaseController.call(LocalReleaseController.init(:stage_promote))
  end
end
