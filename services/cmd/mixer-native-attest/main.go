// mixer-native-attest signs, verifies, and attaches local development attestations.
package main

import (
	"bytes"
	"crypto/ed25519"
	"crypto/rand"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"encoding/pem"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"strings"
	"syscall"
)

const (
	legacyProfile     = "mixer.native-build.ios-simulator.development.v1"
	completionProfile = "mixer.native-build.ios-simulator.development.v2"
)

type statement struct {
	Profile    string     `json:"profile"`
	Origin     string     `json:"origin"`
	KeyID      string     `json:"keyId"`
	Selection  selection  `json:"selection"`
	Provenance provenance `json:"provenance"`
	Subjects   []artifact `json:"subjects"`
}

type attestation struct {
	Statement json.RawMessage `json:"statement"`
	Signature []byte          `json:"signature"`
}

func main() {
	name, err := run(os.Args[1:], os.Stdin)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(name)
}

func run(args []string, stdin io.Reader) (string, error) {
	if len(args) == 0 || (args[0] != "sign" && args[0] != "verify" && args[0] != "attach") {
		return "", errors.New("usage: mixer-native-attest sign|verify|attach -origin ORIGIN -selection QUERY -state DIR -key PEM")
	}
	command := args[0]
	flags := flag.NewFlagSet(command, flag.ContinueOnError)
	origin := flags.String("origin", "", "trusted local Phoenix origin")
	raw := flags.String("selection", "", "exact build selection query")
	state := flags.String("state", "", "mode 0700 attestation directory")
	key := flags.String("key", "", "private PKCS#8 PEM for sign, pinned public SPKI PEM for verify or attach")
	if err := flags.Parse(args[1:]); err != nil {
		return "", err
	}
	if *state == "" || *key == "" || flags.NArg() != 0 {
		return "", errors.New("expected state and key paths")
	}
	sel, err := parseSelection(*raw)
	if err != nil {
		return "", err
	}
	readToken := readSessionToken
	if command == "attach" {
		readToken = readAttachToken
	}
	token, err := readToken(stdin)
	if err != nil {
		return "", err
	}
	s, err := newSource(*origin, token)
	if err != nil {
		return "", err
	}
	root, err := os.OpenRoot(*state)
	if err != nil {
		return "", err
	}
	defer root.Close()
	dir, err := root.Open(".")
	if err != nil {
		return "", err
	}
	defer dir.Close()
	info, err := dir.Stat()
	if err != nil || !info.IsDir() || info.Mode().Perm() != 0700 || !owned(info) {
		return "", errors.New("attestation directory must be owned and mode 0700")
	}
	if err := requireNoACL(dir); err != nil {
		return "", fmt.Errorf("unsafe attestation directory ACL: %w", err)
	}

	// Immutable build identity survives process restart, key changes, or changes to
	// the request's pins. The store is scoped to this local trust context.
	scope := strings.Join([]string{sel.OrganizationID, sel.ProjectID, sel.ApplicationID, sel.Platform, sel.BuildID}, "\x00")
	name := sum([]byte(scope)) + ".json"
	switch command {
	case "attach":
		return attach(s, sel, root, name, *key)
	case "verify":
		return name, verify(s, sel, root, name, *key)
	}
	if _, err := root.Lstat(name); !errors.Is(err, os.ErrNotExist) {
		return "", errors.New("build already attested or state unavailable")
	}
	// Observe the authenticated build before opening the signing key.
	p, subjects, err := s.observe(sel, completionProfile)
	if err != nil {
		return "", err
	}
	private, _, der, err := readKey(*key, true)
	if err != nil {
		return "", err
	}
	defer clear(private)
	payload, err := json.Marshal(statement{completionProfile, s.origin, sum(der), sel, p, subjects})
	if err != nil {
		return "", err
	}
	message := append([]byte(completionProfile+"\x00"), payload...)
	envelope, err := json.Marshal(attestation{payload, ed25519.Sign(private, message)})
	if err != nil {
		return "", err
	}
	return name, publish(root, dir, name, envelope)
}

func readSessionToken(stdin io.Reader) (string, error) {
	token, err := io.ReadAll(io.LimitReader(stdin, 46))
	if err != nil {
		return "", errors.New("cannot read session token from stdin")
	}
	session := strings.TrimSuffix(string(token), "\n")
	decoded, err := base64.RawURLEncoding.Strict().DecodeString(session)
	if err != nil || len(decoded) != 32 || len(session) != 43 {
		return "", errors.New("expected a Mixer session token on stdin")
	}
	return session, nil
}

func verify(s source, sel selection, root *os.Root, name, key string) error {
	envelope, _, err := readAttestation(root, name)
	if err != nil {
		return err
	}
	_, public, der, err := readKey(key, false)
	if err != nil {
		return err
	}
	signed, err := verifyLocalBinding(envelope, public, s.origin)
	if err != nil {
		return err
	}
	p, subjects, err := s.observe(sel, signed.Profile)
	if err != nil {
		return err
	}
	payload, err := json.Marshal(statement{signed.Profile, s.origin, sum(der), sel, p, subjects})
	if err != nil {
		return err
	}
	if !bytes.Equal(envelope.Statement, payload) {
		return errors.New("attestation current build binding failed")
	}
	return nil
}

func verifyLocalBinding(envelope attestation, public ed25519.PublicKey, origin string) (statement, error) {
	var signed statement
	if err := json.Unmarshal(envelope.Statement, &signed); err != nil {
		return statement{}, errors.New("invalid attestation statement")
	}
	if signed.Profile != legacyProfile && signed.Profile != completionProfile {
		return statement{}, errors.New("unsupported attestation profile")
	}
	if !ed25519.Verify(public, append([]byte(signed.Profile+"\x00"), envelope.Statement...), envelope.Signature) {
		return statement{}, errors.New("attestation signature failed")
	}
	if signed.Origin != origin {
		return statement{}, fmt.Errorf("attestation requires the signed Phoenix origin %q (restart with its fixed MIXER_HTTP_PORT)", signed.Origin)
	}
	return signed, nil
}

const maxAttestationSize = 16_384

func readAttestation(root *os.Root, name string) (attestation, []byte, error) {
	file, err := root.OpenFile(name, os.O_RDONLY|syscall.O_NONBLOCK|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return attestation{}, nil, err
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() || info.Mode().Perm() != 0400 || !owned(info) {
		return attestation{}, nil, errors.New("invalid attestation file")
	}
	if err := requireNoACL(file); err != nil {
		return attestation{}, nil, fmt.Errorf("unsafe attestation file ACL: %w", err)
	}
	data, err := io.ReadAll(io.LimitReader(file, maxAttestationSize+1))
	var envelope attestation
	if err != nil || len(data) > maxAttestationSize || json.Unmarshal(data, &envelope) != nil {
		return attestation{}, nil, errors.New("invalid native attestation")
	}
	canonical, err := json.Marshal(envelope)
	if err != nil || !bytes.Equal(data, canonical) {
		return attestation{}, nil, errors.New("invalid native attestation")
	}
	return envelope, data, nil
}

func sum(data []byte) string {
	hash := sha256.Sum256(data)
	return hex.EncodeToString(hash[:])
}

func owned(info os.FileInfo) bool {
	stat, ok := info.Sys().(*syscall.Stat_t)
	return ok && int(stat.Uid) == os.Geteuid()
}

func readKey(path string, sign bool) (ed25519.PrivateKey, ed25519.PublicKey, []byte, error) {
	file, err := os.OpenFile(path, os.O_RDONLY|syscall.O_NONBLOCK|syscall.O_NOFOLLOW, 0)
	if err != nil {
		return nil, nil, nil, errors.New("cannot open local development key")
	}
	defer file.Close()
	info, err := file.Stat()
	if err != nil || !info.Mode().IsRegular() || !owned(info) ||
		info.Mode().Perm()&0022 != 0 || (sign && info.Mode().Perm()&0077 != 0) {
		return nil, nil, nil, errors.New("unsafe local development key file")
	}
	if err := requireNoACL(file); err != nil {
		return nil, nil, nil, fmt.Errorf("unsafe local development key ACL: %w", err)
	}
	raw, err := io.ReadAll(io.LimitReader(file, 4097))
	defer clear(raw)
	keyError := errors.New("expected one local Ed25519 key in PEM form")
	if err != nil || len(raw) > 4096 {
		return nil, nil, nil, keyError
	}
	block, rest := pem.Decode(raw)
	if block == nil || len(bytes.TrimSpace(rest)) != 0 {
		return nil, nil, nil, keyError
	}
	if sign {
		defer clear(block.Bytes)
	}
	if sign && block.Type == "PRIVATE KEY" {
		key, err := x509.ParsePKCS8PrivateKey(block.Bytes)
		private, ok := key.(ed25519.PrivateKey)
		if err == nil && ok {
			public := private.Public().(ed25519.PublicKey)
			der, err := x509.MarshalPKIXPublicKey(public)
			return private, public, der, err
		}
	}
	if !sign && block.Type == "PUBLIC KEY" {
		key, err := x509.ParsePKIXPublicKey(block.Bytes)
		public, ok := key.(ed25519.PublicKey)
		if err == nil && ok {
			der, err := x509.MarshalPKIXPublicKey(public)
			return nil, public, der, err
		}
	}
	return nil, nil, nil, keyError
}

func publish(root *os.Root, dir *os.File, name string, data []byte) error {
	var nonce [16]byte
	rand.Read(nonce[:])
	stage := "." + hex.EncodeToString(nonce[:])
	file, err := root.OpenFile(stage, os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0400)
	if err != nil {
		return err
	}
	defer root.Remove(stage)
	if err := requireNoACL(file); err != nil {
		file.Close()
		return fmt.Errorf("unsafe staging file ACL: %w", err)
	}
	_, writeErr := file.Write(data)
	syncErr := file.Sync()
	if err := errors.Join(writeErr, syncErr, file.Close()); err != nil {
		return err
	}
	if err := root.Link(stage, name); err != nil {
		if errors.Is(err, os.ErrExist) {
			return errors.New("build already attested")
		}
		return err
	}
	if err := root.Remove(stage); err != nil {
		return err
	}
	return dir.Sync()
}
