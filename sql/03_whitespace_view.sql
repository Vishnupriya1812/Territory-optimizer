DROP TABLE IF EXISTS whitespace_view;

CREATE TABLE whitespace_view AS
SELECT
    c.state,
    COALESCE(t.total_revenue, 0.0)           AS total_revenue,
    COALESCE(t.rep_count, 0)                 AS rep_count,
    COALESCE(t.deal_count, 0)                AS deal_count,
    COALESCE(t.avg_deal_size, 0.0)           AS avg_deal_size,
    COALESCE(r.revenue_per_rep, 0.0)         AS revenue_per_rep,
    COALESCE(r.deals_per_rep, 0.0)           AS deals_per_rep,
    COALESCE(c.total_establishments, 0)      AS total_establishments,
    COALESCE(c.employees, 0)                 AS employees,
    COALESCE(c.annual_payroll, 0.0)          AS annual_payroll,
    COALESCE(c.gdp_proxy, 0.0)               AS market_potential,
    COALESCE(t.total_revenue, 0.0) / NULLIF(c.gdp_proxy, 0) AS penetration_index_raw
FROM census_enriched c
LEFT JOIN territory_rollup t ON c.state = t.state
LEFT JOIN rep_coverage r ON c.state = r.state;
