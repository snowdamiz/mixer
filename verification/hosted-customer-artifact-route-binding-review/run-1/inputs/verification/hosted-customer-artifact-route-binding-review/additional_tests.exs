  test "independent: mismatched digest stops before every Repo transaction boundary", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    wrong = String.duplicate("f", 64)
    refute wrong == checked.manifest_sha256

    assert {:error, :digest_mismatch} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), wrong, "independent-key", checked.envelope_bytes, metadata()
             )

    refute_received {:route_binding_review_repo, _}

    assert {:error, :storage_unavailable} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert_received {:route_binding_review_repo, :in_transaction}
    assert_received {:route_binding_review_repo, :transaction}
    refute_received {:route_binding_review_repo, :rollback}
    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: structured expected values cannot select the unrestricted upload path", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    for expected <- [
          :any, {:at, checked.manifest_sha256}, {:any}, %{digest: checked.manifest_sha256},
          String.to_charlist(checked.manifest_sha256), 0, false, <<0>>, <<255>>,
          String.duplicate("0", 63), String.duplicate("g", 64)
        ] do
      assert {:error, :invalid_request} =
               CustomerArtifacts.upload_at(
                 F.identity(), route(), expected, "independent-key", checked.envelope_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: denied identity and exact scope precede invalid-body classification", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    cases = [
      {nil, :unauthenticated},
      {F.identity(%{expires_at: F.now() - 1}), :unauthenticated},
      {F.identity(%{issued_at: F.now() + 120}), :unauthenticated},
      {F.identity(%{identity_class: :service}), :permission_denied},
      {F.identity(%{scopes: ["mixer.artifact.read"]}), :permission_denied},
      {F.identity(%{scopes: ["mixer.artifact.upload.extra"]}), :permission_denied},
      {F.identity(%{scopes: ["MIXER.ARTIFACT.UPLOAD"]}), :permission_denied}
    ]

    for {identity, error} <- cases do
      assert {:error, ^error} =
               CustomerArtifacts.upload_at(
                 identity, route(), checked.manifest_sha256, "independent-key", :not_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: foreign project rejects before invalid-body classification", %{
    checked: checked,
    config: config
  } do
    Application.put_env(:mixer_hosted, CustomerArtifacts, %{
      config | repo: MixerHosted.CustomerArtifacts.RouteBindingReviewRepo
    })

    for foreign <- [Map.put(route(), :organization_id, "other"), Map.put(route(), :project_id, "other")] do
      assert {:error, :not_found} =
               CustomerArtifacts.upload_at(
                 F.identity(), foreign, checked.manifest_sha256, "independent-key", :not_bytes,
                 metadata()
               )

      refute_received {:route_binding_review_repo, _}
    end

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: invalid signature stays artifact_invalid even when route also differs", %{
    checked: checked
  } do
    bad =
      checked.envelope_bytes
      |> Jason.decode!()
      |> put_in(["signed_manifest", "signature"], Base.encode64(:binary.copy(<<0>>, 64)))
      |> Jason.encode!()

    for expected <- [checked.manifest_sha256, String.duplicate("f", 64)] do
      assert {:error, :artifact_invalid} =
               CustomerArtifacts.upload_at(
                 F.identity(), route(), expected, "independent-key", bad, metadata()
               )
    end

    assert {:error, :invalid_request} =
             CustomerArtifacts.upload(F.identity(), route(), "independent-key", bad, metadata())

    assert F.counts() == [[0, 0, 0, 0]]
  end

  test "independent: cached success never rescues invalid bytes or expected digest", %{
    checked: checked
  } do
    assert {:ok, %{status: 201}} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    bad =
      checked.envelope_bytes
      |> Jason.decode!()
      |> put_in(["signed_manifest", "signature"], Base.encode64(:binary.copy(<<0>>, 64)))
      |> Jason.encode!()

    assert {:error, :artifact_invalid} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key", bad, metadata()
             )

    assert {:error, :invalid_request} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), {:at, checked.manifest_sha256}, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert {:error, :digest_mismatch} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), String.duplicate("f", 64), "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 1, 1, 1]]
  end

  test "independent: unrestricted and addressed calls retain the same authorized receipt", %{
    checked: checked
  } do
    assert {:ok, %{status: 201} = first} =
             CustomerArtifacts.upload(
               F.identity(), route(), "independent-key", checked.envelope_bytes, metadata()
             )

    assert {:ok, ^first} =
             CustomerArtifacts.upload_at(
               F.identity(), route(), checked.manifest_sha256, "independent-key",
               checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 1, 1, 1]]

    assert {:ok, %{status: 200, event_sequence: 2}} =
             CustomerArtifacts.upload(
               F.identity(), route(), "independent-next", checked.envelope_bytes, metadata()
             )

    assert F.counts() == [[1, 2, 2, 2]]
  end
