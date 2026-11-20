defmodule MixerHosted.Releases.ReleaseJobs.Materialize do
  @moduledoc false
  use Oban.Worker, queue: :releases

  alias MixerHosted.Repo

  @impl Oban.Worker
  def perform(%Oban.Job{id: id, attempt: attempt})
      when is_integer(id) and id in 1..9_223_372_036_854_775_807 and
             is_integer(attempt) and attempt in 1..2_147_483_647 do
    case Repo.query(
           "SELECT mixer_release_jobs.materialize_v1($1::bigint,$2::integer)",
           [id, attempt],
           timeout: 5_000,
           queue: false
         ) do
      {:ok, %{rows: [["ok"]]}} -> :ok
      {:ok, %{rows: [["invalid_publication_reference"]]}} -> invalid_reference()
      _ -> {:error, :storage_unavailable}
    end
  end

  def perform(%Oban.Job{}), do: invalid_reference()

  defp invalid_reference, do: {:cancel, :invalid_publication_reference}
end
