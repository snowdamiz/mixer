defmodule MixerHosted.Test.StockReleaseCLI do
  @moduledoc false
  import ExUnit.Assertions

  def publish!(cli, port, token, artifact, signed_assignment, assignment) do
    dir =
      "MIXER_TEST_RELEASE_CANDIDATE"
      |> System.fetch_env!()
      |> Path.join(artifact.manifest_sha256)

    File.mkdir_p!(dir)
    File.write!(Path.join(dir, "signed-manifest.json"), artifact.signed_manifest_bytes)
    File.write!(Path.join(dir, "payload.wasm"), artifact.payload)
    assignment_path = Path.join(dir, "signed-assignment.json")
    File.write!(assignment_path, signed_assignment)
    scope = assignment["scope"]
    basis_points = assignment["rollout_basis_points"]
    assert rem(basis_points, 100) == 0
    rollout_percent = Integer.to_string(div(basis_points, 100))

    assert {output, 0} =
             System.cmd(
               cli,
               [
                 "update",
                 "publish",
                 dir,
                 "--organization",
                 scope["organization"],
                 "--project",
                 scope["project"],
                 "--channel",
                 assignment["channel"],
                 "--rollout",
                 rollout_percent,
                 "--assignment",
                 assignment_path
               ],
               env: [
                 {"MIXER_RELEASE_ORIGIN", "http://127.0.0.1:#{port}"},
                 {"MIXER_RELEASE_TOKEN", token}
               ],
               stderr_to_stdout: true
             )

    assert Jason.decode!(output) == %{
             "status" => "ok",
             "action" => "publish",
             "artifact_sha256" => artifact.manifest_sha256,
             "sequence" => assignment["sequence"],
             "rollout_basis_points" => assignment["rollout_basis_points"],
             "delivery" => "local_only"
           }
  end
end
