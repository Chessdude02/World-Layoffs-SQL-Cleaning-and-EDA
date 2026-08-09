-- =============================================================================
-- 03_eda.sql
-- Project 2: Exploratory Data Analysis on cleaned layoffs_staging2
--
-- Uncovers patterns across companies, industries, dates, and countries.
-- Run after 02_data_cleaning.sql
-- =============================================================================

USE world_layoffs;

SELECT * FROM layoffs_staging2;


-- -----------------------------------------------------------------------------
-- 1. Global Metrics & Basic Summary Statistics
-- -----------------------------------------------------------------------------

SELECT MAX(total_laid_off) AS max_laid_off
FROM layoffs_staging2;

SELECT
    MAX(percentage_laid_off) AS max_pct_laid_off,
    MIN(percentage_laid_off) AS min_pct_laid_off
FROM layoffs_staging2
WHERE percentage_laid_off IS NOT NULL;

-- Full-company shutdowns (100% laid off), ranked by funds raised
SELECT *
FROM layoffs_staging2
WHERE percentage_laid_off = 1
ORDER BY funds_raised_millions DESC;


-- -----------------------------------------------------------------------------
-- 2. Grouping & Aggregate Trend Analysis
-- -----------------------------------------------------------------------------

-- Largest single-day layoff events
SELECT company, total_laid_off
FROM layoffs_staging2
ORDER BY total_laid_off DESC
LIMIT 5;

-- By company (cumulative)
SELECT company, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY company
ORDER BY total_laid_off DESC
LIMIT 10;

-- By industry
SELECT industry, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY industry
ORDER BY total_laid_off DESC;

-- By country
SELECT country, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY country
ORDER BY total_laid_off DESC;

-- By location
SELECT location, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY location
ORDER BY total_laid_off DESC
LIMIT 10;

-- By funding stage
SELECT stage, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY stage
ORDER BY total_laid_off DESC;

-- By year
SELECT YEAR(`date`) AS year, SUM(total_laid_off) AS total_laid_off
FROM layoffs_staging2
GROUP BY YEAR(`date`)
ORDER BY year ASC;


-- -----------------------------------------------------------------------------
-- 3. Monthly Trends & Rolling Totals
-- SUBSTRING(date, 1, 7) → 'YYYY-MM' after date is a proper DATE type
-- -----------------------------------------------------------------------------

SELECT
    SUBSTRING(`date`, 1, 7) AS `month`,
    SUM(total_laid_off) AS total_off
FROM layoffs_staging2
WHERE SUBSTRING(`date`, 1, 7) IS NOT NULL
GROUP BY `month`
ORDER BY `month`;

WITH Rolling_Total AS (
    SELECT
        SUBSTRING(`date`, 1, 7) AS `month`,
        SUM(total_laid_off) AS total_off
    FROM layoffs_staging2
    WHERE SUBSTRING(`date`, 1, 7) IS NOT NULL
    GROUP BY `month`
)
SELECT
    `month`,
    total_off,
    SUM(total_off) OVER (ORDER BY `month`) AS rolling_total
FROM Rolling_Total;


-- -----------------------------------------------------------------------------
-- 4. Complex Multi-CTE Year-Over-Year Ranking
-- Top 5 companies with the most layoffs for each calendar year
-- -----------------------------------------------------------------------------

WITH Company_Year AS (
    SELECT
        company,
        YEAR(`date`) AS year,
        SUM(total_laid_off) AS total_laid_off
    FROM layoffs_staging2
    GROUP BY company, YEAR(`date`)
),
Company_Year_Rank AS (
    SELECT
        company,
        year,
        total_laid_off,
        DENSE_RANK() OVER (
            PARTITION BY year
            ORDER BY total_laid_off DESC
        ) AS ranking
    FROM Company_Year
    WHERE year IS NOT NULL
)
SELECT company, year, total_laid_off, ranking
FROM Company_Year_Rank
WHERE ranking <= 5
ORDER BY year ASC, ranking ASC;
