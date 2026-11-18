# Run only as an operator: mix run --no-start priv/restricted_processor/print_install_sql.exs
# Pipe the output into psql -v processor_database=YOUR_DATABASE with maintenance authority.
# Application startup never runs these statements.
alias MixerHosted.Builds.ProcessorProfile

statements =
  case System.argv() do
    [] -> ProcessorProfile.statements(:builds_v1)
    # Apply migrations 498 through 500 before granting the optional entry.
    # Start the builds_v1 processor with MIXER_BUILD_OPERATION_INTENT=durable_intent_v1.
    ["durable_intent_v1"] -> ProcessorProfile.operation_intent_statements(:durable_intent_v1)
    _ -> raise ArgumentError, "unsupported builds processor installation option"
  end

Enum.each(statements, &IO.puts(&1 <> ";"))
