case System.argv() do
  ["configuration", mix_file, output_dir] ->
    Mix.start()
    Mix.env(:test)
    Code.require_file(Path.expand(mix_file))
    project = MixerHosted.MixProject.project()

    expected = [
      "test/mixer_hosted/authorization/jit_policy_spec.exs",
      "test/mixer_hosted/browser_auth/migration_spec.exs",
      "test/mixer_hosted/browser_auth/storage_fixture.exs",
      "test/mixer_hosted/browser_auth/storage_spec.exs"
    ]

    ^expected = Keyword.fetch!(project, :test_ignore_filters)
    false = Keyword.has_key?(project, :test_load_filters)
    false = Keyword.has_key?(project, :test_pattern)

    selected = Keyword.take(project, [:elixirc_paths, :aliases, :test_ignore_filters])
    true = Keyword.fetch!(selected, :elixirc_paths) == ["lib", "test/support"]
    true = Keyword.fetch!(selected, :aliases) == [test: "test --no-start"]

    render = fn value ->
      inspect(value, pretty: true, limit: :infinity, printable_limit: :infinity) <> "\n"
    end

    File.write!(Path.join(output_dir, "fixture-config.exs"), render.(selected))

    File.write!(
      Path.join(output_dir, "baseline-config.exs"),
      render.(Keyword.delete(selected, :test_ignore_filters))
    )

    IO.puts(
      "Read hosted project configuration only; no dependencies, application or test modules loaded."
    )

    IO.puts(render.(selected))

  ["implementation", output_file] ->
    selections = [
      {Mix.Tasks.Test,
       [
         :any_file_matches?,
         :classify_test_files,
         :get_test_ignore_filters,
         :warn_misnamed_test_files,
         :do_run,
         :abort_due_to_warnings
       ]},
      {Mix.Compilers.Test, [:require_and_run]}
    ]

    evidence =
      for {module, names} <- selections do
        path = :code.which(module)

        {:ok, {^module, [{:abstract_code, {:raw_abstract_v1, forms}}]}} =
          :beam_lib.chunks(path, [:abstract_code])

        functions =
          for {:function, _, name, _, _} = form <- forms, name in names, do: :erl_pp.form(form)

        [
          "%% Official installed module: ",
          inspect(module),
          "\n",
          "%% BEAM: ",
          List.to_string(path),
          "\n",
          "%% BEAM SHA-256: ",
          Base.encode16(:crypto.hash(:sha256, File.read!(path)), case: :lower),
          "\n",
          "%% Compile information: ",
          inspect(module.module_info(:compile)),
          "\n\n",
          functions
        ]
      end

    File.write!(output_file, evidence)

    IO.puts(
      "Extracted the installed Mix discovery, warning and test-require implementation from BEAM abstract code."
    )
end
