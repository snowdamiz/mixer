defmodule MixerHosted.Identity.Verifier do
  @moduledoc """
  Contract for a future configured identity adapter.

  `authenticate/2` receives the compact token without an HTTP `Bearer ` prefix.
  An adapter must own current trust configuration and cache state. The pure
  `AccessTokenVerifier.verify/3` helper does not implement that ownership.
  """

  @callback authenticate(compact_token :: binary(), now :: integer()) ::
              {:ok, MixerHosted.Identity.VerifiedIdentity.t()}
              | {:error, :unauthenticated | :identity_unavailable}
end
