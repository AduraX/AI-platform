create table if not exists documents (
    document_id text primary key,
    filename text not null,
    content_type text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists ingestion_jobs (
    job_id text primary key,
    document_id text not null references documents(document_id),
    status text not null check (status in ('pending', 'completed', 'failed')),
    indexed_chunks integer not null default 0,
    tenant_id text not null default 'default',
    user_id text not null default 'anonymous',
    source_text text,
    error text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_ingestion_jobs_document_id
    on ingestion_jobs(document_id);

create index if not exists idx_ingestion_jobs_status
    on ingestion_jobs(status);
