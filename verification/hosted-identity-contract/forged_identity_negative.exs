# Expected compile failure: the proposed verified identity has no role/tenant
# fields. This is a declaration-shape check, not proof against forged runtime data.
Code.require_file("contract_specimen.exs", __DIR__)

Code.compile_string("""
defmodule MixerHostedContractSpecimen.ForbiddenRoleClaim do
  def forged do
    %MixerHostedContractSpecimen.VerifiedIdentity{role: :owner, organization: "org-a"}
  end
end
""")
