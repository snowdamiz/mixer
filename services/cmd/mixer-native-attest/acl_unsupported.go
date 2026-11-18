//go:build !darwin || !cgo

package main

import (
	"errors"
	"os"
)

func requireNoACL(*os.File) error {
	return errors.New("ACL validation requires macOS with cgo enabled")
}
