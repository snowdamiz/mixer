defmodule MixerHosted.BrowserAuth.CustodyTest do
  use ExUnit.Case, async: true
  alias MixerHosted.BrowserAuth.{Custody, Vault}

  @reference "vault://mixer/browser-session-v1"
  @bytes :binary.copy(<<37>>, 32)
  @error {:error, :session_unavailable}

  defp material(reference \\ @reference),
    do: %{reference: reference, key_id: "synthetic-key-v1", key_bytes: @bytes}

  test "wraps exactly the existing validated external Vault key without resolving its reference" do
    assert {:ok, custody} = Custody.new(@reference, material())
    assert {:ok, key} = Vault.key("synthetic-key-v1", @bytes)
    assert custody == %Custody{reference: @reference, key: key}
    assert Enum.sort(Map.keys(custody)) == [:__struct__, :key, :reference]
  end

  test "the constructed key performs the actual versioned preauth AEAD roundtrip" do
    {:ok, custody} = Custody.new(@reference, material())
    csrf = Base.url_encode64(:binary.copy(<<31>>, 32), padding: false)

    context = %{
      purpose: :preauth,
      browser_id: :binary.copy(<<1>>, 16),
      cookie_digest: :binary.copy(<<2>>, 32),
      csrf_digest: :crypto.hash(:sha256, csrf),
      epoch: 1,
      revision: 1,
      generation: Base.url_encode64(:binary.copy(<<3>>, 32), padding: false),
      vault_generation: 1,
      config_digest: :binary.copy(<<4>>, 32),
      profile_id: "human-main",
      profile_version: 7,
      principal_id: nil,
      family_id: nil,
      credential_ref: nil,
      credential_revision: nil
    }

    plaintext = %Vault.Preauth{csrf: csrf}
    assert {:ok, sealed} = Vault.seal(custody.key, context, plaintext)
    assert {:ok, ^plaintext} = Vault.open(custody.key, context, sealed)

    assert {:error, :vault_unavailable} =
             Vault.open(custody.key, %{context | revision: 2}, sealed)

    {:ok, wrong_key} = Vault.key("synthetic-key-v1", :binary.copy(<<38>>, 32))
    assert {:error, :vault_unavailable} = Vault.open(wrong_key, context, sealed)
  end

  test "material has exactly the three atom keys and no input aliases" do
    for key <- Map.keys(material()) do
      assert Custody.new(@reference, Map.delete(material(), key)) == @error
    end

    for key <- [:resolver, :callback, :key, :password, :__struct__, "reference"] do
      assert Custody.new(@reference, Map.put(material(), key, "synthetic-extra")) == @error
    end

    assert Custody.new(@reference, Map.new(material(), fn {k, v} -> {to_string(k), v} end)) ==
             @error
  end

  test "references match exactly including case rather than resolving equivalent destinations" do
    for other <- ["vault://mixer/other", "vault://Mixer/browser-session-v1", nil, 1] do
      assert Custody.new(@reference, material(other)) == @error
    end
  end

  test "canonical references accept the Config grammar and exact 256-byte limit" do
    for reference <- [
          "vault://a",
          "vault://A_z-9.X/path_v1",
          "vault://" <> String.duplicate("x", 248)
        ] do
      assert {:ok, %Custody{reference: ^reference}} = Custody.new(reference, material(reference))
    end
  end

  test "references reject empty unsafe aliased malformed and overbound values" do
    for reference <- [
          nil,
          [],
          :vault,
          1,
          "",
          "vault://",
          "secret://mixer/key",
          "VAULT://mixer/key",
          "vault://a//b",
          "vault://a/",
          "vault://a/./b",
          "vault://a/../b",
          "vault://a%2fb",
          "vault://a?key=synthetic",
          "vault://a#fragment",
          "vault://a\\b",
          "vault://é",
          "vault://a" <> <<0>>,
          "vault://" <> <<255>>,
          "vault://" <> String.duplicate("x", 249)
        ] do
      assert Custody.new(reference, material(reference)) == @error
    end
  end

  test "key bounds are delegated to Vault and cannot admit a fallback or malformed key" do
    for id <- ["x", String.duplicate("k", 128), "key.ID_v-1"] do
      assert {:ok, %Custody{key: %Vault.Key{id: ^id}}} =
               Custody.new(@reference, %{material() | key_id: id})
    end

    for id <- [nil, 1, "", "key/one", "key secret", "key" <> <<0>>, String.duplicate("k", 129)] do
      assert Custody.new(@reference, %{material() | key_id: id}) == @error
    end

    for bytes <- [
          nil,
          "",
          :binary.copy(<<37>>, 31),
          :binary.copy(<<37>>, 33),
          List.duplicate(37, 32)
        ] do
      assert Custody.new(@reference, %{material() | key_bytes: bytes}) == @error
    end
  end

  test "caller functions are rejected as data without execution" do
    caller = self()
    hook = fn -> send(caller, :unexpected_custody_hook) end

    for material <- [hook, Map.put(material(), :resolver, hook), %{material() | key_bytes: hook}] do
      assert Custody.new(@reference, material) == @error
    end

    refute_received :unexpected_custody_hook
  end

  test "Inspect and every public error are closed and contain no supplied material" do
    {:ok, custody} = Custody.new(@reference, material())
    assert inspect(custody) == "#MixerHosted.BrowserAuth.Custody<...>"

    for input <- [
          nil,
          [],
          "synthetic-sensitive",
          %{material() | key_bytes: "synthetic-sensitive"}
        ] do
      assert Custody.new(@reference, input) == @error
    end

    for secret <- [@reference, "synthetic-key-v1", @bytes] do
      refute inspect(custody) =~ secret
    end
  end
end
