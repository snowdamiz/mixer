# Run on a reviewed local installation after build-create and processor provisioning.
# Execute the output as browser_schema_owner in the target database.
IO.puts("BEGIN;")
Enum.each(MixerHosted.CustomerBuilds.CancelSchema.statements(), &IO.puts(&1 <> ";"))
IO.puts("COMMIT;")
