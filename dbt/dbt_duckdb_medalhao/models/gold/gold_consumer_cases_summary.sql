with silver as (
    select * from {{ ref('silver_consumer_cases') }}
),
-- Exemplo de agregação pronta para negócio: métricas por empresa e produto
summary as (
    select
        company,
        product,
        count(*) as total_cases,
        sum(case when status = 'Resolved' then 1 else 0 end) as resolved_cases,
        sum(case when status in ('Open','In Progress') then 1 else 0 end) as open_or_in_progress_cases,
        sum(try_cast(compensation_amount as double)) as total_compensation,
        max(updated_at) as last_update
    from silver
    group by company, product
)
select * from summary
