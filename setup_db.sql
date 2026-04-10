-- Interview Sarathi — PostgreSQL Setup
-- Run as superuser:  psql -U postgres -f scripts/setup_db.sql

CREATE USER sarathi_user WITH PASSWORD 'sarathi_pass';
CREATE DATABASE sarathi_db OWNER sarathi_user;
GRANT ALL PRIVILEGES ON DATABASE sarathi_db TO sarathi_user;

\c sarathi_db;
GRANT ALL ON SCHEMA public TO sarathi_user;

-- Tables are auto-created by SQLAlchemy on first server start.
-- To verify after startup:  \dt
