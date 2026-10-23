// Package protocol implements the independently authored Mixer update protocol.
package protocol

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"reflect"
	"sort"
	"strings"
	"unicode/utf8"
)

// CanonicalCBOR uses RFC 8949 section 4.2.1 core deterministic encoding.
// The v1 data model only permits text maps, text, unsigned integers, booleans,
// arrays and structs. Floating points, nulls, negative integers and tags fail.
// Struct field names are their JSON tags; no fields are omitted.
func CanonicalCBOR(value any) ([]byte, error) {
	return encodeValue(reflect.ValueOf(value))
}

func head(major byte, n uint64) []byte {
	switch {
	case n < 24:
		return []byte{major<<5 | byte(n)}
	case n <= 0xff:
		return []byte{major<<5 | 24, byte(n)}
	case n <= 0xffff:
		b := []byte{major<<5 | 25, 0, 0}
		binary.BigEndian.PutUint16(b[1:], uint16(n))
		return b
	case n <= 0xffffffff:
		b := make([]byte, 5)
		b[0] = major<<5 | 26
		binary.BigEndian.PutUint32(b[1:], uint32(n))
		return b
	default:
		b := make([]byte, 9)
		b[0] = major<<5 | 27
		binary.BigEndian.PutUint64(b[1:], n)
		return b
	}
}

func encodeValue(v reflect.Value) ([]byte, error) {
	if !v.IsValid() {
		return nil, fmt.Errorf("null is not in the v1 data model")
	}
	if v.Kind() == reflect.Interface {
		return encodeValue(v.Elem())
	}
	switch v.Kind() {
	case reflect.String:
		s := v.String()
		if !utf8.ValidString(s) {
			return nil, fmt.Errorf("invalid UTF-8")
		}
		return append(head(3, uint64(len(s))), s...), nil
	case reflect.Uint, reflect.Uint8, reflect.Uint16, reflect.Uint32, reflect.Uint64:
		return head(0, v.Uint()), nil
	case reflect.Bool:
		if v.Bool() {
			return []byte{0xf5}, nil
		}
		return []byte{0xf4}, nil
	case reflect.Slice, reflect.Array:
		b := head(4, uint64(v.Len()))
		for i := 0; i < v.Len(); i++ {
			x, e := encodeValue(v.Index(i))
			if e != nil {
				return nil, e
			}
			b = append(b, x...)
		}
		return b, nil
	case reflect.Struct, reflect.Map:
		type pair struct{ key, value []byte }
		pairs := []pair{}
		add := func(k string, val reflect.Value) error {
			kb, e := encodeValue(reflect.ValueOf(k))
			if e != nil {
				return e
			}
			vb, e := encodeValue(val)
			if e != nil {
				return e
			}
			pairs = append(pairs, pair{kb, vb})
			return nil
		}
		if v.Kind() == reflect.Struct {
			for i := 0; i < v.NumField(); i++ {
				f := v.Type().Field(i)
				name := strings.Split(f.Tag.Get("json"), ",")[0]
				if name == "-" {
					continue
				}
				if name == "" || f.PkgPath != "" {
					return nil, fmt.Errorf("unmapped CBOR struct field %s", f.Name)
				}
				if e := add(name, v.Field(i)); e != nil {
					return nil, e
				}
			}
		} else {
			if v.Type().Key().Kind() != reflect.String {
				return nil, fmt.Errorf("CBOR map keys must be text")
			}
			for _, k := range v.MapKeys() {
				if e := add(k.String(), v.MapIndex(k)); e != nil {
					return nil, e
				}
			}
		}
		sort.Slice(pairs, func(i, j int) bool { return bytes.Compare(pairs[i].key, pairs[j].key) < 0 })
		b := head(5, uint64(len(pairs)))
		for _, p := range pairs {
			b = append(b, p.key...)
			b = append(b, p.value...)
		}
		return b, nil
	default:
		return nil, fmt.Errorf("unsupported CBOR type %s", v.Kind())
	}
}
