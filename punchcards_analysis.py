
import argparse
import os
import sys
from typing import List, Tuple
import pandas as pd
import numpy as np

# Bokeh for interactive plots
from bokeh.plotting import figure, output_file, save
from bokeh.models import HoverTool

def smart_read_csv(path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, sep=None, engine="python", dtype=str, keep_default_na=False)
        return df
    except Exception:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
        return df

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [c.strip().strip('"').strip("'") for c in df.columns]

    # Map user id column
    user_cols = [c for c in df.columns if c.lower() in ("hockey user id", "user id", "user_id", "userid")]
    if user_cols:
        df = df.rename(columns={user_cols[0]: "UserID"})
    else:
        candidates = [c for c in df.columns if ("user" in c.lower() and "id" in c.lower())]
        if candidates:
            df = df.rename(columns={candidates[0]: "UserID"})
        else:
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
    for c in list(df.columns):
        lc = c.lower()
        if lc.startswith("playdate") and lc.replace("playdate", "").isdigit():
            suffix = lc.replace("playdate", "")
            newc = f"PlayDate{int(suffix):02d}"
            df = df.rename(columns={c: newc})

    # Clean strings
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip().str.strip('"').str.strip("'")

    return df

def parse_date_yyyymmdd(val: str):
    if val is None:
        return pd.NaT
    s = str(val).strip()
    if s == "" or s.lower() == "nan":
        return pd.NaT
    if s.endswith(".0"):
        s = s[:-2]
    if len(s) == 8 and s.isdigit():
        yr = int(s[:4])
        if 1900 <= yr <= 2100:
            try:
                return pd.to_datetime(s, format="%Y%m%d", errors="coerce")
            except Exception:
                return pd.NaT
    # Fallback for other formats (e.g., MM/DD/YYYY)
    try:
        return pd.to_datetime(s, format="%m/%d/%Y", errors="coerce")
    except Exception:
        return pd.NaT

def build_attendance_long(df_list: List[pd.DataFrame]) -> pd.DataFrame:
    frames = []
    for df in df_list:
        df_norm = normalize_columns(df)
        play_cols = [c for c in df_norm.columns if c.lower().startswith("playdate")]
        if not play_cols:
            continue

        id_vars = [c for c in ["UserID", "MeetupName", "Status", "PurchaseDate"] if c in df_norm.columns]
        long = df_norm.melt(
            id_vars=id_vars,
            value_vars=sorted(play_cols),
            var_name="PlaySlot",
            value_name="PlayDateRaw"
        )
        long["Date"] = long["PlayDateRaw"].apply(parse_date_yyyymmdd)
        long = long.dropna(subset=["Date"])

        # Normalize identifiers
        long["UserID"] = long.get("UserID", "").astype(str).str.strip()
        long["MeetupName"] = long.get("MeetupName", "").astype(str).str.strip()

        frames.append(long[["UserID", "MeetupName", "Date"]].copy())

    if not frames:
        return pd.DataFrame(columns=["UserID", "MeetupName", "Date"])

    out = pd.concat(frames, ignore_index=True)
    out["Date"] = pd.to_datetime(out["Date"]).dt.normalize()
    # Prefer MeetupName if present, else fallback to UserID
    out["Person"] = np.where(out["MeetupName"].fillna("").str.len() > 0, out["MeetupName"], out["UserID"])
    # Drop duplicates: one person counted once per date
    out = out.drop_duplicates(subset=["Person", "Date"])
    return out

def compute_sessions_and_attendance(att: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if att.empty:
        return pd.DataFrame(columns=["Date","Weekday","AttendeeCount"]), pd.DataFrame(columns=["Date","Person","Weekday"])

    # Sessions per date
    cnt = att.groupby("Date")["Person"].nunique().reset_index(name="AttendeeCount")
    cnt["Weekday"] = cnt["Date"].dt.weekday  # 0=Mon ... 6=Sun
    sessions_df = cnt.sort_values("Date").reset_index(drop=True)

    attendance_df = att.copy()
    attendance_df["Weekday"] = attendance_df["Date"].dt.weekday
    return sessions_df, attendance_df

def weekday_name(idx: int) -> str:
    return ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][idx]

def number_of_practices_per_weekday(sessions_df: pd.DataFrame) -> pd.Series:
    if sessions_df.empty:
        return pd.Series(dtype=int)
    counts = sessions_df.groupby("Weekday")["Date"].nunique()
    counts.index = counts.index.map(weekday_name)
    return counts

def fractions_by_person_per_weekday(sessions_df: pd.DataFrame, attendance_df: pd.DataFrame) -> pd.DataFrame:
    if sessions_df.empty or attendance_df.empty:
        cols = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun","Total"]
        return pd.DataFrame(columns=cols)

    # totals per weekday (denominator)
    total_sessions = sessions_df.groupby("Weekday")["Date"].nunique()

    # numerators per person/weekday
    per_person_counts = attendance_df.groupby(["Person", "Weekday"])["Date"].nunique().unstack(fill_value=0)

    # Align/limit to weekdays that actually have sessions
    per_person_counts = per_person_counts.reindex(columns=sorted(total_sessions.index), fill_value=0)

    # Fractions by weekday
    frac = per_person_counts.div(total_sessions, axis=1)

    # Rename weekday columns
    frac.columns = [weekday_name(i) for i in frac.columns]

    # Drop weekdays with zero sessions entirely (shouldn't exist after alignment, but keep safe)
    nonzero_wd = [weekday_name(i) for i, total in total_sessions.items() if total > 0]
    frac = frac.reindex(columns=nonzero_wd)

    # Add Total fraction: (sum of numerators) / (sum of denominators)
    total_denominator = total_sessions.sum()
    total_numerators = per_person_counts.sum(axis=1)  # total sessions attended by person
    frac["Total"] = (total_numerators / total_denominator).fillna(0.0)

    # Sort by Total desc then by name
    frac = frac.sort_values(["Total"], ascending=[False])

    # Reset index to have a named column
    frac = frac.reset_index().rename(columns={"Person": "Meetup name"})

    return frac

def make_bokeh_surplus_plots(sessions_df: pd.DataFrame, outdir: str, revenue_per_person: float = 10.0, pool_cost: float = 105.0) -> pd.DataFrame:
    if sessions_df.empty:
        return pd.DataFrame(columns=["WeekdayName","Date","Attendees","Delta","Deficit"])

    os.makedirs(outdir, exist_ok=True)
    all_rows = []

    for wd, grp in sessions_df.groupby("Weekday", sort=True):
        grp = grp.sort_values("Date").reset_index(drop=True)

        # Compute cumulative "deficit" (same running value as before, typically negative)
        deficit = 0.0
        dates = []
        ys = []
        deltas = []
        attendees_list = []
        for _, row in grp.iterrows():
            p = row["AttendeeCount"]
            delta = p * revenue_per_person - pool_cost
            deficit += delta
            dates.append(row["Date"])
            ys.append(deficit)
            deltas.append(delta)
            attendees_list.append(p)

        # Bokeh plot
        wkname = weekday_name(wd)
        pfig = figure(
            x_axis_type="datetime",
            title=f"Money Deficit over Time — {wkname}",
            width=900,
            height=400,
            tools="pan,wheel_zoom,box_zoom,reset,save,hover",
            active_scroll="wheel_zoom"
        )
        pfig.yaxis.axis_label = "Deficit ($)"
        pfig.xaxis.axis_label = "Date"

        source_data = dict(date=dates, y=ys, attendees=attendees_list, delta=deltas)
        pfig.line(x="date", y="y", source=source_data)
        pfig.circle(x="date", y="y", source=source_data, size=6)

        hover = pfig.select_one(HoverTool)
        hover.tooltips = [
            ("Date", "@date{%F}"),
            ("Deficit", "@y{$0,0.00}"),
            ("Attendees", "@attendees"),
            ("Delta", "@delta{$0,0.00}"),
        ]
        hover.formatters = {"@date": "datetime"}

        html_path = os.path.join(outdir, f"surplus_{wkname}.html")
        output_file(html_path, title=f"Deficit — {wkname}")
        save(pfig)

        for d, a, delta, yv in zip(dates, attendees_list, deltas, ys):
            all_rows.append({
                "Weekday": wd,
                "WeekdayName": wkname,
                "Date": d,
                "Attendees": a,
                "Delta": delta,
                "Deficit": yv,
            })

    return pd.DataFrame(all_rows)

def main():
    parser = argparse.ArgumentParser(description="Analyze punchcard attendance and finances by weekday (interactive Bokeh plots).")
    parser.add_argument("--punchcards", required=True, help="Path to punchcards.csv")
    parser.add_argument("--history", required=True, help="Path to punchcards_history.csv")
    parser.add_argument("--outdir", default="analysis_output", help="Directory to save outputs")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    df1 = smart_read_csv(args.punchcards)
    df2 = smart_read_csv(args.history)

    attendance = build_attendance_long([df1, df2])
    if attendance.empty:
        print("No attendance dates found in the provided files.")
        sys.exit(0)

    sessions_df, attendance_df = compute_sessions_and_attendance(attendance)

    # 1) Number of practices per weekday
    weekday_counts = number_of_practices_per_weekday(sessions_df).sort_index()

    # 2) Fractions per person (Meetup name preferred) per weekday + Total
    fractions_df = fractions_by_person_per_weekday(sessions_df, attendance_df)

    # 3) Interactive Bokeh deficit plots & data
    deficit_df = make_bokeh_surplus_plots(sessions_df, args.outdir, revenue_per_person=10.0, pool_cost=105.0)

    # Save outputs
    weekday_counts.to_csv(os.path.join(args.outdir, "weekday_practice_counts.csv"), header=["Count"])
    fractions_df.to_csv(os.path.join(args.outdir, "fractions_by_weekday_meetupname.csv"), index=False)
    deficit_df.to_csv(os.path.join(args.outdir, "deficit_timeseries_by_weekday.csv"), index=False)

    with open(os.path.join(args.outdir, "README.txt"), "w") as f:
        f.write("Outputs generated:\n")
        f.write("- weekday_practice_counts.csv: number of distinct practice dates per weekday (Mon..Sun)\n")
        f.write("- fractions_by_weekday_meetupname.csv: per-weekday attendance fraction by Meetup name, plus Total fraction\n")
        f.write("- deficit_timeseries_by_weekday.csv: per-weekday time series with attendees, delta, cumulative deficit\n")
        f.write("- surplus_<Weekday>.html: interactive Bokeh plots for each weekday with sessions\n")

    print("== Number of distinct practice dates per weekday ==")
    print(weekday_counts)
    print("\nSaved:")
    print(f"- {os.path.join(args.outdir, 'weekday_practice_counts.csv')}")
    print(f"- {os.path.join(args.outdir, 'fractions_by_weekday_meetupname.csv')}")
    print(f"- {os.path.join(args.outdir, 'deficit_timeseries_by_weekday.csv')}")
    print(f"- {os.path.join(args.outdir, 'surplus_*.html')}")

if __name__ == "__main__":
    main()
