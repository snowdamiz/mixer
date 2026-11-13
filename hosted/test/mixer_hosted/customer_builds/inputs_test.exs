defmodule MixerHosted.CustomerBuilds.InputsTest do
  use ExUnit.Case, async: true
  alias MixerHosted.CustomerBuilds.Inputs
  @scope %{organization_id: "org-a", project_id: "project-a", application_id: "fieldlog"}
  test "closed canonical query rejects duplicate unknown missing and noncanonical encodings" do
    good = URI.encode_query(@scope)
    assert {:ok, %{scope: @scope, last: nil}} = Inputs.parse(good)

    for bad <- [
          "",
          good <> "&limit=25",
          good <> "&organization_id=org-a",
          good <> "&cursor=",
          good <> "&cursor=%",
          good <> "&cursor=%61",
          "organization_id=org%2da&project_id=project-a&application_id=fieldlog",
          "organization_id=org-a&project_id=project-a",
          String.duplicate("a", 8193)
        ] do
      assert Inputs.parse(bad) == {:error, :invalid_request}
    end
  end

  test "cursor is bounded canonical and bound to all scope keys version kind and valid last keys" do
    token = Inputs.cursor(@scope, ["ios", "input-1"])
    assert {:ok, %{last: ["ios", "input-1"]}} = Inputs.new(@scope, token)

    for scope <- [
          Map.put(@scope, :organization_id, "org-b"),
          Map.put(@scope, :project_id, "project-b"),
          Map.put(@scope, :application_id, "other")
        ] do
      assert Inputs.new(scope, token) == {:error, :invalid_request}
    end

    raw = Base.url_decode64!(token, padding: false)

    for bytes <- [
          raw <> " ",
          String.replace(raw, "\"v\":1", "\"v\":2"),
          String.replace(raw, "build_inputs", "builds"),
          String.replace(raw, "ios", "future-platform"),
          String.replace(raw, "input-1", "bad id"),
          String.replace(raw, "\"v\":1", "\"v\":1,\"v\":1")
        ] do
      assert Inputs.new(@scope, Base.url_encode64(bytes, padding: false)) ==
               {:error, :invalid_request}
    end

    for bad <- [token <> "=", String.duplicate("a", 1401), 1, "!"] do
      assert Inputs.new(@scope, bad) == {:error, :invalid_request}
    end
  end

  test "trusted row projection fails closed including malformed sentinel row without creating platform atoms" do
    row = [
      "ios",
      "input",
      String.duplicate("a", 64),
      String.duplicate("b", 64),
      String.duplicate("c", 64)
    ]

    assert {:ok, %{inputs: [], nextCursor: nil}} = Inputs.project(@scope, [])

    for bad <- [
          ["future-platform" | tl(row)],
          List.replace_at(row, 1, "bad id"),
          List.replace_at(row, 2, "bad"),
          row ++ ["secret"],
          nil
        ] do
      assert Inputs.project(@scope, [bad]) == {:error, :storage_unavailable}

      assert Inputs.project(@scope, List.duplicate(row, 25) ++ [bad]) ==
               {:error, :storage_unavailable}
    end

    assert Inputs.project(@scope, List.duplicate(row, 27)) == {:error, :storage_unavailable}
  end

  test "browser listing cannot use the internal nil binding fallback" do
    assert catch_throw(
             MixerHosted.BrowserAuth.ActiveCreate.require_browser_current!(%{
               repo: __MODULE__,
               identity: :identity
             })
           ) == {:rollback, :authorization_unavailable}
  end

  def rollback(reason), do: throw({:rollback, reason})
end
