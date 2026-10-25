defmodule MixerHosted.Authorization.PostgresRepository do
  @moduledoc """
  Durable, read-only policy evidence on a fresh protected PostgreSQL transaction.

  This implements the existing callback-envelope seam. Its result remains a pure
  evaluation; no domain repository may accept it as transaction-bound authority.
  Deployment must separately provision a non-owner read-only runtime and grant
  only the migration's fixed lock helpers. No positive evidence is cached.
  """
  @behaviour MixerHosted.Authorization.Repository

  alias MixerHosted.Authorization.Postgres.{Evidence, Session}
  alias MixerHosted.Authorization.Scope

  @impl true
  def with_evidence(lookup, callback), do: with_evidence(lookup, callback, MixerHosted.Repo)

  @doc false
  def with_evidence(lookup, callback, repo) do
    with true <- is_function(callback, 1),
         {:ok, lookup} <- valid_lookup(lookup),
         false <- repo.in_transaction?() do
      case repo.transaction(
             fn ->
               linkage = Session.prepare!(repo, lookup)
               evidence = Evidence.load!(repo, lookup, linkage)
               result = callback.(evidence)
               Session.finish!(repo)
               result
             end,
             timeout: 5_000,
             queue: false
           ) do
        {:ok, result} -> result
        {:error, reason} when reason in [:unauthenticated, :not_found] -> {:error, reason}
        _ -> {:error, :authorization_unavailable}
      end
    else
      _ -> {:error, :authorization_unavailable}
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end

  defp valid_lookup(%{identity: identity, action: action, target: target} = lookup)
       when map_size(lookup) == 3 and is_map(identity) and not is_struct(identity) and
              map_size(identity) == 7,
       do: validate(lookup, action, target)

  defp valid_lookup(_), do: :error

  defp validate(lookup, action, target) do
    alias MixerHosted.Identity.Encoding
    i = lookup.identity

    with true <-
           Enum.sort(Map.keys(i)) ==
             Enum.sort([
               :profile_id,
               :profile_version,
               :issuer,
               :subject,
               :client_id,
               :identity_class,
               :credential_ref
             ]),
         true <- Encoding.bounded_string?(i.profile_id, 128),
         true <- is_integer(i.profile_version) and i.profile_version in 1..2_147_483_647,
         true <- Encoding.bounded_string?(i.issuer, 2_048),
         true <- Encoding.bounded_string?(i.subject, 256),
         true <- Encoding.bounded_string?(i.client_id, 256),
         true <- Encoding.bounded_string?(i.credential_ref, 256),
         true <- i.identity_class == :human,
         {:ok, scope} <- Scope.new(target),
         true <-
           (action in ["artifact.read", "artifact.upload"] and Scope.environment?(scope)) or
             (action == "audit.read" and Scope.project_only?(scope)) do
      {:ok, %{lookup | target: scope}}
    else
      _ -> :error
    end
  end
end
