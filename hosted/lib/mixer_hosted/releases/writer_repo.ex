defmodule MixerHosted.Releases.WriterRepo do
  @moduledoc """
  Opt-in database pool for local v3 CLI writes over loopback HTTP.

  Set `:local_release_target` to the reviewed target with its host and public
  roots, and configure this Repo with the provisioned writer database and login.
  Apply the local release ledger, head-read and CLI request migrations. Bind
  the login in the target's `mixer_release_heads.writer_role` field.

  Give the login the existing fresh authorization SELECT and lock grants,
  head SELECT and sequence UPDATE, publication SELECT and column INSERT,
  and CLI request SELECT and INSERT. Grant EXECUTE on the two release access
  guards and `mixer_release_bound_artifact`. The upload pool retains its own
  artifact table grants.

  The CLI bearer must authorize both artifact upload and release publication.
  A validation receipt covers the signed protocol artifact at this target.
  """
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres

  def children(endpoint) do
    case Application.fetch_env(:mixer_hosted, __MODULE__) do
      :error ->
        []

      {:ok, options} ->
        unless Keyword.keyword?(options) and is_binary(options[:username]) and
                 is_binary(options[:database]) and endpoint[:http][:ip] == {127, 0, 0, 1} and
                 endpoint[:https] == nil do
          raise ArgumentError,
                "local release writer requires a loopback HTTP listener and Repo options"
        end

        [__MODULE__]
    end
  end
end
