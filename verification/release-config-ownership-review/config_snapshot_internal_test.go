// Candidate-only direct check of dormant PostgreSQL configuration ownership.
// The public HTTP probes remain in a separate external package.
package release

import (
	"testing"

	"mixer/services/protocol"
)

func TestIndependentSnapshotPostgresPointeeOwnsAllValueFields(t *testing.T) {
	postgres := &PostgresConfig{ConnectionStringEnv: "TEST_ONLY_UNREAD_DSN", MaxConnections: 3, QueryTimeoutMilliseconds: 1234}
	original := Config{Postgres: postgres}
	owned := snapshotConfig(original)
	if owned.Postgres == original.Postgres {
		t.Fatal("Postgres pointee retained caller ownership")
	}
	postgres.ConnectionStringEnv = "TEST_ONLY_CHANGED_DSN"
	postgres.MaxConnections = 8
	postgres.QueryTimeoutMilliseconds = 9999
	if owned.Postgres.ConnectionStringEnv != "TEST_ONLY_UNREAD_DSN" || owned.Postgres.MaxConnections != 3 || owned.Postgres.QueryTimeoutMilliseconds != 1234 {
		t.Fatalf("caller mutation reached copied PostgreSQL values: %+v", owned.Postgres)
	}
	owned.Postgres.ConnectionStringEnv = "TEST_ONLY_SERVER_SIDE"
	if postgres.ConnectionStringEnv != "TEST_ONLY_CHANGED_DSN" {
		t.Fatal("snapshot mutation reached original PostgreSQL pointee")
	}
	if snapshotConfig(Config{}).Postgres != nil {
		t.Fatal("nil PostgreSQL config became nonnil")
	}
}

func TestIndependentSnapshotPreservesNilAndExplicitEmptyContainers(t *testing.T) {
	nilValue := snapshotConfig(Config{})
	if nilValue.Tokens != nil || nilValue.Roots != nil || nilValue.Hosts != nil {
		t.Fatal("nil top-level slices changed shape")
	}
	emptyValue := snapshotConfig(Config{Tokens: []Token{}, Roots: []protocol.Root{}, Hosts: []protocol.Host{}})
	if emptyValue.Tokens == nil || emptyValue.Roots == nil || emptyValue.Hosts == nil {
		t.Fatal("explicit empty top-level slices became nil")
	}
	withNested := snapshotConfig(Config{Roots: []protocol.Root{{}, {PublicKey: []byte{}}}, Hosts: []protocol.Host{{}, {CapabilityHashes: map[string]string{}}}})
	if withNested.Roots[0].PublicKey != nil || withNested.Hosts[0].CapabilityHashes != nil {
		t.Fatal("nil nested values changed shape")
	}
	if withNested.Roots[1].PublicKey == nil || withNested.Hosts[1].CapabilityHashes == nil {
		t.Fatal("explicit empty nested values became nil")
	}
}
