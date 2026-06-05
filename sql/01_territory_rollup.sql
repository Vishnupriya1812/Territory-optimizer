-- Roll up revenue, deal count, rep coverage by state
DROP TABLE IF EXISTS territory_rollup;

CREATE TABLE territory_rollup AS
SELECT
    state,
    COUNT(DISTINCT sales_rep)        AS rep_count,
    COUNT(*)                         AS deal_count,
    SUM(revenue)                     AS total_revenue,
    AVG(revenue)                     AS avg_deal_size
FROM crm_sales
WHERE deal_stage = 'Won'
GROUP BY state;
