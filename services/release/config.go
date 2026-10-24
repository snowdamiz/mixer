package release

import (
	"maps"
	"slices"
)

// snapshotConfig gives the server exclusive ownership of every mutable value it
// retains. Copy before validation so requests use the same values that passed
// construction checks. Callers must keep input stable until New returns; later
// mutations are not configuration updates and cannot change server authority.
func snapshotConfig(c Config) Config {
	c.Tokens = slices.Clone(c.Tokens)
	c.Roots = slices.Clone(c.Roots)
	for i := range c.Roots {
		c.Roots[i].PublicKey = slices.Clone(c.Roots[i].PublicKey)
	}
	c.Hosts = slices.Clone(c.Hosts)
	for i := range c.Hosts {
		c.Hosts[i].CapabilityHashes = maps.Clone(c.Hosts[i].CapabilityHashes)
	}
	if c.Postgres != nil {
		postgres := *c.Postgres
		c.Postgres = &postgres
	}
	return c
}
