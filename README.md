# Duka Sales Exploration and Agent Data Cleanup

**Name:** PAULINE MAGEMBE MOSE | **Cohort:** 1 MILLION DEVS

## Summary of both engagements
**Engagement 1 · Duka Electronics.** Half-year review (1 Jan to 29 Jun 2026) of 1,000 orders across five branches. The notebook inspects the data, derives `revenue`, `month`, `weekday`, `is_weekend` and `price_band`, answers each task in Markdown beneath the code, exports the Premium online orders from Nairobi and Mombasa, and confirms that an Excel workbook (SUMIFS, XLOOKUP, PivotTable) matches pandas.

**Engagement 2 · Mobile-money agent network.** A legacy extract (612 rows, 20 agents) was audited across six data-quality dimensions, cleaned with a reusable function, merged with the agent register and summarised by county and week. Five amounts of exactly KES 250,000 make up 46.5% of all value and are flagged for verification, not deleted.

## How to regenerate the data and run each notebook
1. `pip install -r requirements.txt`
2. `python generate_data.py` writes `duka_sales.csv`, `agents.csv` and `agent_transactions.csv` (raw files are not committed).
3. Run `duka_sales_exploration.ipynb` and `agent_cleanup.ipynb` with Restart and Run All. The agent notebook imports `clean_agent_data()` from `cleaning_pipeline.py`.

## Duka Executive Summary
- Duka earned **KES 71,792,500** from **1,000 orders** (1 Jan to 29 Jun 2026), **KES 71,792.50** per order.
- **Nairobi** leads with **KES 26,106,100 (36.4%)** from 376 orders, and all five branches rank the same by revenue and by orders because average order values differ by only about 10% (KES 68,353 to 75,591).
- **Laptops** earn **57.9%** of revenue (KES 41,535,000) from 220 orders, and the Premium products (Laptop, Tablet) together earn **84.8%**.
- **Weekends are not a peak:** they hold **27.7%** of orders (277) with a near-identical average order (KES 71,972 vs 71,724), and 5.3 orders a day against 5.6 on weekdays.
- **April** was the best month (KES 13,518,300) and **June** the worst (KES 10,903,400), a **24.0%** gap, and Premium online orders from Nairobi and Mombasa total **83 orders worth KES 10,218,000 (14.2%)**.

## Agent data: before and after row count
| Stage | Rows |
|---|---:|
| Raw `agent_transactions.csv` | 612 |
| Duplicate `txn_id` rows removed | 12 |
| **Clean `agent_transactions_clean.csv`** | **600** |

No other rows were dropped: 20 missing amounts were imputed (`amount_imputed`), 40 amounts flagged (`is_outlier`) and 7 transactions from unregistered agent `AG099` kept with county `Unknown`.
