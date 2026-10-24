defmodule MixerRawCapture.TestClock do
  def now_ms do
    case Process.get(:capture_clock_sequence) do
      [value | rest] ->
        Process.put(:capture_clock_sequence, rest)
        Process.put(:capture_clock_last, value)
        value

      [] ->
        Process.get(:capture_clock_last)

      nil ->
        System.monotonic_time(:millisecond)
    end
  end
end

