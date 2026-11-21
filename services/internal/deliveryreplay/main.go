// Command deliveryreplay checks PostgreSQL identity and outage for the local release fixture.
package main

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"net/url"
	"os"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5"
)

func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: deliveryreplay CA_FILE up|down")
		os.Exit(2)
	}
	if err := probe(os.Args[1], os.Args[2]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func probe(caFile, state string) error {
	if state != "up" && state != "down" {
		return errors.New("expected up or down")
	}
	dsn := url.URL{
		Scheme: "postgres",
		User:   url.UserPassword("mixer_release_delivery", "synthetic-replay-reader"),
		Host:   "127.0.0.1:5432",
		Path:   "/postgres",
		RawQuery: url.Values{
			"sslmode":     {"verify-full"},
			"sslrootcert": {caFile},
		}.Encode(),
	}
	ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
	defer cancel()

	connection, err := pgx.Connect(ctx, dsn.String())
	if connection != nil {
		defer connection.Close(ctx)
	}
	if state == "down" {
		if !errors.Is(err, syscall.ECONNREFUSED) {
			return fmt.Errorf("expected TCP connection refused, received %v", err)
		}
		fmt.Println("connection_refused")
		return nil
	}
	if err != nil {
		return err
	}

	transport, ok := connection.PgConn().Conn().(*tls.Conn)
	if !ok || len(transport.ConnectionState().VerifiedChains) == 0 {
		return errors.New("expected an independently verified PostgreSQL TLS chain")
	}
	var version int
	var role string
	var encrypted bool
	err = connection.QueryRow(ctx, `
		SELECT current_setting('server_version_num')::int, session_user::text, ssl
		FROM pg_stat_ssl WHERE pid = pg_backend_pid()
	`).Scan(&version, &role, &encrypted)
	if err != nil {
		return err
	}
	if version != 170011 || role != "mixer_release_delivery" || !encrypted {
		return fmt.Errorf("unexpected server identity: %d %s TLS=%t", version, role, encrypted)
	}
	fmt.Println("17.11 verify-full mixer_release_delivery")
	return nil
}
