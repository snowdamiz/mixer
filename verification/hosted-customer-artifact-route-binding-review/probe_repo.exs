defmodule MixerHosted.CustomerArtifacts.RouteBindingReviewRepo do
  def in_transaction? do
    send(self(), {:route_binding_review_repo, :in_transaction})
    false
  end

  def transaction(_callback, _options) do
    send(self(), {:route_binding_review_repo, :transaction})
    {:error, :storage_unavailable}
  end

  def rollback(reason) do
    send(self(), {:route_binding_review_repo, :rollback})
    throw({:unexpected_review_rollback, reason})
  end
end
