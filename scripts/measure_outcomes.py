"""
Measure the project's outcomes from the files in the repo (no database needed).

1. Data quality before vs after: runs the same checks on the raw CSV and on the
   cleaned export of layoffs_staging2, so every fix has a count.
2. Reconciliation: replays the SQL cleaning rules in pandas and confirms the
   row count matches the cleaned export.
3. Quantified findings, including a hypothesis test.

Writes outputs/measured_outcomes.md.

Usage:
    python scripts/measure_outcomes.py
"""

from pathlib import Path

import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV = ROOT / "data" / "layoffs.csv"
CLEAN_CSV = ROOT / "outputs" / "layoffs_cleaned.csv"
REPORT = ROOT / "outputs" / "measured_outcomes.md"

KEY_COLS = [
    "company", "location", "industry", "total_laid_off", "percentage_laid_off",
    "date", "stage", "country", "funds_raised_millions",
]
EARLY_STAGES = ["Seed", "Series A", "Series B"]
LATE_STAGES = ["Post-IPO"]


def load_raw() -> pd.DataFrame:
    # Read everything as text so whitespace and label problems stay visible
    df = pd.read_csv(RAW_CSV, dtype=str, keep_default_na=False)
    return df.replace({"": None, "NULL": None})


def load_clean() -> pd.DataFrame:
    df = pd.read_csv(CLEAN_CSV, sep="\t", dtype=str, keep_default_na=False)
    return df.replace({"": None, "NULL": None})


def quality_checks(df: pd.DataFrame) -> dict:
    """Row-level defect flags. Each value is a boolean Series over rows."""
    return {
        "Exact duplicate rows": df.duplicated(subset=KEY_COLS, keep="first"),
        "Company name with extra whitespace": df["company"].fillna("").ne(
            df["company"].fillna("").str.strip()
        ),
        "Non-standard industry label (Crypto variants)": df["industry"].fillna("").str.match(
            r"^Crypto.+"
        ),
        "Country with trailing '.'": df["country"].fillna("").str.endswith("."),
        "Missing industry": df["industry"].isna(),
        "No layoff count AND no layoff %": df["total_laid_off"].isna()
        & df["percentage_laid_off"].isna(),
    }


def text_dates(df: pd.DataFrame) -> int:
    """Dates stored as m/d/Y text (a format fix, not counted as a defect)."""
    as_iso = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce")
    return int((df["date"].notna() & as_iso.isna()).sum())


def replay_cleaning(raw: pd.DataFrame) -> pd.DataFrame:
    """The rules from sql/02_data_cleaning.sql, in the same order."""
    df = raw.drop_duplicates(subset=KEY_COLS).copy()
    df["company"] = df["company"].str.strip()
    df.loc[df["industry"].fillna("").str.startswith("Crypto"), "industry"] = "Crypto"
    df["country"] = df["country"].str.rstrip(".")
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    known = df.dropna(subset=["industry"]).groupby("company")["industry"].first()
    missing = df["industry"].isna()
    df.loc[missing, "industry"] = df.loc[missing, "company"].map(known)
    df = df[~(df["total_laid_off"].isna() & df["percentage_laid_off"].isna())]
    return df


def findings(clean: pd.DataFrame) -> list[str]:
    df = clean.copy()
    df["total"] = pd.to_numeric(df["total_laid_off"], errors="coerce")
    df["pct"] = pd.to_numeric(df["percentage_laid_off"], errors="coerce")
    df["funds"] = pd.to_numeric(df["funds_raised_millions"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    out = []

    # 1. Early-stage vs Post-IPO: share of staff cut (Mann-Whitney U, one-sided)
    early = df.loc[df["stage"].isin(EARLY_STAGES), "pct"].dropna()
    late = df.loc[df["stage"].isin(LATE_STAGES), "pct"].dropna()
    u = stats.mannwhitneyu(early, late, alternative="greater")
    shut_early, shut_late = (early == 1).mean(), (late == 1).mean()
    out.append(
        f"**Early-stage startups cut deeper.** Seed-Series B companies cut a median "
        f"**{early.median():.0%}** of staff vs **{late.median():.0%}** for Post-IPO companies "
        f"(n={len(early)} vs n={len(late)}; Mann-Whitney U, one-sided p = {u.pvalue:.1e}). "
        f"**{shut_early:.1%}** of early-stage events were full shutdowns (100% laid off) vs "
        f"**{shut_late:.1%}** for Post-IPO, about **{shut_early / shut_late:.0f}x** higher."
    )

    # 2. Funding vs share of staff cut (Spearman)
    f = df.dropna(subset=["funds", "pct"])
    rho = stats.spearmanr(f["funds"], f["pct"])
    out.append(
        f"**More funding, smaller cuts.** Funds raised vs % of staff laid off: Spearman "
        f"rho = **{rho.statistic:.2f}** (n={len(f)}, p = {rho.pvalue:.1e})."
    )

    # 3. Timing concentration
    dated = df.dropna(subset=["total", "date"])
    window = dated[(dated["date"] >= "2022-10-01") & (dated["date"] < "2023-04-01")]
    out.append(
        f"**Six months held over half the total.** Oct 2022-Mar 2023 accounts for "
        f"**{window['total'].sum() / dated['total'].sum():.0%}** of all dated layoffs "
        f"({int(window['total'].sum()):,} of {int(dated['total'].sum()):,})."
    )

    # 4. Event concentration
    counted = df.dropna(subset=["total"])
    big = counted[counted["total"] >= 1000]
    out.append(
        f"**A few large events dominate.** {len(big)} events of 1,000+ people "
        f"(**{len(big) / len(counted):.0%}** of {len(counted):,} events with a count) make up "
        f"**{big['total'].sum() / counted['total'].sum():.0%}** of all layoffs."
    )
    return out


def main() -> None:
    raw, clean = load_raw(), load_clean()
    before, after = quality_checks(raw), quality_checks(clean)

    rows = []
    for name in before:
        rows.append(f"| {name} | {int(before[name].sum()):,} | {int(after[name].sum()):,} |")
    any_before = pd.concat(before.values(), axis=1).any(axis=1)
    any_after = pd.concat(after.values(), axis=1).any(axis=1)
    rows.append(
        f"| **Rows with at least one defect** | **{int(any_before.sum()):,} "
        f"({any_before.mean():.1%})** | **{int(any_after.sum()):,} ({any_after.mean():.1%})** |"
    )

    replayed = replay_cleaning(raw)
    match = "matches" if len(replayed) == len(clean) else "DOES NOT match"

    lines = [
        "# Measured outcomes",
        "",
        "Generated by `scripts/measure_outcomes.py` from `data/layoffs.csv` (raw) and "
        "`outputs/layoffs_cleaned.csv` (export of `layoffs_staging2`).",
        "",
        "## Data quality: before vs after cleaning",
        "",
        f"Raw: {len(raw):,} rows. Cleaned: {len(clean):,} rows "
        f"({len(raw) - len(clean):,} removed, {(len(raw) - len(clean)) / len(raw):.1%}).",
        "",
        "| Check | Raw rows flagged | Cleaned rows flagged |",
        "|---|---|---|",
        *rows,
        "",
        f"Format fix (not counted above): {text_dates(raw):,} raw dates stored as m/d/Y text "
        f"were converted to a DATE column ({text_dates(clean):,} left as text).",
        "",
        f"Reconciliation: replaying the SQL rules in pandas gives {len(replayed):,} rows, "
        f"which {match} the cleaned export ({len(clean):,}).",
        "",
        "The one remaining missing industry is Bally's Interactive: it has no other row "
        "to copy an industry from, so it is left as NULL rather than guessed.",
        "",
        "## Findings",
        "",
        *[f"- {line}" for line in findings(clean)],
        "",
        "## Limits",
        "",
        "- The source is media-reported layoffs, so small companies are under-counted.",
        "- % laid off is missing for many rows, and small companies report it more often. "
        "The stage comparison only covers rows where it is reported.",
        "- Totals are a floor: rows without a layoff count are excluded from sums.",
        "",
    ]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
