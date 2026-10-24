defmodule IndependentReview.MixProject do
  use Mix.Project
  def project, do: [app: :independent_verifier_review, version: "0.0.0", elixir: "== 1.20.4",
    deps: [{:jason, path: "deps/jason", env: :prod}, {:jose, path: "deps/jose", env: :prod}]]
  def application, do: [extra_applications: [:crypto, :public_key, :jason, :jose]]
end
