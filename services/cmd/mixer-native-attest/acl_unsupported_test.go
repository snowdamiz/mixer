//go:build !darwin || !cgo

package main

import (
	"os"
	"testing"
)

func TestUnavailableACLValidationIsRefused(t *testing.T) {
	dir, err := os.Open(t.TempDir())
	if err != nil {
		t.Fatal(err)
	}
	defer dir.Close()
	if err := requireNoACL(dir); err == nil {
		t.Fatal("accepted a directory without an ACL check")
	}
}
