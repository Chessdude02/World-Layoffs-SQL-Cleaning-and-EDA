# World Layoffs — SQL Data Cleaning & EDA

MySQL portfolio project that cleans a messy world tech layoffs dataset, then explores trends across companies, industries, countries, and time.

**Dataset source:** [Alex The Analyst — layoffs.csv](https://github.com/AlexTheAnalyst/MySQL-YouTube-Series/blob/main/layoffs.csv) (mirrored in `data/layoffs.csv`)

---

## Project structure

```
World-Layoffs-SQL-Cleaning-and-EDA/
├── data/
│   └── layoffs.csv                 # Raw source (~2,361 rows)
├── sql/
│   ├── 01_setup.sql                # Create DB + raw table
│   ├── 02_data_cleaning.sql        # Staging, dedupe, standardize, nulls
│   └── 03_eda.sql                  # Metrics, aggregates, rolling totals, rankings
├── scripts/
│   └── generate_eda_charts.py      # Export chart PNGs from cleaned table
├── outputs/
│   ├── images/                     # EDA chart PNGs
│   ├── *.csv                       # Query result exports + cleaned table
│   ├── cleaning_summary.txt
│   └── eda_key_results.txt
└── README.md
```

---

## How to run

1. Start **MySQL / MariaDB** and open Workbench or the CLI.
2. Run `sql/01_setup.sql`, then load `data/layoffs.csv` into `world_layoffs.layoffs`.
3. Run `sql/02_data_cleaning.sql` → working table: `layoffs_staging2`.
4. Run `sql/03_eda.sql` for exploratory analysis.
5. (Optional) Generate charts:

```bash
pip install pymysql pandas matplotlib
python scripts/generate_eda_charts.py
```

---

## Cleaning results (executed run)

| Stage | Rows |
|-------|------|
| Raw `layoffs` | 2,361 |
| After dedupe + null cleanup (`layoffs_staging2`) | **1,995** |
| Date range | 2020-03-11 → 2023-03-06 |

Pipeline: staging → `ROW_NUMBER` dedupe → `TRIM` / Crypto consolidation / country trailing `.` / `STR_TO_DATE` → blank→NULL + industry self-join → drop rows missing both layoff metrics → drop `row_num`.

---

## Key EDA findings

| Insight | Result |
|---------|--------|
| Peak year | **2022** — 160,661 laid off |
| 2023 (partial through Mar) | 125,677 |
| Cumulative rolling total | **383,159** by 2023-03 |
| Top country | United States |
| Hardest-hit industries | Consumer, Retail, Other, Transportation, Finance |
| Top companies (cumulative) | Amazon, Google, Meta, Salesforce, Microsoft, … |
| 2020 top-5 | Uber, Booking.com, Groupon, Swiggy, Airbnb |
| 2022 top-5 | Meta, Amazon, Cisco, Peloton, Carvana/Philips |
| 2023 top-5 | Google, Microsoft, Ericsson, Amazon/Salesforce, Dell |

---

## Charts

![Layoffs by year](outputs/images/01_layoffs_by_year.png)

![Layoffs by industry](outputs/images/02_layoffs_by_industry.png)

![Layoffs by country](outputs/images/03_layoffs_by_country.png)

![Layoffs by company](outputs/images/04_layoffs_by_company.png)

![Monthly rolling total](outputs/images/05_monthly_rolling_total.png)

![Top 5 companies by year](outputs/images/06_top5_companies_by_year.png)

---

## Skills demonstrated

- Staging tables and safe mutation patterns  
- Window functions (`ROW_NUMBER`, `DENSE_RANK`, rolling `SUM`)  
- CTEs for multi-step analysis  
- String / date cleanup (`TRIM`, `LIKE`, `STR_TO_DATE`)  
- Self-joins for imputation  
- Grouping and ranking for business insights  
