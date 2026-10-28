# Learn the case in stages

## 1. Predict before running

Write down what a 25.10 transfer should do to 1000.00 and 250.00. Predict what
should happen if the identical message arrives twice. Explain why a response
saying COMPLETED alone cannot establish correct account balances.

Checkpoint: expected balances are 974.90 and 275.10, with one recorded transfer.

## 2. Read the contract

Open service/accounts.wsdl. Identify types, request/response messages, portType,
binding and service address. This is WSDL 1.1 describing SOAP 1.1 document/literal.
Read the inline Money restriction and compare it with service/accounts.xsd.
The generator embeds that schema so the portable cached WSDL has no remote import.

Checkpoint: explain which information comes from XSD and which requires a business
rule. An amount of 1000.01 satisfies Money but exceeds the fixture's available funds.

## 3. Trace one real operation

Follow SOAP-002 in the imported project or generated XML. Read its Transfer request,
then its two GetAccount requests. Inspect SOAPAction and the endpoint property.

```xml
<a:TransferRequest xmlns:a="urn:qa:accounts:v1">
  <a:requestId>transfer-001</a:requestId>
  <a:fromAccount>A100</a:fromAccount>
  <a:toAccount>B200</a:toAccount>
  <a:amount>25.10</a:amount>
  <a:currency>USD</a:currency>
</a:TransferRequest>
```

Checkpoint: distinguish XML namespace URI from the arbitrary prefix `a`.

## 4. Explain the assertions

```xquery
declare namespace a='urn:qa:accounts:v1';
//a:GetAccountResponse/a:balance/text()
```

Schema compliance checks the response structure and types, not sufficient funds
or correct arithmetic. HTTP status checks the transport contract. XPath checks
specific business values. Each assertion answers a different question.

Checkpoint: explain why valid XML with a wrong balance must still fail.

## 5. Execute the baseline

Run `python scripts/run.py`. Inspect the summary and sanitized JUnit in the newly
created reports directory. Separate startup/download time from SoapUI suite time.
Read the Java dispatch method and locate validation before the mutation boundary.

Checkpoint: 13 cases, 40 requests, 296 assertions and zero failures.

## 6. Diagnose a real failing test

Run `python scripts/run.py --mutation`; expect nonzero. Read the first financial
mismatch: fromBalance expected 974.90, actual 1000.00. The SOAP response can be
well formed, schema compliant and HTTP 200 while financially wrong.

Run `python scripts/check_mutation.py` to verify the reason was the intended
missing debit. It validates failure evidence, not just any nonzero status.

Checkpoint: identify the single conditional in Java that introduces the defect.

## 7. Read expected faults and verify state

Inspect SOAP-007 and SOAP-012. One rejects a business condition; the other rejects
the XSD amount restriction. Both have HTTP 500 and expected typed fault detail.
Read both account responses afterward; a fault alone cannot prove atomic rejection.

Checkpoint: distinguish an expected Fault from a timeout or inaccessible server.

## 8. Add a small data-driven exercise

In scripts/build_project.py, extend the existing rejection table with `amount`
values -0.01, 1000000.01 or a missing field. Generate the files and review the diff.
Each generated case should have its own reset, request, exact fault and state reads.
This is ordinary Python-authored parameterization of native SoapUI cases, not a
claim that the commercial DataSource test step exists in Open Source.

Suggested solution for the upper bound: add a new tuple with amount 1000000.01,
expected INVALID_REQUEST and unchanged balances/count. For a missing field, copy
the fields dictionary, remove currency, then generate a native request step; expect
the XSD rejection before dispatch. Update expected case count only after explaining
why the new test is independent. These additions are exercises, not baseline coverage.

## 9. Design an independent challenge

Add a retry of 25.1 after 25.10 using the same request ID. Explain BigDecimal
normalization, original receipt semantics and the receipt-count oracle. Then consider
a retry after a second transfer: should the old receipt show current balances?

Checkpoint: preserve the documented original-receipt behavior instead of silently
changing the requirement to fit an expectation.

## 10. Teach with limits

Use docs/demo.md and explain one excluded production concern. Have another learner
predict a result before seeing your test. Learning checkpoints represent work for
the owner to demonstrate; implementation completion is not proof of understanding.
