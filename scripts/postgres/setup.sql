-- MailBrief PostgreSQL setup
-- Run as a PostgreSQL superuser:
--   sudo -u postgres psql -f scripts/postgres/setup.sql

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'mailbrief') THEN
        CREATE ROLE mailbrief WITH LOGIN PASSWORD 'mailbrief_dev_password';
    END IF;
END
$$;

SELECT 'CREATE DATABASE mailbrief OWNER mailbrief'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'mailbrief')\gexec

GRANT ALL PRIVILEGES ON DATABASE mailbrief TO mailbrief;

\connect mailbrief

GRANT ALL ON SCHEMA public TO mailbrief;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO mailbrief;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO mailbrief;
