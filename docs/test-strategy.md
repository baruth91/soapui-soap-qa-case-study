# Risk, contract and executable checks

## Requirements chosen for this teaching service

Transfer uses a nonempty request ID, known distinct accounts, USD, an amount from
0.01 to 1000000.00 and at most two meaningful fractional digits. Available funds
must cover the transfer. All rejection checks precede mutation. A successful
transfer atomically changes both in-memory balances and records one receipt.

An identical request ID and semantic payload returns its original receipt without
moving money again. Reusing the ID with different input produces
IDEMPOTENCY_CONFLICT. Receipts last only for this process's current fixture.
Amounts such as 25.1 and 25.10 normalize to the same amount; cross-process retries
and concurrent retry campaigns are outside this suite.

## Traceability matrix

| Case | Risk / boundary | Independent observable outcome |
| --- | --- | --- |
| SOAP-001 | Wrong resource/contract | Both account IDs, USD, exact balances, zero receipts |
| SOAP-002 | Rounding or one-sided mutation | 25.10 moves; subsequent reads show 974.90 and 275.10; one receipt |
| SOAP-003 | Minimum amount off by one cent | 0.01 moves; reads show 999.99 and 250.01 |
| SOAP-004 | Rejecting an exact-balance payment | 1000.00 moves; reads show 0.00 and 1250.00 |
| SOAP-005 | Duplicate charge | Same request twice; original receipt, same final balances, one receipt |
| SOAP-006 | Conflicting retry silently accepted | Changed amount rejected; first transfer and receipt count unchanged |
| SOAP-007 | Overspending | 1000.01 rejected as INSUFFICIENT_FUNDS; both balances and receipt count unchanged |
| SOAP-008 | Debit before destination validation | Unknown destination rejected; no money or receipt changes |
| SOAP-009 | Self-transfer corrupting state | SAME_ACCOUNT; no changes |
| SOAP-010 | Silent currency conversion | UNSUPPORTED_CURRENCY; no changes |
| SOAP-011 | Zero amount accepted | INVALID_REQUEST from XSD; no changes |
| SOAP-012 | Fractional cent rounded silently | 1.001 rejected by XSD; no changes |
| SOAP-013 | Negative amount reversing movement | INVALID_REQUEST from XSD; no changes |

Every SOAP request checks SOAP structure, WSDL response compliance, expected HTTP
status and fault presence/absence. XPath uses `urn:qa:accounts:v1`, not a fragile
prefix assumption. Exact values are extracted with text(); raw substring matching
is insufficient for account identity or balances. Fixed expected account reads
independently observe state after mutation rather than trusting only the transfer
receipt. They remain observations through the same service, not an independent
database oracle or independent implementation.

## Faults are part of the contract

A normal response uses HTTP 200. A declared business/schema rejection uses SOAP
1.1 Fault, HTTP 500 and a BusinessFault detail with a stable code. A received
expected Fault can therefore be a passing test. A refused connection, a timeout
or an unexpected INTERNAL_ERROR is not an acceptable business outcome.

The local contract intentionally maps validation failures to Client faults. The
service's fallback also emits a Client fault for INTERNAL_ERROR; production fault
classification and a richer fault hierarchy remain improvements, not verified
behavior. Tests never accept INTERNAL_ERROR as a business rejection.

## Fixture and oracle design

Each case resets fixtures using a bounded Groovy setup request to loopback. Setup
failures fail the case. All cases can run separately. The baseline counts 40 SOAP
requests; the 13 reset HTTP calls are setup and are excluded from that number.
Transfer counts in GetAccount are the lab's global receipt count, not an
account-specific statement history.

Conservation is checked by both known balances summing to the original 1250.00,
not by comparing a total computed by the service against itself. The explicit
missing-debit mutation proves a meaningful financial assertion can fail; it does
not prove all assertions or all possible implementation defects are detectable.

## Deliberate exclusions and next exercises

Required-field omission, wrong namespaces, malformed envelopes, wrong SOAPAction,
unknown source, maximum amount, lexical decimal equivalents, retry after another
transfer and concurrent requests are useful next coverage. They are not claimed
as executed cases. The input parser disables DTDs/external entities, but no XXE
security certification follows from that implementation setting.

WS-Security, ownership, HTTPS, durable database transactions, recovery after a
process crash and throughput require distinct fixtures and contracts. The existing
API security and database repositories explore other layers separately.
