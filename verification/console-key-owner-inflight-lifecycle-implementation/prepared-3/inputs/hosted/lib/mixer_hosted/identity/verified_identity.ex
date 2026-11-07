defmodule MixerHosted.Identity.VerifiedIdentity do
  @moduledoc """
  Bounded identity evidence constructed after access-token verification.

  The credential reference is namespaced by the exact profile, issuer and client;
  it is not globally authoritative on its own. This value grants no membership or
  permission. Opaque types express ownership within the trusted BEAM application,
  not a sandbox against malicious code running in that application.
  """

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

  @opaque t :: %__MODULE__{
            profile_id: binary(),
            profile_version: pos_integer(),
            issuer: binary(),
            subject: binary(),
            client_id: binary(),
            credential_ref: binary(),
            issued_at: non_neg_integer(),
            expires_at: non_neg_integer(),
            identity_class: :human | :service,
            scopes: [binary()]
          }
end
