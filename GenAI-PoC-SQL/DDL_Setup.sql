-- CREATE SCHEMA IF NOT EXISTS public;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS hstore;
-- drop table public.general_ledger_line_items;
-- drop table public.events;

CREATE TABLE public.general_ledger_line_items (
	effective_on timestamp NULL,
	description varchar(255) NULL,
	amount numeric(16, 2) NULL,
	account_balance_id int4 NULL,
	tenant_id int4 NULL,
	ledger_id int4 NULL,
	facility_id int4 NULL,
	created_at timestamp NULL,
	updated_at timestamp NULL,
	"uuid" uuid DEFAULT uuid_generate_v4() NULL,
	reversal bool DEFAULT false NULL,
	account_balance_item_id int4 NULL,
	internal_account_code varchar NULL,
	daily_transaction bool DEFAULT false NULL,
	transaction_type varchar NULL,
	hidden bool DEFAULT false NULL,
	reference_number varchar NULL,
	display_code varchar NULL,
	id bigserial NOT NULL
)
WITH (
	autovacuum_vacuum_scale_factor=0.0,
	autovacuum_vacuum_threshold=500000,
	autovacuum_analyze_scale_factor=0.0,
	autovacuum_analyze_threshold=500000
);


-- public.events definition

-- Drop table

-- DROP TABLE public.events;

CREATE TABLE public.events (
	id serial4 NOT NULL,
	"type" varchar(255) NULL,
	"data" public."hstore" DEFAULT ''::hstore NOT NULL,
	needs_followup bool DEFAULT false NULL,
	needs_followup_by timestamp NULL,
	followup_date timestamp NULL,
	resolved bool DEFAULT false NULL,
	created_by_id int4 NULL,
	updated_by_id int4 NULL,
	unit_id int4 NULL,
	tenant_id int4 NULL,
	source_id int4 NULL,
	facility_id int4 NULL,
	created_at timestamp NULL,
	updated_at timestamp NULL,
	parent_event_id int4 NULL,
	related_object_id int4 NULL,
	related_object_type varchar(255) NULL,
	"uuid" uuid DEFAULT uuid_generate_v4() NULL,
	status varchar(255) NULL,
	important_task bool DEFAULT false NULL,
	resolved_on timestamp NULL,
	created_by_type varchar(255) NULL,
	updated_by_type varchar(255) NULL,
	ledger_id int4 NULL,
	lead_id int4 NULL,
	support_case_id int4 NULL,
	attachment_id int4 NULL,
	action_item varchar NULL,
	ledger_delinquency_id int4 NULL,
	company_uuid uuid NULL,
	facility_uuid uuid NULL,
	tenant_uuid uuid NULL,
	ledger_uuid uuid NULL,
	unit_uuid uuid NULL,
	lead_uuid uuid NULL,
	related_object_uuid uuid NULL,
	client_application_id uuid NULL,
	payment_intent_id uuid NULL,
	CONSTRAINT events_pkey PRIMARY KEY (id)
)
WITH (
	autovacuum_vacuum_scale_factor=0.0,
	autovacuum_vacuum_threshold=500000,
	autovacuum_analyze_scale_factor=0.0,
	autovacuum_analyze_threshold=500000
);
CREATE INDEX index_events_on_attachment_id ON public.events USING btree (attachment_id);
CREATE INDEX index_events_on_created_by_id_and_created_by_type ON public.events USING btree (created_by_id, created_by_type);
CREATE INDEX index_events_on_facid_type_created_at ON public.events USING btree (facility_id, type, created_at);
CREATE INDEX index_events_on_facility_id_and_followup_date ON public.events USING btree (facility_id, followup_date);
CREATE INDEX index_events_on_facility_id_and_needs_followup ON public.events USING btree (facility_id, needs_followup) WHERE (needs_followup = true);
CREATE INDEX index_events_on_lead_id ON public.events USING btree (lead_id);
CREATE INDEX index_events_on_ledger_id_and_type ON public.events USING btree (ledger_id, type);
CREATE INDEX index_events_on_parent_event_id ON public.events USING btree (parent_event_id);
CREATE INDEX index_events_on_related_object_id_and_related_object_type ON public.events USING btree (related_object_id, related_object_type);
CREATE INDEX index_events_on_source_id ON public.events USING btree (source_id);
CREATE INDEX index_events_on_support_case_id ON public.events USING btree (support_case_id);
CREATE INDEX index_events_on_tenant_id_and_created_at ON public.events USING btree (tenant_id, created_at);
CREATE INDEX index_events_on_tenant_id_and_type_and_created_at ON public.events USING btree (tenant_id, type, created_at);
CREATE INDEX index_events_on_type ON public.events USING btree (type);
CREATE INDEX index_events_on_unit_id_and_type_and_created_at ON public.events USING btree (unit_id, type, created_at);
CREATE UNIQUE INDEX index_events_on_uuid ON public.events USING btree (uuid);
CREATE INDEX index_payment_and_unit_events_on_payment_intent_id ON public.events USING btree (payment_intent_id) WHERE ((payment_intent_id IS NOT NULL) AND (((type)::text ~~ '%UnitEvent'::text) OR ((type)::text ~~ '%PaymentEvent'::text)));


COPY public.general_ledger_line_items
FROM 'C:/EPAM-Personal/GenAI-PoC-SQL/general_ledger_line_items_postgres.csv'
DELIMITER ','
CSV HEADER;


COPY public.events
FROM 'C:/EPAM-Personal/GenAI-PoC-SQL/events_postgres.csv'
DELIMITER ','
CSV HEADER;

SELECT COUNT(*) FROM public.general_ledger_line_items;

SELECT COUNT(*) FROM public.events;


-- create table abc(name varchar(100));

