CREATE ROLE hfs WITH ENCRYPTED PASSWORD 'DEFAULT_PASSWORD' NOINHERIT VALID UNTIL 'infinity';
CREATE DATABASE hfs OWNER hfs;
-- Connect to database hfs
\c hfs;
SET ROLE hfs; -- Switch to user hfs
CREATE TABLE user_location(id SERIAL, hfs INTEGER, username VARCHAR);
