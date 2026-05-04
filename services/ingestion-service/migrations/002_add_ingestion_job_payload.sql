alter table ingestion_jobs
    add column if not exists tenant_id text not null default 'default',
    add column if not exists user_id text not null default 'anonymous',
    add column if not exists source_text text;
