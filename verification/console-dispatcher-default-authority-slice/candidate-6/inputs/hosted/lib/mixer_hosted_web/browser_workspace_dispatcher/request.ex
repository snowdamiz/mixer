defmodule MixerHostedWeb.BrowserWorkspaceDispatcher.Request do
  @moduledoc false
  alias MixerHosted.Authorization.Scope
  alias MixerHosted.CustomerWorkspace.Input

  @spec new(term()) :: {:ok, map()} | {:error, :invalid_request}
  def new({:organizations, page}), do: build(:organizations, nil, page)

  def new({:projects, organization, page}) do
    if Scope.identifier?(organization),
      do: build(:projects, organization, page),
      else: {:error, :invalid_request}
  end

  def new(_), do: {:error, :invalid_request}

  defp build(operation, organization, page) do
    with {:ok, _decoded_page} <- Input.page(page, Atom.to_string(operation), organization) do
      prefix =
        if operation == :projects,
          do: "organization_id=" <> URI.encode_www_form(organization) <> "&",
          else: ""

      query = prefix <> "limit=" <> Integer.to_string(page.limit)

      query =
        if is_nil(page.cursor),
          do: query,
          else: query <> "&cursor=" <> URI.encode_www_form(page.cursor)

      if byte_size(query) <= 8_192,
        do:
          {:ok,
           %{
             operation: operation,
             path: if(operation == :organizations, do: "/v3/orgs", else: "/v3/projects"),
             query: query
           }},
        else: {:error, :invalid_request}
    else
      _ -> {:error, :invalid_request}
    end
  end
end
