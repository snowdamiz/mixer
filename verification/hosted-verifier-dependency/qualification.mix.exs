defmodule HostedVerifierQualification.MixProject do
  use Mix.Project

  def project do
    [app: :hosted_verifier_qualification, version: "0.0.0", elixir: "== 1.20.4",
     deps: [{:jose, "== 1.11.12"}, {:jason, "== 1.4.5"}]]
  end

  def application, do: [extra_applications: [:crypto, :public_key]]
end
