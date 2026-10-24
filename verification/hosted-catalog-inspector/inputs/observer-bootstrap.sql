-- Disposable isolated fixture only. Never run against a live deployment.
CREATE ROLE catalog_inspector_observer LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION;
GRANT pg_read_all_settings TO catalog_inspector_observer WITH ADMIN FALSE, INHERIT TRUE, SET FALSE;
GRANT CONNECT ON DATABASE authority_contract TO catalog_inspector_observer;
