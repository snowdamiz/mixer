defmodule MixerHosted.CustomerBuilds.AttestationRepo do
  @moduledoc false
  use Ecto.Repo, otp_app: :mixer_hosted, adapter: Ecto.Adapters.Postgres
end

defmodule MixerHosted.CustomerBuilds.AttachNativeAttestation do
  @moduledoc false

  alias MixerHosted.Authorization
  alias MixerHosted.Authorization.Transaction.Context

  alias MixerHosted.Builds.{
    Dispatch,
    Lifecycle,
    NativeDevelopmentAttestation,
    RetainedNativeArtifacts
  }

  alias MixerHosted.Builds.NativeDevelopmentAttestation.ExpectedBuild

  alias MixerHosted.CustomerBuilds.{
    AttestationRepo,
    AttestationSchema,
    LocalAttestation,
    Selection,
    Snapshot
  }

  @action "build.attest"
  @config :native_development_attestation
  @max_envelope 16_384
  @record_keys ~w(id organization_id project_id application_id build_id platform request_key revision journal)a

  def run(identity, input, envelope)
      when is_binary(envelope) and byte_size(envelope) in 1..@max_envelope do
    with {:ok, %Selection{platform: "ios"} = selection} <- Selection.new(input),
         %{origin: origin, public_spki_der: spki} = trust <- trust(),
         {:ok, snapshot} <- transaction(identity, selection, [nil, nil, nil, nil, nil, nil]),
         {:ok, %ExpectedBuild{worker_operation_id: operation} = expected} <-
           completion(snapshot, selection, origin),
         {:ok, binding} <-
           RetainedNativeArtifacts.verify_ios_development(operation, expected.artifacts),
         :ok <-
           NativeDevelopmentAttestation.verify(
             envelope,
             %ExpectedBuild{expected | native_binding_sha256: binding},
             spki
           ) do
      key_id = Base.encode16(:crypto.hash(:sha256, spki), case: :lower)

      transaction(
        identity,
        selection,
        [snapshot, operation, binding, key_id, origin, envelope],
        trust
      )
    else
      {:ok, %Selection{}} ->
        {:error, :invalid_request}

      {:error, reason}
      when reason in [
             :invalid_retained_products,
             :invalid_envelope,
             :invalid_signature,
             :build_binding_mismatch
           ] ->
        {:error, :artifact_invalid}

      {:error, reason} when reason in [:invalid_trusted_key, :invalid_expected_build] ->
        {:error, :authorization_unavailable}

      {:error, _} = error ->
        error
    end
  end

  def run(_, _, _), do: {:error, :invalid_request}

  defp trust do
    case LocalAttestation.configuration() do
      {:ok, config} ->
        config

      _ ->
        if Process.whereis(MixerHosted.Supervisor) == nil and
             Application.fetch_env(:mixer_hosted, :startup) == :error,
           do: fixture_trust(),
           else: {:error, :authorization_unavailable}
    end
  end

  defp fixture_trust do
    case Application.get_env(:mixer_hosted, @config) do
      %{origin: origin, public_spki_der: <<_::352>>} = config when is_binary(origin) -> config
      _ -> {:error, :authorization_unavailable}
    end
  end

  defp transaction(identity, selection, payload, trust_snapshot \\ nil) do
    target = Map.take(selection, [:organization_id, :project_id, :application_id])

    if Process.whereis(AttestationRepo) == nil or
         AttestationRepo.get_dynamic_repo() !== AttestationRepo do
      {:error, :authorization_unavailable}
    else
      Authorization.with_authorized_transaction(
        identity,
        @action,
        target,
        fn context ->
          Context.effect!(context, AttestationRepo, @action, context.target, fn _ ->
            with :ok <- AttestationSchema.admit!(AttestationRepo),
                 :ok <- same_trust(trust_snapshot),
                 {:ok, result} <- AttestationSchema.apply!(AttestationRepo, selection, payload),
                 :ok <- same_trust(trust_snapshot) do
              {:ok, result}
            end
          end)
        end,
        AttestationRepo
      )
    end
  end

  defp same_trust(nil), do: :ok

  defp same_trust(snapshot) do
    if trust() === snapshot, do: :ok, else: {:error, :authorization_unavailable}
  end

  defp completion(
         %{
           "record" => row,
           "attempt" => attempt,
           "worker_fence" => fence,
           "terminal_event_id" => event_id
         },
         selection,
         origin
       )
       when is_map(row) do
    record = Map.new(@record_keys, &{&1, Map.get(row, Atom.to_string(&1))})

    with {:ok, id} <- Ecto.UUID.cast(record.id),
         {:ok, %{state: :native_succeeded, attempt: ^attempt, active_ref: nil} = build} <-
           Snapshot.restore(record, selection),
         %{
           state: :native_succeeded,
           worker_ref: %Lifecycle.WorkerRef{fence: ^fence} = ref,
           finished_at: finished_at,
           artifacts: artifacts
         } <-
           Enum.find(build.history, &(&1.attempt == attempt)),
         %{
           first_observed_at: ^finished_at,
           payload: %{
             type: :completed,
             ref: ^ref,
             result: %{outcome: :native_succeeded, artifacts: ^artifacts}
           }
         } <-
           Map.get(build.events, event_id),
         true <- build.artifacts === artifacts do
      {:ok,
       %ExpectedBuild{
         origin: origin,
         selection: selection,
         state: build.state,
         worker_completion_pending: false,
         journal_revision: record.revision,
         attempt: attempt,
         worker_operation_id: Dispatch.operation_id(id, ref),
         native_binding_sha256: nil,
         artifacts: artifacts
       }}
    else
      _ -> {:error, :storage_unavailable}
    end
  end

  defp completion(_, _, _), do: {:error, :storage_unavailable}
end
