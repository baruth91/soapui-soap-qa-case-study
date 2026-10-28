# SOAP account transfers with SoapUI

A practical QA case study offered to the community: inspect a WSDL, predict a
financial outcome, execute real SOAP requests and explain why a rejection must
leave state unchanged. All accounts, balances and rules are synthetic.

This is learning material for a public QA portfolio and future practical training.
It contains original teaching code and no client systems, work artifacts or data.

## The business question

Can a transfer move exactly the requested USD amount, preserve total funds and
remain safe to retry? Can an invalid transfer be rejected without changing either
account or recording a transfer?

The service starts with A100 = 1000.00 USD and B200 = 250.00 USD. Each test case
resets its own fixture. Request steps within a case form an intentional workflow;
cases do not depend on a previous case's outcome.

## What runs

- An original Java 21 service using the JDK HTTP server, JAXP and BigDecimal.
- A versioned SOAP 1.1 document/literal WSDL with two operations: GetAccount and Transfer.
- The actual SoapUI Open Source 5.10.0 command-line test runner.
- Native SOAP, WSDL schema, HTTP status and namespace-aware XPath assertions.
- 13 cases / 40 SOAP requests / 296 request assertions in the complete baseline.
- A separate deliberate missing-debit mutation that must fail a specific financial assertion.
- GitHub Actions with a manual Run workflow button and downloadable JUnit evidence.

The service is a small contract-first implementation with in-memory state, not a
SOAP mock returning canned responses. It is not a production bank or a complete
SOAP framework. The test runner performs real HTTP requests over loopback.

## Run locally

Install Python 3.13, JDK 21 (including javac) and Git. Set JAVA_HOME to the JDK.
No Python packages, Maven, database, Docker or paid ReadyAPI license are needed.
Internet is required for the first official SoapUI download.

```bash
git clone https://github.com/baruth91/soapui-soap-qa-case-study.git
cd soapui-soap-qa-case-study
python scripts/run.py
```

On Windows use PowerShell with JAVA_HOME set, for example:

```powershell
$env:JAVA_HOME = 'C:\path\to\your\jdk-21'
python scripts/run.py
```

The script verifies a recorded SHA-256, compiles the service, waits for readiness,
runs SoapUI, checks the JUnit case count and stops only its owned Java process.
Port 18081 must be free; use `python scripts/run.py --port 18082` otherwise.
Reports are in `reports/baseline/`; later runs use a fresh suffixed directory.
Raw tool logs stay ignored in `.work/`. JVM properties are removed from exported
JUnit before it is uploaded. All request data is synthetic.

The archive's hash is a locally recorded pin from the official release URL, not
a claim of an independently signed vendor checksum. See [decisions](docs/decisions.md).

## Demonstrate that a test can fail

```bash
python scripts/run.py --mutation
```

This deliberately omits the source debit and must return nonzero. SoapUI should
report SOAP-002 failing: expected source balance 974.90, actual 1000.00. The normal
baseline never enables this defect. To verify the *specific expected failure*
as a successful engineering exercise, run:

```bash
python scripts/check_mutation.py
```

That wrapper checks the runner's failure, the one-case JUnit result and the exact
financial mismatch. It rejects setup failures and unrelated assertion failures;
the workflow does not hide failures using blanket continue-on-error.

## Run online

Open [Actions](https://github.com/baruth91/soapui-soap-qa-case-study/actions), choose
**SOAP contract and transfer integrity**, then **Run workflow**. The Ubuntu runner
downloads SoapUI and starts its own local service. Inspect both the baseline and
mutation-verification steps. Download `soapui-transfer-evidence` within seven days.
No separate cloud VM or manually maintained server is needed.

## Explore in the SoapUI desktop application

1. Use JDK 21 to compile the service: `javac --release 21 -d .work/classes service/AccountService.java`.
2. Start it from the repository root: `java -cp .work/classes AccountService 18081`.
3. In SoapUI Open Source 5.10.0, import `soapui/accounts-soapui-project.xml`.
4. Open the **Account transfer integrity** suite and run one case or the suite.
5. Inspect the request XML, SOAPAction, response and assertions. Stop the Java
   service with Ctrl+C when finished.

The headless runner and project loading are verified by execution. The desktop
click-through is a learner exercise, not a claimed manually verified GUI session.
Changing the WSDL address alone does not override the project Endpoint property.
Both the fixture reset and the service intentionally accept only the local lab.

## Read, explain and extend

| Resource | Purpose |
| --- | --- |
| [Test strategy](docs/test-strategy.md) | Risks, requirements, matrix and exclusions |
| [Contract](service/accounts.wsdl) / [XSD](service/accounts.xsd) | Types, messages, binding and declared fault |
| [Importable SoapUI project](soapui/accounts-soapui-project.xml) | Real requests and native assertions |
| [Java service](service/AccountService.java) | Validation, exact arithmetic and retry semantics |
| [Walkthrough](docs/tutorial.md) | Staged learning and small code exercises |
| [Demo script](docs/demo.md) | An 8–10 minute presentation |
| [Decisions](docs/decisions.md) | Tradeoffs, tool pin and scoped claims |
| [Validation](docs/validation.md) | Observed execution and remaining limits |

The project generator, `scripts/build_project.py`, makes the scenario table and
cached WSDL reviewable. After editing a schema or scenario, regenerate and review
both generated files. CI rejects drift. Manual edits in SoapUI can be explored on
a branch; port lasting changes back into the generator before regenerating.

## Scope and attribution

No authentication, WS-Security, TLS, persistence, distributed idempotency,
multi-currency conversion, crash recovery or load-test claims are made. Test reset
is explicitly a disposable-lab facility. Financial values never use floating point
in the service. Replays return the original receipt, not a new live balance quote.

Original project code and material are MIT licensed. SoapUI is SmartBear's
separate third-party tool and retains its upstream license; it is downloaded at
runtime and is not committed here. References: [official SoapUI release](https://github.com/SmartBear/soapui/releases/tag/v5.10.0),
[functional CLI](https://www.soapui.org/docs/automation/cli/functional-tests/),
[WSDL 1.1](https://www.w3.org/TR/wsdl.html) and [SOAP 1.1](https://www.w3.org/TR/2000/NOTE-SOAP-20000508/).
