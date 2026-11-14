# Run only as an operator: mix run --no-start priv/restricted_processor/print_install_sql.exs
# Pipe the output into psql -v processor_database=YOUR_DATABASE with maintenance authority.
# Application startup never runs these statements.
Enum.each(MixerHosted.Builds.ProcessorProfile.statements(:builds_v1), &IO.puts(&1 <> ";"))
