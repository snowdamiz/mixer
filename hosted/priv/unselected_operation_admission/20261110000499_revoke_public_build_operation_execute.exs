defmodule MixerHosted.Repo.Migrations.RevokePublicBuildOperationExecute do
  use Ecto.Migration

  # Apply with the private operation schema before starting hosted services.
  def up do
    execute("""
    REVOKE EXECUTE ON FUNCTION
      public.mixer_build_operation_admissions_immutable(),
      public.mixer_build_operation_admit(text, text, bytea, bytea, bigint, uuid, bigint, bigint, text, timestamptz)
    FROM PUBLIC
    """)
  end

  def down do
    raise "private operation admission cannot restore PUBLIC EXECUTE"
  end
end
