package main

import (
	"context"
	"fmt"
	"io"
	"os"
	"os/signal"
	"syscall"

	"mixer/services/protocol"
	"mixer/services/release"
)

func main() {
	if e := run(); e != nil {
		fmt.Fprintln(os.Stderr, "mixer-service:", e)
		os.Exit(1)
	}
}
func run() error {
	path := os.Getenv("MIXER_SERVICE_CONFIG")
	if path == "" {
		return fmt.Errorf("MIXER_SERVICE_CONFIG must name explicit developer JSON config; no default credentials")
	}
	file, e := os.Open(path)
	if e != nil {
		return e
	}
	defer file.Close()
	b, e := io.ReadAll(file)
	if e != nil {
		return e
	}
	var cfg release.Config
	if e = protocol.DecodeJSON(b, &cfg); e != nil {
		return e
	}
	if cfg.FeatureUI != nil {
		info, err := file.Stat()
		if err != nil {
			return err
		}
		owner, ok := info.Sys().(*syscall.Stat_t)
		if !ok || int(owner.Uid) != os.Geteuid() || !info.Mode().IsRegular() || info.Mode().Perm()&0022 != 0 {
			return fmt.Errorf("feature UI requires an operator-owned config file without group or world write access")
		}
	}
	if e = file.Close(); e != nil {
		return e
	}
	if len(os.Args) != 1 {
		if len(os.Args) != 4 || os.Args[1] != "migrate-postgres" || os.Args[2] != "--connection-env" || cfg.StorageBackend != "postgres" || cfg.Postgres == nil {
			return fmt.Errorf("usage: mixer-service [migrate-postgres --connection-env OWNER_DSN_ENV]")
		}
		if e = release.ValidateConfig(cfg); e != nil {
			return e
		}
		migration := *cfg.Postgres
		migration.ConnectionStringEnv = os.Args[3]
		return release.MigratePostgres(context.Background(), migration)
	}
	service, e := release.New(cfg)
	if e != nil {
		return e
	}
	defer service.Close()
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	fmt.Fprintf(os.Stderr, "mixer-service: local development only, listening on %s\n", cfg.Listen)
	return service.Run(ctx)
}
