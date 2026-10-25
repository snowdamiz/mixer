defmodule MixerPreauthStoreReview.SyntheticRuntimeFixture do
  @moduledoc """
  Preparation-only data builder; loading this file starts no process or network.

  The hand-assembled loopback/random-port/plaintext config is deliberately outside
  RuntimeConfig.new/4's production TLS/5432 contract. Never call this production
  configuration or external custody qualification. Never print returned settings.
  """
  alias MixerHosted.BrowserAuth.{Config, ConfigurationDigest, Custody, RuntimeConfig}

  def build(port, database)
      when is_integer(port) and port in 10_000..65_535 and port != 5432 and
             is_binary(database) and byte_size(database) in 1..63 do
    browser = %Config{
      mode: :configured,
      public_origin: "https://console.mixer-review.invalid",
      profile_id: "review-human",
      profile_version: 1,
      issuer: "https://identity.mixer-review.invalid",
      client_id: "review-browser",
      api_audience: "review-api",
      authorization_endpoint: "https://identity.mixer-review.invalid/authorize",
      token_endpoint: "https://identity.mixer-review.invalid/token",
      id_token_jwks_endpoint: "https://identity.mixer-review.invalid/jwks",
      redirect_uri: "https://console.mixer-review.invalid/auth/callback",
      client_auth_method: :client_secret_basic,
      client_credential_ref: "secret://review/client",
      session_vault_ref: "vault://review/session"
    }

    roles = %{
      lifecycle_login: "mixer_review_lifecycle",
      writer: "mixer_review_writer",
      relation_owner: "mixer_review_owner",
      ordinary_runtime_login: "mixer_review_runtime"
    }

    {:ok, custody} =
      Custody.new(browser.session_vault_ref, %{
        reference: browser.session_vault_ref,
        key_id: "review-key-v1",
        key_bytes: :crypto.strong_rand_bytes(32)
      })

    {:ok, digest} = ConfigurationDigest.digest(browser)
    ordinary_password = random_secret()
    lifecycle_password = random_secret()

    runtime = %RuntimeConfig{
      mode: :configured,
      browser_config: browser,
      configuration_digest: digest,
      lifecycle_repo: repo_options(port, database, roles.lifecycle_login, lifecycle_password),
      expected_roles: roles,
      custody: custody
    }

    %{
      runtime: runtime,
      ordinary_repo:
        repo_options(port, database, roles.ordinary_runtime_login, ordinary_password),
      role_passwords: %{
        roles.lifecycle_login => lifecycle_password,
        roles.ordinary_runtime_login => ordinary_password
      },
      identity_manifest: [identity_entry(browser)],
      identity_binding: browser.profile_id,
      provenance: %{
        scope: :synthetic_manual_component_fixture,
        production_constructor_called: false,
        loopback_only: true,
        verified_tls: false,
        postgres_port: port,
        application_started: false,
        provider_called: false
      }
    }
  end

  defp repo_options(port, database, username, password) do
    [
      hostname: "127.0.0.1",
      port: port,
      database: database,
      username: username,
      password: password,
      pool_size: 2,
      pool_count: 1,
      timeout: 5_000,
      connect_timeout: 5_000,
      queue: false,
      show_sensitive_data_on_connection_error: false,
      ssl: false
    ]
  end

  defp identity_entry(browser) do
    %{
      profile: %{
        profile_id: browser.profile_id,
        profile_version: browser.profile_version,
        issuer: browser.issuer,
        audience: browser.api_audience,
        client_id: browser.client_id,
        identity_class: :human,
        enabled: true
      },
      jwks_endpoint: %{host: "identity.mixer-review.invalid", port: 443, path: "/jwks"},
      transport: :hosted_https
    }
  end

  defp random_secret, do: Base.url_encode64(:crypto.strong_rand_bytes(24), padding: false)
end
