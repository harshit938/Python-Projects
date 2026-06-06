"""
============================================================
  Student Result Analysis System
  Author : Harshit Kumar Mishra
  Tech   : Python | Pandas | Matplotlib | CSV
  Desc   : Reads student marks from CSV and generates:
           - Subject-wise pass/fail reports
           - Class averages, toppers, lowest scorers
           - Grade assignment (A+/A/B/C/D/F)
           - Bar charts & pie charts via Matplotlib
           Full logging, error handling & validation.
============================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import logging
import os
import sys
from datetime import datetime

# ─────────────────────────────────────────────
#  LOGGING SETUP
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
    handlers=[
        logging.FileHandler("result_analysis.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────
INPUT_CSV  = "students.csv"    # path to input file
OUTPUT_DIR = "output"
PASS_MARKS = 40                # minimum marks to pass a subject
MAX_MARKS  = 100               # maximum marks per subject

GRADE_SCALE = [
    (90, "A+"),
    (80, "A"),
    (70, "B"),
    (60, "C"),
    (50, "D"),
    (0,  "F"),
]

# ─────────────────────────────────────────────
#  SAMPLE DATA GENERATOR (for demo / testing)
# ─────────────────────────────────────────────
def generate_sample_csv(path: str = INPUT_CSV):
    """Create a sample students.csv if none exists."""
    import random
    random.seed(42)

    subjects = ["Math", "Science", "English", "History", "Computer"]
    names    = [
        "Aarav Sharma", "Priya Singh", "Rohan Gupta", "Anjali Verma",
        "Vikram Patel", "Sneha Reddy", "Arjun Mehta", "Kavya Nair",
        "Rahul Joshi", "Divya Rao", "Aditya Kumar", "Pooja Tiwari",
        "Sahil Khan", "Neha Mishra", "Yash Kapoor", "Riya Bose",
        "Nikhil Chatterjee", "Swati Pandey", "Deepak Yadav", "Shreya Das",
    ]

    rows = []
    for i, name in enumerate(names, start=1):
        row = {"Roll No": i, "Student Name": name}
        for sub in subjects:
            # Simulate realistic marks — a few failures
            row[sub] = random.randint(30 if random.random() < 0.1 else 45, 100)
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    log.info(f"Sample CSV created: {path}  ({len(df)} students, {len(subjects)} subjects)")
    return df

# ─────────────────────────────────────────────
#  DATA LOADING & VALIDATION
# ─────────────────────────────────────────────
def load_data(path: str) -> pd.DataFrame:
    """Load CSV, validate columns and data types."""
    if not os.path.exists(path):
        log.warning(f"'{path}' not found. Generating sample data …")
        return generate_sample_csv(path)

    try:
        df = pd.read_csv(path)
        log.info(f"Loaded '{path}'  →  {df.shape[0]} rows, {df.shape[1]} columns")
    except Exception as e:
        log.error(f"Failed to read CSV: {e}")
        sys.exit(1)

    # Required columns
    required = {"Roll No", "Student Name"}
    missing  = required - set(df.columns)
    if missing:
        log.error(f"Missing required columns: {missing}")
        sys.exit(1)

    # Identify subject columns (all numeric columns except Roll No)
    subject_cols = [c for c in df.columns if c not in ("Roll No", "Student Name")]
    if not subject_cols:
        log.error("No subject columns found in the CSV.")
        sys.exit(1)

    # Coerce marks to numeric, flag invalid entries
    for col in subject_cols:
        original = df[col].copy()
        df[col]  = pd.to_numeric(df[col], errors="coerce")
        invalid  = df[col].isna() & original.notna()
        if invalid.any():
            log.warning(f"  '{col}': {invalid.sum()} invalid value(s) set to NaN.")

    # Clip marks to [0, MAX_MARKS]
    df[subject_cols] = df[subject_cols].clip(0, MAX_MARKS)

    log.info(f"Subject columns detected: {subject_cols}")
    return df

# ─────────────────────────────────────────────
#  GRADE ASSIGNMENT
# ─────────────────────────────────────────────
def assign_grade(avg: float) -> str:
    for threshold, grade in GRADE_SCALE:
        if avg >= threshold:
            return grade
    return "F"

# ─────────────────────────────────────────────
#  CORE ANALYSIS
# ─────────────────────────────────────────────
def analyse(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Perform full analysis. Returns:
      - student_report  : per-student summary
      - subject_report  : per-subject summary
      - pass_fail_matrix: pass/fail status per student per subject
    """
    subject_cols = [c for c in df.columns if c not in ("Roll No", "Student Name")]

    # ── Per-student metrics ──────────────────
    sr = df[["Roll No", "Student Name"]].copy()
    sr["Total"]     = df[subject_cols].sum(axis=1)
    sr["Average"]   = df[subject_cols].mean(axis=1).round(2)
    sr["Max Mark"]  = df[subject_cols].max(axis=1)
    sr["Min Mark"]  = df[subject_cols].min(axis=1)
    sr["Grade"]     = sr["Average"].apply(assign_grade)
    sr["Rank"]      = sr["Average"].rank(ascending=False, method="min").astype(int)

    # Overall pass = passed ALL subjects
    pass_matrix = df[subject_cols] >= PASS_MARKS
    sr["Status"] = pass_matrix.all(axis=1).map({True: "PASS", False: "FAIL"})
    sr["Subjects Failed"] = (df[subject_cols] < PASS_MARKS).sum(axis=1)
    sr = sr.sort_values("Rank")

    # ── Per-subject metrics ──────────────────
    subj_data = []
    for sub in subject_cols:
        col      = df[sub].dropna()
        passed   = (col >= PASS_MARKS).sum()
        failed   = (col < PASS_MARKS).sum()
        subj_data.append({
            "Subject"       : sub,
            "Average"       : round(col.mean(), 2),
            "Highest"       : col.max(),
            "Lowest"        : col.min(),
            "Pass Count"    : passed,
            "Fail Count"    : failed,
            "Pass %"        : round(passed / len(col) * 100, 1),
        })
    subject_report = pd.DataFrame(subj_data)

    # ── Pass/Fail matrix ─────────────────────
    pf_matrix = df[["Roll No", "Student Name"]].copy()
    for sub in subject_cols:
        pf_matrix[sub] = df[sub].apply(
            lambda x: f"PASS ({int(x)})" if pd.notna(x) and x >= PASS_MARKS
                      else f"FAIL ({int(x)})" if pd.notna(x)
                      else "N/A"
        )

    return sr, subject_report, pf_matrix

# ─────────────────────────────────────────────
#  VISUALISATIONS
# ─────────────────────────────────────────────
def plot_results(df: pd.DataFrame, student_report: pd.DataFrame,
                 subject_report: pd.DataFrame, output_dir: str):
    """Generate and save all charts."""
    os.makedirs(output_dir, exist_ok=True)
    subject_cols = [c for c in df.columns if c not in ("Roll No", "Student Name")]

    plt.style.use("seaborn-v0_8-whitegrid")
    colors_main = ["#2196F3", "#4CAF50", "#F44336", "#FF9800",
                   "#9C27B0", "#00BCD4", "#795548"]

    # ── 1. Subject-wise Average Bar Chart ───────
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(subject_report["Subject"], subject_report["Average"],
                  color=colors_main[:len(subject_cols)], edgecolor="white", linewidth=0.8)
    ax.axhline(y=PASS_MARKS, color="red", linestyle="--", linewidth=1.5,
               label=f"Pass Mark ({PASS_MARKS})")
    for bar, val in zip(bars, subject_report["Average"]):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                f"{val:.1f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_title("Subject-wise Class Average", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Subject", fontsize=11)
    ax.set_ylabel("Average Marks", fontsize=11)
    ax.set_ylim(0, MAX_MARKS + 10)
    ax.legend()
    plt.tight_layout()
    path1 = os.path.join(output_dir, "chart_subject_averages.png")
    plt.savefig(path1, dpi=150)
    plt.close()
    log.info(f"Chart saved: {path1}")

    # ── 2. Grade Distribution Pie Chart ─────────
    grade_counts = student_report["Grade"].value_counts()
    grade_colors = {"A+": "#4CAF50", "A": "#8BC34A", "B": "#2196F3",
                    "C": "#FF9800",  "D": "#FF5722", "F": "#F44336"}
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        grade_counts.values,
        labels=grade_counts.index,
        autopct="%1.1f%%",
        colors=[grade_colors.get(g, "#9E9E9E") for g in grade_counts.index],
        startangle=140,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    for autotext in autotexts:
        autotext.set_fontsize(10)
        autotext.set_fontweight("bold")
    ax.set_title("Grade Distribution (All Students)", fontsize=14, fontweight="bold", pad=15)
    plt.tight_layout()
    path2 = os.path.join(output_dir, "chart_grade_distribution.png")
    plt.savefig(path2, dpi=150)
    plt.close()
    log.info(f"Chart saved: {path2}")

    # ── 3. Top 5 Performers Bar Chart ───────────
    top5 = student_report.nsmallest(5, "Rank")[["Student Name", "Average", "Grade"]]
    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(top5["Student Name"], top5["Average"],
                   color="#4CAF50", edgecolor="white")
    for bar, avg, grade in zip(bars, top5["Average"], top5["Grade"]):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{avg:.1f}  [{grade}]", va="center", fontsize=9, fontweight="bold")
    ax.set_xlim(0, MAX_MARKS + 15)
    ax.set_title("Top 5 Performers", fontsize=14, fontweight="bold", pad=15)
    ax.set_xlabel("Average Marks", fontsize=11)
    ax.invert_yaxis()
    plt.tight_layout()
    path3 = os.path.join(output_dir, "chart_top5_performers.png")
    plt.savefig(path3, dpi=150)
    plt.close()
    log.info(f"Chart saved: {path3}")

    # ── 4. Pass vs Fail per Subject ──────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    x   = range(len(subject_report))
    w   = 0.35
    ax.bar([i - w/2 for i in x], subject_report["Pass Count"],
           width=w, label="Pass", color="#4CAF50", edgecolor="white")
    ax.bar([i + w/2 for i in x], subject_report["Fail Count"],
           width=w, label="Fail", color="#F44336", edgecolor="white")
    ax.set_xticks(list(x))
    ax.set_xticklabels(subject_report["Subject"])
    ax.set_title("Pass vs Fail Count per Subject", fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel("Number of Students", fontsize=11)
    ax.legend()
    plt.tight_layout()
    path4 = os.path.join(output_dir, "chart_pass_fail_per_subject.png")
    plt.savefig(path4, dpi=150)
    plt.close()
    log.info(f"Chart saved: {path4}")

# ─────────────────────────────────────────────
#  SAVE REPORTS TO CSV
# ─────────────────────────────────────────────
def save_reports(student_report: pd.DataFrame,
                 subject_report: pd.DataFrame,
                 pf_matrix: pd.DataFrame,
                 output_dir: str):
    """Save all report DataFrames to CSV files."""
    os.makedirs(output_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    paths = {
        "student_report": os.path.join(output_dir, f"student_report_{ts}.csv"),
        "subject_report": os.path.join(output_dir, f"subject_report_{ts}.csv"),
        "pass_fail_matrix": os.path.join(output_dir, f"pass_fail_matrix_{ts}.csv"),
    }

    student_report.to_csv(paths["student_report"],   index=False)
    subject_report.to_csv(paths["subject_report"],   index=False)
    pf_matrix.to_csv(paths["pass_fail_matrix"],      index=False)

    for name, path in paths.items():
        log.info(f"Saved {name}: {path}")

    return paths

# ─────────────────────────────────────────────
#  PRINT SUMMARY TO CONSOLE
# ─────────────────────────────────────────────
def print_summary(student_report: pd.DataFrame, subject_report: pd.DataFrame):
    sep = "=" * 60

    print(f"\n{sep}")
    print("  STUDENT RESULT ANALYSIS — SUMMARY REPORT")
    print(sep)

    total    = len(student_report)
    passed   = (student_report["Status"] == "PASS").sum()
    failed   = total - passed
    class_avg = student_report["Average"].mean()

    print(f"  Total Students   : {total}")
    print(f"  Overall Passed   : {passed}  ({passed/total*100:.1f}%)")
    print(f"  Overall Failed   : {failed}  ({failed/total*100:.1f}%)")
    print(f"  Class Average    : {class_avg:.2f} / {MAX_MARKS}")
    print(sep)

    # Topper
    topper = student_report.iloc[0]
    print(f"  🏆 Topper        : {topper['Student Name']}  "
          f"(Avg: {topper['Average']}, Grade: {topper['Grade']})")

    # Lowest scorer
    lowest = student_report.iloc[-1]
    print(f"  📉 Lowest Scorer : {lowest['Student Name']}  "
          f"(Avg: {lowest['Average']}, Grade: {lowest['Grade']})")
    print(sep)

    # Top 5
    print("\n  TOP 5 PERFORMERS:")
    print(f"  {'Rank':<6} {'Name':<22} {'Avg':>6}  {'Grade':<5}  Status")
    print("  " + "-"*55)
    for _, row in student_report.head(5).iterrows():
        print(f"  {row['Rank']:<6} {row['Student Name']:<22} "
              f"{row['Average']:>6.1f}  {row['Grade']:<5}  {row['Status']}")

    # Subject summary
    print(f"\n  SUBJECT-WISE SUMMARY:")
    print(f"  {'Subject':<14} {'Avg':>6}  {'High':>5}  {'Low':>4}  {'Pass%':>6}")
    print("  " + "-"*45)
    for _, row in subject_report.iterrows():
        print(f"  {row['Subject']:<14} {row['Average']:>6.1f}  "
              f"{row['Highest']:>5}  {row['Lowest']:>4}  {row['Pass %']:>5.1f}%")

    print(f"\n{sep}\n")

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    log.info("Student Result Analysis System started.")

    # 1. Load data
    df = load_data(INPUT_CSV)

    # 2. Analyse
    student_report, subject_report, pf_matrix = analyse(df)

    # 3. Print summary
    print_summary(student_report, subject_report)

    # 4. Generate charts
    plot_results(df, student_report, subject_report, OUTPUT_DIR)

    # 5. Save CSV reports
    save_reports(student_report, subject_report, pf_matrix, OUTPUT_DIR)

    log.info("Analysis complete. Check the 'output/' folder for reports and charts.")