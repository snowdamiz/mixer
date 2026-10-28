# One root-authorized formatting-only VM. No product source evaluation or compilation.
true = System.version() == "1.20.4"
true = System.otp_release() == "29"
:"nonode@nohost" = node()
2 = :erlang.system_info(:schedulers_online)
false = List.keymember?(Application.started_applications(), :mixer_hosted, 0)
[output | sources] = System.argv()
3 = length(sources)

IO.puts("FORMAT_RUNTIME elixir=#{System.version()} otp=#{System.otp_release()} node=#{node()} schedulers=2 product_application_started=false")

for source <- sources do
  original = File.read!(source)
  formatted = Code.format_string!(original, file: source) |> IO.iodata_to_binary()
  File.write!(Path.join(output, Path.basename(source)), formatted <> "\n")
  IO.puts("FORMATTED " <> Path.basename(source))
end

System.halt(0)
