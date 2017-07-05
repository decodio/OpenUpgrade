-------------------------------------------------------------------------
-- Postgres tools
-------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "unaccent";
CREATE EXTENSION IF NOT EXISTS "tablefunc";
CREATE EXTENSION IF NOT EXISTS "adminpack";
CREATE EXTENSION IF NOT EXISTS "postgres_fdw";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "ltree";
CREATE EXTENSION IF NOT EXISTS "hstore";
CREATE EXTENSION IF NOT EXISTS plpythonu;

-------------------------------------------------------------------------
-- Database wide IR dictionary
-------------------------------------------------------------------------
CREATE TABLE ir_serial
(
    id bigint NOT NULL,
    name varchar,
    guid uuid DEFAULT uuid_generate_v4(),
    schema_name varchar,
    table_name varchar,
    ir_model_id bigint, -- references ir_model without FK!

    create_date timestamp without time zone,
    write_date  timestamp without time zone,
    delete_date timestamp without time zone,
    create_uid bigint, --references res_users on delete ? restrict or set null,
    write_uid bigint,
    delete_uid bigint,
    CONSTRAINT ir_serial_pkey PRIMARY KEY (id)
);
CREATE SEQUENCE ir_serial_id_seq;
SELECT setval('ir_serial_id_seq', 1000000); -- have to be bigger than largest

CREATE TABLE ir_audit
 (
  id bigserial NOT NULL,
  ir_serial_id bigint, -- references ir_serial
  change_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
  operation varchar,
  --values_before hstore,
  values_after  hstore,
  CONSTRAINT ir_audit_pkey PRIMARY KEY (id)
 );

CREATE OR REPLACE FUNCTION oe_audit()
  RETURNS trigger
  LANGUAGE plpgsql
AS $$
DECLARE
   _uid bigint := 1; -- blame the admin :(
   _values_before hstore;
   _excluded_cols text[] := '{"id","parent_left","parent_right","level"}' ;
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF hstore(NEW) ? 'create_uid' THEN
           _uid = coalesce(NEW.create_uid, 1);
        END IF;
        -- insert all rows from all tables using ir_serial_id_seq for id
        INSERT INTO ir_serial ( id, table_name,     schema_name, create_uid, create_date)
                    VALUES (NEW.id, TG_RELNAME, TG_TABLE_SCHEMA,       _uid, now() AT TIME ZONE 'UTC');
    ELSE
        IF hstore(OLD) ? 'write_uid' THEN
           _uid = coalesce(OLD.write_uid, 1); --TODO this is wrong for now...
        END IF;
        IF TG_OP = 'DELETE' THEN
            UPDATE ir_serial SET (delete_uid, delete_date             )
                                =(_uid      , now() AT TIME ZONE 'UTC')
             WHERE id = OLD.id;
            IF TG_ARGV[0] IS NOT NULL THEN  -- 1. parameter log values after updates and deletes?
               INSERT INTO ir_audit (ir_serial_id, operation, values_before)
                             VALUES (      OLD.id,     TG_OP, hstore(OLD)  );  -- row_to_json(OLD)
            END IF;
        END IF;
        IF TG_OP = 'UPDATE' THEN
            UPDATE ir_serial SET (write_uid, write_date              )
                                =(_uid     , now() AT TIME ZONE 'UTC')
             WHERE id = OLD.id;
            IF TG_ARGV[0] IS NULL THEN  RETURN NULL; END IF;-- 1. parameter log values after updates and deletes?
            IF TG_ARGV[1] IS NOT NULL THEN -- -- 2. parameter holds array of excluded cols for this table
               _excluded_cols := _excluded_cols || TG_ARGV[1]::text[];
            END IF;
             _values_before =  (hstore(NEW.*) - hstore(OLD.*)) - _excluded_cols;
            IF _values_before = hstore('') THEN RETURN NULL; END IF; -- All changed fields are ignored. Skip this update.
            INSERT INTO ir_audit (ir_serial_id, operation, values_before)
                          VALUES (      OLD.id,     TG_OP, _values_before);  -- row_to_json(OLD)
        END IF;
    END IF;
    RETURN NULL;
END;
$$;
-------------------------------------------------------------------------
-- CHANGES:
-- "id serial," -> "id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),"
-- "integer" -> "bigint"
-------------------------------------------------------------------------


---------------------------------
-- id and sequence change example for ir_model
---------------------------------
--ALTER TABLE ir_model ALTER COLUMN id TYPE bigint;
--ALTER TABLE ir_model ALTER COLUMN id SET DEFAULT nextval('ir_serial_id_seq'::regclass);

