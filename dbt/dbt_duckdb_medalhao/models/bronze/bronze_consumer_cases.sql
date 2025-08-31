with landing_zone_consumer_cases as (
    select * from {{ ref('landing_zone_consumer_cases') }}
),

final as (
    SELECT 
    case_id,
    consumer_name,
    product,
    issue,
    date_reported,
    company,
    status,
    resolution_date,
    violation_type,
    compensation_amount,
    updated_at
    FROM (
        SELECT *,
        row_number() over(partition by case_id order by updated_at desc) as ROW_NUM
        from landing_zone_consumer_cases
    )
    WHERE ROW_NUM = 1
)

SELECT *
FROM final