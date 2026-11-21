package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"regexp"
	"time"
)

const (
	detailPath     = "/console-api/v1/builds"
	completionPath = "/console-api/v1/build-attestation-completion"
	artifactPath   = "/console-api/v1/build-artifacts/"
	metadataMax    = 8 << 20
	artifactMax    = 256 << 20
	archiveMagic   = "MXNATIVE1\n"
)

var (
	idPattern     = regexp.MustCompile(`^[A-Za-z0-9._-]{1,128}$`)
	digestPattern = regexp.MustCompile(`^[0-9a-f]{64}$`)
)

type selection struct {
	OrganizationID        string `json:"organizationId"`
	ProjectID             string `json:"projectId"`
	ApplicationID         string `json:"applicationId"`
	BuildID               string `json:"buildId"`
	Platform              string `json:"platform"`
	SourceSHA256          string `json:"sourceSha256"`
	ToolchainLockSHA256   string `json:"toolchainLockSha256"`
	BuildDefinitionSHA256 string `json:"buildDefinitionSha256"`
}

func (s selection) query() url.Values {
	return url.Values{
		"organization_id": {s.OrganizationID}, "project_id": {s.ProjectID},
		"application_id": {s.ApplicationID}, "build_id": {s.BuildID}, "platform": {s.Platform},
		"source_sha256": {s.SourceSHA256}, "toolchain_lock_sha256": {s.ToolchainLockSHA256},
		"build_definition_sha256": {s.BuildDefinitionSHA256},
	}
}

func parseSelection(raw string) (selection, error) {
	q, err := url.ParseQuery(raw)
	s := selection{
		OrganizationID: q.Get("organization_id"), ProjectID: q.Get("project_id"),
		ApplicationID: q.Get("application_id"), BuildID: q.Get("build_id"), Platform: q.Get("platform"),
		SourceSHA256: q.Get("source_sha256"), ToolchainLockSHA256: q.Get("toolchain_lock_sha256"),
		BuildDefinitionSHA256: q.Get("build_definition_sha256"),
	}
	if err != nil || q.Encode() != s.query().Encode() || s.Platform != "ios" {
		return selection{}, errors.New("expected one exact iOS build selection")
	}
	for _, id := range []string{s.OrganizationID, s.ProjectID, s.ApplicationID, s.BuildID} {
		if !idPattern.MatchString(id) {
			return selection{}, errors.New("invalid scope identifier")
		}
	}
	for _, digest := range []string{s.SourceSHA256, s.ToolchainLockSHA256, s.BuildDefinitionSHA256} {
		if !digestPattern.MatchString(digest) {
			return selection{}, errors.New("invalid build pin")
		}
	}
	return s, nil
}

type artifact struct {
	Kind      string `json:"kind"`
	SHA256    string `json:"sha256"`
	SizeBytes int64  `json:"sizeBytes"`
}

type observedBuild struct {
	selection
	State             string `json:"state"`
	CompletionPending *bool  `json:"workerCompletionPending"`
	Revision          int    `json:"revision"`
	Attempt           int    `json:"attempt"`
	WorkerOperationID string `json:"workerOperationId,omitempty"`
	Artifacts         []struct {
		artifact
		DownloadPath string `json:"downloadPath"`
	} `json:"artifacts"`
}

type provenance struct {
	Revision          int    `json:"journalRevision"`
	Attempt           int    `json:"attempt"`
	BindingSHA256     string `json:"nativeBindingSha256"`
	WorkerOperationID string `json:"workerOperationId,omitempty"`
}

type source struct {
	origin string
	token  string
	client *http.Client
}

func newSource(origin, token string) (source, error) {
	u, err := url.Parse(origin)
	if err != nil || u.Scheme != "http" || u.Host != "127.0.0.1:"+u.Port() ||
		u.Port() == "" || origin != "http://"+u.Host {
		return source{}, errors.New("origin must be an explicit IPv4 loopback HTTP origin")
	}
	return source{origin, token, &http.Client{
		Timeout:       30 * time.Second,
		Transport:     &http.Transport{DisableCompression: true, DisableKeepAlives: true},
		CheckRedirect: func(*http.Request, []*http.Request) error { return http.ErrUseLastResponse },
	}}, nil
}

func (s source) get(path, mediaType string, selection selection) (*http.Response, error) {
	request, err := http.NewRequest(http.MethodGet, s.origin+path+"?"+selection.query().Encode(), nil)
	if err != nil {
		return nil, err
	}
	request.AddCookie(&http.Cookie{Name: "__Host-mixer-session", Value: s.token})
	response, err := s.client.Do(request)
	if err != nil {
		return nil, fmt.Errorf("GET %s: %w", path, err)
	}
	if response.StatusCode != http.StatusOK {
		response.Body.Close()
		return nil, fmt.Errorf("GET %s: HTTP %d", path, response.StatusCode)
	}
	if response.Header.Get("Content-Type") != mediaType ||
		response.Header.Get("Content-Encoding") != "" || response.Header.Get("Cache-Control") != "no-store" {
		response.Body.Close()
		return nil, fmt.Errorf("GET %s: unexpected response headers", path)
	}
	return response, nil
}

func (s source) detail(sel selection, path string) (observedBuild, error) {
	response, err := s.get(path, "application/json; charset=utf-8", sel)
	if err != nil {
		return observedBuild{}, err
	}
	defer response.Body.Close()
	var body struct {
		Build observedBuild `json:"build"`
	}
	data, err := io.ReadAll(io.LimitReader(response.Body, 16385))
	if err != nil || len(data) > 16384 || json.Unmarshal(data, &body) != nil {
		return observedBuild{}, errors.New("invalid build detail")
	}
	b := body.Build
	if b.selection != sel || b.State != "native_succeeded" || b.CompletionPending == nil ||
		*b.CompletionPending || b.Revision < 2 || b.Attempt < 1 || len(b.Artifacts) != 3 {
		return observedBuild{}, errors.New("detail does not describe the exact completed native build")
	}
	return b, nil
}

type inventory struct {
	Version       int      `json:"version"`
	Kind          string   `json:"kind"`
	ParentApp     artifact `json:"parentApp"`
	ParentSymbols artifact `json:"parentSymbols"`
	BindingSHA256 string   `json:"bindingSHA256"`
}

func (s source) observe(sel selection, profile string) (provenance, []artifact, error) {
	path := completionPath
	if profile == legacyProfile {
		path = detailPath
	}
	b, err := s.detail(sel, path)
	if err != nil {
		return provenance{}, nil, err
	}
	var operation string
	if profile == completionProfile {
		operation = b.WorkerOperationID
		if !digestPattern.MatchString(operation) {
			return provenance{}, nil, errors.New("detail does not identify the completed worker operation")
		}
	}
	kinds := [...]string{"unsigned_native_binary", "debug_symbols", "resource_inventory"}
	subjects := make([]artifact, len(kinds))
	for _, d := range b.Artifacts {
		for i, kind := range kinds {
			if d.Kind != kind {
				continue
			}
			u, err := url.Parse(d.DownloadPath)
			if err != nil {
				return provenance{}, nil, errors.New("invalid artifact path")
			}
			pinned, err := parseSelection(u.RawQuery)
			if subjects[i].Kind != "" || !digestPattern.MatchString(d.SHA256) ||
				d.SizeBytes < 1 || d.SizeBytes > artifactMax || err != nil || pinned != sel ||
				d.DownloadPath != artifactPath+kind+"?"+u.RawQuery {
				return provenance{}, nil, errors.New("invalid or foreign artifact descriptor")
			}
			subjects[i] = d.artifact
		}
	}
	var bindings [2]string
	var inv inventory
	for i, d := range subjects {
		if d.Kind == "" {
			return provenance{}, nil, errors.New("missing native product")
		}
		if i < len(bindings) {
			err = s.readArtifact(sel, d, func(r io.Reader) error {
				bindings[i], err = archiveBinding(r, d.Kind)
				return err
			})
		} else {
			err = s.readArtifact(sel, d, func(r io.Reader) error {
				if d.SizeBytes > metadataMax {
					return errors.New("resource inventory too large")
				}
				data, err := io.ReadAll(r)
				if err != nil {
					return err
				}
				return json.Unmarshal(data, &inv)
			})
		}
		if err != nil {
			return provenance{}, nil, err
		}
	}
	if inv.Version != 1 || inv.Kind != kinds[2] || inv.ParentApp != subjects[0] ||
		inv.ParentSymbols != subjects[1] || inv.BindingSHA256 != bindings[0] || bindings[0] != bindings[1] {
		return provenance{}, nil, errors.New("native products have inconsistent provenance")
	}
	return provenance{b.Revision, b.Attempt, inv.BindingSHA256, operation}, subjects, nil
}

func (s source) readArtifact(sel selection, d artifact, readMetadata func(io.Reader) error) error {
	response, err := s.get(artifactPath+d.Kind, "application/octet-stream", sel)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.ContentLength != d.SizeBytes {
		return fmt.Errorf("%s: content length mismatch", d.Kind)
	}
	hash := sha256.New()
	limited := &io.LimitedReader{R: response.Body, N: d.SizeBytes + 1}
	reader := io.TeeReader(limited, hash)
	if err := readMetadata(reader); err != nil {
		return fmt.Errorf("%s: %w", d.Kind, err)
	}
	if _, err := io.Copy(io.Discard, reader); err != nil {
		return fmt.Errorf("%s: %w", d.Kind, err)
	}
	if limited.N != 1 || hex.EncodeToString(hash.Sum(nil)) != d.SHA256 {
		return fmt.Errorf("%s: byte digest mismatch", d.Kind)
	}
	return nil
}

func archiveBinding(r io.Reader, kind string) (string, error) {
	var prefix [len(archiveMagic) + 8]byte
	if _, err := io.ReadFull(r, prefix[:]); err != nil {
		return "", err
	}
	size := binary.BigEndian.Uint64(prefix[len(archiveMagic):])
	if !bytes.Equal(prefix[:len(archiveMagic)], []byte(archiveMagic)) || size == 0 || size > metadataMax {
		return "", errors.New("invalid native archive header")
	}
	data := make([]byte, size)
	if _, err := io.ReadFull(r, data); err != nil {
		return "", err
	}
	var header struct {
		Version int    `json:"version"`
		Kind    string `json:"kind"`
		Binding string `json:"binding"`
	}
	if json.Unmarshal(data, &header) != nil || header.Version != 1 ||
		header.Kind != kind || !digestPattern.MatchString(header.Binding) {
		return "", errors.New("invalid native archive binding")
	}
	return header.Binding, nil
}
