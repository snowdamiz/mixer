defmodule MixerHosted.Builds.Dispatch do
  @moduledoc """
  Trusted external build adapter contract; no adapter is installed by default.

  An implementation must durably bind operation_id to the exact original ref,
  spec and deadline, authorize its worker separately, and enforce lexicographic
  {lease epoch, journal revision} ordering. An expired or older request must not
  act. ensure_started is idempotent for the operation's entire retention period;
  stop installs a permanent terminal tombstone even for an absent operation.
  A delayed ensure must never reopen that identity. query's :absent observation
  is not proof that a request in flight cannot create a worker. Only definitive
  completion or stop observations authorize capacity release.

  These are provider implementation obligations, not claims of authentication,
  isolation, deployment qualification or exactly-once Oban execution. Adapters
  run trusted transport code only; customer build scripts run outside BEAM.
  """

  defmodule Request do
    @moduledoc "Immutable operation identity plus a separate coordinator lease guard."
    @enforce_keys [:operation_id, :ref, :spec, :deadline_ms, :guard]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  defmodule Observation do
    @moduledoc "A trusted adapter observation bound to one immutable worker operation."
    @enforce_keys [:operation_id, :ref, :status]
    defstruct @enforce_keys
    @type t :: %__MODULE__{}
  end

  @type result :: {:ok, Observation.t()} | {:error, :unavailable | :uncertain | :stale}
  @callback query(Request.t()) :: result()
  @callback ensure_started(Request.t()) :: result()
  @callback stop(Request.t()) :: result()

  @doc false
  def request(context) do
    ref = context.build.active_ref

    identity = [
      "mixer-build-operation-v1",
      context.record.id,
      ref.organization_id,
      ref.project_id,
      ref.application_id,
      ref.build_id,
      Atom.to_string(ref.platform),
      ref.attempt,
      ref.fence
    ]

    operation_id = :crypto.hash(:sha256, Jason.encode!(identity)) |> Base.encode16(case: :lower)

    %Request{
      operation_id: operation_id,
      ref: ref,
      spec: context.build.spec,
      deadline_ms: context.build.deadline,
      guard: %{
        record_id: context.record.id,
        revision: context.record.revision,
        owner_id: context.token.owner_id,
        epoch: context.token.epoch,
        expires_at: context.lease.expires_at
      }
    }
  end

  @doc false
  def observation(%Request{} = request, {:ok, %Observation{} = observation}) do
    if observation.operation_id == request.operation_id and observation.ref == request.ref and
         (observation.status in [:absent, :running] or
            match?({:completed, %{}}, observation.status) or
            match?({:stopped, _}, observation.status)) do
      {:ok, observation.status}
    else
      {:error, :invalid_observation}
    end
  end

  def observation(_, {:error, error}) when error in [:unavailable, :uncertain, :stale],
    do: {:error, error}

  def observation(_, _), do: {:error, :invalid_observation}
end
