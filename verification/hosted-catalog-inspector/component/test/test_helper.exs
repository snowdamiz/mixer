ExUnit.start(seed: 0)

defmodule MixerCatalogInspector.Evidence do
  def path(name), do: Path.join(System.fetch_env!("MIXER_INSPECTOR_OUT"), name)
  def save(name, value), do: File.write!(path(name), Jason.encode!(value, pretty: true))
end
