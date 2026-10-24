// Intentionally must not compile as an external consumer. The harness checks
// specifically for inaccessible initialization, not an unrelated import error.
import MixerUpdates
let inventedGrant = VerifiedCapabilityGrant(capabilityID: "network.http.v1", schemaSHA256: "unverified",
    permissions: ["network.https"], origins: ["https://example.com"], methods: ["GET"], namespaces: [])
let inventedGrants = VerifiedCapabilityGrants(entries: [])
let inventedArtifact = VerifiedArtifact()
