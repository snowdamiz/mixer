Code.require_file("contract_specimen.exs", __DIR__)
ExUnit.start()

defmodule MixerHostedContractSpecimen.DeclarationTest do
  use ExUnit.Case, async: true
  alias MixerHostedContractSpecimen.{AuthorizedContext, Request, VerifiedIdentity}

  test "verified identity declaration does not carry a tenant or product role" do
    fields = Map.keys(VerifiedIdentity.__struct__())

    for forbidden <- [:organization, :project, :role, :actor, :permissions] do
      refute forbidden in fields
    end

    for required <- [:issuer, :subject, :client_id, :credential_ref, :identity_class] do
      assert required in fields
    end
  end

  test "request declaration selects a resource but cannot select actor or role" do
    fields = Map.keys(Request.__struct__())
    assert :resource_ref in fields
    refute :actor in fields
    refute :role in fields
    refute :principal_id in fields
  end

  test "context declaration has connection lifetime and policy evidence slots" do
    fields = Map.keys(AuthorizedContext.__struct__())

    for required <- [
          :transaction_owner,
          :transaction_ref,
          :target,
          :action,
          :principal_id,
          :policy_revisions,
          :audit_actor
        ] do
      assert required in fields
    end

    refute :role in fields
    refute :bearer in fields
  end

  test "behavior callbacks compile with separated identity and transaction contracts" do
    assert MixerHostedContractSpecimen.Verifier.behaviour_info(:callbacks) == [authenticate: 2]

    assert MixerHostedContractSpecimen.Authorization.behaviour_info(:callbacks) == [
             with_authorized_transaction: 3
           ]

    assert Enum.sort(MixerHostedContractSpecimen.ReleaseRepository.behaviour_info(:callbacks)) == [
             artifact: 2,
             history: 3,
             upload: 3
           ]
  end
end
