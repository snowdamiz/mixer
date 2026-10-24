// Package durable provides local-development, single-process filesystem commits.
// It is not a substitute for PostgreSQL replication, backup or an external outbox.
package durable

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"syscall"
)

type Fault func(point string) error
type Lock struct{ f *os.File }

func Acquire(dir string) (*Lock, error) {
	if e := os.MkdirAll(dir, 0700); e != nil {
		return nil, e
	}
	if e := os.Chmod(dir, 0700); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(filepath.Join(dir, ".lock"), os.O_CREATE|os.O_RDWR, 0600)
	if e != nil {
		return nil, e
	}
	if e = syscall.Flock(int(f.Fd()), syscall.LOCK_EX|syscall.LOCK_NB); e != nil {
		f.Close()
		return nil, fmt.Errorf("store already in use: %w", e)
	}
	return &Lock{f}, nil
}
func (l *Lock) Close() error {
	if l == nil || l.f == nil {
		return nil
	}
	e := syscall.Flock(int(l.f.Fd()), syscall.LOCK_UN)
	c := l.f.Close()
	l.f = nil
	return errors.Join(e, c)
}
func SyncDir(dir string) error {
	f, e := os.Open(dir)
	if e != nil {
		return e
	}
	defer f.Close()
	return f.Sync()
}
func Write(dir, name string, data []byte, fault Fault) error {
	check := func(p string) error {
		if fault != nil {
			return fault(p)
		}
		return nil
	}
	f, e := os.CreateTemp(dir, ".transaction-")
	if e != nil {
		return e
	}
	tmp := f.Name()
	defer os.Remove(tmp)
	if e = f.Chmod(0600); e != nil {
		f.Close()
		return e
	}
	if e = check("before_write"); e != nil {
		f.Close()
		return e
	}
	if _, e = f.Write(data); e != nil {
		f.Close()
		return e
	}
	if e = check("before_file_sync"); e != nil {
		f.Close()
		return e
	}
	if e = f.Sync(); e != nil {
		f.Close()
		return e
	}
	if e = f.Close(); e != nil {
		return e
	}
	if e = check("before_rename"); e != nil {
		return e
	}
	if e = os.Rename(tmp, filepath.Join(dir, name)); e != nil {
		return e
	}
	if e = check("after_rename"); e != nil {
		return e
	}
	if e = SyncDir(dir); e != nil {
		return e
	}
	return check("after_directory_sync")
}
func JSON(dir, name string, v any, fault Fault) error {
	b, e := json.Marshal(v)
	if e != nil {
		return e
	}
	return Write(dir, name, b, fault)
}
