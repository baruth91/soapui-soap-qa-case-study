"""Run real SoapUI requests against an owned Java process; preserve the runner exit code."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".tools"
WORK = ROOT / ".work"
VERSION = "5.10.0"
URL = f"https://dl.eviware.com/soapuios/{VERSION}/SoapUI-{VERSION}-windows-bin.zip"
SHA256 = "efdd5684eeecd942ceff297a7771db23a66f94cc13d33e83a039d51fe787aade"


def jdk(tool):
    home = os.environ.get("JAVA_HOME")
    candidate = Path(home) / "bin" / (tool + (".exe" if os.name == "nt" else "")) if home else None
    found = str(candidate) if candidate and candidate.is_file() else shutil.which(tool)
    if not found:
        raise RuntimeError("Install JDK 21 and set JAVA_HOME (both java and javac are needed)")
    return found


def prepare():
    TOOLS.mkdir(exist_ok=True)
    archive = TOOLS / "soapui.zip"
    if not archive.exists():
        partial = archive.with_suffix(".partial")
        print(f"Downloading official SoapUI {VERSION}", flush=True)
        urllib.request.urlretrieve(URL, partial)
        partial.replace(archive)
    with archive.open("rb") as stream:
        if hashlib.file_digest(stream, "sha256").hexdigest() != SHA256:
            raise RuntimeError("SoapUI archive checksum differs from the recorded download")
    home = TOOLS / f"SoapUI-{VERSION}"
    if not home.exists():
        with zipfile.ZipFile(archive) as zipped:
            for item in zipped.infolist():
                if not (TOOLS / item.filename).resolve().is_relative_to(TOOLS.resolve()):
                    raise RuntimeError("Archive path escapes tools directory")
            zipped.extractall(TOOLS)
    return home


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mutation",
        action="store_true",
        help="Deliberately omit debit; a real SoapUI failure is required",
    )
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--port", type=int, default=18081)
    args = parser.parse_args()
    home = prepare()
    if args.prepare_only:
        return 0
    if not 1024 <= args.port <= 65535:
        raise ValueError("Choose an unprivileged local TCP port")
    WORK.mkdir(exist_ok=True)
    classes = WORK / "classes"
    classes.mkdir(exist_ok=True)
    subprocess.run(
        [
            jdk("javac"),
            "--release",
            "21",
            "-d",
            str(classes),
            "service/AccountService.java",
        ],
        cwd=ROOT,
        check=True,
    )
    reports = ROOT / "reports" / ("mutation" if args.mutation else "baseline")
    if reports.exists() and any(reports.iterdir()):
        # Do not let stale reports appear to prove a new execution.
        reports = reports.with_name(reports.name + "-" + str(time.time_ns()))
    reports.mkdir(parents=True, exist_ok=True)
    endpoint = f"http://127.0.0.1:{args.port}/accounts"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    result = None
    with (WORK / "service.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(
            [
                jdk("java"),
                "-Dqa.skipDebit=" + str(args.mutation).lower(),
                "-cp",
                str(classes),
                "AccountService",
                str(args.port),
            ],
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=flags,
        )
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            for _ in range(100):
                if process.poll() is not None:
                    raise RuntimeError(
                        "Owned service stopped; inspect .work/service.log. Check for a port collision."
                    )
                try:
                    with opener.open(f"http://127.0.0.1:{args.port}/health", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise TimeoutError("Service readiness exceeded ten seconds")
            classpath = os.pathsep.join(
                [str(home / f"bin/soapui-{VERSION}.jar"), str(home / "lib/*")]
            )
            isolated_home = WORK / "runner-home"
            isolated_home.mkdir(exist_ok=True)
            command = [
                jdk("java"),
                "-Xmx768m",
                "-Djava.awt.headless=true",
                f"-Duser.home={isolated_home}",
                f"-Dsoapui.home={home / 'bin'}",
                f"-Dsoapui.logroot={WORK}",
            ]
            for module in (
                "java.base/java.lang",
                "java.base/java.lang.invoke",
                "java.base/java.util",
                "java.base/java.lang.reflect",
                "java.desktop/java.beans",
            ):
                command.extend(["--add-opens", module + "=ALL-UNNAMED"])
            command.extend(
                [
                    "-cp",
                    classpath,
                    "com.eviware.soapui.tools.SoapUITestCaseRunner",
                    "-r",
                    "-j",
                    "-f" + str(reports),
                    "-P" + "Endpoint=" + endpoint,
                ]
            )
            if args.mutation:
                command.append("-cSOAP-002 exact decimal transfer and conservation")
            command.append(str(ROOT / "soapui/accounts-soapui-project.xml"))
            print("Running real SoapUI test runner", flush=True)
            result = subprocess.run(command, cwd=WORK, timeout=180, check=False)
            xml_reports = list(reports.glob("TEST-*.xml"))
            if not xml_reports:
                raise RuntimeError(
                    "SoapUI produced no JUnit report; a zero exit code alone is insufficient"
                )
            cases = []
            for path in xml_reports:
                tree = ET.parse(path)
                root = tree.getroot()
                # SoapUI includes JVM system properties (including paths) in raw JUnit.
                # Publish only test evidence, not the runner machine's configuration.
                for properties in root.findall("properties"):
                    root.remove(properties)
                cases.extend(root.iter("testcase"))
                tree.write(path, encoding="utf-8", xml_declaration=True)
            failures = [
                c.get("name")
                for c in cases
                if c.find("failure") is not None or c.find("error") is not None
            ]
            expected = 1 if args.mutation else 13
            summary = {
                "soapui_version": VERSION,
                "mutation": args.mutation,
                "runner_exit_code": result.returncode,
                "test_cases": len(cases),
                "failed_cases": failures,
            }
            (reports / "execution.json").write_text(
                json.dumps(summary, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(summary, indent=2), flush=True)
            print(f"Reports: {reports}", flush=True)
            if len(cases) != expected:
                raise RuntimeError(
                    f"Expected {expected} executed SoapUI cases, observed {len(cases)}"
                )
            if args.mutation and (result.returncode == 0 or len(failures) != 1):
                raise RuntimeError(
                    "The mutation did not produce the required one-case regression failure"
                )
            if not args.mutation and (result.returncode != 0 or failures):
                return result.returncode or 1
            # Mutation deliberately returns a failing status; the caller must interpret it explicitly.
            return result.returncode
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
