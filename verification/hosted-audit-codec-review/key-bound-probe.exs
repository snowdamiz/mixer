# Finite measurements only: input allocation happens before the measured call.
alias MixerHosted.Audit.UploadEvent
Code.ensure_loaded!(UploadEvent)
base = File.read!(System.fetch_env!("REVIEW_VECTORS")) |> Jason.decode!()
raw = base["cases"] |> hd() |> Map.fetch!("row")
binary = ~w(event_cbor event_hash previous_hash previous_state current_state display_bytes)
row = Map.new(raw, fn {k, v} ->
  {String.to_existing_atom(k), if(k in binary, do: Base.decode16!(v, case: :lower), else: v)}
end)
samples = for size <- [1024, 1_048_576, 4_194_304], repeat <- 1..3 do
  prefix = :binary.copy("x", size)
  display = Map.new(0..15, fn n -> {prefix <> <<n>>, nil} end)
  retained = Map.new(0..9, fn n -> {prefix <> <<n>>, nil} end)
  # Known-key controls use the same already-allocated hostile values, avoiding rendering.
  bounded_display = Map.put(row.display_json, "reason", prefix)
  bounded_row = Map.put(row, :event_hash, prefix)
  values = for {label, argument, function} <- [
    {"unknown_display_keys", display, &UploadEvent.decode/1},
    {"known_display_oversized_value", bounded_display, &UploadEvent.decode/1},
    {"unknown_row_keys", retained, &UploadEvent.validate_row/1},
    {"known_row_oversized_value", bounded_row, &UploadEvent.validate_row/1}
  ] do
    :erlang.garbage_collect()
    {microseconds, result} = :timer.tc(fn ->
      for _ <- 1..20 do
        {:error, :invalid_audit_event} = function.(argument)
      end
      :rejected
    end)
    %{label: label, key_or_value_bytes: size, calls: 20, elapsed_microseconds: microseconds,
      repeat: repeat, result: result}
  end
  values
end
IO.puts(Jason.encode!(%{measurements: List.flatten(samples),
  scope: "Finite host timing observations; already allocated input; not a total memory benchmark or a timing-based pass/fail gate."}))
