"""Reusable cleaning pipeline for the agent transaction extract."""
import pandas as pd

TYPES = {"deposit": "Deposit", "withdrawal": "Withdrawal"}


def clean_agent_data(txns, agents):
    """Clean the agent transactions and merge them with the agent register.

    Rules (all applied in code; no hard-coded rows, no manual edits):
    1 Uniqueness: drop duplicate txn_id (keep the row with a registered agent).
    2 Consistency: txn_type -> exactly "Deposit" / "Withdrawal".
    3 Validity: parse txn_date ("-" or "/") and amount (blank, "N/A", text and
      non-positive values become missing).
    4 Accuracy: flag IQR outliers in is_outlier (flagged, never deleted).
    5 Completeness: fill missing amounts with the median of observed non-outlier
      amounts by txn_type and set amount_imputed.
    6 Integrity: left-join the register; unknown agents get county "Unknown".

    Args:
        txns: DataFrame with txn_id, agent_id, txn_type, amount, txn_date.
        agents: DataFrame with agent_id, county, onboarded.

    Returns:
        (clean_df, log): the clean DataFrame and a list of dicts with keys
        step, issue, dimension, column, rows_affected, treatment.
    """
    log = []

    def note(issue, dim, col, rows, how):
        log.append({"step": len(log) + 1, "issue": issue, "dimension": dim,
                    "column": col, "rows_affected": int(rows), "treatment": how})

    df, reg = txns.copy(), agents.copy()
    reg["agent_id"] = reg["agent_id"].astype("string").str.strip()

    # 1 Uniqueness: keep the copy whose agent is registered
    for c in ("txn_id", "agent_id"):
        df[c] = df[c].astype("string").str.strip()
    n0, exact = len(df), int(df.duplicated().sum())
    df = (df.assign(_k=df["agent_id"].isin(reg["agent_id"]))
            .sort_values("_k", ascending=False, kind="stable")
            .drop_duplicates("txn_id").sort_index().drop(columns="_k")
            .reset_index(drop=True))
    note("Duplicate transactions (same txn_id)", "Uniqueness", "txn_id", n0 - len(df),
         f"Removed; {exact} exact copies, {n0 - len(df) - exact} with a conflicting agent_id.")

    # 2 Consistency: txn_type
    old = df["txn_type"].astype("string")
    new = old.str.strip().str.lower().map(TYPES)
    df["txn_type"] = new
    note("txn_type has mixed case and spaces", "Consistency", "txn_type",
         (old != new).sum(), f"Mapped to Deposit/Withdrawal; unmapped: {int(new.isna().sum())}.")

    # 3 Validity: dates, then amounts
    d = df["txn_date"].astype("string").str.strip()
    df["txn_date"] = pd.to_datetime(d.str.replace("/", "-", regex=False),
                                    format="%Y-%m-%d", errors="coerce")
    note("Dates written with '/' instead of '-'", "Consistency", "txn_date",
         d.str.contains("/", na=False).sum(),
         f"Normalised and parsed; unparseable: {int(df['txn_date'].isna().sum())}.")
    a = df["amount"].astype("string").str.strip().str.replace(",", "", regex=False)
    blank = int(a.isna().sum() + (a == "").sum())
    df["amount"] = pd.to_numeric(a.replace("", pd.NA), errors="coerce").astype("float64")
    bad = int(df["amount"].isna().sum()) - blank
    nonpos = int((df["amount"] <= 0).sum())
    df.loc[df["amount"] <= 0, "amount"] = float("nan")
    note("Missing amounts (blank, 'N/A' read as NaN)", "Completeness", "amount", blank,
         "Left missing here; imputed in step 7.")
    note("Non-numeric text or non-positive amounts", "Validity", "amount", bad + nonpos,
         "to_numeric(errors='coerce'); imputed in step 7.")

    # 4 Accuracy: IQR outliers on observed amounts (flag only)
    q1, q3 = df["amount"].quantile([0.25, 0.75])
    lo, hi = q1 - 1.5 * (q3 - q1), q3 + 1.5 * (q3 - q1)
    df["is_outlier"] = ((df["amount"] > hi) | (df["amount"] < lo)).fillna(False)
    note("Suspiciously large amounts (IQR rule)", "Accuracy", "amount", df["is_outlier"].sum(),
         f"Flagged, not deleted: outside [{lo:,.0f}, {hi:,.0f}].")

    # 5 Completeness: flagged median imputation by txn_type
    df["amount_imputed"] = df["amount"].isna()
    ok = df.loc[~df["is_outlier"] & ~df["amount_imputed"]]
    med = ok.groupby("txn_type")["amount"].median()
    df["amount"] = df["amount"].fillna(df["txn_type"].map(med).fillna(ok["amount"].median())).round(0)
    note("Missing or invalid amounts imputed", "Completeness", "amount", df["amount_imputed"].sum(),
         "Median of observed non-outlier amounts by txn_type: "
         + ", ".join(f"{k}={v:,.0f}" for k, v in med.items()) + "; flagged amount_imputed.")

    # 6 Integrity: left join keeps every transaction
    m = df.merge(reg[["agent_id", "county", "onboarded"]], on="agent_id", how="left",
                 validate="many_to_one", indicator=True)
    m["unknown_agent"] = m["_merge"].eq("left_only")
    m["county"] = m["county"].fillna("Unknown")
    note("Transactions from agents not in the register", "Consistency", "agent_id",
         m["unknown_agent"].sum(), "Kept with county 'Unknown' and unknown_agent = True.")
    early = m["txn_date"] < pd.to_datetime(m["onboarded"], format="%Y-%m-%d", errors="coerce")
    note("Transactions dated before the agent was onboarded", "Timeliness", "txn_date",
         early.sum(), "Checked only; no rows changed.")
    assert len(m) == len(df), "Merge changed the number of rows"

    cols = ["txn_id", "agent_id", "county", "txn_type", "amount", "txn_date",
            "amount_imputed", "is_outlier", "unknown_agent"]
    return m[cols].reset_index(drop=True), log
