defmodule MixerHosted.Repo.Migrations.AddNativeDevelopmentAttestations do
  use Ecto.Migration

  def up do
    for sql <- MixerHosted.CustomerBuilds.AttestationSchema.statements(), do: execute(sql)
  end

  def down do
    raise "native development attestation records are append-only"
  end
end
