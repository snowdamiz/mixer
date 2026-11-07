defmodule MixerHosted.BrowserAuth.CatalogManifest do
  @moduledoc false

  # This is a build-time source expectation, never a snapshot of the database
  # being admitted. Changing the installed function cannot change this value.
  @functions MixerHosted.BrowserAuth.StorageSchema.catalog_manifest().functions
  @argument_names Map.new(
                    MixerHosted.BrowserAuth.StorageSchema.statements()
                    |> Enum.filter(
                      &String.starts_with?(&1, "CREATE FUNCTION public.mixer_browser_")
                    ),
                    fn sql ->
                      [head | _] = String.split(sql, ") RETURNS ", parts: 2)
                      [name, args] = String.split(head, "(", parts: 2)
                      name = String.replace_prefix(name, "CREATE FUNCTION public.", "")

                      names =
                        if args == "",
                          do: nil,
                          else: Enum.map(String.split(args, ","), &(String.split(&1) |> hd()))

                      {name, names}
                    end
                  )
  @returns %{
    "mixer_browser_bootstrap" => "jsonb",
    "mixer_browser_load" => "jsonb",
    "mixer_browser_begin" => "jsonb",
    "mixer_browser_claim" => "jsonb",
    "mixer_browser_provider_reject" => "jsonb",
    "mixer_browser_fail_claim" => "boolean",
    "mixer_browser_activate" => "jsonb",
    "mixer_browser_logout" => "boolean",
    "mixer_browser_expire" => "boolean",
    "mixer_browser_snapshot" => "jsonb",
    "mixer_browser_cipher_valid" => "boolean",
    "mixer_browser_audit" => "void",
    "mixer_browser_integrity" => "trigger",
    "mixer_browser_attempt_integrity" => "trigger",
    "mixer_browser_event_immutable" => "trigger",
    "mixer_browser_event_integrity" => "trigger",
    "mixer_browser_lock_existing" => "void",
    "mixer_browser_revoke_existing" => "void"
  }
  # Independently transcribed, in declared field order, from the accepted
  # ordinary StorageSchema types. These expectations do not use pg_attribute.
  @composites %{
    "mixer_browser_cipher" => [
      {"key_id", "text"},
      {"iv", "bytea"},
      {"tag", "bytea"},
      {"ciphertext", "bytea"}
    ],
    "mixer_browser_attempt" => [
      {"state_digest", "bytea"},
      {"nonce_digest", "bytea"},
      {"profile_id", "text"},
      {"profile_version", "integer"},
      {"issuer", "text"},
      {"client_id", "text"},
      {"redirect_uri", "text"},
      {"expires_at", "bigint"},
      {"cipher", "public.mixer_browser_cipher"}
    ],
    "mixer_browser_verified" => [
      {"profile_id", "text"},
      {"profile_version", "integer"},
      {"issuer", "text"},
      {"subject", "text"},
      {"client_id", "text"},
      {"credential_ref", "text"},
      {"issued_at", "bigint"},
      {"expires_at", "bigint"},
      {"scopes", "text[]"},
      {"profile_revision", "bigint"},
      {"binding_revision", "bigint"},
      {"principal_revision", "bigint"}
    ]
  }

  unless map_size(@functions) == 18 and
           MapSet.new(Map.keys(@functions)) == MapSet.new(Map.keys(@returns)) do
    raise "reviewed browser function expectation is incomplete"
  end

  unless Enum.all?(@functions, fn {_name, expected} ->
           byte_size(expected.source) <= 65_536 and
             length(String.split(expected.signature, ",")) <= 16
         end) do
    raise "reviewed browser function exceeds fixed catalog wire bounds"
  end

  def functions, do: @functions
  def argument_names, do: @argument_names
  def returns, do: @returns
  def composites, do: @composites
end
