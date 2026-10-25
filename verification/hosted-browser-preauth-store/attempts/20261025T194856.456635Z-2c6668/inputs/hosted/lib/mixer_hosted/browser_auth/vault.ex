defmodule MixerHosted.BrowserAuth.Vault do
  @moduledoc """
  Pure bounded AES-256-GCM custody for ordinary browser-session secrets.

  The trusted lifecycle owner supplies a reviewed runtime key and current durable
  context. This module does not authenticate a user, load a key, perform I/O, or
  establish that context came from a database transaction. No BEAM memory
  zeroization is claimed. Never log inputs, keys or decrypted values.
  """

  defmodule Key do
    @moduledoc "Externally supplied key material. Inspect intentionally reveals no fields."
    @derive {Inspect, only: []}
    @enforce_keys [:id, :bytes]
    defstruct [:id, :bytes]
  end

  defmodule Sealed do
    @moduledoc "Database-safe encryption fields; plaintext is never included."
    @derive {Inspect, only: [:version]}
    @enforce_keys [:version, :key_id, :iv, :tag, :ciphertext]
    defstruct [:version, :key_id, :iv, :tag, :ciphertext]
  end

  defmodule Preauth do
    @moduledoc "Closed pre-authentication CSRF envelope."
    @derive {Inspect, only: []}
    @enforce_keys [:csrf]
    defstruct [:csrf]
  end

  defmodule Active do
    @moduledoc "Closed CSRF and access-token envelope; no refresh or ID token."
    @derive {Inspect, only: []}
    @enforce_keys [:csrf, :access_token]
    defstruct [:csrf, :access_token]
  end

  defmodule Verifier do
    @moduledoc "Closed short-lived PKCE verifier envelope."
    @derive {Inspect, only: []}
    @enforce_keys [:verifier]
    defstruct [:verifier]
  end

  @max_integer 9_007_199_254_740_991
  @max_profile_version 2_147_483_647
  @max_ciphertext 8192
  @session_keys ~w(purpose browser_id cookie_digest csrf_digest epoch revision generation
    vault_generation config_digest profile_id profile_version principal_id family_id
    credential_ref credential_revision)a
  @attempt_keys ~w(purpose state_digest browser_id cookie_digest epoch revision generation
    config_digest profile_id profile_version issuer client_id redirect_uri expires_at)a
  @link_keys ~w(principal_id family_id credential_ref credential_revision)a
  @error {:error, :vault_unavailable}

  @doc "Wraps exactly 32 externally supplied key bytes and a bounded, nonsecret key ID."
  def key(id, bytes) when is_binary(bytes) and byte_size(bytes) == 32 do
    if key_id?(id), do: {:ok, %Key{id: id, bytes: bytes}}, else: @error
  end

  def key(_, _), do: @error

  @doc "Encrypts one typed envelope using a fresh independent 96-bit platform CSPRNG IV."
  def seal(key, context, plaintext) do
    with true <- key?(key),
         {:ok, aad} <- associated_data(key.id, context),
         {:ok, encoded} <- encode_plaintext(context, plaintext) do
      encrypt(key, aad, encoded)
    else
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  @doc "Authenticates exact context and key version before parsing the closed plaintext."
  def open(key, context, sealed) do
    with true <- key?(key) and sealed?(sealed),
         true <- sealed.key_id == key.id,
         {:ok, aad} <- associated_data(key.id, context),
         {:ok, plaintext} <- decrypt(key, sealed, aad),
         {:ok, result} <- decode_plaintext(context, plaintext) do
      {:ok, result}
    else
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  @doc "Deterministic version-1 AAD bytes; all inputs are bounded public durable metadata."
  def associated_data(key_id, context) do
    with true <- key_id?(key_id),
         {:ok, domain, fields} <- context_fields(context) do
      {:ok, IO.iodata_to_binary([domain, Enum.map([<<1>>, key_id | fields], &field/1)])}
    else
      _ -> @error
    end
  end

  defp encrypt(key, aad, plaintext) do
    iv = :crypto.strong_rand_bytes(12)

    {ciphertext, tag} =
      :crypto.crypto_one_time_aead(:aes_256_gcm, key.bytes, iv, plaintext, aad, 16, true)

    {:ok, %Sealed{version: 1, key_id: key.id, iv: iv, tag: tag, ciphertext: ciphertext}}
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  defp decrypt(key, sealed, aad) do
    case :crypto.crypto_one_time_aead(
           :aes_256_gcm,
           key.bytes,
           sealed.iv,
           sealed.ciphertext,
           aad,
           sealed.tag,
           false
         ) do
      plaintext when is_binary(plaintext) -> {:ok, plaintext}
      _ -> @error
    end
  rescue
    _ -> @error
  catch
    _, _ -> @error
  end

  defp key?(%Key{id: id, bytes: bytes} = key),
    do: map_size(key) == 3 and key_id?(id) and is_binary(bytes) and byte_size(bytes) == 32

  defp key?(_), do: false

  defp sealed?(%Sealed{version: 1, key_id: id, iv: iv, tag: tag, ciphertext: ciphertext} = sealed) do
    map_size(sealed) == 6 and key_id?(id) and raw?(iv, 12) and raw?(tag, 16) and
      is_binary(ciphertext) and byte_size(ciphertext) in 1..@max_ciphertext
  end

  defp sealed?(_), do: false

  defp context_fields(%{purpose: purpose} = c) when purpose in [:preauth, :active] do
    with true <- exact_keys?(c, @session_keys),
         true <- raw?(c.browser_id, 16) and raw?(c.cookie_digest, 32) and raw?(c.csrf_digest, 32),
         true <- positive?(c.epoch) and positive?(c.revision) and positive?(c.vault_generation),
         true <- token?(c.generation) and raw?(c.config_digest, 32),
         true <- text?(c.profile_id, 128) and profile_version?(c.profile_version),
         {:ok, linkage} <- linkage(c, purpose) do
      {:ok, "mixer.browser.vault.v1\0",
       [
         kind(purpose),
         c.browser_id,
         c.cookie_digest,
         c.csrf_digest,
         number(c.epoch),
         number(c.revision),
         c.generation,
         number(c.vault_generation),
         c.config_digest,
         c.profile_id,
         number(c.profile_version) | linkage
       ]}
    else
      _ -> @error
    end
  end

  defp context_fields(%{purpose: :attempt} = c) do
    with true <- exact_keys?(c, @attempt_keys),
         true <- raw?(c.state_digest, 32) and raw?(c.browser_id, 16) and raw?(c.cookie_digest, 32),
         true <- positive?(c.epoch) and positive?(c.revision) and token?(c.generation),
         true <- raw?(c.config_digest, 32) and text?(c.profile_id, 128),
         true <- profile_version?(c.profile_version) and text?(c.issuer, 2048),
         true <-
           text?(c.client_id, 256) and text?(c.redirect_uri, 2048) and positive?(c.expires_at) do
      {:ok, "mixer.browser.attempt.v1\0",
       [
         kind(:attempt),
         c.state_digest,
         c.browser_id,
         c.cookie_digest,
         number(c.epoch),
         number(c.revision),
         c.generation,
         c.config_digest,
         c.profile_id,
         number(c.profile_version),
         c.issuer,
         c.client_id,
         c.redirect_uri,
         number(c.expires_at)
       ]}
    else
      _ -> @error
    end
  end

  defp context_fields(_), do: @error

  defp linkage(c, :preauth) do
    if Enum.all?(@link_keys, &(Map.fetch!(c, &1) == nil)), do: {:ok, [<<0>>]}, else: @error
  end

  defp linkage(c, :active) do
    if text?(c.principal_id, 128) and text?(c.family_id, 128) and
         text?(c.credential_ref, 256) and positive?(c.credential_revision),
       do:
         {:ok,
          [<<1>>, c.principal_id, c.family_id, c.credential_ref, number(c.credential_revision)]},
       else: @error
  end

  defp encode_plaintext(%{purpose: :preauth} = c, %Preauth{csrf: csrf} = p) do
    if map_size(p) == 2 and valid_csrf?(c, csrf),
      do: {:ok, IO.iodata_to_binary([<<1>>, field(csrf)])},
      else: @error
  end

  defp encode_plaintext(%{purpose: :active} = c, %Active{csrf: csrf, access_token: token} = p) do
    if map_size(p) == 3 and valid_csrf?(c, csrf) and bearer?(token),
      do: {:ok, IO.iodata_to_binary([<<2>>, field(csrf), field(token)])},
      else: @error
  end

  defp encode_plaintext(%{purpose: :attempt}, %Verifier{verifier: verifier} = p) do
    if map_size(p) == 2 and token?(verifier),
      do: {:ok, IO.iodata_to_binary([<<3>>, field(verifier)])},
      else: @error
  end

  defp encode_plaintext(_, _), do: @error

  defp decode_plaintext(
         %{purpose: :preauth} = c,
         <<1, 43::unsigned-big-32, csrf::binary-size(43)>>
       ) do
    if valid_csrf?(c, csrf), do: {:ok, %Preauth{csrf: csrf}}, else: @error
  end

  defp decode_plaintext(
         %{purpose: :active} = c,
         <<2, 43::unsigned-big-32, csrf::binary-size(43), size::unsigned-big-32,
           token::binary-size(size)>>
       ) do
    if valid_csrf?(c, csrf) and bearer?(token),
      do: {:ok, %Active{csrf: csrf, access_token: token}},
      else: @error
  end

  defp decode_plaintext(
         %{purpose: :attempt},
         <<3, 43::unsigned-big-32, verifier::binary-size(43)>>
       ) do
    if token?(verifier), do: {:ok, %Verifier{verifier: verifier}}, else: @error
  end

  defp decode_plaintext(_, _), do: @error

  defp valid_csrf?(context, csrf),
    do: token?(csrf) and :crypto.hash_equals(:crypto.hash(:sha256, csrf), context.csrf_digest)

  defp bearer?(value) when is_binary(value) and byte_size(value) in 1..4089 do
    case :binary.split(value, "=") do
      [token] -> bearer_body?(token)
      [token, padding] -> bearer_body?(token) and ascii?(padding, &(&1 == ?=))
    end
  end

  defp bearer?(_), do: false

  defp bearer_body?(value),
    do:
      byte_size(value) > 0 and
        ascii?(value, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in ~c"._~+/-"))

  defp token?(value) when is_binary(value) and byte_size(value) == 43 do
    case Base.url_decode64(value, padding: false) do
      {:ok, bytes} when byte_size(bytes) == 32 ->
        Base.url_encode64(bytes, padding: false) == value

      _ ->
        false
    end
  end

  defp token?(_), do: false

  defp key_id?(value),
    do:
      is_binary(value) and byte_size(value) in 1..128 and
        ascii?(value, &(&1 in ?a..?z or &1 in ?A..?Z or &1 in ?0..?9 or &1 in ~c"._-"))

  defp exact_keys?(map, keys),
    do: map_size(map) == length(keys) and Enum.all?(keys, &Map.has_key?(map, &1))

  defp raw?(value, size), do: is_binary(value) and byte_size(value) == size

  defp text?(value, limit),
    do:
      is_binary(value) and byte_size(value) in 1..limit and String.valid?(value) and
        :binary.match(value, <<0>>) == :nomatch

  defp positive?(value), do: is_integer(value) and value in 1..@max_integer
  defp profile_version?(value), do: is_integer(value) and value in 1..@max_profile_version
  defp field(value), do: [<<byte_size(value)::unsigned-big-32>>, value]
  defp number(value), do: <<value::unsigned-big-64>>
  defp kind(:preauth), do: <<1>>
  defp kind(:active), do: <<2>>
  defp kind(:attempt), do: <<3>>
  defp ascii?(<<>>, _), do: true
  defp ascii?(<<byte, rest::binary>>, check), do: check.(byte) and ascii?(rest, check)
end
