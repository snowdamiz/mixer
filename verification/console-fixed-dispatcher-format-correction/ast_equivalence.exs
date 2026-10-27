[root, before_root | files] = System.argv()

normalize = fn ast ->
  Macro.prewalk(ast, fn
    {form, metadata, arguments} when is_list(metadata) -> {form, [], arguments}
    term -> term
  end)
end

digest = fn ast ->
  :crypto.hash(:sha256, :erlang.term_to_binary(ast)) |> Base.encode16(case: :lower)
end

Enum.each(files, fn relative ->
  before_ast =
    before_root
    |> Path.join(relative)
    |> File.read!()
    |> Code.string_to_quoted!(file: relative, columns: false, token_metadata: false)
    |> normalize.()

  after_ast =
    root
    |> Path.join(relative)
    |> File.read!()
    |> Code.string_to_quoted!(file: relative, columns: false, token_metadata: false)
    |> normalize.()

  true = before_ast === after_ast
  IO.puts(Enum.join([relative, digest.(before_ast), digest.(after_ast), "equal"], "\t"))
end)
