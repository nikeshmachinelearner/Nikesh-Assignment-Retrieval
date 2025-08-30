"""
Weekly Scheduler
----------------
Runs crawler.py and indexer.py every Sunday at 03:30 (Asia/Kathmandu time).
Keeps running in the foreground; stop with Ctrl+C.
"""
import os
import sys
import datetime
import subprocess
from apscheduler.schedulers.blocking import BlockingScheduler

BASE = os.path.dirname(__file__) # Base directory (same as this file)

SCRIPTS = [
    os.path.join(BASE, "crawler.py"),
    os.path.join(BASE, "indexer.py"),
]

def run_script(path: str):
    """Run a Python script with the same interpreter, log start/end times."""
    ts = datetime.datetime.now().isoformat()
    print(f"[{ts}] Starting {os.path.basename(path)}")
    result = subprocess.run([sys.executable, path])
    print(f"[{ts}] Finished {os.path.basename(path)} (exit code {result.returncode})")

def job():
    """Job that runs all scripts sequentially."""
    for script in SCRIPTS:
        run_script(script)

if __name__ == "__main__":
    # Scheduler with local timezone (Kathmandu). Use "UTC" if you prefer.
    sched = BlockingScheduler(timezone="Asia/Kathmandu")

    # Add weekly job: every Sunday 03:30
    sched.add_job(job, "cron", day_of_week="sun", hour=3, minute=30)

    print("Scheduler started (runs every Sunday 03:30 Asia/Kathmandu). Press Ctrl+C to stop.")
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")
