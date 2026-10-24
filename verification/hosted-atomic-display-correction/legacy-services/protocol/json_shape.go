package protocol

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"reflect"
	"strings"
)

var jsonUnmarshalerType = reflect.TypeFor[json.Unmarshaler]()

func jsonProtocolDocumentLimit(model reflect.Type) int {
	for model != nil && model.Kind() == reflect.Pointer {
		model = model.Elem()
	}
	switch model {
	case reflect.TypeFor[Manifest](), reflect.TypeFor[Assignment](), reflect.TypeFor[SignedManifest](), reflect.TypeFor[SignedAssignment](),
		reflect.TypeFor[Scope](), reflect.TypeFor[Limits](), reflect.TypeFor[Host](), reflect.TypeFor[Root]():
		return maxV1DocumentBytes
	case reflect.TypeFor[ManifestV2](), reflect.TypeFor[AssignmentV2](), reflect.TypeFor[SignedManifestV2](), reflect.TypeFor[SignedAssignmentV2](),
		reflect.TypeFor[CapabilityGrant](), reflect.TypeFor[CapabilityGrants]():
		return MaxV2DocumentBytes
	case reflect.TypeFor[ManifestV3](), reflect.TypeFor[AssignmentV3](), reflect.TypeFor[SignedManifestV3](), reflect.TypeFor[SignedAssignmentV3]():
		return MaxV3DocumentBytes
	default:
		return 0
	}
}

// Generic DTOs retain their established missing-field/default behavior. Only
// fixed struct names are checked here. Closed protocol models independently
// require every field in their UnmarshalJSON methods below. Maps retain dynamic,
// case-sensitive keys; custom JSON values (notably RawMessage) stay opaque while
// the syntax/duplicate/null walk still covers their complete contents.
func jsonTargetType(target any) reflect.Type {
	value := reflect.ValueOf(target)
	for value.IsValid() && (value.Kind() == reflect.Pointer || value.Kind() == reflect.Interface) {
		if value.IsNil() {
			return value.Type()
		}
		value = value.Elem()
	}
	if value.IsValid() {
		return value.Type()
	}
	return nil
}

func jsonShapeType(model reflect.Type) reflect.Type {
	for model != nil {
		if model.Implements(jsonUnmarshalerType) || model.Kind() != reflect.Pointer && reflect.PointerTo(model).Implements(jsonUnmarshalerType) {
			return nil
		}
		if model.Kind() != reflect.Pointer {
			break
		}
		model = model.Elem()
	}
	return model
}

func isJSONBytes(model reflect.Type) bool {
	return model != nil && model.Kind() == reflect.Slice && model.Elem().Kind() == reflect.Uint8
}

func jsonModelFields(model reflect.Type) (map[string]reflect.Type, error) {
	if model == nil || model.Kind() != reflect.Struct {
		return nil, nil
	}
	fields := map[string]reflect.Type{}
	var add func(reflect.Type, int) error
	add = func(current reflect.Type, depth int) error {
		if depth > 32 {
			return fmt.Errorf("embedded JSON model depth exceeded")
		}
		for i := 0; i < current.NumField(); i++ {
			field := current.Field(i)
			if field.PkgPath != "" {
				continue
			}
			name := strings.Split(field.Tag.Get("json"), ",")[0]
			if name == "-" {
				continue
			}
			if field.Anonymous && name == "" {
				embedded := field.Type
				if embedded.Kind() == reflect.Pointer {
					embedded = embedded.Elem()
				}
				if embedded.Kind() == reflect.Struct {
					if e := add(embedded, depth+1); e != nil {
						return e
					}
					continue
				}
			}
			if name == "" {
				name = field.Name
			}
			if _, exists := fields[name]; exists {
				return fmt.Errorf("ambiguous embedded JSON model fields")
			}
			fields[name] = field.Type
		}
		return nil
	}
	if e := add(model, 0); e != nil {
		return nil, e
	}
	return fields, nil
}

func canonicalBase64(text string) ([]byte, error) {
	decoded, e := base64.StdEncoding.Strict().DecodeString(text)
	if e != nil || base64.StdEncoding.EncodeToString(decoded) != text {
		return nil, fmt.Errorf("noncanonical base64 JSON text")
	}
	return decoded, nil
}

func signatureEncoding(raw []byte) error {
	var text string
	if e := json.Unmarshal(raw, &text); e != nil || len(text) != 88 {
		return fmt.Errorf("signature must be canonical base64 text")
	}
	decoded, e := canonicalBase64(text)
	if e != nil || len(decoded) != ed25519.SignatureSize {
		return fmt.Errorf("signature must encode exactly 64 bytes in canonical padded base64")
	}
	return nil
}

func exactProtocolObject(data []byte, maximum int, fields ...string) (map[string]json.RawMessage, error) {
	if len(data) > maximum {
		return nil, fmt.Errorf("protocol document exceeds byte limit")
	}
	var raw map[string]json.RawMessage
	if e := DecodeJSON(data, &raw); e != nil {
		return nil, e
	}
	if len(raw) != len(fields) {
		return nil, fmt.Errorf("missing or unknown protocol fields")
	}
	for _, field := range fields {
		if _, ok := raw[field]; !ok {
			return nil, fmt.Errorf("missing protocol field")
		}
	}
	return raw, nil
}
