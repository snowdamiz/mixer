defmodule MixerHosted.Releases.ReleaseJobsTest do
  use ExUnit.Case, async: true

  alias MixerHosted.Releases.{Publication, ReleaseJobs}
  alias MixerHosted.Releases.ReleaseJobs.Materialize

  test "materialization jobs have just the exact target, version and full-width sequence" do
    runtime = String.duplicate("a", 64)

    publication = %Publication{
      organization_id: "org-a",
      project_id: "project-a",
      application_id: "app-a",
      environment_id: "development",
      platform: "ios",
      runtime_sha256: runtime,
      channel: "stable",
      sequence: Decimal.new("18446744073709551615.000"),
      action: "halt",
      signed_assignment_bytes: <<1, 2, 3>>,
      artifact_sha256: String.duplicate("9", 64),
      rollout_basis_points: 0
    }

    assert %Oban.Job{queue: "releases", worker: worker, args: args} =
             publication |> ReleaseJobs.changeset() |> Ecto.Changeset.apply_action!(:insert)

    assert worker == "MixerHosted.Releases.ReleaseJobs.Materialize"

    assert args == %{
             "version" => 1,
             "organization_id" => "org-a",
             "project_id" => "project-a",
             "application_id" => "app-a",
             "environment_id" => "development",
             "platform" => "ios",
             "runtime_sha256" => runtime,
             "channel" => "stable",
             "sequence" => "18446744073709551615"
           }
  end

  test "a job with no representable actual execution reference is cancelled" do
    for job <- [
          %Oban.Job{args: %{"id" => 1, "attempt" => 1}},
          %Oban.Job{id: "1", attempt: 1},
          %Oban.Job{id: 1, attempt: 0},
          %Oban.Job{id: 1, attempt: 2_147_483_648},
          %Oban.Job{id: 9_223_372_036_854_775_808, attempt: 1}
        ] do
      assert {:cancel, :invalid_publication_reference} = Materialize.perform(job)
    end
  end
end
