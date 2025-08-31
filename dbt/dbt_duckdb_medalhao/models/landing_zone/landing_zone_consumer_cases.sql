with source_consumer_cases as (
    
    select * from {{ source('landing_zone', 'consumer_cases')}}
),
final as (
    select *
    from source_consumer_cases
)

select * from final