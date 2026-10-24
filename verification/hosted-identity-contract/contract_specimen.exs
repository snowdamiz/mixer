# Independently authored declaration specimen only. This namespace is deliberately
# separate from the proposed MixerHosted application. No verifier, policy engine,
# database, HTTP route, secret or cryptographic implementation is provided.
defmodule MixerHostedContractSpecimen.VerifiedIdentity do
  @moduledoc false
  @enforce_keys [
    :profile_id,
    :profile_version,
    :issuer,
    :subject,
    :client_id,
    :credential_ref,
    :issued_at,
    :expires_at,
    :identity_class,
    :scopes
  ]
  defstruct @enforce_keys

  # Opaque documents ownership; it is not a BEAM security boundary. Only the real
  # adapter may construct this after verified cryptographic/protocol validation.
  @opaque t :: %__MODULE__{
            profile_id: binary(),
            profile_version: pos_integer(),
            issuer: binary(),
            subject: binary(),
            client_id: binary(),
            credential_ref: binary(),
            issued_at: integer(),
            expires_at: integer(),
            identity_class: :human | :service,
            scopes: [binary()]
          }
end

defmodule MixerHostedContractSpecimen.Request do
  @moduledoc false
  @type action :: :artifact_read | :artifact_upload | :audit_read
  @enforce_keys [:organization, :project, :action, :resource_ref, :request_id]
  defstruct @enforce_keys
  @type t :: %__MODULE__{
          organization: binary(),
          project: binary(),
          action: action(),
          resource_ref: binary(),
          request_id: binary()
        }
end

defmodule MixerHostedContractSpecimen.Target do
  @moduledoc false
  @enforce_keys [:organization, :project, :app, :environment, :platform, :runtime, :digest]
  defstruct @enforce_keys
  @type t :: %__MODULE__{
          organization: binary(),
          project: binary(),
          app: binary(),
          environment: binary(),
          platform: binary(),
          runtime: binary(),
          digest: binary()
        }
end

defmodule MixerHostedContractSpecimen.AuthorizedContext do
  @moduledoc false
  @enforce_keys [
    :transaction_owner,
    :transaction_ref,
    :request_id,
    :principal_id,
    :principal_kind,
    :credential_ref,
    :action,
    :target,
    :policy_revisions,
    :audit_actor
  ]
  defstruct @enforce_keys
  # The real repository must check owner + transaction liveness/action/target.
  # This declaration does not implement those checks or mint a usable ticket.
  @opaque t :: %__MODULE__{
            transaction_owner: pid(),
            transaction_ref: reference(),
            request_id: binary(),
            principal_id: binary(),
            principal_kind: :human | :service,
            credential_ref: binary(),
            action: MixerHostedContractSpecimen.Request.action(),
            target: MixerHostedContractSpecimen.Target.t() | :project_audit,
            policy_revisions: %{atom() => non_neg_integer()},
            audit_actor: map()
          }
end

defmodule MixerHostedContractSpecimen.Verifier do
  @moduledoc false
  @callback authenticate(binary(), integer()) ::
              {:ok, MixerHostedContractSpecimen.VerifiedIdentity.t()}
              | {:error, :unauthenticated | :identity_unavailable}
end

defmodule MixerHostedContractSpecimen.Authorization do
  @moduledoc false
  @type failure ::
          :unauthenticated
          | :not_found
          | :permission_denied
          | :authorization_unavailable
          | :storage_unavailable
  @callback with_authorized_transaction(
              MixerHostedContractSpecimen.VerifiedIdentity.t(),
              MixerHostedContractSpecimen.Request.t(),
              (MixerHostedContractSpecimen.AuthorizedContext.t() ->
                 {:ok, term()} | {:error, term()})
            ) :: {:ok, term()} | {:error, failure()}
end

defmodule MixerHostedContractSpecimen.ReleaseRepository do
  @moduledoc false
  @callback artifact(MixerHostedContractSpecimen.AuthorizedContext.t(), binary()) ::
              {:ok, term()} | {:error, term()}
  @callback upload(MixerHostedContractSpecimen.AuthorizedContext.t(), binary(), binary()) ::
              {:ok, term()} | {:error, term()}
  @callback history(MixerHostedContractSpecimen.AuthorizedContext.t(), non_neg_integer(), 1..100) ::
              {:ok, term()} | {:error, term()}
end
