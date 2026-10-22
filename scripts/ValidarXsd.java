// Valida los XML de specs/ref/ contra los XSD oficiales de OASIS UBL 2.1 (SPEC-006 R-04).
// Uso: java scripts/ValidarXsd.java   (JDK 11+; descarga los XSD en .cache/ la primera vez)
import java.io.*;
import java.net.URI;
import java.net.http.*;
import java.nio.file.*;
import java.util.zip.*;
import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.*;
import org.xml.sax.SAXParseException;

public class ValidarXsd {
    static final String ZIP_URL = "https://docs.oasis-open.org/ubl/os-UBL-2.1/UBL-2.1.zip";
    static final Path CACHE = Path.of(".cache", "ubl-2.1");

    public static void main(String[] args) throws Exception {
        Path maindoc = CACHE.resolve("xsdrt/maindoc");
        if (!Files.exists(maindoc.resolve("UBL-Invoice-2.1.xsd"))) descargarXsd();

        SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
        int errores = 0, archivos = 0;
        try (DirectoryStream<Path> xmls = Files.newDirectoryStream(Path.of("specs", "ref"), "*.xml")) {
            for (Path xml : xmls) {
                archivos++;
                String raiz = raiz(xml);
                Schema schema = factory.newSchema(maindoc.resolve("UBL-" + raiz + "-2.1.xsd").toFile());
                // Los ejemplos no están firmados: la firma (ds:Signature) se inserta al firmar (SPEC-006).
                // Para validar la estructura se coloca un marcador en ext:ExtensionContent vacío.
                String contenido = Files.readString(xml);
                String sinFirma = contenido.replaceAll(
                    "(?s)<ext:ExtensionContent\\s*/>|<ext:ExtensionContent>\\s*(<!--.*?-->)?\\s*</ext:ExtensionContent>",
                    "<ext:ExtensionContent><f:FirmaPendiente xmlns:f=\"urn:abc:firma-pendiente\"/></ext:ExtensionContent>");
                String nota = sinFirma.equals(contenido) ? "" : " (estructura; firma pendiente)";
                try {
                    schema.newValidator().validate(new StreamSource(new StringReader(sinFirma)));
                    System.out.println("✓ " + xml.getFileName() + " cumple UBL-" + raiz + "-2.1.xsd" + nota);
                } catch (SAXParseException e) {
                    errores++;
                    System.out.println("✗ " + xml.getFileName() + " línea " + e.getLineNumber() + ": " + e.getMessage());
                }
            }
        }
        System.out.println(archivos - errores + "/" + archivos + " XML válidos contra el XSD oficial.");
        System.exit(errores == 0 ? 0 : 1);
    }

    /** Nombre local del elemento raíz (Invoice, CreditNote, DebitNote…). */
    static String raiz(Path xml) throws IOException {
        String txt = Files.readString(xml).replaceAll("(?s)<\\?.*?\\?>|<!--.*?-->", "");
        var m = java.util.regex.Pattern.compile("<\\s*(?:\\w+:)?(\\w+)").matcher(txt);
        if (!m.find()) throw new IOException("Sin elemento raíz: " + xml);
        return m.group(1);
    }

    static void descargarXsd() throws Exception {
        System.out.println("Descargando XSD oficiales de OASIS UBL 2.1…");
        Path zip = Files.createTempFile("ubl21", ".zip");
        HttpClient.newBuilder().followRedirects(HttpClient.Redirect.NORMAL).build()
            .send(HttpRequest.newBuilder(URI.create(ZIP_URL)).build(), HttpResponse.BodyHandlers.ofFile(zip));
        try (ZipInputStream in = new ZipInputStream(Files.newInputStream(zip))) {
            for (ZipEntry e; (e = in.getNextEntry()) != null; ) {
                if (e.isDirectory() || !e.getName().startsWith("xsdrt/")) continue;
                Path destino = CACHE.resolve(e.getName()).normalize();
                if (!destino.startsWith(CACHE)) continue;
                Files.createDirectories(destino.getParent());
                Files.copy(in, destino, StandardCopyOption.REPLACE_EXISTING);
            }
        }
        Files.delete(zip);
    }
}
