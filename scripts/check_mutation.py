"""Accept only the specifically demonstrated missing-debit regression failure."""

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    before = set((ROOT / "reports").glob("mutation*"))
    result = subprocess.run(
        [sys.executable, "scripts/run.py", "--mutation"], cwd=ROOT, timeout=240, check=False
    )
    created = set((ROOT / "reports").glob("mutation*")) - before
    if len(created) != 1:
        raise RuntimeError("Expected one fresh mutation report directory")
    report_directory = created.pop()
    summary = json.loads((report_directory / "execution.json").read_text(encoding="utf-8"))
    expected = ["SOAP-002 exact decimal transfer and conservation"]
    if (
        result.returncode == 0
        or summary["runner_exit_code"] == 0
        or summary["failed_cases"] != expected
        or summary["test_cases"] != 1
    ):
        raise RuntimeError("Missing-debit mutation was not detected by the required case")
    failures = "\n".join(
        failure.text or ""
        for report in report_directory.glob("TEST-*.xml")
        for failure in ET.parse(report).getroot().iter("failure")
    )
    if not all(text in failures for text in ("Exact fromBalance", "974.90", "1000.00")):
        raise RuntimeError("Case failed for a reason other than the demonstrated missing debit")
    print("Confirmed: the real SoapUI runner failed the selected financial regression.")


if __name__ == "__main__":
    main()
