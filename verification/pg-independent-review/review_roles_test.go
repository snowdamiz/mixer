//go:build postgres_integration

package release

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5"
)

func TestPostgresReviewRoleMembershipSemantics(t *testing.T) {
	for _, mode := range []string{"inherit", "set", "inert", "admin", "inherited-admin", "set-admin"} {
		t.Run(mode, func(t *testing.T) {
			cfg, _, owner, _ := pgFixture(t)
			var database string
			if err := owner.QueryRow(context.Background(), "SELECT current_database()").Scan(&database); err != nil {
				t.Fatal(err)
			}
			group := "role_" + strings.TrimPrefix(database, "test_")
			middle := group + "_mid"
			g := pgx.Identifier{group}.Sanitize()
			m := pgx.Identifier{middle}.Sanitize()
			if _, err := owner.Exec(context.Background(), "CREATE ROLE "+g+" NOLOGIN; CREATE ROLE "+m+" NOLOGIN"); err != nil {
				t.Fatal(err)
			}
			options := "INHERIT FALSE, SET FALSE, ADMIN FALSE"
			if mode == "inherit" {
				options = "INHERIT TRUE, SET FALSE, ADMIN FALSE"
			} else if mode == "set" {
				options = "INHERIT FALSE, SET TRUE, ADMIN FALSE"
			} else if mode == "admin" {
				options = "INHERIT FALSE, SET FALSE, ADMIN TRUE"
			}
			grant := "GRANT " + g + " TO mixer_test_runtime WITH " + options
			if mode == "inherited-admin" || mode == "set-admin" {
				intermediate := "INHERIT TRUE, SET FALSE, ADMIN FALSE"
				if mode == "set-admin" {
					intermediate = "INHERIT FALSE, SET TRUE, ADMIN FALSE"
				}
				grant = "GRANT " + g + " TO " + m + " WITH INHERIT FALSE, SET FALSE, ADMIN TRUE; GRANT " + m + " TO mixer_test_runtime WITH " + intermediate
			}
			if _, err := owner.Exec(context.Background(), grant); err != nil {
				t.Fatal(err)
			}
			defer owner.Exec(context.Background(), "REVOKE "+g+", "+m+" FROM mixer_test_runtime")
			conn, err := pgx.Connect(context.Background(), os.Getenv(cfg.Postgres.ConnectionStringEnv))
			if err != nil {
				t.Fatal(err)
			}
			defer closePostgres(conn)
			var member, usage, assume bool
			if err := conn.QueryRow(context.Background(), "SELECT pg_has_role(current_user,$1,'MEMBER'),pg_has_role(current_user,$1,'USAGE'),pg_has_role(current_user,$1,'SET')", group).Scan(&member, &usage, &assume); err != nil {
				t.Fatal(err)
			}
			if !member || usage != (mode == "inherit") || assume != (mode == "set") {
				t.Fatalf("unexpected membership semantics: mode%s member%v usage%v set%v", mode, member, usage, assume)
			}
			if mode == "set-admin" {
				if _, err := conn.Exec(context.Background(), "SET ROLE "+m); err != nil {
					t.Fatal(err)
				}
			}
			_, err = conn.Exec(context.Background(), "GRANT "+g+" TO mixer_test_runtime WITH SET TRUE")
			granted := err == nil
			t.Logf("mode=%s MEMBER=%v USAGE=%v SET=%v canGrantSelfSET=%v", mode, member, usage, assume, granted)
			if granted != (mode == "admin" || mode == "inherited-admin" || mode == "set-admin") {
				t.Fatalf("unexpected administrative authority: %v", err)
			}
		})
	}
}
