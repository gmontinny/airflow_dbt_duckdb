{{ config(
        materialized='incremental',
        incremental_strategy='merge',
        unique_key=['case_id']
    )
}}
with bronze_consumer_cases as (
    select * from {{ ref('bronze_consumer_cases') }}
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
    CAST(updated_at AS TIMESTAMP) AS updated_at
    FROM bronze_consumer_cases
    {% if is_incremental() %}
        WHERE updated_at > (select max(updated_at) from {{ this }})
    {% endif %}
)

SELECT *
FROM final