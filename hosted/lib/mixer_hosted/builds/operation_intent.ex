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
    Multi.run(multi, name, fn repo, _ -> record(repo, context) end)
  end

  defp record(
         repo,
         %{
           outcome: :renewed,
           build: %Lifecycle.Build{state: state} = build,
           record: %Record{},
           token: %Admission.Token{},
           lease: %Admission.Lease{}
         } = context
       )
       when state in [:running, :cancelling, :reconciling] do
    with {:ok, _ref} <- Lifecycle.worker_ref(build) do
      request = Dispatch.request(context)

      case state do
        :running -> OperationAdmission.ensure_admitted(repo, request)
        _ -> OperationAdmission.stop_intent(repo, request)
      end
    end
  end

  defp record(_, _), do: {:error, :invalid_operation_context}
end
