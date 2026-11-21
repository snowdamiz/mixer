defmodule MixerHosted.Test.StockReleaseCLI do
  @moduledoc false
  import ExUnit.Assertions

  def promote_environment!(cli, port, token, inputs, expected) do
    folder = Path.join(System.fetch_env!("MIXER_TEST_RELEASE_CANDIDATE"), "stage-promotion")
    File.mkdir_p!(folder)
    ios = Path.join(folder, "ios-assignment.json")
    android = Path.join(folder, "android-assignment.json")
    File.write!(ios, inputs.ios.assignment)
    File.write!(android, inputs.android.assignment)

    %{"assignment" => %{"scope" => scope}} = Jason.decode!(inputs.ios.assignment)

    command = fn ->
      System.cmd(
        cli,
        [
          "update",
          "promote-environment",
          inputs.direction,
          "--organization",
          scope["organization"],
          "--project",
          scope["project"],
          "--application",
          scope["app"],
          "--reason",
          inputs.reason,
          "--source-ios-sequence",
          Integer.to_string(inputs.ios.source_sequence),
          "--source-android-sequence",
          Integer.to_string(inputs.android.source_sequence),
          "--ios-assignment",
          ios,
          "--android-assignment",
          android
        ],
        env: [
          {"MIXER_RELEASE_ORIGIN", "http://127.0.0.1:#{port}"},
          {"MIXER_RELEASE_TOKEN", token}
        ],
        stderr_to_stdout: true
      )
    end

    assert {output, 0} = retry_stage_promotion(command, 2)
    assert Jason.decode!(output) == expected
  end

  defp retry_stage_promotion(command, retries) do
    {output, status} = result = command.()

    with true <- status == 1 and retries > 0,
         {:ok, %{"code" => "update.stage_promote.rejected", "message" => message}} <-
           Jason.decode(output),
         true <- String.starts_with?(message, "Local v3 origin returned HTTP 503") do
      Process.sleep(1_000)
      retry_stage_promotion(command, retries - 1)
    else
      _ -> result
    end
  end

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
