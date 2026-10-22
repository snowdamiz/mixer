package main

import (
	"context"
	"fmt"
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
	b, e := os.ReadFile(path)
	if e != nil {
		return e
	}
	var cfg release.Config
	if e = protocol.DecodeJSON(b, &cfg); e != nil {
		return e
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
