defmodule MixerTransportProbe.MixProject do
  use Mix.Project
  def project, do: [app: :mixer_transport_probe, version: "0.0.0", deps: [
    {:mint, path: "/private/var/folders/w6/vbftz74j4jzb2t9ry9r724g00000gn/T/mixer-key-owner-contract-qs27k17o/mint"}, {:hpax, path: "/Users/andreyyurlov/Documents/dev/mixer/hosted/deps/hpax", override: true}]]
  def application, do: [extra_applications: [:ssl, :inets]]
end
