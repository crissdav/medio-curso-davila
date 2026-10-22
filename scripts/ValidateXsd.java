// Validates the XML files in specs/ref/ against the official OASIS UBL 2.1 XSDs (SPEC-006 R-04).
// Usage: java scripts/ValidateXsd.java   (JDK 11+; downloads the XSDs into .cache/ the first time)
import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.zip.*;
import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.*;
import org.xml.sax.SAXParseException;

public class ValidateXsd {
    static final String ZIP_URL = "https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.zip";
    static final Path CACHE = Path.of(".cache", "ubl-2.1");

    public static void main(String[] args) throws Exception {
        Path maindoc = CACHE.resolve("xsdrt/maindoc");
        if (!Files.exists(maindoc.resolve("UBL-Invoice-2.1.xsd"))) downloadXsd();

        SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
        int errors = 0, files = 0;
        try (DirectoryStream<Path> xmls = Files.newDirectoryStream(Path.of("specs", "ref"), "*.xml")) {
            for (Path xml : xmls) {
                files++;
                String root = rootName(xml);
                Schema schema = factory.newSchema(maindoc.resolve("UBL-" + root + "-2.1.xsd").toFile());
                // The samples are not signed: the signature (ds:Signature) is inserted when signing (SPEC-006).
                // To validate the structure, a placeholder is put into an empty ext:ExtensionContent.
                String content = Files.readString(xml);
                String unsigned = content.replaceAll(
                    "(?s)<ext:ExtensionContent\\s*/>|<ext:ExtensionContent>\\s*(<!--.*?-->)?\\s*</ext:ExtensionContent>",
                    "<ext:ExtensionContent><s:SignaturePending xmlns:s=\"urn:abc:signature-pending\"/></ext:ExtensionContent>");
                String note = unsigned.equals(content) ? "" : " (structure; signature pending)";
                try {
                    schema.newValidator().validate(new StreamSource(new StringReader(unsigned)));
                    System.out.println("✓ " + xml.getFileName() + " complies with UBL-" + root + "-2.1.xsd" + note);
                } catch (SAXParseException e) {
                    errors++;
                    System.out.println("✗ " + xml.getFileName() + " line " + e.getLineNumber() + ": " + e.getMessage());
                }
            }
        }
        System.out.println(files - errors + "/" + files + " XML files valid against the official XSD.");
        System.exit(errors == 0 ? 0 : 1);
    }

    /** Local name of the root element (Invoice, CreditNote, DebitNote…). */
    static String rootName(Path xml) throws IOException {
        String text = Files.readString(xml).replaceAll("(?s)<\\?.*?\\?>|<!--.*?-->", "");
        var m = java.util.regex.Pattern.compile("<\\s*(?:\\w+:)?(\\w+)").matcher(text);
        if (!m.find()) throw new IOException("No root element: " + xml);
        return m.group(1);
    }

    static void downloadXsd() throws Exception {
        System.out.println("Downloading the official OASIS UBL 2.1 XSDs…");
        Path zip = Files.createTempFile("ubl21", ".zip");
        HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build()
            .send(HttpRequest.newBuilder(URI.create(ZIP_URL)).build(), HttpResponse.BodyHandlers.ofFile(zip));
        try (ZipInputStream in = new ZipInputStream(Files.newInputStream(zip))) {
            for (ZipEntry e; (e = in.getNextEntry()) != null; ) {
                if (e.isDirectory() || !e.getName().startsWith("xsdrt/")) continue;
                Path target = CACHE.resolve(e.getName()).normalize();
                if (!target.startsWith(CACHE)) continue;
                Files.createDirectories(target.getParent());
                Files.copy(in, target, StandardCopyOption.REPLACE_EXISTING);
            }
        }
        Files.delete(zip);
    }
}
