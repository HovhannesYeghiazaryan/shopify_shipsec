#!/bin/bash
# This script creates the PostgreSQL user, database, and sets the password.
# It is safe to run multiple times (idempotent).

DB_USER="shipsec_user"
DB_PASS="shipsec_passwd"
DB_NAME="shipsec"

# Run as the postgres user
sudo -u postgres psql <<EOF
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';
   END IF;
END
$do$;

CREATE DATABASE $DB_NAME OWNER $DB_USER;
GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;
EOF

echo "Database and user setup complete." 