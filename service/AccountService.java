import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.ByteArrayInputStream;
import java.math.BigDecimal;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

/** Original contract-first, in-memory teaching service. No production banking claim. */
public final class AccountService {
    static final String NS = "urn:qa:accounts:v1";
    static final String SOAP = "http://schemas.xmlsoap.org/soap/envelope/";
    private final Map<String, BigDecimal> balances = new HashMap<>();
    private final Map<String, Receipt> receipts = new HashMap<>();
    private final Schema schema;
    private final Path contractDirectory;
    private final boolean skipDebit;
    private record Receipt(String signature, String response) {}
    private static final class BusinessError extends RuntimeException {
        final String code;
        BusinessError(String code, String message) { super(message); this.code = code; }
    }

    private AccountService(Path directory, boolean skipDebit) throws Exception {
        contractDirectory = directory;
        this.skipDebit = skipDebit;
        SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
        factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        schema = factory.newSchema(directory.resolve("accounts.xsd").toFile());
        reset();
    }

    private synchronized void reset() {
        balances.clear(); receipts.clear();
        balances.put("A100", new BigDecimal("1000.00"));
        balances.put("B200", new BigDecimal("250.00"));
    }

    private static String field(Element root, String name) {
        return root.getElementsByTagNameNS(NS, name).item(0).getTextContent();
    }
    private static String element(String name, Object value) {
        String text = value.toString().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
        return "<a:" + name + ">" + text + "</a:" + name + ">";
    }
    private static String payload(String name, String content) {
        return "<a:" + name + " xmlns:a=\"" + NS + "\">" + content + "</a:" + name + ">";
    }
    private static String envelope(String content) {
        return "<s:Envelope xmlns:s=\"" + SOAP + "\"><s:Body>" + content + "</s:Body></s:Envelope>";
    }
    private static String fault(String code, String message) {
        return envelope("<s:Fault><faultcode>s:Client</faultcode><faultstring>Request rejected</faultstring><detail>"
                + payload("BusinessFault", element("code", code) + element("message", message)) + "</detail></s:Fault>");
    }

    private synchronized String dispatch(Element request) {
        if (request.getLocalName().equals("GetAccountRequest")) {
            String account = field(request, "accountId");
            if (!balances.containsKey(account)) throw new BusinessError("ACCOUNT_NOT_FOUND", "Account is not available");
            return payload("GetAccountResponse", element("accountId", account) + element("currency", "USD")
                    + element("balance", balances.get(account)) + element("transferCount", receipts.size()));
        }
        if (!request.getLocalName().equals("TransferRequest")) throw new BusinessError("INVALID_REQUEST", "Unknown operation");
        String id = field(request, "requestId"), from = field(request, "fromAccount"), to = field(request, "toAccount");
        BigDecimal amount = new BigDecimal(field(request, "amount")).setScale(2);
        String currency = field(request, "currency");
        String signature = from + ":" + to + ":" + amount.toPlainString() + ":" + currency;
        Receipt old = receipts.get(id);
        if (old != null) {
            if (!old.signature.equals(signature)) throw new BusinessError("IDEMPOTENCY_CONFLICT", "Request ID already used for different input");
            return old.response;
        }
        if (!balances.containsKey(from) || !balances.containsKey(to)) throw new BusinessError("ACCOUNT_NOT_FOUND", "Account is not available");
        if (from.equals(to)) throw new BusinessError("SAME_ACCOUNT", "Source and destination must differ");
        if (!currency.equals("USD")) throw new BusinessError("UNSUPPORTED_CURRENCY", "Only USD is supported");
        if (balances.get(from).compareTo(amount) < 0) throw new BusinessError("INSUFFICIENT_FUNDS", "Available balance is too low");
        // All checks precede mutation; synchronization keeps this in-memory transfer atomic.
        if (!skipDebit) balances.put(from, balances.get(from).subtract(amount));
        balances.put(to, balances.get(to).add(amount));
        String response = payload("TransferResponse", element("requestId", id) + element("status", "COMPLETED")
                + element("fromBalance", balances.get(from)) + element("toBalance", balances.get(to)));
        receipts.put(id, new Receipt(signature, response));
        return response;
    }

    private void handle(HttpExchange exchange) throws java.io.IOException {
        String route = exchange.getRequestURI().getPath();
        try {
            if (route.equals("/health") && exchange.getRequestMethod().equals("GET")) { send(exchange, 200, "text/plain", "ready"); return; }
            // Explicit disposable-lab control, never a production endpoint.
            if (route.equals("/__test/reset") && exchange.getRequestMethod().equals("POST")) { reset(); send(exchange, 204, "text/plain", ""); return; }
            if (exchange.getRequestMethod().equals("GET") && (route.equals("/accounts.xsd") || route.equals("/accounts"))) {
                String file = route.endsWith(".xsd") ? "accounts.xsd" : "accounts.wsdl";
                send(exchange, 200, "text/xml; charset=utf-8", Files.readString(contractDirectory.resolve(file))); return;
            }
            if (!route.equals("/accounts") || !exchange.getRequestMethod().equals("POST")) { send(exchange, 404, "text/plain", "Not found"); return; }
            byte[] bytes = exchange.getRequestBody().readNBytes(65537);
            if (bytes.length > 65536) { send(exchange, 413, "text/xml", fault("INVALID_REQUEST", "Request too large")); return; }
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
            Element root = factory.newDocumentBuilder().parse(new ByteArrayInputStream(bytes)).getDocumentElement();
            if (!SOAP.equals(root.getNamespaceURI()) || !"Envelope".equals(root.getLocalName())) throw new BusinessError("INVALID_REQUEST", "Expected SOAP 1.1 envelope");
            Element body = null;
            for (Node n = root.getFirstChild(); n != null; n = n.getNextSibling()) {
                if (n instanceof Element e && SOAP.equals(e.getNamespaceURI()) && "Body".equals(e.getLocalName())) {
                    if (body != null) throw new BusinessError("INVALID_REQUEST", "One body required");
                    body = e;
                }
            }
            if (body == null) throw new BusinessError("INVALID_REQUEST", "Body required");
            Element request = null;
            for (Node n = body.getFirstChild(); n != null; n = n.getNextSibling()) {
                if (n instanceof Element e) {
                    if (request != null) throw new BusinessError("INVALID_REQUEST", "One operation required");
                    request = e;
                }
            }
            if (request == null) throw new BusinessError("INVALID_REQUEST", "Operation required");
            try { schema.newValidator().validate(new DOMSource(request)); }
            catch (org.xml.sax.SAXException e) { throw new BusinessError("INVALID_REQUEST", "Payload violates the published XSD"); }
            String action = exchange.getRequestHeaders().getFirst("SOAPAction");
            String expected = "urn:qa:accounts:v1/" + request.getLocalName().replace("Request", "");
            if (action == null || !action.replace("\"", "").equals(expected)) throw new BusinessError("INVALID_ACTION", "SOAPAction does not match the operation");
            send(exchange, 200, "text/xml; charset=utf-8", envelope(dispatch(request)));
        } catch (BusinessError e) { send(exchange, 500, "text/xml; charset=utf-8", fault(e.code, e.getMessage())); }
        catch (org.xml.sax.SAXException e) { send(exchange, 500, "text/xml; charset=utf-8", fault("INVALID_REQUEST", "Malformed XML")); }
        catch (Exception e) { System.err.println("Service failure: " + e.getClass().getSimpleName()); send(exchange, 500, "text/xml", fault("INTERNAL_ERROR", "Unexpected service failure")); }
        finally { exchange.close(); }
    }
    private static void send(HttpExchange e, int status, String type, String content) throws java.io.IOException {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        e.getResponseHeaders().set("Content-Type", type);
        e.sendResponseHeaders(status, status == 204 ? -1 : bytes.length);
        if (status != 204) e.getResponseBody().write(bytes);
    }
    public static void main(String[] args) throws Exception {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 18081;
        AccountService app = new AccountService(Path.of("service"), Boolean.getBoolean("qa.skipDebit"));
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", port), 0);
        server.createContext("/", app::handle);
        server.setExecutor(Executors.newFixedThreadPool(4));
        Runtime.getRuntime().addShutdownHook(new Thread(() -> server.stop(0)));
        server.start();
        System.out.println("Synthetic account SOAP service ready on 127.0.0.1:" + port);
    }
}
