[before_path, after_path, output] = System.argv()
before_source = File.read!(before_path)
after_source = File.read!(after_path)

normalize_ast = fn source ->
  source
  |> Code.string_to_quoted!()
  |> Macro.prewalk(fn
    {name, metadata, arguments} when is_list(metadata) -> {name, [], arguments}
    other -> other
  end)
end

normalize_tokens = fn source ->
  {:ok, tokens, []} = :elixir.string_to_tokens(String.to_charlist(source), 1, 1, "candidate.ex", [])

  tokens
  |> Enum.reject(&(elem(&1, 0) == :eol))
  |> Enum.map(fn token ->
    # Token positions and EOL tokens are formatter whitespace. The AST check
    # independently checks that newline changes have no grammar effect.
    case token do
      {:in_op, _, :"not in", _second_position} -> {:in_op, :"not in"}
      other -> other |> Tuple.to_list() |> List.delete_at(1) |> List.to_tuple()
    end
  end)
end

before_ast = normalize_ast.(before_source)
after_ast = normalize_ast.(after_source)
before_tokens = normalize_tokens.(before_source)
after_tokens = normalize_tokens.(after_source)
true = before_ast == after_ast
true = before_tokens == after_tokens

hash = fn value ->
  :crypto.hash(:sha256, :erlang.term_to_binary(value)) |> Base.encode16(case: :lower)
end

result = %{
  ast_equivalent: true,
  token_stream_equivalent_ignoring_positions_and_eol: true,
  normalized_ast_sha256: hash.(before_ast),
  normalized_token_stream_sha256: hash.(before_tokens),
  tokens: length(before_tokens),
  elixir: System.version(),
  otp: System.otp_release()
}

File.write!(output, :json.encode(result))
IO.inspect(result, label: "formatter_equivalence")
