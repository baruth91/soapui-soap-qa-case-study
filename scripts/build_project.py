"""Author the portable SoapUI project from explicit, reviewable test scenarios."""

import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NS = "http://eviware.com/soapui/config"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
ET.register_namespace("con", NS)
ET.register_namespace("xsi", XSI)


def sub(parent, tag, text=None, **attributes):
    node = ET.SubElement(parent, f"{{{NS}}}{tag}", attributes)
    node.text = text
    return node


def assertion(request, kind, name, values=None):
    node = sub(request, "assertion", type=kind, name=name)
    config = sub(node, "configuration")
    for key, value in (values or {}).items():
        ET.SubElement(config, key).text = value


def xpath(request, expression, expected, name):
    assertion(
        request,
        "XPath Match",
        name,
        {
            "path": "declare namespace a='urn:qa:accounts:v1';\n" + expression,
            "content": str(expected),
            "allowWildcards": "false",
            "ignoreNamespaceDifferences": "false",
        },
    )


def soap_step(case, name, operation, fields, expected=None, fault=None):
    step = sub(case, "testStep", type="request", name=name)
    sub(step, "settings")
    config = sub(step, "config", **{f"{{{XSI}}}type": "con:RequestStep"})
    sub(config, "interface", "AccountsSoapBinding")
    sub(config, "operation", operation)
    request = sub(config, "request", name=name)
    sub(request, "settings")
    sub(request, "encoding", "UTF-8")
    sub(request, "endpoint", "${#Project#Endpoint}")
    body = "".join(f"<a:{key}>{value}</a:{key}>" for key, value in fields.items())
    sub(
        request,
        "request",
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" xmlns:a="urn:qa:accounts:v1"><s:Body>'
        + f"<a:{operation}Request>{body}</a:{operation}Request></s:Body></s:Envelope>",
    )
    assertion(request, "SOAP Response", "SOAP 1.1 response")
    assertion(request, "Schema Compliance", "Published WSDL response contract")
    assertion(
        request,
        "Valid HTTP Status Codes",
        "Expected HTTP status",
        {"codes": "500" if fault else "200"},
    )
    if fault:
        assertion(request, "Not SOAP Fault Assertion", "Expected SOAP fault")
        xpath(
            request,
            "//a:BusinessFault/a:code/text()",
            fault,
            "Exact business fault code",
        )
    else:
        assertion(request, "SOAP Fault Assertion", "No SOAP fault")
    for key, value in (expected or {}).items():
        xpath(request, f"//a:{operation}Response/a:{key}/text()", value, f"Exact {key}")
    sub(request, "credentials")
    return request


def account(case, key, balance, count):
    soap_step(
        case,
        f"Read {key} after operation",
        "GetAccount",
        {"accountId": key},
        {
            "accountId": key,
            "currency": "USD",
            "balance": balance,
            "transferCount": count,
        },
    )


def transfer(
    case,
    name="Transfer",
    amount="25.10",
    request_id="transfer-001",
    source="A100",
    destination="B200",
    currency="USD",
    fault=None,
    balances=("974.90", "275.10"),
):
    expected = (
        None
        if fault
        else {
            "requestId": request_id,
            "status": "COMPLETED",
            "fromBalance": balances[0],
            "toBalance": balances[1],
        }
    )
    soap_step(
        case,
        name,
        "Transfer",
        {
            "requestId": request_id,
            "fromAccount": source,
            "toAccount": destination,
            "amount": amount,
            "currency": currency,
        },
        expected,
        fault,
    )


def build():
    xsd = (ROOT / "service/accounts.xsd").read_text(encoding="utf-8").split("?>", 1)[1].strip()
    operations = ("GetAccount", "Transfer")
    messages = "".join(
        f'<wsdl:message name="{op}{direction}"><wsdl:part name="parameters" element="a:{op}{direction}"/></wsdl:message>'
        for op in operations
        for direction in ("Request", "Response")
    )
    port_ops = "".join(
        f'<wsdl:operation name="{op}"><wsdl:input message="a:{op}Request"/><wsdl:output message="a:{op}Response"/><wsdl:fault name="BusinessFault" message="a:BusinessFault"/></wsdl:operation>'
        for op in operations
    )
    binding_ops = "".join(
        f'<wsdl:operation name="{op}"><soap:operation soapAction="urn:qa:accounts:v1/{op}"/><wsdl:input><soap:body use="literal"/></wsdl:input><wsdl:output><soap:body use="literal"/></wsdl:output><wsdl:fault name="BusinessFault"><soap:fault name="BusinessFault" use="literal"/></wsdl:fault></wsdl:operation>'
        for op in operations
    )
    wsdl = f"""<?xml version="1.0" encoding="UTF-8"?>
<wsdl:definitions xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:a="urn:qa:accounts:v1" targetNamespace="urn:qa:accounts:v1" name="Accounts">
<wsdl:types>{xsd}</wsdl:types>{messages}
<wsdl:message name="BusinessFault"><wsdl:part name="fault" element="a:BusinessFault"/></wsdl:message>
<wsdl:portType name="AccountsPort">{port_ops}</wsdl:portType>
<wsdl:binding name="AccountsSoapBinding" type="a:AccountsPort"><soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>{binding_ops}</wsdl:binding>
<wsdl:service name="Accounts"><wsdl:port name="AccountsPort" binding="a:AccountsSoapBinding"><soap:address location="http://127.0.0.1:18081/accounts"/></wsdl:port></wsdl:service>
</wsdl:definitions>"""
    (ROOT / "service/accounts.wsdl").write_text(wsdl + "\n", encoding="utf-8")
    project = ET.Element(
        f"{{{NS}}}soapui-project",
        {
            "name": "Synthetic account transfers",
            "soapui-version": "5.10.0",
            "activeEnvironment": "Default",
        },
    )
    sub(project, "settings")
    interface = sub(
        project,
        "interface",
        name="AccountsSoapBinding",
        bindingName="{urn:qa:accounts:v1}AccountsSoapBinding",
        soapVersion="1_1",
        definition="../service/accounts.wsdl",
        **{f"{{{XSI}}}type": "con:WsdlInterface"},
    )
    sub(interface, "settings")
    cache = sub(interface, "definitionCache", type="TEXT", rootPart="../service/accounts.wsdl")
    part = sub(cache, "part")
    sub(part, "url", "../service/accounts.wsdl")
    sub(part, "content", wsdl)
    sub(part, "type", "http://schemas.xmlsoap.org/wsdl/")
    sub(sub(interface, "endpoints"), "endpoint", "http://127.0.0.1:18081/accounts")
    for op in operations:
        sub(
            interface,
            "operation",
            name=op,
            bindingOperationName=op,
            action=f"urn:qa:accounts:v1/{op}",
            isOneWay="false",
            type="Request-Response",
            receivesAttachments="false",
            sendsAttachments="false",
        )
    suite = sub(project, "testSuite", name="Account transfer integrity")
    sub(suite, "settings")

    def case(name):
        node = sub(
            suite,
            "testCase",
            name=name,
            failOnError="true",
            failTestCaseOnErrors="true",
            keepSession="false",
        )
        sub(node, "settings")
        return node

    c = case("SOAP-001 owner account contract")
    account(c, "A100", "1000.00", 0)
    account(c, "B200", "250.00", 0)
    c = case("SOAP-002 exact decimal transfer and conservation")
    transfer(c)
    account(c, "A100", "974.90", 1)
    account(c, "B200", "275.10", 1)
    c = case("SOAP-003 minimum cent transfer")
    transfer(c, amount="0.01", balances=("999.99", "250.01"))
    account(c, "A100", "999.99", 1)
    account(c, "B200", "250.01", 1)
    c = case("SOAP-004 full available balance transfer")
    transfer(c, amount="1000.00", balances=("0.00", "1250.00"))
    account(c, "A100", "0.00", 1)
    account(c, "B200", "1250.00", 1)
    c = case("SOAP-005 identical retry is not applied twice")
    transfer(c, name="Initial transfer")
    transfer(c, name="Retry same request")
    account(c, "A100", "974.90", 1)
    account(c, "B200", "275.10", 1)
    c = case("SOAP-006 conflicting retry preserves first transfer")
    transfer(c, name="Initial transfer")
    transfer(c, name="Retry changed amount", amount="30.00", fault="IDEMPOTENCY_CONFLICT")
    account(c, "A100", "974.90", 1)
    account(c, "B200", "275.10", 1)
    for number, title, options, code in [
        (7, "insufficient funds", {"amount": "1000.01"}, "INSUFFICIENT_FUNDS"),
        (8, "unknown destination", {"destination": "Z999"}, "ACCOUNT_NOT_FOUND"),
        (9, "same account", {"destination": "A100"}, "SAME_ACCOUNT"),
        (10, "unsupported currency", {"currency": "EUR"}, "UNSUPPORTED_CURRENCY"),
        (11, "zero amount violates XSD", {"amount": "0.00"}, "INVALID_REQUEST"),
        (12, "fractional cent violates XSD", {"amount": "1.001"}, "INVALID_REQUEST"),
        (13, "negative amount violates XSD", {"amount": "-1.00"}, "INVALID_REQUEST"),
    ]:
        c = case(f"SOAP-{number:03d} {title} leaves state unchanged")
        transfer(c, fault=code, **options)
        account(c, "A100", "1000.00", 0)
        account(c, "B200", "250.00", 0)
    # Each case owns its fixture; ordered request steps model a workflow, not inter-case dependence.
    for c in suite.findall(f"{{{NS}}}testCase"):
        sub(c, "properties")
        sub(
            c,
            "setupScript",
            """def endpoint = context.expand('${#Project#Endpoint}')
def url = new URL(endpoint)
assert url.host == '127.0.0.1' && url.protocol == 'http' : 'Owned loopback lab only'
def connection = new URL("http://127.0.0.1:${url.port}/__test/reset").openConnection()
connection.requestMethod = 'POST'
connection.connectTimeout = 5000
connection.readTimeout = 5000
assert connection.responseCode == 204 : 'Fixture reset failed'
connection.disconnect()""",
        )
    sub(suite, "properties")
    properties = sub(project, "properties")
    prop = sub(properties, "property")
    sub(prop, "name", "Endpoint")
    sub(prop, "value", "http://127.0.0.1:18081/accounts")
    ET.indent(project, space="  ")
    path = ROOT / "soapui/accounts-soapui-project.xml"
    path.parent.mkdir(exist_ok=True)
    ET.ElementTree(project).write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    build()
