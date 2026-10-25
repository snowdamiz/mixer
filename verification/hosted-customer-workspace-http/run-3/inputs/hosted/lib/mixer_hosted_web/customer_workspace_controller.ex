defmodule MixerHostedWeb.CustomerWorkspaceController do
  @moduledoc "Read-only representations of committed, currently authorized workspace pages."
  @behaviour Plug
  import Plug.Conn
  alias MixerHosted.{Authorization.Scope, CustomerWorkspace}
  alias MixerHostedWeb.Plugs.CustomerWorkspaceRequest, as: Request

  @roles ~w(administrator billing_manager developer owner release_manager viewer)

  @impl true
  def init(operation) when operation in [:organizations, :projects],
    do: %{operation: operation, facade: CustomerWorkspace, request: Request.init(operation)}

  def init(opts) when is_list(opts) do
    unless Keyword.keyword?(opts) and
             Enum.all?(Keyword.keys(opts), &(&1 in [:operation, :facade, :clock])) and
             length(Keyword.keys(opts)) == length(Enum.uniq(Keyword.keys(opts))) do
      raise ArgumentError, "invalid workspace controller options"
    end

    operation = Keyword.fetch!(opts, :operation)
    facade = Keyword.fetch!(opts, :facade)

    unless is_atom(facade) and match?({:module, ^facade}, Code.ensure_compiled(facade)) and
             function_exported?(facade, :organizations, 2) and
             function_exported?(facade, :projects, 3),
           do: raise(ArgumentError, "invalid workspace facade")

    %{
      operation: operation,
      facade: facade,
      request: Request.init(Keyword.take(opts, [:operation, :clock]))
    }
  end

  def init(_), do: raise(ArgumentError, "invalid workspace controller operation")

  @impl true
  def call(conn, %{operation: operation, facade: facade, request: options}) do
    conn = Request.call(conn, options)

    if conn.halted do
      conn
    else
      request = conn.assigns.customer_workspace_request
      identity = conn.assigns.verified_identity

      result =
        case operation do
          :organizations -> facade.organizations(identity, request.page)
          :projects -> facade.projects(identity, request.organization_id, request.page)
        end

      respond(conn, operation, request, result)
    end
  rescue
    _ -> Request.reject(conn, :authorization_unavailable)
  catch
    :throw, _ -> Request.reject(conn, :authorization_unavailable)
  end

  defp respond(conn, _, _, {:error, reason}), do: Request.reject(conn, reason)

  defp respond(conn, operation, request, {:ok, page}) do
    if valid_page?(page, operation, request) do
      conn |> put_resp_content_type("application/json") |> send_resp(200, Jason.encode!(page))
    else
      Request.reject(conn, :authorization_unavailable)
    end
  end

  defp respond(conn, _, _, _), do: Request.reject(conn, :authorization_unavailable)

  defp valid_page?(page, operation, request) do
    with true <- exact?(page, [operation, :next_cursor]),
         rows when is_list(rows) <- page[operation],
         true <- length(rows) <= request.page.limit,
         true <- Enum.all?(rows, &valid_row?(&1, operation, request.organization_id)),
         ids = Enum.map(rows, & &1.id),
         true <- ids == Enum.sort(Enum.uniq(ids)) do
      case page.next_cursor do
        nil ->
          true

        cursor ->
          rows != [] and
            Request.decode_cursor(cursor, operation, request.organization_id) ==
              {:ok, List.last(ids)}
      end
    else
      _ -> false
    end
  end

  defp valid_row?(row, :organizations, nil),
    do:
      exact?(row, [:id, :display_name, :organization_roles]) and Scope.identifier?(row.id) and
        name?(row.display_name) and roles?(row.organization_roles, true)

  defp valid_row?(row, :projects, organization),
    do:
      exact?(row, [:organization_id, :id, :display_name, :roles]) and
        row.organization_id == organization and Scope.identifier?(row.id) and
        name?(row.display_name) and roles?(row.roles, false)

  defp exact?(map, keys),
    do:
      is_map(map) and not is_struct(map) and map_size(map) == length(keys) and
        Enum.all?(keys, &Map.has_key?(map, &1))

  defp name?(nil), do: true

  defp name?(name) when is_binary(name) and byte_size(name) in 1..256,
    do:
      String.valid?(name) and String.printable?(name) and
        Enum.all?(String.to_charlist(name), &(&1 >= 32 and &1 not in 127..159))

  defp name?(_), do: false

  defp roles?(roles, empty?) when is_list(roles),
    do:
      (empty? or roles != []) and length(roles) <= 6 and roles == Enum.sort(Enum.uniq(roles)) and
        Enum.all?(roles, &(&1 in @roles))

  defp roles?(_, _), do: false
end
