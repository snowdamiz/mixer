defmodule MixerAtomicStoragePreflight.Codec do
  @moduledoc "Synthetic deterministic fixed-schema codec. No accepted product module is loaded."
  @u64 18_446_744_073_709_551_615
  def encode(value, limit \\ 16_384) when is_integer(limit) and limit in 1..65_536 do
    encoded = enc(value)
    if byte_size(encoded) > limit, do: raise(ArgumentError, "encoded budget")
    encoded
  end
  defp enc(nil), do: <<0xF6>>
  defp enc(n) when is_integer(n) and n in 0..@u64, do: head(0,n)
  defp enc({:bytes,b}) when is_binary(b), do: head(2,byte_size(b)) <> b
  defp enc(t) when is_binary(t) do
    if not String.valid?(t), do: raise(ArgumentError,"UTF8")
    head(3,byte_size(t)) <> t
  end
  defp enc(a) when is_list(a) and length(a)<=256, do: head(4,length(a)) <> IO.iodata_to_binary(Enum.map(a,&enc/1))
  defp enc(_), do: raise(ArgumentError,"unsupported type")
  defp head(m,n) when n<24, do: <<m*32+n>>
  defp head(m,n) when n<=255, do: <<m*32+24,n>>
  defp head(m,n) when n<=65_535, do: <<m*32+25,n::16>>
  defp head(m,n) when n<=4_294_967_295, do: <<m*32+26,n::32>>
  defp head(m,n), do: <<m*32+27,n::64>>
  def hash(domain,b), do: :crypto.hash(:sha256,domain <> <<0>> <> b)
  def b(v), do: {:bytes,v}
  def hex(v), do: Base.encode16(v,case: :lower)
  def unhex(v), do: Base.decode16!(v,case: :lower)
  def uuid(v), do: v |> String.replace("-","") |> unhex()
  def from_display(d) do
    keys = ~w(audit_schema id tenant actor decision target action reason request_id source_ip recorded_at previous_state current_state previous_hash request_hash hash)
    if Enum.sort(Map.keys(d)) != Enum.sort(keys), do: raise(ArgumentError,"closed display")
    [principal,kind,binding,profile,version,issuer,subject,client,credential,family,auth] = d["actor"]
    [time,pr,ar,fr,orr,pjr,members] = d["decision"]
    [o,p,a,e,platform,runtime,manifest] = d["target"]
    [d["audit_schema"],String.to_integer(d["id"]),d["tenant"],
      [b(uuid(principal)),kind,b(uuid(binding)),profile,String.to_integer(version),b(unhex(issuer)),b(unhex(subject)),b(unhex(client)),b(unhex(credential)),b(uuid(family)),String.to_integer(auth)],
      [String.to_integer(time),String.to_integer(pr),String.to_integer(ar),String.to_integer(fr),String.to_integer(orr),String.to_integer(pjr),Enum.map(members,fn [id,role,rev]->[b(uuid(id)),role,String.to_integer(rev)] end)],
      [o,p,a,e,platform,if(runtime,do: b(unhex(runtime)),else: nil),if(manifest,do: b(unhex(manifest)),else: nil)],d["action"],d["reason"],b(uuid(d["request_id"])),d["source_ip"],String.to_integer(d["recorded_at"]),b(unhex(d["previous_state"])),b(unhex(d["current_state"])),b(unhex(d["previous_hash"])),b(unhex(d["request_hash"]))]
  end
end
