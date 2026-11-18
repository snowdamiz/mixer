//go:build darwin && cgo

package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/x509"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"
)

func TestParsedPublicKeyVerifiesAfterLoaderReturns(t *testing.T) {
	public, private, err := ed25519.GenerateKey(nil)
	if err != nil {
		t.Fatal(err)
	}
	der, err := x509.MarshalPKIXPublicKey(public)
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(t.TempDir(), "public.pem")
	if err := os.WriteFile(path, pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der}), 0600); err != nil {
		t.Fatal(err)
	}
	_, loaded, spki, err := readKey(path, false)
	if err != nil {
		t.Fatal(err)
	}
	message := []byte("native attestation test")
	if !bytes.Equal(der, spki) || !ed25519.Verify(loaded, message, ed25519.Sign(private, message)) {
		t.Fatal("loaded key failed to verify signature")
	}
}
