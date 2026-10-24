defmodule MixerAtomicStoragePreflight.Blob do
  @moduledoc "One-process, owned-root local DEVELOPMENT fixture. Never production durability."
  alias MixerAtomicStoragePreflight.Codec
  @max 4_194_304
  @quota 16_777_216
  @count 8
  def open(root) do
    File.mkdir_p!(root)
    File.chmod!(root,0o700)
    # Reopen verifies every immutable file; no symlink or unknown-path traversal.
    files=File.ls!(root)
    if length(files)>@count, do: raise(ArgumentError,"object count")
    bytes=Enum.reduce(files,0,fn name,n ->
      if byte_size(name)!=64 or name!=Codec.hex(Codec.unhex(name)), do: raise(ArgumentError,"filename")
      path=Path.join(root,name)
      if File.lstat!(path).type!=:regular, do: raise(ArgumentError,"file type")
      value=File.read!(path)
      if byte_size(value) not in 1..@max or Codec.hex(:crypto.hash(:sha256,value))!=name, do: raise(ArgumentError,"corruption")
      n+byte_size(value)
    end)
    if bytes>@quota, do: raise(ArgumentError,"quota")
    %{root: root,bytes: bytes,count: length(files)}
  end
  def stage(store,value) when is_binary(value) do
    if byte_size(value) not in 1..@max, do: raise(ArgumentError,"size")
    hash=Codec.hex(:crypto.hash(:sha256,value));path=Path.join(store.root,hash)
    if File.exists?(path) do
      if File.read!(path)!=value, do: raise(ArgumentError,"corruption")
      {store,"sha256:"<>hash}
    else
      # Check quota before exclusive creation and never replace another immutable object.
      if store.count+1>@count or store.bytes+byte_size(value)>@quota, do: raise(ArgumentError,"quota")
      {:ok,file}=:file.open(String.to_charlist(path),[:write,:binary,:exclusive,:raw])
      try do
        :ok=:file.write(file,value)
        :ok=:file.sync(file)
      after
        :file.close(file)
      end
      File.chmod!(path,0o400)
      {%{store|bytes: store.bytes+byte_size(value),count: store.count+1},"sha256:"<>hash}
    end
  end
  def read(store,"sha256:"<>hash) do
    if byte_size(hash)!=64 or hash!=Codec.hex(Codec.unhex(hash)), do: raise(ArgumentError,"reference")
    path=Path.join(store.root,hash)
    if File.lstat!(path).type!=:regular, do: raise(ArgumentError,"file type")
    value=File.read!(path)
    if Codec.hex(:crypto.hash(:sha256,value))!=hash, do: raise(ArgumentError,"corruption")
    value
  end
  def reconcile(store,referenced,uncertain) do
    # Called only outside transactions, after complete authoritative reference scan.
    # Any uncertain COMMIT freezes collection, even for apparently orphaned objects.
    if uncertain, do: store, else: collect(store,referenced)
  end
  defp collect(store,referenced) do
    Enum.each(File.ls!(store.root),fn name ->
      if not MapSet.member?(referenced,"sha256:"<>name), do: File.rm!(Path.join(store.root,name))
    end)
    open(store.root)
  end
end
