-- Revenue per rep (efficiency metric)
DROP TABLE IF EXISTS rep_coverage;

CREATE TABLE rep_coverage AS
SELECT
    state,
    total_revenue / NULLIF(rep_count, 0) AS revenue_per_rep,
    deal_count    / NULLIF(rep_count, 0) AS deals_per_rep
FROM territory_rollup;
