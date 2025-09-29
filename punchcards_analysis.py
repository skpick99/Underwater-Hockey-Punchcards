
import argparse
import os
import sys
from typing import List, Tuple
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def smart_read_csv(path: str) -> pd.DataFrame:
    """
    Read a CSV/TSV with unknown delimiter/quoting via Python engine and separator inference.
    """
    try:
        df = pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False)
        return df
    except Exception as e:
        # Fallback to comma
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names to a shared schema.
    Recognize user id, meetup name, status, purchase date, playdateNN columns, followup.
    """
    # Strip whitespace and quotes from headers
    df = df.copy()
    df.columns = [c.strip().strip('"').strip("'") for c in df.columns]

    # Map user id column
    user_cols = [c for c in df.columns if c.lower() in ("hockey user id", "user id", "user_id", "userid")]
    if user_cols:
        df = df.rename(columns={user_cols[0]: "UserID"})
    else:
        # Try heuristic: column containing "user" and "id"
        candidates = [c for c in df.columns if ("user" in c.lower() and "id" in c.lower())]
        if candidates:
            df = df.rename(columns={candidates[0]: "UserID"})
        else:
            # If absent, synthesize from row index
            df["UserID"] = df.index.astype(str)

    # Meetup name
    meetup_cols = [c for c in df.columns if c.lower() in ("meetup name", "meetup_name")]
    if meetup_cols:
        df = df.rename(columns={meetup_cols[0]: "MeetupName"})

    # Status
    status_cols = [c for c in df.columns if c.lower() == "status"]
    if status_cols:
        df = df.rename(columns={status_cols[0]: "Status"})

    # PurchaseDate
    purch_cols = [c for c in df.columns if c.lower() == "purchasedate"]
    if purch_cols:
        df = df.rename(columns={purch_cols[0]: "PurchaseDate"})

    # FollowUp (optional)
    fu_cols = [c for c in df.columns if c.lower() == "followup"]
    if fu_cols:
        df = df.rename(columns={fu_cols[0]: "FollowUp"})

    # Standardize playdate columns
    play_cols = []
    for c in df.columns:
        lc = c.lower()
        if lc.startswith("playdate") and lc.replace("playdate", "").isdigit():
            # normalize to PlayDateNN
            suffix = lc.replace("playdate", "")
            newc = f"PlayDate{int(suffix):02d}"
            df = df.rename(columns={c: newc})
            play_cols.append(newc)
    if not play_cols:
        # try any column exactly 'PlayDate01' style already present
        play_cols = [c for c in df.columns if c.lower().startswith("playdate")]
    play_cols = sorted(play_cols)

    # Clean strings
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().str.strip('"').str.strip("'")

    return df

def parse_date_yyyymmdd(val: str):
    """
    Parse yyyymmdd as datetime; coerce invalid to NaT.
    Accept numeric-like strings; ignore blanks.
    """
    if val is None:
        return pd.NaT
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return pd.NaT
    # Some rows might be floats from CSV; drop .0
    if s.endswith(".0"):
        s = s[:-2]
    # Only accept pure digits length 8
    if len(s) == 8 and s.isdigit():
        # basic sanity on year
        yr = int(s[:4])
        if 1900 <= yr <= 2100:
            try:
                return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
            except Exception:
                return pd.NaT
    # Try MM/DD/YYYY as a fallback (e.g., PurchaseDate might be like 03/19/2022)
    try:
        return pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    except Exception:
        return pd.NaT

def build_attendance_long(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    """
    From input dataframes, extract (UserID, Date) rows from PlayDateNN columns.
    Returns a dataframe with columns: UserID, Date (datetime64[ns]).
    """
    frames = []
    for df in df_list:
        df_norm = normalize_columns(df)
        # Identify playdate columns
        play_cols = [c for c in df_norm.columns if c.lower().startswith("playdate")]
        if not play_cols:
            continue
        # Melt to long
        long = df_norm.melt(
            id_vars=[c for c in ["UserID", "MeetupName", "Status", "PurchaseDate"] if c in df_norm.columns],
            value_vars=play_cols,
            var_name="PlaySlot",
            value_name="PlayDateRaw"
        )
        # Clean and parse dates
        long["Date"] = long["PlayDateRaw"].apply(parse_date_yyyymmdd)
        long = long.dropna(subset=["Date"])
        # Keep only user + date (others optional)
        keep_cols = ["UserID", "Date"]
        if "MeetupName" in long.columns: keep_cols.append("MeetupName")
        if "Status" in long.columns: keep_cols.append("Status")
        frames.append(long[keep_cols].copy())
    if not frames:
        return pd.DataFrame(columns=["UserID", "Date"])
    out = pd.concat(frames, ignore_index=True)
    # Normalize UserID string
    out["UserID"] = out["UserID"].astype(str).str.strip()
    return out

def compute_sessions_and_attendance(att: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    From attendance (UserID, Date), compute:
      - sessions_df: one row per session date with list of attendees and weekday (0=Mon,...6=Sun)
      - attendance_df: one row per (Date, UserID) unique attendance
    """
    if att.empty:
        return pd.DataFrame(columns=["Date","Weekday","AttendeeCount"]), pd.DataFrame(columns=["Date","UserID","Weekday"])

    # Ensure datetime and drop duplicates (a user counted once per date)
    att = att.copy()
    att["Date"] = pd.to_datetime(att["Date"]).dt.normalize()
    att = att.drop_duplicates(subset=["UserID", "Date"])

    # Build session-level info
    # Count attendees per date
    cnt = att.groupby("Date")["UserID"].nunique().reset_index(name="AttendeeCount")
    cnt["Weekday"] = cnt["Date"].dt.weekday  # 0=Mon ... 6=Sun
    sessions_df = cnt.sort_values("Date").reset_index(drop=True)

    # Attendance with weekday
    attendance_df = att.copy()
    attendance_df["Weekday"] = attendance_df["Date"].dt.weekday
    return sessions_df, attendance_df

def weekday_name(idx: int) -> str:
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][idx]

def number_of_practices_per_weekday(sessions_df: pd.DataFrame) -> pd.Series:
    """
    Count distinct session dates per weekday.
    """
    if sessions_df.empty:
        return pd.Series(dtype=int)
    counts = sessions_df.groupby("Weekday")["Date"].nunique()
    counts.index = counts.index.map(weekday_name)
    return counts

def fractions_by_user_per_weekday(sessions_df: pd.DataFrame, attendance_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each weekday, fraction of sessions each user attended:
      frac(user, d) = (# distinct dates user attended on weekday d) / (total sessions on weekday d)
    Returns a DataFrame indexed by UserID with columns Mon..Sun (missing weekdays kept if no sessions? Skip days without sessions).
    """
    if sessions_df.empty or attendance_df.empty:
        cols = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        return pd.DataFrame(columns=cols)

    # total sessions per weekday
    total_sessions = sessions_df.groupby("Weekday")["Date"].nunique()
    # attended counts per user and weekday
    att_counts = attendance_df.groupby(["UserID", "Weekday"])["Date"].nunique().unstack(fill_value=0)
    # Align columns and divide
    att_counts = att_counts.reindex(columns=sorted(total_sessions.index), fill_value=0)
    frac = att_counts.div(total_sessions, axis=1)
    # Rename columns to names
    frac.columns = [weekday_name(i) for i in frac.columns]
    # Drop weekdays with zero sessions entirely
    nonzero_cols = []
    for i, total in total_sessions.items():
        if total > 0:
            nonzero_cols.append(weekday_name(i))
    frac = frac.reindex(columns=nonzero_cols)
    # Sort users by overall attendance fraction sum (desc) for readability
    frac["__sum__"] = frac.sum(axis=1)
    frac = frac.sort_values("__sum__", ascending=False).drop(columns="__sum__")
    return frac

def make_surplus_plots(sessions_df: pd.DataFrame, outdir: str, revenue_per_person: float = 10.0, pool_cost: float = 105.0) -> pd.DataFrame:
    """
    For each weekday with at least one session, compute and plot cumulative surplus:
      y[n] = y[n-1] + (attendees[n] * revenue_per_person) - pool_cost
    Save a PNG per weekday to outdir, and return a long DataFrame with all points.
    """
    if sessions_df.empty:
        return pd.DataFrame(columns=["WeekdayName","Date","Attendees","Delta","Surplus"])

    os.makedirs(outdir, exist_ok=True)
    all_rows = []
    for wd, grp in sessions_df.groupby("Weekday", sort=True):
        grp = grp.sort_values("Date").reset_index(drop=True)
        surplus = 0.0
        dates = []
        ys = []
        deltas = []
        attendees_list = []
        for _, row in grp.iterrows():
            p = row["AttendeeCount"]
            delta = p * revenue_per_person - pool_cost
            surplus += delta
            dates.append(row["Date"])
            ys.append(surplus)
            deltas.append(delta)
            attendees_list.append(p)

        # Plot
        plt.figure()
        plt.plot(dates, ys, marker="o")
        plt.title(f"Money Surplus over Time — {weekday_name(wd)}")
        plt.xlabel("Date")
        plt.ylabel("Surplus ($)")
        plt.grid(True, which="both", axis="both")
        fname = os.path.join(outdir, f"surplus_{weekday_name(wd)}.png")
        plt.tight_layout()
        plt.savefig(fname, dpi=150)
        plt.close()

        for d, p, delta, yv in zip(dates, attendees_list, deltas, ys):
            all_rows.append({
                "Weekday": wd,
                "WeekdayName": weekday_name(wd),
                "Date": d,
                "Attendees": p,
                "Delta": delta,
                "Surplus": yv,
            })

    return pd.DataFrame(all_rows)

def main():
    parser = argparse.ArgumentParser(description="Analyze punchcard attendance and finances by weekday.")
    parser.add_argument("--punchcards", required=True, help="Path to punchcards.csv")
    parser.add_argument("--history", required=True, help="Path to punchcards_history.csv")
    parser.add_argument("--outdir", default="analysis_output", help="Directory to save outputs")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    # Read inputs
    df1 = smart_read_csv(args.punchcards)
    df2 = smart_read_csv(args.history)

    # Build attendance
    attendance = build_attendance_long([df1, df2])

    if attendance.empty:
        print("No attendance dates found in the provided files.")
        sys.exit(0)

    # Compute sessions and attendance
    sessions_df, attendance_df = compute_sessions_and_attendance(attendance)

    # 1) Number of practices per weekday (distinct dates)
    weekday_counts = number_of_practices_per_weekday(sessions_df).sort_index()

    # 2) Fractions per user per weekday
    fractions_df = fractions_by_user_per_weekday(sessions_df, attendance_df)

    # 3) Surplus plots & data
    surplus_df = make_surplus_plots(sessions_df, args.outdir, revenue_per_person=10.0, pool_cost=105.0)

    # Save outputs
    weekday_counts.to_csv(os.path.join(args.outdir, "weekday_practice_counts.csv"), header=["Count"])
    fractions_df.to_csv(os.path.join(args.outdir, "fractions_by_user_per_weekday.csv"))
    surplus_df.to_csv(os.path.join(args.outdir, "surplus_timeseries_by_weekday.csv"), index=False)

    # Also dump a human-readable summary
    with open(os.path.join(args.outdir, "README.txt"), "w") as f:
        f.write("Outputs generated:\n")
        f.write("- weekday_practice_counts.csv: number of distinct practice dates per weekday (Mon..Sun)\n")
        f.write("- fractions_by_user_per_weekday.csv: for each weekday, fraction of sessions attended by each user\n")
        f.write("- surplus_timeseries_by_weekday.csv: per-weekday time series with attendees, delta, cumulative surplus\n")
        f.write("- surplus_*.png: plots of surplus vs date for each weekday that had at least one session\n")

    # Console summary
    print("== Number of distinct practice dates per weekday ==")
    print(weekday_counts)
    print("\nSaved:")
    print(f"- {os.path.join(args.outdir, 'weekday_practice_counts.csv')}")
    print(f"- {os.path.join(args.outdir, 'fractions_by_user_per_weekday.csv')}")
    print(f"- {os.path.join(args.outdir, 'surplus_timeseries_by_weekday.csv')}")
    print(f"- {os.path.join(args.outdir, 'surplus_*.png')}")

if __name__ == "__main__":
    main()
