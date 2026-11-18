defmodule MixerHosted.Builds.OperationIntent do
  @moduledoc """
  Private transaction fragment for operation intent only.

  The internal caller supplies the context immediately after Admission renewal
  and current-intent checking in the same transaction. Its map is not a new
  authorization or provenance capability. No worker observation is returned.
  """
  alias Ecto.Multi
  alias MixerHosted.Builds.{Admission, Dispatch, Lifecycle, OperationAdmission, Record}

  @spec record_multi(Multi.t(), term(), map()) :: Multi.t()
  def record_multi(%Multi{} = multi, name, context) do
    Multi.run(multi, name, fn repo, _ -> record(repo, context, :owner) end)
  end

  @doc false
  @spec record_fenced_multi(Multi.t(), term(), map()) :: Multi.t()
  def record_fenced_multi(%Multi{} = multi, name, context) do
    Multi.run(multi, name, fn repo, _ -> record(repo, context, :fenced) end)
  end

  defp record(
         repo,
         %{
           outcome: :renewed,
           build: %Lifecycle.Build{state: state} = build,
           record: %Record{},
           token: %Admission.Token{},
           lease: %Admission.Lease{}
         } = context,
         entry
       )
       when state in [:running, :cancelling, :reconciling] do
    with {:ok, _ref} <- Lifecycle.worker_ref(build) do
      request = Dispatch.request(context)

      record_intent(repo, state, request, entry)
    end
  end

  defp record(_, _, _), do: {:error, :invalid_operation_context}

  defp record_intent(repo, state, request, :fenced) do
    action = if state == :running, do: "ensure", else: "stop"

    case OperationAdmission.fenced_intent(repo, action, request) do
      {:ok, %{decision: :fenced}} -> {:error, :stale}
      result -> result
    end
  end

  defp record_intent(repo, :running, request, :owner),
    do: OperationAdmission.ensure_admitted(repo, request)

  defp record_intent(repo, _, request, :owner), do: OperationAdmission.stop_intent(repo, request)
end
