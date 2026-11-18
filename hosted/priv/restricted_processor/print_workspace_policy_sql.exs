# Run with the existing workspace writer and restricted builds profile provisioned.
IO.puts("BEGIN;")

for statement <- MixerHosted.CustomerWorkspace.SelfServiceSchema.processor_policy_statements(),
    do: IO.puts(statement <> ";")

IO.puts("COMMIT;")
