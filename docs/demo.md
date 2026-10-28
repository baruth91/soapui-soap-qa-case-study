# An 8–10 minute demonstration

1. **Business risk, one minute.** Two synthetic accounts must transfer exact money
   once. Describe duplicate delivery and partial mutation in plain language.
2. **Contract, one minute.** Show WSDL messages/binding, Money constraints and the
   declared BusinessFault. Distinguish schema rules from available funds.
3. **Tests, two minutes.** Show SOAP-002 and its namespace-aware XPath assertions.
   Explain subsequent account reads and why fixed fixture expectations matter.
4. **Execution, one minute.** Run `python scripts/run.py`, or show the verified
   Actions run. First-time download may exceed the presentation slot; prepare tools
   with `python scripts/run.py --prepare-only` before presenting.
5. **Faults and retries, one minute.** Compare insufficient funds, fractional cents,
   identical retry and conflicting retry. Explain HTTP 500 as expected here.
6. **A genuine red result, one minute.** Run the deliberate mutation. Show expected
   974.90 versus actual 1000.00. Explain that the normal implementation passes.
7. **CI and limits, one minute.** Show manual execution, baseline/mutation steps and
   JUnit artifact. State that persistence, WS-Security and concurrent guarantees
   were not established by this suite.
8. **Learning, one minute.** Propose one missing-input exercise and its state oracle.

Be prepared to explain BigDecimal, namespace URI versus prefix, fixture isolation,
fault versus transport failure, receipt versus current balance and why 296 assertions
are useful only when tied to distinct risks. Do not present synthetic teaching rules
as the policy of an employer, client or actual financial institution.
