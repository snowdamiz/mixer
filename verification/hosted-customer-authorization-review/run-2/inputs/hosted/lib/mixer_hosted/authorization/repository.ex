defmodule MixerHosted.Authorization.Repository do
  @moduledoc """
  Trusted repository seam for the pure first-slice policy; no durable adapter exists.

  A configured server module must start or join the actual protected Repo
  transaction, take current principal/credential/authorization-head locks, resolve
  current memberships and actual stored target ancestry, and invoke the callback
  there. Apply same-connection storage policy and recheck before persistence.
  Revocation writers must take conflicting locks in the same canonical order.
  No cached positive evidence, caller roles, self-reported revisions, request
  ancestry or detached callback may substitute for that protocol.

  This facade returns only a policy evaluation. It does not create the separate
  transaction-bound context required by domain stores, execute domain callbacks,
  or implement RLS, database locks, provisioning, HTTP, service or CI authority.
  Repository selection is trusted server configuration, never HTTP input.
  """

  alias MixerHosted.Authorization.{Policy, Scope}

  @type lookup :: %{identity: map(), action: binary(), target: Scope.t()}
  @callback with_evidence(lookup(), (Policy.evidence() -> Policy.result())) :: Policy.result()

  defmodule Unavailable do
    @moduledoc false
    @behaviour MixerHosted.Authorization.Repository
    @impl true
    def with_evidence(_lookup, _callback), do: {:error, :authorization_unavailable}
  end

  @spec evaluate(term(), term(), term(), term(), module()) :: Policy.result()
  def evaluate(identity, action, target, now, repository \\ Unavailable) do
    with {:ok, scope} <- Policy.request(identity, action, target, now),
         true <-
           is_atom(repository) and Code.ensure_loaded?(repository) and
             function_exported?(repository, :with_evidence, 2) do
      lookup = %{identity: Policy.identity_key(identity), action: action, target: scope}

      case repository.with_evidence(lookup, fn evidence ->
             Policy.evaluate(identity, action, scope, evidence, now)
           end) do
        {:ok, %Policy.Decision{action: ^action, target: ^scope}} = result ->
          result

        {:error, error} = result
        when error in [
               :invalid_request,
               :unauthenticated,
               :not_found,
               :permission_denied,
               :authorization_unavailable
             ] ->
          result

        _ ->
          {:error, :authorization_unavailable}
      end
    else
      false -> {:error, :authorization_unavailable}
      error -> error
    end
  rescue
    _ -> {:error, :authorization_unavailable}
  catch
    _, _ -> {:error, :authorization_unavailable}
  end
end
