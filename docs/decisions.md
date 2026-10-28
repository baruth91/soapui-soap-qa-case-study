# Engineering decisions and tradeoffs

- **Original controlled service.** A local Java service makes actual state changes
  and exposes an explicit contract. It avoids dependence on public sample services.
  JDK HTTP/XML APIs keep setup small; handwritten envelope dispatch is educational,
  not a recommendation to replace an established enterprise SOAP stack in production.
- **Contract before examples.** The XSD defines schema constraints; Java defines
  business validation. WSDL embeds the same XSD. The generator updates the WSDL
  and the SoapUI definition cache together; CI checks for generation drift.
- **SoapUI Open Source 5.10.0.** This is a separate third-party tool. The archive
  comes from the Windows binary link on the official release page. We execute its
  platform-independent Java jars directly on Windows/Ubuntu rather than invoking
  platform shell launchers or the graphical application. The Ubuntu run is the
  portability evidence; other OS/JDK combinations are not automatically verified.
- **Recorded SHA-256.** Official URL:
  https://dl.eviware.com/soapuios/5.10.0/SoapUI-5.10.0-windows-bin.zip
  SHA-256: efdd5684eeecd942ceff297a7771db23a66f94cc13d33e83a039d51fe787aade.
  This pin was computed after downloading the official archive. It detects later
  changes against the recorded copy; it is not a signed vendor attestation. The
  tool is cached in ignored .tools, with its upstream license intact.
- **Small Python orchestration.** Standard-library code downloads/verifies tools,
  starts the owned process, waits for readiness and checks the actual JUnit result.
  Assertions execute in SoapUI. Python is not substituting for the SOAP test runner.
- **Exact arithmetic and atomic in-memory mutation.** BigDecimal and synchronized
  dispatch avoid floating-point money and interleaving inside this small process.
  Tests are sequential. Crash consistency and durable/distributed idempotency need
  a database transaction design and separate tests.
- **Positive and negative controls.** Every rejected transfer is followed by reads
  of both accounts and the receipt count. Replays preserve the original receipt;
  they are not fresh balance quotes. Existing API/database/security cases cover
  other layers with their own stated limits.
- **A bounded defect demonstration.** The missing-debit flag is deliberately
  enabled only for the mutation exercise. Its wrapper verifies the exact mismatch
  and one-case failure. No blanket expected-failure setting hides the baseline.
- **Evidence hygiene.** Exported JUnit has JVM properties removed; raw logs stay
  ignored. Reports contain synthetic data only and are retained online seven days.
  Owned process termination happens in finally, including test-runner timeout.
- **No paid-only dependencies.** The suite uses native assertions and Groovy case
  setup available in Open Source. Parameterized exercises generate independent
  cases in Python; no ReadyAPI DataSource or commercial report feature is assumed.

References: [SoapUI release](https://github.com/SmartBear/soapui/releases/tag/v5.10.0),
[functional runner](https://www.soapui.org/docs/automation/cli/functional-tests/),
[WSDL 1.1](https://www.w3.org/TR/wsdl.html),
[SOAP 1.1](https://www.w3.org/TR/2000/NOTE-SOAP-20000508/).
