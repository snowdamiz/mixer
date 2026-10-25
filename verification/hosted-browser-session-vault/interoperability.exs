alias MixerHosted.BrowserAuth.Vault
alias Vault.{Active, Preauth, Verifier}

csrf = Base.url_encode64(:binary.copy(<<11>>, 32), padding: false)
generation = Base.url_encode64(:binary.copy(<<13>>, 32), padding: false)
verifier = Base.url_encode64(:binary.copy(<<12>>, 32), padding: false)
{:ok, key} = Vault.key("session-key-v1", :binary.copy(<<42>>, 32))

preauth = %{
  purpose: :preauth,
  browser_id: :binary.copy(<<1>>, 16),
  cookie_digest: :binary.copy(<<2>>, 32),
  csrf_digest: :crypto.hash(:sha256, csrf),
  epoch: 1,
  revision: 2,
  generation: generation,
  vault_generation: 3,
  config_digest: :binary.copy(<<4>>, 32),
  profile_id: "human-main",
  profile_version: 7,
  principal_id: nil,
  family_id: nil,
  credential_ref: nil,
  credential_revision: nil
}

active =
  Map.merge(preauth, %{
    purpose: :active,
    principal_id: "person-1",
    family_id: "browser_" <> generation,
    credential_ref: "external-jti-1",
    credential_revision: 5
  })

attempt =
  Map.take(preauth, [
    :browser_id,
    :cookie_digest,
    :epoch,
    :revision,
    :generation,
    :config_digest,
    :profile_id,
    :profile_version
  ])
  |> Map.merge(%{
    purpose: :attempt,
    state_digest: :binary.copy(<<5>>, 32),
    issuer: "https://id.example.test",
    client_id: "console-client",
    redirect_uri: "https://console.example.test/auth/callback",
    expires_at: 123_456
  })

for {context, plaintext} <- [
      {preauth, %Preauth{csrf: csrf}},
      {active, %Active{csrf: csrf, access_token: "header.payload.signature"}},
      {attempt, %Verifier{verifier: verifier}}
    ] do
  {:ok, sealed} = Vault.seal(key, context, plaintext)
  {:ok, aad} = Vault.associated_data(key.id, context)

  IO.puts(
    Enum.join(
      [
        Atom.to_string(context.purpose)
        | Enum.map(
            [key.bytes, sealed.iv, aad, sealed.ciphertext, sealed.tag],
            &Base.encode16(&1, case: :lower)
          )
      ],
      "|"
    )
  )
end
