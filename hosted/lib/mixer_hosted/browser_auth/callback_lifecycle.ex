defmodule MixerHosted.BrowserAuth.CallbackLifecycle do
  @moduledoc false
  alias MixerHosted.BrowserAuth.{
    PreauthDraft,
    Protocol,
    Store,
    Vault,
    RuntimeOwner,
    ProviderOwner,
    IDTokenVerifier
  }

  alias MixerHosted.Identity.{
    BoundedJSON,
    ConfiguredVerifier,
    Admission,
    KeyOwner,
    TrustSnapshot,
    AccessTokenVerifier
  }

  defmodule Claim do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:lease, :source, :digest, :expires_at]
    defstruct @enforce_keys
  end

  defmodule Activate do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [
      :claim,
      :identity,
      :access_token,
      :id_expires_at,
      :cookie,
      :csrf,
      :generation,
      :family
    ]
    defstruct @enforce_keys
  end

  defmodule Result do
    @moduledoc "Token-free private callback result, published only after confirmed COMMIT."
    @derive {Inspect, only: []}
    @enforce_keys [:cookie, :csrf, :generation, :expires_at]
    defstruct @enforce_keys
  end

  defmodule Fence do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:permit, :key_lease, :ticket, :config, :deadline]
    defstruct @enforce_keys
  end

  defmodule Completion do
    @moduledoc false
    @derive {Inspect, only: []}
    @enforce_keys [:receipt, :fence]
    defstruct @enforce_keys
  end

  def final_check(%Fence{} = f) do
    with :ok <- KeyOwner.finish(KeyOwner, f.key_lease),
         :ok <- ProviderOwner.finish(f.ticket, f.config, f.deadline),
         do: :ok
  end

  def release(%Fence{} = f) do
    KeyOwner.release(KeyOwner, f.permit)
    Admission.release(f.permit)
  end

  def run(lease, headers, query) do
    config = lease.runtime.browser_config

    with {:ok, cookie} when is_binary(cookie) <- Protocol.parse_session_cookie(headers),
         {:ok, callback} <- Protocol.parse_callback(config, query),
         :ok <- RuntimeOwner.checkpoint(lease),
         input = %PreauthDraft.Load{lease: lease, cookie_digest: hash(cookie)},
         {:ok, source} when not is_nil(source) <- Store.discover_begin(input),
         true <- source.attempt !== nil and source.attempt["status"] === "pending",
         true <- source.attempt["state_digest"] === hash(callback.state),
         true <- source.attempt["issuer"] === callback.issuer,
         :ok <- RuntimeOwner.checkpoint(lease) do
      claim = %Claim{
        lease: lease,
        source: source,
        digest: :crypto.strong_rand_bytes(32),
        expires_at: min(source.attempt["expires_at"], System.system_time(:second) + 5)
      }

      case Store.lifecycle(lease, {:claim, claim}) do
        {:ok, _} -> complete(claim, callback.outcome)
        error -> error
      end
    else
      {:error, %Store.Failure{}} = error -> error
      _ -> Store.failure(:admission, :not_started)
    end
  end

  defp complete(claim, {:code, code}) do
    lease = claim.lease
    runtime = lease.runtime
    config = runtime.browser_config
    envelope = claim.source.attempt_envelope

    result =
      with :ok <- RuntimeOwner.checkpoint(lease),
           {:ok, %Vault.Verifier{verifier: verifier}} <-
             Vault.open(runtime.custody.key, envelope.context, envelope.sealed),
           {:ok, raw, snapshot, ticket} <-
             ProviderOwner.exchange(config, code, verifier, lease.deadline),
           {:ok, response} <- BoundedJSON.object(raw, 16384),
           true <-
             Enum.all?(
               Map.keys(response),
               &(&1 in ~w(id_token access_token token_type expires_in scope))
             ),
           "Bearer" <- response["token_type"],
           {:ok, id} <-
             IDTokenVerifier.verify(
               response["id_token"],
               response["access_token"],
               claim.source.attempt["nonce_digest"],
               config,
               snapshot,
               System.system_time(:second)
             ),
           {:ok, identity} <-
             ConfiguredVerifier.authenticate(
               KeyOwner,
               config.profile_id,
               response["access_token"],
               System.system_time(:second)
             ),
           true <-
             identity.subject === id.subject and identity.issuer === config.issuer and
               identity.client_id === config.client_id and
               identity.profile_id === config.profile_id and
               identity.profile_version === config.profile_version and
               identity.identity_class === :human and
               "mixer.workspace.read" in identity.scopes,
           :ok <- ProviderOwner.finish(ticket, config, lease.deadline),
           :ok <- RuntimeOwner.checkpoint(lease) do
        # Retain current access-key generation through SQL COMMIT and publication.
        with {:ok, permit} <- Admission.acquire(KeyOwner, config.profile_id) do
          retained =
            try do
              with {:ok, key_lease} <-
                     KeyOwner.checkout(KeyOwner, permit, System.system_time(:second)),
                   p = TrustSnapshot.profile(key_lease.snapshot),
                   true <-
                     p.profile_id === config.profile_id and
                       p.profile_version === config.profile_version and
                       p.issuer === config.issuer and p.client_id === config.client_id and
                       p.audience === config.api_audience,
                   {:ok, ^identity} <-
                     AccessTokenVerifier.verify(
                       response["access_token"],
                       System.system_time(:second),
                       key_lease.snapshot
                     ),
                   :ok <- KeyOwner.finish(KeyOwner, key_lease) do
                draft = %Activate{
                  claim: claim,
                  identity: identity,
                  access_token: response["access_token"],
                  id_expires_at: id.expires_at,
                  cookie: Protocol.random_token(),
                  csrf: Protocol.random_token(),
                  generation: Protocol.random_token(),
                  family: "browser_" <> Protocol.random_token()
                }

                with {:ok, value} <- Store.lifecycle(lease, {:activate, draft}),
                     :ok <- KeyOwner.finish(KeyOwner, key_lease),
                     :ok <- ProviderOwner.finish(ticket, config, lease.deadline),
                     :ok <- RuntimeOwner.checkpoint(lease) do
                  {:ok, value,
                   %Fence{
                     permit: permit,
                     key_lease: key_lease,
                     ticket: ticket,
                     config: config,
                     deadline: lease.deadline
                   }}
                else
                  {:error, %Store.Failure{}} = error -> error
                  _ -> Store.failure(:commit, :committed)
                end
              else
                _ -> Store.failure(:effect, :not_started)
              end
            rescue
              _ -> Store.failure(:effect, :unknown)
            catch
              _, _ -> Store.failure(:commit, :unknown)
            end

          case retained do
            {:ok, _, %Fence{}} ->
              retained

            error ->
              KeyOwner.release(KeyOwner, permit)
              Admission.release(permit)
              error
          end
        end
      end

    case result do
      {:ok, _, %Fence{}} = success ->
        success

      {:error, %Store.Failure{outcome: outcome}} = error when outcome in [:unknown, :committed] ->
        error

      _ ->
        fail(claim)
    end
  end

  defp complete(claim, _), do: fail(claim)

  defp fail(claim) do
    case Store.lifecycle(claim.lease, {:fail, claim}) do
      {:ok, true} -> Store.failure(:effect, :committed)
      error -> error
    end
  end

  defp hash(v), do: :crypto.hash(:sha256, v)
end
