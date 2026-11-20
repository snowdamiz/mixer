defmodule MixerHosted.Releases.ReleaseJobs do
  @moduledoc false

  alias Ecto.Multi
  alias MixerHosted.Protocol.ArtifactV3Policy
  alias MixerHosted.Releases.Publication
  alias MixerHosted.Releases.ReleaseJobs.{Materialize, ProcessorProfile}
  alias MixerHosted.RuntimeConfig

  @target_fields ~w(organization_id project_id application_id environment_id platform runtime_sha256 channel)a

  def enqueue(repo, %Publication{} = publication) do
    case MixerHosted.Application.startup() do
      {:ok, {%RuntimeConfig{role: :api, local_release_jobs: true}, _}} ->
        insert(repo, publication)

      {:ok, {%RuntimeConfig{role: :api, local_release_jobs: false}, _}} ->
        :ok

      :error ->
        if Process.whereis(MixerHosted.Supervisor) == nil and
             Application.fetch_env(:mixer_hosted, :startup) == :error,
           do: :ok,
           else: {:error, :authorization_unavailable}

      _ ->
        {:error, :authorization_unavailable}
    end
  end

  @doc false
  def changeset(%Publication{sequence: sequence} = publication) do
    sequence = Decimal.to_integer(sequence)
    true = sequence > 0 and ArtifactV3Policy.uint?(sequence)

    args =
      publication
      |> Map.take(@target_fields)
      |> Map.new(fn {key, value} -> {Atom.to_string(key), value} end)
      |> Map.merge(%{"version" => 1, "sequence" => Integer.to_string(sequence)})

    Materialize.new(args)
  end

  defp insert(repo, publication) do
    true = repo.in_transaction?()
    job = publication |> changeset() |> Ecto.Changeset.apply_action!(:insert)

    # Let PostgreSQL supply the Oban defaults under the writer's column grants.
    multi =
      Multi.insert_all(
        Multi.new(),
        :release_job,
        Oban.Job,
        [Map.take(job, [:queue, :worker, :args])],
        prefix: ProcessorProfile.prefix(),
        returning: [:id]
      )

    case repo.transact(multi, timeout: 5_000, queue: false) do
      {:ok, %{release_job: {1, [%Oban.Job{id: id}]}}} when is_integer(id) and id > 0 -> :ok
      _ -> {:error, :authorization_unavailable}
    end
  end
end
