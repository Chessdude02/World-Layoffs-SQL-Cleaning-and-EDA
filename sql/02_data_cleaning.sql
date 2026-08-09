-- =============================================================================
-- 02_data_cleaning.sql
-- Project 1: Clean the raw world tech layoffs dataset in MySQL
--
-- Workflow:
--   1. Staging table (never mutate raw source)
--   2. Remove duplicates via layoffs_staging2 + row_num
--   3. Standardize / format strings and dates
--   4. Handle blanks / nulls (self-join for missing industry)
--   5. Drop unusable rows and helper columns
--
-- Run after 01_setup.sql with data loaded into world_layoffs.layoffs
-- =============================================================================

USE world_layoffs;

-- -----------------------------------------------------------------------------
-- 1. Creating a Staging Table
-- Why: never run UPDATE/DELETE directly on raw source data.
-- -----------------------------------------------------------------------------

DROP TABLE IF EXISTS layoffs_staging;
CREATE TABLE layoffs_staging LIKE layoffs;

INSERT INTO layoffs_staging
SELECT * FROM layoffs;

SELECT COUNT(*) AS staging_row_count FROM layoffs_staging;


-- -----------------------------------------------------------------------------
-- 2. Removing Duplicate Records
-- Identify exact duplicates with ROW_NUMBER() over all analytic columns.
-- MySQL cannot easily DELETE from a CTE with window functions, so we materialize
-- a second staging table that includes row_num, then delete where row_num > 1.
-- -----------------------------------------------------------------------------

-- Preview potential duplicates (partition on a subset first — some are legitimate)
SELECT *
FROM (
    SELECT
        company,
        industry,
        total_laid_off,
        `date`,
        ROW_NUMBER() OVER (
            PARTITION BY company, industry, total_laid_off, `date`
        ) AS row_num
    FROM layoffs_staging
) duplicates
WHERE row_num > 1;

-- Example: Oda has multiple legitimate layoff events (different dates/amounts)
SELECT *
FROM layoffs_staging
WHERE company = 'Oda';

-- True duplicates: identical across all columns
SELECT *
FROM (
    SELECT
        company,
        location,
        industry,
        total_laid_off,
        percentage_laid_off,
        `date`,
        stage,
        country,
        funds_raised_millions,
        ROW_NUMBER() OVER (
            PARTITION BY
                company,
                location,
                industry,
                total_laid_off,
                percentage_laid_off,
                `date`,
                stage,
                country,
                funds_raised_millions
        ) AS row_num
    FROM layoffs_staging
) duplicates
WHERE row_num > 1;

DROP TABLE IF EXISTS layoffs_staging2;

CREATE TABLE layoffs_staging2 (
    company TEXT,
    location TEXT,
    industry TEXT,
    total_laid_off INT,
    percentage_laid_off TEXT,
    `date` TEXT,
    stage TEXT,
    country TEXT,
    funds_raised_millions INT,
    row_num INT
);

INSERT INTO layoffs_staging2 (
    company,
    location,
    industry,
    total_laid_off,
    percentage_laid_off,
    `date`,
    stage,
    country,
    funds_raised_millions,
    row_num
)
SELECT
    company,
    location,
    industry,
    total_laid_off,
    percentage_laid_off,
    `date`,
    stage,
    country,
    funds_raised_millions,
    ROW_NUMBER() OVER (
        PARTITION BY
            company,
            location,
            industry,
            total_laid_off,
            percentage_laid_off,
            `date`,
            stage,
            country,
            funds_raised_millions
    ) AS row_num
FROM layoffs_staging;

-- Keep one copy of each unique row
DELETE FROM layoffs_staging2
WHERE row_num > 1;

SELECT COUNT(*) AS after_dedupe_count FROM layoffs_staging2;


-- -----------------------------------------------------------------------------
-- 3. Standardizing & Formatting Data
-- -----------------------------------------------------------------------------

-- 3a. Trim company whitespace
SELECT company, TRIM(company)
FROM layoffs_staging2;

UPDATE layoffs_staging2
SET company = TRIM(company);

-- 3b. Consolidate industry label variations (Crypto*)
SELECT DISTINCT industry
FROM layoffs_staging2
ORDER BY industry;

UPDATE layoffs_staging2
SET industry = 'Crypto'
WHERE industry LIKE 'Crypto%';

SELECT DISTINCT industry
FROM layoffs_staging2
ORDER BY industry;

-- 3c. Remove trailing periods from country names (e.g. "United States.")
SELECT DISTINCT country
FROM layoffs_staging2
ORDER BY country;

UPDATE layoffs_staging2
SET country = TRIM(TRAILING '.' FROM country);

SELECT DISTINCT country
FROM layoffs_staging2
ORDER BY country;

-- 3d. Convert string dates → DATE
UPDATE layoffs_staging2
SET `date` = STR_TO_DATE(`date`, '%m/%d/%Y');

ALTER TABLE layoffs_staging2
MODIFY COLUMN `date` DATE;

SELECT `date`
FROM layoffs_staging2
ORDER BY `date`
LIMIT 10;


-- -----------------------------------------------------------------------------
-- 4. Handling Nulls & Blank Values
-- -----------------------------------------------------------------------------

-- Convert blank industry strings to explicit NULL
SELECT *
FROM layoffs_staging2
WHERE industry IS NULL
   OR industry = '';

UPDATE layoffs_staging2
SET industry = NULL
WHERE industry = '';

-- Populate missing industry from another row of the same company (self-join)
-- Example: Airbnb missing industry on one row but present on another
SELECT *
FROM layoffs_staging2
WHERE company LIKE 'Airbnb%';

UPDATE layoffs_staging2 t1
JOIN layoffs_staging2 t2
    ON t1.company = t2.company
SET t1.industry = t2.industry
WHERE t1.industry IS NULL
  AND t2.industry IS NOT NULL;

-- Remaining industry NULLs (e.g. Bally's) have no matching non-null row
SELECT *
FROM layoffs_staging2
WHERE industry IS NULL;


-- -----------------------------------------------------------------------------
-- 5. Dropping Unnecessary Columns & Unusable Rows
-- Rows with both layoff metrics NULL cannot support analysis.
-- -----------------------------------------------------------------------------

SELECT *
FROM layoffs_staging2
WHERE total_laid_off IS NULL
  AND percentage_laid_off IS NULL;

DELETE FROM layoffs_staging2
WHERE total_laid_off IS NULL
  AND percentage_laid_off IS NULL;

ALTER TABLE layoffs_staging2
DROP COLUMN row_num;

-- Cleaned table ready for EDA
SELECT COUNT(*) AS cleaned_row_count FROM layoffs_staging2;
SELECT * FROM layoffs_staging2 LIMIT 25;
