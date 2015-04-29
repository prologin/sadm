CREATE ROLE hfs WITH LOGIN ENCRYPTED PASSWORD 'DEFAULT_PASSWORD';
CREATE DATABASE hfs OWNER hfs;
-- Connect to database hfs
\c hfs;
SET ROLE hfs; -- Switch to user hfs
CREATE TABLE user_location(id SERIAL, hfs INTEGER, username VARCHAR);
