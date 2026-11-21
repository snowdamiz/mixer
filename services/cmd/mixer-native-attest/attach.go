package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"slices"
	"strings"
	"unicode/utf8"
)

const (
	maxBearerToken    = 4089 // The Phoenix BearerIdentity header limit minus "Bearer ".
	maxAttachResponse = 4096
)

var bearerPattern = regexp.MustCompile(`^[A-Za-z0-9._~+/-]+=*$`)

func readAttachToken(stdin io.Reader) (string, error) {
	raw, err := io.ReadAll(io.LimitReader(stdin, maxBearerToken+2))
	if err != nil {
		return "", errors.New("cannot read bearer token from stdin")
	}
	token := strings.TrimSuffix(string(raw), "\n")
	if len(token) > maxBearerToken || !bearerPattern.MatchString(token) {
		return "", errors.New("expected a Mixer bearer token on stdin")
	}
	return token, nil
}

func attach(s source, sel selection, root *os.Root, name, key string) (string, error) {
	envelope, data, err := readAttestation(root, name)
	if err != nil {
		return "", err
	}
	_, public, der, err := readKey(key, false)
	if err != nil {
		return "", err
	}
	signed, err := verifyLocalBinding(envelope, public, s.origin)
	if err != nil {
		return "", err
	}
	if signed.Profile != completionProfile {
		return "", errors.New("attachment requires a V2 attestation")
	}
	if signed.KeyID != sum(der) {
		return "", errors.New("attestation key ID does not match the pinned public key")
	}
	if signed.Selection != sel {
		return "", errors.New("attestation selection does not match the requested build")
	}
	return s.postAttestation(sel, data)
}

func (s source) postAttestation(sel selection, envelope []byte) (string, error) {
	for _, id := range []string{sel.OrganizationID, sel.ProjectID, sel.ApplicationID, sel.BuildID} {
		if id == "." || id == ".." {
			return "", errors.New("attachment scope cannot contain a dot path segment")
		}
	}
	path := fmt.Sprintf("/v3/orgs/%s/projects/%s/apps/%s/builds/%s/ios/native-development-attestation",
		sel.OrganizationID, sel.ProjectID, sel.ApplicationID, sel.BuildID)
	query := url.Values{
		"source_sha256":           {sel.SourceSHA256},
		"toolchain_lock_sha256":   {sel.ToolchainLockSHA256},
		"build_definition_sha256": {sel.BuildDefinitionSHA256},
	}
	request, err := http.NewRequest(http.MethodPost, s.origin+path+"?"+query.Encode(), bytes.NewReader(envelope))
	if err != nil {
		return "", errors.New("cannot construct attachment request")
	}
	// NewRequest sets Content-Length from the reader. Keep the POST body one-shot.
	request.GetBody = nil
	request.Header.Set("Content-Type", "application/json")
	request.Header.Set("Authorization", "Bearer "+s.token)
	response, err := s.client.Do(request)
	if err != nil {
		return "", errors.New("attach: HTTP request failed; result unconfirmed")
	}
	defer response.Body.Close()
	return readAttachResponse(response)
}

var attachErrorCodes = map[int][]string{
	http.StatusBadRequest:            {"invalid_request"},
	http.StatusUnauthorized:          {"unauthenticated"},
	http.StatusForbidden:             {"permission_denied"},
	http.StatusNotFound:              {"not_found"},
	http.StatusConflict:              {"conflict", "immutable_conflict"},
	http.StatusRequestEntityTooLarge: {"payload_too_large"},
	http.StatusUnsupportedMediaType:  {"unsupported_media_type"},
	http.StatusUnprocessableEntity:   {"artifact_invalid"},
	http.StatusServiceUnavailable:    {"authorization_unavailable"},
}

var bearerErrorCodes = map[int]string{
	http.StatusBadRequest:         "invalid_request",
	http.StatusUnauthorized:       "unauthenticated",
	http.StatusServiceUnavailable: "identity_unavailable",
}

func readAttachResponse(response *http.Response) (string, error) {
	status := response.StatusCode
	unexpected := fmt.Errorf("attach: HTTP %d: unexpected response; result unconfirmed", status)
	if !slices.Equal(response.Header.Values("Content-Type"), []string{"application/json; charset=utf-8"}) ||
		!slices.Equal(response.Header.Values("Cache-Control"), []string{"no-store"}) ||
		len(response.Header.Values("Content-Encoding")) != 0 {
		return "", unexpected
	}
	body, err := io.ReadAll(io.LimitReader(response.Body, maxAttachResponse+1))
	if err != nil || len(body) > maxAttachResponse || !utf8.Valid(body) {
		return "", unexpected
	}
	fields := attachResponseObject(body)
	if len(fields) == 1 {
		value := attachResponseString(fields["status"])
		if (status == http.StatusCreated && value == "attached") ||
			(status == http.StatusOK && value == "duplicate") {
			return value, nil
		}
	}
	details := attachResponseObject(fields["error"])
	code := attachResponseString(details["code"])
	controllerError := len(fields) == 1 && len(details) == 1 && slices.Contains(attachErrorCodes[status], code)
	bearerError := len(fields) == 2 && len(details) == 2 && code != "" && code == bearerErrorCodes[status] &&
		attachResponseString(fields["request_id"]) != "" && attachResponseString(details["message"]) != ""
	if controllerError || bearerError {
		return "", fmt.Errorf("attach: HTTP %d: %s", status, code)
	}
	return "", unexpected
}

func attachResponseString(raw json.RawMessage) string {
	var value string
	if json.Unmarshal(raw, &value) != nil {
		return ""
	}
	return value
}

// Reject duplicate keys and trailing data in both Phoenix response objects.
func attachResponseObject(data []byte) map[string]json.RawMessage {
	decoder := json.NewDecoder(bytes.NewReader(data))
	start, err := decoder.Token()
	if err != nil || start != json.Delim('{') {
		return nil
	}
	fields := make(map[string]json.RawMessage)
	for decoder.More() {
		token, err := decoder.Token()
		key, ok := token.(string)
		if err != nil || !ok || fields[key] != nil {
			return nil
		}
		var value json.RawMessage
		if decoder.Decode(&value) != nil {
			return nil
		}
		fields[key] = value
	}
	if end, err := decoder.Token(); err != nil || end != json.Delim('}') {
		return nil
	}
	if _, err := decoder.Token(); err != io.EOF {
		return nil
	}
	return fields
}
