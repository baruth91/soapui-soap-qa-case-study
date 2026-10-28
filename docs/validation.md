# Execution evidence

| Environment | Scope | Observed result |
| --- | --- | --- |
| Windows, Python 3.13, JDK 21, SoapUI Open Source 5.10.0 | Real Java service / SoapUI baseline | 13 cases, 40 requests, 296 assertions passed |
| Same lab, deliberate missing-debit flag | SOAP-002 only | Nonzero SoapUI result; expected 974.90, actual 1000.00 |
| Ubuntu 24.04 hosted runner | Same Java service and SoapUI jars | 13 cases / 40 requests / 296 assertions passed; mutation detected |

[Verified GitHub Actions run](https://github.com/baruth91/soapui-soap-qa-case-study/actions/runs/40773900067)
executed commit `fd051d9`. Hosted baseline JUnit reports 13 tests, zero failures and
zero errors. The separate mutation reports one test and one failure, with runner
exit code 255 and the exact missing-debit mismatch. Its evidence-checking wrapper
passed. Baseline JUnit test-case time totals 2.782 seconds; runner preparation and
process startup are additional time.

Downloaded hosted artifacts were independently inspected: both JUnit files contain
zero JVM-properties blocks. The baseline execution summary records runner exit 0;
the mutation summary names only SOAP-002 as failing. This is the intended red/green
teaching comparison, not a hidden failure in the normal implementation.

The baseline covers real state mutation, exact decimals, minimum/exact-balance
boundaries, retry behavior, specific business faults and XSD rejections. GetAccount
reads verify both account balances and global receipt count after the operation.
Per-case fixture resets are additional HTTP setup calls, not part of the 40 SOAP requests.

The mutation demonstrates one meaningful financial check failing. It does not
prove every assertion can detect every possible defect. Expected SOAP faults are
successful negative tests; a setup/transport failure is never accepted as their substitute.

SoapUI emits compatibility warnings about its bundled SOAP encoding schemas even
for this document/literal service. Those warnings are distinct from test assertion
failures. The project intentionally uses native schema assertions; none are removed
to make the baseline pass. The native internal IDs for Fault and Not Fault are
counterintuitive and were checked against the 5.10.0 source during implementation.

The exported JUnit is sanitized to remove JVM system properties. Raw tool logs and
downloaded artifacts remain ignored. Hosted artifacts expire after seven days.
The headless importer/runner is verified; a manual desktop UI walkthrough remains
a learner exercise. See test-strategy.md for unexecuted cases and excluded guarantees.
