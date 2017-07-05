-------------------------------------------------------------------------
-- Pure SQL
-------------------------------------------------------------------------

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
SELECT setval('ir_serial_id_seq', 1000); -- to allow initial inserts

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

CREATE TABLE ir_actions (
  id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
  create_uid bigint,
  primary key(id)
);
CREATE TABLE ir_act_window (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_report_xml (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_url (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_server (primary key(id)) INHERITS (ir_actions);
CREATE TABLE ir_act_client (primary key(id)) INHERITS (ir_actions);

--CREATE TRIGGER ir_actions_audit        AFTER INSERT OR UPDATE OR DELETE ON ir_actions        FOR EACH ROW EXECUTE PROCEDURE oe_audit();
--CREATE TRIGGER ir_act_window_audit     AFTER INSERT OR UPDATE OR DELETE ON ir_act_window     FOR EACH ROW EXECUTE PROCEDURE oe_audit();
--CREATE TRIGGER ir_act_report_xml_audit AFTER INSERT OR UPDATE OR DELETE ON ir_act_report_xml FOR EACH ROW EXECUTE PROCEDURE oe_audit();
--CREATE TRIGGER ir_act_url_audit        AFTER INSERT OR UPDATE OR DELETE ON ir_act_url        FOR EACH ROW EXECUTE PROCEDURE oe_audit();
--CREATE TRIGGER ir_act_server_audit     AFTER INSERT OR UPDATE OR DELETE ON ir_act_server     FOR EACH ROW EXECUTE PROCEDURE oe_audit();
--CREATE TRIGGER ir_act_client_audit     AFTER INSERT OR UPDATE OR DELETE ON ir_act_client     FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_model (
  id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
  create_uid bigint,
  model varchar NOT NULL,
  name varchar,
  state varchar,
  info text,
  primary key(id)
);
--CREATE TRIGGER ir_model_audit AFTER INSERT OR UPDATE OR DELETE ON ir_model FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_model_fields (
  id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
  create_uid bigint,
  model varchar NOT NULL,
  model_id bigint references ir_model on delete cascade,
  name varchar NOT NULL,
  relation varchar,
  select_level varchar,
  field_description varchar,
  ttype varchar,
  state varchar default 'base',
  relation_field varchar,
  translate boolean default False,
  serialization_field_id bigint references ir_model_fields on delete cascade,
  primary key(id)
);
--CREATE TRIGGER ir_model_fields_audit AFTER INSERT OR UPDATE OR DELETE ON ir_model_fields FOR EACH ROW EXECUTE PROCEDURE oe_audit();


CREATE TABLE res_lang (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    name VARCHAR NOT NULL UNIQUE,
    code VARCHAR(16) NOT NULL UNIQUE,
    primary key(id)
);
--CREATE TRIGGER res_lang_audit AFTER INSERT OR UPDATE OR DELETE ON res_lang FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE res_users (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    active boolean default True,
    login varchar(64) NOT NULL UNIQUE,
    password varchar default null,
    -- No FK references below, will be added later by ORM
    -- (when the destination rows exist)
    company_id bigint, -- references res_company,
    partner_id bigint, -- references res_partner,
    primary key(id)
);
--CREATE TRIGGER res_users_audit AFTER INSERT OR UPDATE OR DELETE ON res_users FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE wkf (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    name varchar,
    osv varchar,
    on_create bool default false,
    primary key(id)
);
--CREATE TRIGGER wkf_audit AFTER INSERT OR UPDATE OR DELETE ON wkf FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_module_category (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    write_date timestamp without time zone,
    write_uid bigint,
    parent_id bigint REFERENCES ir_module_category ON DELETE SET NULL,
    name character varying NOT NULL,
    primary key(id)
);
--CREATE TRIGGER ir_module_category_audit AFTER INSERT OR UPDATE OR DELETE ON ir_module_category FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_module_module (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    write_date timestamp without time zone,
    write_uid bigint,
    website character varying,
    summary character varying,
    name character varying NOT NULL,
    author character varying,
    icon varchar,
    state character varying,
    latest_version character varying,
    shortdesc character varying,
    category_id bigint REFERENCES ir_module_category ON DELETE SET NULL,
    description text,
    application boolean default False,
    demo boolean default False,
    web boolean DEFAULT FALSE,
    license character varying,
    sequence bigint DEFAULT 100,
    auto_install boolean default False,
    primary key(id)
);
ALTER TABLE ir_module_module add constraint name_uniq unique (name);
--CREATE TRIGGER ir_module_module_audit AFTER INSERT OR UPDATE OR DELETE ON ir_module_module FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_module_module_dependency (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    write_date timestamp without time zone,
    write_uid bigint,
    name character varying,
    module_id bigint REFERENCES ir_module_module ON DELETE cascade,
    primary key(id)
);
--CREATE TRIGGER ir_module_module_dependency_audit AFTER INSERT OR UPDATE OR DELETE ON ir_module_module_dependency FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE ir_model_data (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    write_date timestamp without time zone,
    write_uid bigint,
    noupdate boolean,
    name varchar NOT NULL,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module varchar NOT NULL,
    model varchar NOT NULL,
    res_id bigint,
    primary key(id)
);
--CREATE TRIGGER ir_model_data_audit AFTER INSERT OR UPDATE OR DELETE ON ir_model_data FOR EACH ROW EXECUTE PROCEDURE oe_audit();

-- Records foreign keys and constraints installed by a module (so they can be
-- removed when the module is uninstalled):
--   - for a foreign key: type is 'f',
--   - for a constraint: type is 'u' (this is the convention PostgreSQL uses).
CREATE TABLE ir_model_constraint (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module bigint NOT NULL references ir_module_module on delete restrict,
    model bigint NOT NULL references ir_model on delete restrict,
    type character varying(1) NOT NULL,
    name varchar NOT NULL,
    primary key(id)
);
--CREATE TRIGGER ir_model_constraint_audit AFTER INSERT OR UPDATE OR DELETE ON ir_model_constraint FOR EACH ROW EXECUTE PROCEDURE oe_audit();

-- Records relation tables (i.e. implementing many2many) installed by a module
-- (so they can be removed when the module is uninstalled).
CREATE TABLE ir_model_relation (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    date_init timestamp without time zone,
    date_update timestamp without time zone,
    module bigint NOT NULL references ir_module_module on delete restrict,
    model bigint NOT NULL references ir_model on delete restrict,
    name varchar NOT NULL,
    primary key(id)
);  
--CREATE TRIGGER ir_model_relation_audit AFTER INSERT OR UPDATE OR DELETE ON ir_model_relation FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE res_currency (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    name varchar NOT NULL,
    primary key(id)
);
--CREATE TRIGGER res_currency_audit AFTER INSERT OR UPDATE OR DELETE ON res_currency FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE res_company (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    name varchar NOT NULL,
    partner_id bigint,
    currency_id bigint,
    primary key(id)
);
--CREATE TRIGGER res_company_audit AFTER INSERT OR UPDATE OR DELETE ON res_company FOR EACH ROW EXECUTE PROCEDURE oe_audit();

CREATE TABLE res_partner (
    id bigint NOT NULL DEFAULT nextval('ir_serial_id_seq'),
    create_uid bigint,
    create_date timestamp without time zone DEFAULT (now() AT TIME ZONE 'UTC'),
    name varchar,
    company_id bigint,
    primary key(id)
);
--CREATE TRIGGER res_partner_audit AFTER INSERT OR UPDATE OR DELETE ON res_partner FOR EACH ROW EXECUTE PROCEDURE oe_audit();

---------------------------------
-- Default data
---------------------------------
insert into res_currency (id, name) VALUES (10, 'EUR');
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('EUR', 'base', 'res.currency', true, 10);
--select setval('res_currency_id_seq', 2);

insert into res_company (id, name, partner_id, currency_id) VALUES (20, 'Your Company', 30, 10);
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('main_company', 'base', 'res.company', true, 20);
--select setval('res_company_id_seq', 2);

insert into res_partner (id, name, company_id) VALUES (30, 'Your Company', 20);
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('main_partner', 'base', 'res.partner', true, 30);
--select setval('res_partner_id_seq', 2);

insert into res_users (id, login, password, active, partner_id, company_id) VALUES (1, 'admin', 'admin', true, 30, 20);
insert into ir_model_data (name, module, model, noupdate, res_id) VALUES ('user_root', 'base', 'res.users', true, 1);
--select setval('res_users_id_seq', 2);
