// SUNAT CONTENT layer on the XML files in specs/ref/ (the STRUCTURE layer is checked by ValidateXsd.java).
//  1. XML codes exist in the catalogs in specs/catalogs/ (T-nn rows of the matrix).
//  2. Peruvian rules: CustomizationID 2.0, F/B series, RUC modulus 11, invoice → customer with RUC.
//  3. Internal XML arithmetic (lines, taxes, totals).
//  4. If an equivalent JSON exists, the XML matches it field by field.
import { readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DOMParser } from '@xmldom/xmldom';
import xpath from 'xpath';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const refDir = join(root, 'specs', 'ref');
const select = xpath.useNamespaces({
  inv: 'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2',
  cac: 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
  cbc: 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
});
// XML → JSON equivalence (the other XML files in specs/ref/ are references without JSON).
const equivalents = { '20123456786-01-F001-123.xml': 'schemas/examples/invoice-response.json' };
// Third-party samples: their findings are reported but do not fail the validation.
const thirdParty = new Set(['sunat-factura-minima-ejemplo.xml']);

const catalogs = {};
for (const f of readdirSync(join(root, 'specs', 'catalogs'))) {
  const c = JSON.parse(readFileSync(join(root, 'specs', 'catalogs', f), 'utf8'));
  catalogs[c.number] = new Map(c.codes.map((x) => [x.code, x]));
}

const validRuc = (ruc) => {
  if (!/^(10|15|16|17|20)\d{9}$/.test(ruc)) return false;
  const sum = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2].reduce((s, w, i) => s + w * Number(ruc[i]), 0);
  const dv = (11 - (sum % 11)) % 10;
  return dv === Number(ruc[10]);
};
const num = (n) => Number(n?.textContent ?? n?.value ?? NaN);
const txt = (n) => (n?.textContent ?? n?.value ?? '').trim();
const r2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;
const equal = (a, b) => Math.abs(a - b) < 0.005;

let totalErrors = 0;
for (const file of readdirSync(refDir).filter((f) => f.endsWith('.xml')).sort()) {
  const doc = new DOMParser().parseFromString(readFileSync(join(refDir, file), 'utf8'), 'text/xml');
  const one = (xp, ctx = doc) => select(xp, ctx, true);
  const all = (xp, ctx = doc) => select(xp, ctx);
  const errors = [];
  const warnings = [];
  let checks = 0;
  const ok = (cond, msg) => { checks++; if (!cond) errors.push(msg); };
  const inCatalog = (cat, code, row) => ok(catalogs[cat]?.has(code), `${row}: "${code}" does not exist in catalog ${cat}`);

  // ---------- 1 and 2. SUNAT codes and rules ----------
  ok(txt(one('/inv:Invoice/cbc:UBLVersionID')) === '2.1', 'T-01: UBLVersionID must be 2.1');
  ok(txt(one('/inv:Invoice/cbc:CustomizationID')) === '2.0', 'T-02: CustomizationID must be 2.0 (SUNAT)');
  const number = txt(one('/inv:Invoice/cbc:ID'));
  ok(/^[FB][A-Z0-9]{3}-\d{1,8}$/.test(number), `T-05: "${number}" is not in SUNAT series-number format`);
  const type = txt(one('/inv:Invoice/cbc:InvoiceTypeCode'));
  inCatalog('01', type, 'T-08');
  inCatalog('51', txt(one('/inv:Invoice/cbc:InvoiceTypeCode/@listID')), 'T-09');
  ok(number[0] === catalogs['01'].get(type)?.seriesPrefix, `T-05/T-08: the series of ${number} does not match document type ${type}`);
  const currency = txt(one('/inv:Invoice/cbc:DocumentCurrencyCode'));
  inCatalog('02', currency, 'T-11');
  for (const n of all('//@currencyID')) ok(n.value === currency, `T-11: currencyID "${n.value}" differs from the document currency`);

  const issuer = one('/inv:Invoice/cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID');
  ok(txt(one('@schemeID', issuer)) === '6', 'T-12: the issuer must be identified by RUC (schemeID 6)');
  ok(validRuc(txt(issuer)), `T-12: issuer RUC ${txt(issuer)} fails modulus 11`);
  ok(txt(one('/inv:Invoice/cac:Signature/cac:SignatoryParty/cac:PartyIdentification/cbc:ID')) === txt(issuer), 'T-04: the signatory must be the issuer RUC');
  const customer = one('/inv:Invoice/cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID');
  const customerDocType = txt(one('@schemeID', customer));
  inCatalog('06', customerDocType, 'T-16');
  const pattern = catalogs['06'].get(customerDocType)?.pattern;
  if (pattern) ok(new RegExp(pattern).test(txt(customer)), `T-17: customer document "${txt(customer)}" does not match the catalog 06 pattern`);
  if (customerDocType === '6') ok(validRuc(txt(customer)), `T-17: customer RUC ${txt(customer)} fails modulus 11`);
  if (type === '01') ok(customerDocType === '6', 'SPEC-001 R-01: an invoice requires a customer with RUC');

  for (const ts of all('//cac:TaxScheme')) {
    const id = txt(one('cbc:ID', ts));
    inCatalog('05', id, 'T-24…T-29');
    const c = catalogs['05'].get(id);
    if (c) {
      ok(txt(one('cbc:Name', ts)) === c.name, `T-24…T-29: TaxScheme ${id} must be named ${c.name}`);
      ok(txt(one('cbc:TaxTypeCode', ts)) === c.internationalCode, `T-24…T-29: TaxScheme ${id} must have TaxTypeCode ${c.internationalCode}`);
    }
  }
  for (const n of all('//cbc:TaxExemptionReasonCode')) inCatalog('07', txt(n), 'T-49');
  for (const n of all('//cbc:TierRange')) inCatalog('08', txt(n), 'T-51');
  for (const n of all('//cbc:PriceTypeCode')) inCatalog('16', txt(n), 'T-43');
  for (const n of all('//cbc:InvoicedQuantity/@unitCode')) inCatalog('03', n.value, 'T-41');
  // ISC present ⇒ must declare its calculation system (catalog 08). Lines only.
  for (const sub of all('//cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID="2000"]')) {
    ok(one('cac:TaxCategory/cbc:TierRange', sub), 'T-51 / SPEC-003 R-05: line with ISC but without TierRange (catalog 08)');
  }
  if (!one('/inv:Invoice/cac:PaymentTerms[cbc:ID="FormaPago"]')) {
    warnings.push('T-20: payment terms (cac:PaymentTerms "FormaPago") missing, required by SUNAT since 2021 (RS 000193-2020)');
  }

  // ---------- 3. Internal arithmetic ----------
  const lines = all('/inv:Invoice/cac:InvoiceLine');
  let sumValue = 0;
  const byTax = {};
  for (const l of lines) {
    const id = txt(one('cbc:ID', l));
    const value = num(one('cbc:LineExtensionAmount', l));
    sumValue += value;
    ok(equal(value, r2(num(one('cbc:InvoicedQuantity', l)) * num(one('cac:Price/cbc:PriceAmount', l)))), `Line ${id}: LineExtensionAmount ≠ quantity × unit value (SPEC-003 R-01)`);
    const subs = all('cac:TaxTotal/cac:TaxSubtotal', l);
    ok(equal(num(one('cac:TaxTotal/cbc:TaxAmount', l)), subs.reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0)), `Line ${id}: TaxTotal ≠ Σ TaxSubtotal (T-55)`);
    const isc = subs.filter((x) => txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', x)) === '2000').reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0);
    for (const s of subs) {
      const tax = txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', s));
      byTax[tax] = (byTax[tax] ?? 0) + num(one('cbc:TaxAmount', s));
      if (tax === '1000') {
        ok(equal(num(one('cbc:TaxableAmount', s)), r2(value + isc)), `Line ${id}: IGV base ≠ sale value + ISC (SPEC-003 R-03)`);
        ok(equal(num(one('cbc:TaxAmount', s)), r2(num(one('cbc:TaxableAmount', s)) * num(one('cac:TaxCategory/cbc:Percent', s)) / 100)), `Line ${id}: IGV ≠ base × rate (SPEC-003 R-04)`);
      }
      if (tax === '7152') {
        ok(equal(num(one('cbc:TaxAmount', s)), r2(num(one('cbc:BaseUnitMeasure', s)) * num(one('cac:TaxCategory/cbc:PerUnitAmount', s)))), `Line ${id}: ICBPER ≠ bags × unit amount (SPEC-003 R-06)`);
      }
    }
  }
  const head = (xp) => num(one(`/inv:Invoice/${xp}`));
  ok(equal(head('cac:LegalMonetaryTotal/cbc:LineExtensionAmount'), r2(sumValue)), 'T-30: LineExtensionAmount ≠ Σ line sale values');
  const headSubs = all('/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal');
  ok(equal(head('cac:TaxTotal/cbc:TaxAmount'), headSubs.reduce((s, x) => s + num(one('cbc:TaxAmount', x)), 0)), 'T-23: TaxTotal ≠ Σ header TaxSubtotal');
  for (const s of headSubs) {
    const tax = txt(one('cac:TaxCategory/cac:TaxScheme/cbc:ID', s));
    const tolerance = tax === '1000' ? 1 : 0.005; // SPEC-003 R-09: ±1.00 between global IGV and Σ lines
    ok(Math.abs(num(one('cbc:TaxAmount', s)) - (byTax[tax] ?? 0)) <= tolerance, `T-24…T-29: total of tax ${tax} does not match Σ lines`);
  }
  ok(equal(head('cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount'), r2(head('cac:LegalMonetaryTotal/cbc:LineExtensionAmount') + head('cac:TaxTotal/cbc:TaxAmount'))), 'T-31: TaxInclusiveAmount ≠ sale value + taxes');
  ok(equal(head('cac:LegalMonetaryTotal/cbc:PayableAmount'), head('cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount')), 'T-34: PayableAmount ≠ TaxInclusiveAmount (no discounts or prepayments)');

  // ---------- 4. Cross-check with the equivalent JSON ----------
  if (equivalents[file]) {
    const j = JSON.parse(readFileSync(join(root, 'specs', equivalents[file]), 'utf8'));
    const t = j.totals;
    ok(number === `${j.series}-${j.sequenceNumber}`, `T-05: ${number} ≠ ${j.number} in the JSON`);
    ok(txt(one('/inv:Invoice/cbc:IssueDate')) === j.issueDate, 'T-06: date differs from the JSON');
    ok(type === j.documentType && currency === j.currency, 'T-08/T-11: type or currency differs from the JSON');
    ok(txt(issuer) === j.issuer.ruc && txt(customer) === j.customer.documentNumber, 'T-12/T-17: RUC differs from the JSON');
    ok(txt(one('/inv:Invoice/cbc:Note[@languageLocaleID="1000"]')) === t.amountInWords, 'T-10: amount in words differs from the JSON');
    ok(lines.length === j.items.length, 'T-40: number of lines differs from the JSON');
    const pairs = [
      ['cac:TaxTotal/cbc:TaxAmount', t.taxTotal, 'T-23'],
      ['cac:LegalMonetaryTotal/cbc:LineExtensionAmount', t.saleValueTotal, 'T-30'],
      ['cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount', t.salePriceTotal, 'T-31'],
      ['cac:LegalMonetaryTotal/cbc:PayableAmount', t.payableAmount, 'T-34'],
    ];
    for (const [xp, value, row] of pairs) ok(equal(head(xp), Number(value)), `${row}: ${xp} differs from the JSON (${value})`);
    for (const [tax, field] of [['1000', 'igvTotal'], ['2000', 'iscTotal'], ['7152', 'icbperTotal']]) {
      const n = one(`/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID="${tax}"]/cbc:TaxAmount`);
      ok(equal(num(n), Number(t[field])), `T-24…T-29: tax ${tax} differs from ${field} in the JSON`);
    }
    j.items.forEach((it, i) => {
      const l = lines[i];
      if (!l) return;
      const row = `Line ${it.lineNumber}`;
      ok(txt(one('cac:Item/cac:SellersItemIdentification/cbc:ID', l)) === it.productCode, `${row}: product code differs from the JSON (T-47)`);
      ok(equal(num(one('cbc:InvoicedQuantity', l)), Number(it.quantity)) && txt(one('cbc:InvoicedQuantity/@unitCode', l)) === it.unitOfMeasure, `${row}: quantity or unit differs from the JSON (T-41)`);
      ok(equal(num(one('cbc:LineExtensionAmount', l)), Number(it.saleValue)), `${row}: sale value differs from the JSON (T-42)`);
      ok(Math.abs(num(one('cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount', l)) - Number(it.unitPrice)) < 0.0001, `${row}: unit price differs from the JSON (T-43)`);
      ok(txt(one('.//cbc:TaxExemptionReasonCode', l)) === it.igvAffectation, `${row}: IGV affectation differs from the JSON (T-49)`);
      ok(txt(one('.//cbc:TierRange', l)) === (it.isc?.system ?? ''), `${row}: ISC system differs from the JSON (T-51)`);
      ok(equal(num(one('cac:TaxTotal/cbc:TaxAmount', l)), Number(it.totalTaxes)), `${row}: total taxes differ from the JSON (T-55)`);
    });
  }

  const isThirdParty = thirdParty.has(file);
  const mark = errors.length ? (isThirdParty ? '⚠' : '✗') : '✓';
  const note = equivalents[file] ? ' (includes JSON cross-check)' : isThirdParty ? ' (third-party sample, informational only)' : '';
  console.log(`${mark} ${file}: ${checks - errors.length}/${checks} SUNAT checks${note}`);
  for (const e of errors) console.log(`   ${isThirdParty ? '⚠' : '✗'} ${e}`);
  for (const w of warnings) console.log(`   ⚠ ${w}`);
  if (!isThirdParty) totalErrors += errors.length;
}
process.exit(totalErrors ? 1 : 0);
