//go:build postgres_integration

package release

import (
	"context"
	"strings"
	"testing"

	"github.com/jackc/pgx/v5"
)

func TestPostgresStartupRejectsUsableSchemaAndFunctionOwnership(t *testing.T) {
	for _, object := range []string{"SCHEMA mixer_release", "FUNCTION mixer_release.monotonic_channel()"} {
		for _, mode := range []string{"direct", "inherit", "set", "inert", "admin", "inherited-admin", "set-admin", "nested-admin"} {
			t.Run(object+"/"+mode, func(t *testing.T) {
				cfg, _, owner, _ := pgFixture(t)
				target := "mixer_test_runtime"
				if mode != "direct" {
					var database string
					var version int
					if err := owner.QueryRow(context.Background(), "SELECT current_database(),current_setting('server_version_num')::integer").Scan(&database, &version); err != nil {
						t.Fatal(err)
					}
					if version < 160000 {
						t.Skip("per-membership INHERIT/SET options require PostgreSQL16+; this case is not qualified on older servers")
					}
					target = "owner_" + strings.TrimPrefix(database, "test_")
					group, middle, bridge := pgx.Identifier{target}.Sanitize(), pgx.Identifier{target + "_mid"}.Sanitize(), pgx.Identifier{target + "_bridge"}.Sanitize()
					if _, err := owner.Exec(context.Background(), "CREATE ROLE "+group+" NOLOGIN; CREATE ROLE "+middle+" NOLOGIN; CREATE ROLE "+bridge+" NOLOGIN"); err != nil {
						t.Fatal(err)
					}
					grant := "GRANT " + group + " TO mixer_test_runtime WITH INHERIT FALSE, SET FALSE, ADMIN FALSE"
					switch mode {
					case "inherit":
						grant = "GRANT " + group + " TO mixer_test_runtime WITH INHERIT TRUE, SET FALSE, ADMIN FALSE"
					case "set":
						grant = "GRANT " + group + " TO mixer_test_runtime WITH INHERIT FALSE, SET TRUE, ADMIN FALSE"
					case "admin":
						grant = "GRANT " + group + " TO mixer_test_runtime WITH INHERIT FALSE, SET FALSE, ADMIN TRUE"
					case "inherited-admin", "set-admin":
						options := "INHERIT TRUE, SET FALSE, ADMIN FALSE"
						if mode == "set-admin" {
							options = "INHERIT FALSE, SET TRUE, ADMIN FALSE"
						}
						grant = "GRANT " + group + " TO " + middle + " WITH INHERIT FALSE, SET FALSE, ADMIN TRUE; GRANT " + middle + " TO mixer_test_runtime WITH " + options
					case "nested-admin":
						grant = "GRANT " + group + " TO " + middle + " WITH INHERIT FALSE, SET FALSE, ADMIN TRUE; GRANT " + middle + " TO " + bridge + " WITH INHERIT FALSE, SET FALSE, ADMIN TRUE; GRANT " + bridge + " TO mixer_test_runtime WITH INHERIT FALSE, SET FALSE, ADMIN TRUE"
					}
					if _, err := owner.Exec(context.Background(), grant); err != nil {
						t.Fatal(err)
					}
					defer owner.Exec(context.Background(), "REVOKE "+group+", "+middle+", "+bridge+" FROM mixer_test_runtime")
				}
				if _, err := owner.Exec(context.Background(), "ALTER "+object+" OWNER TO "+pgx.Identifier{target}.Sanitize()); err != nil {
					t.Fatal(err)
				}
				service, err := New(cfg)
				if mode == "inert" {
					if err != nil {
						t.Fatal("non-inherited, non-assumable, non-administrable membership was rejected", err)
					}
					service.Close()
					return
				}
				if err == nil {
					service.Close()
					t.Fatal("runtime with usable installed schema/function owner authority accepted")
				}
				if !strings.Contains(err.Error(), "non-owner") {
					t.Fatal("ownership did not produce the explicit role rejection", err)
				}
			})
		}
	}
}

func TestPostgresStartupAndMigrationRejectUnknownVersionWithMatchingChecksum(t *testing.T) {
	cfg, _, owner, ownerDSN := pgFixture(t)
	// Simulate owner-side migration metadata drift. A matching historical checksum
	// must not substitute for an explicit supported-version check.
	if _, err := owner.Exec(context.Background(), "ALTER TABLE mixer_release.schema_migrations DROP CONSTRAINT schema_migrations_version_check; UPDATE mixer_release.schema_migrations SET version=2"); err != nil {
		t.Fatal(err)
	}
	service, err := New(cfg)
	if err == nil {
		service.Close()
		t.Fatal("runtime accepted version2 with version1 checksum")
	}
	if !strings.Contains(err.Error(), "version/checksum") {
		t.Fatal("unknown version did not produce the explicit metadata rejection", err)
	}
	t.Setenv(cfg.Postgres.ConnectionStringEnv, ownerDSN)
	if err := MigratePostgres(context.Background(), *cfg.Postgres); err == nil || !strings.Contains(err.Error(), "version/checksum") {
		t.Fatal("migration retry did not reject version2 with version1 checksum", err)
	}
}

func TestPostgresStartupElevatedAttributesRequireAssumableRole(t *testing.T) {
	for _, attribute := range []string{"SUPERUSER", "BYPASSRLS", "CREATEROLE", "CREATEDB"} {
		for _, mode := range []string{"inherit", "set", "inert"} {
			t.Run(attribute+"/"+mode, func(t *testing.T) {
				cfg, fixture, owner, _ := pgFixture(t)
				var database string
				var version int
				if err := owner.QueryRow(context.Background(), "SELECT current_database(),current_setting('server_version_num')::integer").Scan(&database, &version); err != nil {
					t.Fatal(err)
				}
				if version < 160000 {
					t.Skip("per-membership INHERIT/SET options require PostgreSQL16+; this case is not qualified on older servers")
				}
				initial := pgServer(t, cfg, nil)
				_, _ = pgUpload(t, initial, fixture, "role-attribute")
				initial.Close()
				group := pgx.Identifier{"attribute_" + strings.TrimPrefix(database, "test_")}.Sanitize()
				options := "INHERIT FALSE, SET FALSE, ADMIN FALSE"
				if mode == "inherit" {
					options = "INHERIT TRUE, SET FALSE, ADMIN FALSE"
				} else if mode == "set" {
					options = "INHERIT FALSE, SET TRUE, ADMIN FALSE"
				}
				if _, err := owner.Exec(context.Background(), "CREATE ROLE "+group+" NOLOGIN "+attribute+"; GRANT "+group+" TO mixer_test_runtime WITH "+options); err != nil {
					t.Fatal(err)
				}
				defer owner.Exec(context.Background(), "REVOKE "+group+" FROM mixer_test_runtime")
				service, err := New(cfg)
				if mode == "set" {
					if err == nil {
						service.Close()
						t.Fatal("assumable elevated role was accepted")
					}
					if !strings.Contains(err.Error(), "non-owner") {
						t.Fatal("elevated role did not produce explicit role rejection", err)
					}
					return
				}
				if err != nil {
					t.Fatal("non-assumable attribute-only role was rejected", err)
				}
				defer service.Close()
				var count int
				if err := service.db.(*postgresStore).pool.QueryRow(context.Background(), "SELECT count(*) FROM mixer_release.artifacts").Scan(&count); err != nil || count != 0 {
					t.Fatal("non-assumable elevated attributes bypassed unscoped FORCE RLS", count, err)
				}
			})
		}
	}
}
