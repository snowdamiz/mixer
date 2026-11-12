defmodule MixerHosted.CustomerBuildCatalogInputTest do
  use ExUnit.Case, async: true
  @moduletag :r1158_pure
  alias MixerHosted.CustomerBuildCatalog.{Input, Snapshot}
  alias MixerHostedWeb.BrowserBuildCatalogRequest, as: Request
  @project %{organization_id: "org-a", project_id: "project-a"}
  @application Map.put(@project, :application_id, "fieldlog")

  test "exact raw scope keys and no caller authority or limit" do
    assert {:ok, {:applications, @project, %{cursor: nil}}} =
             Request.parse(
               "/console-api/v1/applications",
               "organization_id=org-a&project_id=project-a"
             )

    for raw <- [
          "organization_id=org-a&project_id=project-a&limit=25",
          "organization_id=org-a&project_id=project-a&organization_id=org-a",
          "%6frganization_id=org-a&project_id=project-a",
          "organization_id=org-a&project_id=%GG",
          "organization_id=org-a&project_id=%2f",
          "organization_id=org-a&project_id=project-a&cursor="
        ] do
      assert {:error, :invalid_request} = Request.parse("/console-api/v1/applications", raw)
    end
  end

  test "canonical cursors bind kind parents order keys encoding and exact continuation" do
    cursor = Input.cursor(:applications, @project, ["app-25"])
    assert {:ok, %{last: ["app-25"]}} = Input.new(:applications, @project, %{cursor: cursor})

    for {kind, scope, value} <- [
          {:applications, %{organization_id: "org-b", project_id: "project-a"}, cursor},
          {:builds, @application, cursor},
          {:applications, @project, cursor <> "="},
          {:applications, @project, String.duplicate("a", 1401)}
        ] do
      assert {:error, :invalid_request} = Input.new(kind, scope, %{cursor: value})
    end

    raw = Base.url_decode64!(cursor, padding: false)

    for changed <- [
          String.replace(raw, "\"v\":1", "\"v\":1,\"v\":1"),
          " " <> raw,
          String.replace(raw, "\"kind\":\"applications\"", "\"kind\":\"builds\"")
        ] do
      assert {:error, :invalid_request} =
               Input.new(:applications, @project, %{
                 cursor: Base.url_encode64(changed, padding: false)
               })
    end
  end

  test "fixed25 lookahead sorts C keys and invalid rows fail whole page" do
    rows =
      for n <- 0..25,
          do: %{
            "organization_id" => "org-a",
            "project_id" => "project-a",
            "id" => "app-" <> String.pad_leading(Integer.to_string(n), 2, "0"),
            "active" => true
          }

    assert {:ok, %{applications: applications, nextCursor: cursor}} =
             Snapshot.project(%{kind: :applications, scope: @project, last: nil}, %{
               "records" => rows
             })

    assert length(applications) == 25 and is_binary(cursor)
    assert {:ok, %{last: ["app-24"]}} = Input.new(:applications, @project, %{cursor: cursor})

    assert {:ok, %{applications: [], nextCursor: nil}} =
             Snapshot.project(%{kind: :applications, scope: @project, last: nil}, %{
               "records" => []
             })

    for bad <- [
          Enum.reverse(rows),
          rows ++ [hd(rows)],
          [Map.put(hd(rows), "project_id", "project-b")],
          [Map.put(hd(rows), "id", "bad/id")],
          [Map.put(hd(rows), "active", false)]
        ] do
      assert {:error, :storage_unavailable} =
               Snapshot.project(%{kind: :applications, scope: @project, last: nil}, %{
                 "records" => bad
               })
    end
  end
end
