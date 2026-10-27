CREATE ROLE dispatcher_default_admin LOGIN SUPERUSER;
CREATE ROLE dispatcher_default_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE dispatcher_default_runtime LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE DATABASE mixer_dispatcher_default_authority OWNER dispatcher_default_admin;
\connect mixer_dispatcher_default_authority
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
ALTER SCHEMA public OWNER TO dispatcher_default_owner;
GRANT USAGE ON SCHEMA public TO dispatcher_default_runtime;
