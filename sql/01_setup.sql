-- =============================================================================
-- 01_setup.sql
-- Create the database, raw table, and load layoffs.csv
--
-- Prerequisites:
--   1. MySQL Server running (8.0+ recommended)
--   2. Update the LOAD DATA INFILE path below to your local CSV absolute path
--   3. If LOAD DATA is blocked, use MySQL Workbench:
--        Table Data Import Wizard on world_layoffs.layoffs
-- =============================================================================

CREATE DATABASE IF NOT EXISTS world_layoffs;
USE world_layoffs;

DROP TABLE IF EXISTS layoffs;

CREATE TABLE layoffs (
    company TEXT,
    location TEXT,
    industry TEXT,
    total_laid_off INT,
    percentage_laid_off TEXT,
    `date` TEXT,
    stage TEXT,
    country TEXT,
    funds_raised_millions INT
);

-- Option A: LOAD DATA (adjust path; may require LOCAL and secure_file_priv settings)
-- LOAD DATA LOCAL INFILE 'C:/Users/vedan/Projects/World-Layoffs-SQL-Cleaning-and-EDA/data/layoffs.csv'
-- INTO TABLE layoffs
-- FIELDS TERMINATED BY ','
-- ENCLOSED BY '"'
-- LINES TERMINATED BY '\n'
-- IGNORE 1 ROWS;

-- Option B (Workbench): right-click world_layoffs.layoffs → Table Data Import Wizard
--   → select data/layoffs.csv → map columns → import

SELECT COUNT(*) AS raw_row_count FROM layoffs;
SELECT * FROM layoffs LIMIT 10;
