"""check.py -- every selftest, then pyflakes. Exit 1 on any failure."""
import os
import subprocess
import sys

os.environ["ARGO_NO_SETTINGS"] = "1"        # the selftests test the defaults, whatever Ben has set

MODULES = ["rates", "settings", "sports", "weeks", "milestones", "sync", "score", "statement", "reply"]
fails = 0
for m in MODULES:
    r = subprocess.run([sys.executable, "-m", f"argo.{m}", "--selftest"], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip().splitlines()[-1])
    fails += r.returncode != 0
r = subprocess.run([sys.executable, "-m", "pyflakes", "argo", "check.py"], capture_output=True, text=True)
print(r.stdout.strip() or "pyflakes: clean")
fails += r.returncode != 0
print("OK" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
