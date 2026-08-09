"""
Generate EDA chart images from cleaned world_layoffs.layoffs_staging2.
Saves PNGs under outputs/images/ and summary CSVs under outputs/.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pymysql

ROOT = Path(__file__).resolve().parents[1]
IMG = ROOT / "outputs" / "images"
OUT = ROOT / "outputs"
IMG.mkdir(parents=True, exist_ok=True)

# Distinct, non-default palette (avoid purple-on-white AI cliché)
COLORS = {
    "bar": "#1B6B4A",
    "bar_alt": "#C45C26",
    "line": "#1F4E79",
    "fill": "#A8C5D4",
    "accent": "#8B1E3F",
    "bg": "#F7F4EF",
    "grid": "#D9D2C5",
    "text": "#1A1A1A",
}


def connect():
    return pymysql.connect(
        host="127.0.0.1",
        user="root",
        password="",
        database="world_layoffs",
    )


def query(sql: str) -> pd.DataFrame:
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
    return pd.DataFrame(rows, columns=cols)


def style_ax(ax, title: str, ylabel: str | None = None):
    ax.set_facecolor(COLORS["bg"])
    ax.figure.patch.set_facecolor(COLORS["bg"])
    ax.set_title(title, fontsize=14, fontweight="bold", color=COLORS["text"], pad=12)
    if ylabel:
        ax.set_ylabel(ylabel, color=COLORS["text"])
    ax.tick_params(colors=COLORS["text"])
    ax.grid(axis="y", color=COLORS["grid"], linewidth=0.8)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color(COLORS["grid"])
    ax.spines["bottom"].set_color(COLORS["grid"])


def save(fig, name: str):
    path = IMG / name
    fig.tight_layout()
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"saved {path}")


def chart_by_year():
    df = query(
        """
        SELECT YEAR(`date`) AS year, SUM(total_laid_off) AS total_laid_off
        FROM layoffs_staging2
        WHERE `date` IS NOT NULL
        GROUP BY YEAR(`date`)
        ORDER BY year
        """
    )
    df.to_csv(OUT / "layoffs_by_year.csv", index=False)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(df["year"].astype(str), df["total_laid_off"], color=COLORS["bar"], width=0.6)
    style_ax(ax, "Total Layoffs by Year", "Employees laid off")
    save(fig, "01_layoffs_by_year.png")


def chart_by_industry():
    df = query(
        """
        SELECT industry, SUM(total_laid_off) AS total_laid_off
        FROM layoffs_staging2
        WHERE industry IS NOT NULL
        GROUP BY industry
        ORDER BY total_laid_off DESC
        LIMIT 12
        """
    )
    df.to_csv(OUT / "layoffs_by_industry.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.barh(df["industry"][::-1], df["total_laid_off"][::-1], color=COLORS["bar_alt"])
    style_ax(ax, "Top Industries by Total Layoffs", "Employees laid off")
    save(fig, "02_layoffs_by_industry.png")


def chart_by_country():
    df = query(
        """
        SELECT country, SUM(total_laid_off) AS total_laid_off
        FROM layoffs_staging2
        GROUP BY country
        ORDER BY total_laid_off DESC
        LIMIT 10
        """
    )
    df.to_csv(OUT / "layoffs_by_country.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(df["country"][::-1], df["total_laid_off"][::-1], color=COLORS["line"])
    style_ax(ax, "Top Countries by Total Layoffs", "Employees laid off")
    save(fig, "03_layoffs_by_country.png")


def chart_top_companies():
    df = query(
        """
        SELECT company, SUM(total_laid_off) AS total_laid_off
        FROM layoffs_staging2
        GROUP BY company
        ORDER BY total_laid_off DESC
        LIMIT 10
        """
    )
    df.to_csv(OUT / "layoffs_by_company.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(df["company"][::-1], df["total_laid_off"][::-1], color=COLORS["accent"])
    style_ax(ax, "Top Companies by Cumulative Layoffs", "Employees laid off")
    save(fig, "04_layoffs_by_company.png")


def chart_monthly_rolling():
    df = query(
        """
        WITH Rolling_Total AS (
            SELECT
                SUBSTRING(`date`, 1, 7) AS month,
                SUM(total_laid_off) AS total_off
            FROM layoffs_staging2
            WHERE SUBSTRING(`date`, 1, 7) IS NOT NULL
            GROUP BY month
        )
        SELECT
            month,
            total_off,
            SUM(total_off) OVER (ORDER BY month) AS rolling_total
        FROM Rolling_Total
        ORDER BY month
        """
    )
    df.to_csv(OUT / "monthly_rolling_total.csv", index=False)
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax1.bar(df["month"], df["total_off"], color=COLORS["fill"], label="Monthly layoffs", width=0.8)
    ax2 = ax1.twinx()
    ax2.plot(df["month"], df["rolling_total"], color=COLORS["line"], linewidth=2.4, label="Rolling total")
    style_ax(ax1, "Monthly Layoffs and Cumulative Rolling Total")
    ax1.set_ylabel("Monthly", color=COLORS["text"])
    ax2.set_ylabel("Rolling total", color=COLORS["line"])
    ax1.set_xticks(range(0, len(df), 3))
    ax1.set_xticklabels(df["month"].iloc[::3], rotation=45, ha="right")
    ax2.spines["top"].set_visible(False)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", frameon=False)
    save(fig, "05_monthly_rolling_total.png")


def chart_top5_by_year():
    df = query(
        """
        WITH Company_Year AS (
            SELECT company, YEAR(`date`) AS year, SUM(total_laid_off) AS total_laid_off
            FROM layoffs_staging2
            GROUP BY company, YEAR(`date`)
        ),
        Company_Year_Rank AS (
            SELECT
                company,
                year,
                total_laid_off,
                DENSE_RANK() OVER (PARTITION BY year ORDER BY total_laid_off DESC) AS ranking
            FROM Company_Year
            WHERE year IS NOT NULL
        )
        SELECT company, year, total_laid_off, ranking
        FROM Company_Year_Rank
        WHERE ranking <= 5
        ORDER BY year, ranking
        """
    )
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["total_laid_off"] = pd.to_numeric(df["total_laid_off"], errors="coerce")
    df = df.dropna(subset=["year", "total_laid_off"])
    df["year"] = df["year"].astype(int)
    df.to_csv(OUT / "top5_companies_by_year.csv", index=False)

    years = sorted(df["year"].unique())
    fig, axes = plt.subplots(1, len(years), figsize=(3.2 * len(years), 5), sharey=False)
    if len(years) == 1:
        axes = [axes]
    palette = [COLORS["bar"], COLORS["bar_alt"], COLORS["line"], COLORS["accent"], "#5C6B4A"]
    for ax, year in zip(axes, years):
        sub = df[df["year"] == year].sort_values("total_laid_off")
        ax.barh(sub["company"], sub["total_laid_off"], color=palette[: len(sub)])
        style_ax(ax, str(year))
        ax.set_xlabel("Laid off")
    fig.suptitle("Top 5 Companies by Layoffs Each Year", fontsize=15, fontweight="bold", color=COLORS["text"], y=1.02)
    fig.patch.set_facecolor(COLORS["bg"])
    save(fig, "06_top5_companies_by_year.png")


def main():
    chart_by_year()
    chart_by_industry()
    chart_by_country()
    chart_top_companies()
    chart_monthly_rolling()
    chart_top5_by_year()
    print("All charts written to", IMG)


if __name__ == "__main__":
    main()
