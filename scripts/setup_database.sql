-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the database if it doesn't exist
-- Note: This needs to be run as a superuser from the postgres database
-- CREATE DATABASE teddy_service_db;

-- Create the teddy-ai schema
CREATE SCHEMA IF NOT EXISTS "teddy-ai";

-- Grant permissions on the schema
GRANT ALL ON SCHEMA "teddy-ai" TO postgres;
GRANT USAGE ON SCHEMA "teddy-ai" TO postgres;

-- Set search path to include teddy-ai schema
-- ALTER USER postgres SET search_path TO "teddy-ai", public;
