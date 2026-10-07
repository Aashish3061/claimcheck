-- ClaimCheck schema (run once in the Supabase SQL editor). RLS on everything, no policies:
-- only the server, using the secret key (service_role), can read or write.
create extension if not exists vector with schema extensions;

create table if not exists corpus_chunks (
  id bigserial primary key,
  chunk_id text unique not null,
  doc_id text not null,
  doc_type text not null check (doc_type in ('regulation','policy_wording','checklist','non_payable_item','claim_form')),
  policy_id text,
  title text, issuer text, ref_no text, doc_date date,
  status text not null check (status in ('in_force','repealed','policy_wording','checklist','verify')),
  section text, page int, list_no int, url text,
  content text not null,
  fts tsvector generated always as (to_tsvector('english', content)) stored,
  embedding extensions.vector(768)
);
create index if not exists corpus_chunks_fts on corpus_chunks using gin (fts);
create index if not exists corpus_chunks_emb on corpus_chunks using hnsw (embedding vector_ip_ops);
create index if not exists corpus_chunks_type on corpus_chunks (doc_type, policy_id);

-- Hybrid search: full-text + semantic, merged with reciprocal rank fusion (Supabase docs pattern, with filters).
create or replace function hybrid_search(
  query_text text, query_embedding extensions.vector(768), match_count int,
  filter_doc_types text[], filter_policy_id text default null,
  full_text_weight float default 1, semantic_weight float default 1, rrf_k int default 50)
returns setof corpus_chunks language sql set search_path = public, extensions as $$
with full_text as (
  select id, row_number() over (order by ts_rank_cd(fts, websearch_to_tsquery('english', replace(query_text, ' ', ' or '))) desc) as rank_ix
  from corpus_chunks
  where fts @@ websearch_to_tsquery('english', replace(query_text, ' ', ' or '))
    and doc_type = any(filter_doc_types)
    and (filter_policy_id is null or policy_id = filter_policy_id)
  order by rank_ix limit least(match_count, 30) * 2
),
semantic as (
  select id, row_number() over (order by embedding <#> query_embedding) as rank_ix
  from corpus_chunks
  where doc_type = any(filter_doc_types)
    and (filter_policy_id is null or policy_id = filter_policy_id)
  order by rank_ix limit least(match_count, 30) * 2
)
select corpus_chunks.* from full_text
  full outer join semantic on full_text.id = semantic.id
  join corpus_chunks on coalesce(full_text.id, semantic.id) = corpus_chunks.id
order by coalesce(1.0 / (rrf_k + full_text.rank_ix), 0.0) * full_text_weight
       + coalesce(1.0 / (rrf_k + semantic.rank_ix), 0.0) * semantic_weight desc
limit least(match_count, 30)
$$;

create table if not exists runs (
  id bigserial primary key, created_at timestamptz default now(),
  session_id text, stage text, pipeline_version text, model text, thinking_level text,
  prompt_tokens int, output_tokens int, thoughts_tokens int, cached_tokens int, tool_prompt_tokens int,
  latency_ms int, cost_inr numeric, ok bool, error_code text, verdict_counts jsonb
);  -- no document content is ever stored here

create table if not exists eval_runs (
  id bigserial primary key, created_at timestamptz default now(),
  pipeline_version text, model text, thinking_level text, split text, case_id text,
  metrics jsonb, cost_inr numeric, latency_ms int
);

create table if not exists daily_usage (day date primary key, sessions int not null default 0);
create or replace function bump_usage(cap int) returns boolean language plpgsql set search_path = public as $$
declare n int;
begin
  insert into daily_usage(day, sessions) values (current_date, 1)
  on conflict (day) do update set sessions = daily_usage.sessions + 1 returning sessions into n;
  return n <= cap;
end $$;

alter table corpus_chunks enable row level security;
alter table runs enable row level security;
alter table eval_runs enable row level security;
alter table daily_usage enable row level security;

-- Data API roles get nothing; service_role (secret key) gets what the server needs.
revoke all on corpus_chunks, runs, eval_runs, daily_usage from anon, authenticated;
revoke execute on function hybrid_search(text, extensions.vector, int, text[], text, float, float, int) from public, anon, authenticated;
revoke execute on function bump_usage(int) from public, anon, authenticated;
grant usage on schema public to service_role;
grant select, insert, update, delete on corpus_chunks, runs, eval_runs, daily_usage to service_role;
grant usage, select on all sequences in schema public to service_role;
grant execute on function hybrid_search(text, extensions.vector, int, text[], text, float, float, int) to service_role;
grant execute on function bump_usage(int) to service_role;
