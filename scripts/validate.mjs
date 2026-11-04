// Validation of the Spec-First deliverable:
//  1. JSON Schemas compile and the examples comply with them.
//  2. Catalogs comply with their schema and match the enums of common.schema.json.
//  3. The invoice example matches the SPEC-003 calculation rules.
//  4. The traceability matrix only uses existing DTO paths and catalog codes.
//  5. Cited rules (SPEC-nnn R-nn / M-nn) exist and relative links resolve.
//  6. PLE books: tables, unit mapping, formats 14.1 and 12.1 (matrix rows and sample files).
//  7. OpenAPI: every operation declares the reusable error responses.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';
import { parse as parseYaml } from 'yaml';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const p = (...s) => join(root, ...s);
// Line endings are normalized so results do not depend on CRLF checkouts (Windows).
const readText = (f) => readFileSync(f, 'utf8').replace(/\r\n/g, '\n');
const readJson = (f) => JSON.parse(readText(f));

const errors = [];
const warnings = [];
let checks = 0;
const ok = (cond, msg) => { checks++; if (!cond) errors.push(msg); };

// ---------- 1. Schemas and examples ----------
const ajv = new Ajv2020({ allErrors: true, strict: true, strictRequired: false, strictTypes: false });
addFormats(ajv);
const schemaDir = p('specs', 'schemas');
const schemas = {};
for (const f of readdirSync(schemaDir).filter((f) => f.endsWith('.schema.json'))) {
  schemas[f] = readJson(join(schemaDir, f));
  ajv.addSchema(schemas[f]);
}
const base = 'https://abc-software.pe/specs/schemas/';
for (const f of Object.keys(schemas)) {
  try { ajv.getSchema(base + f); checks++; } catch (e) { errors.push(`Schema ${f} does not compile: ${e.message}`); }
}

const examples = [
  ['invoice-request.json', 'invoice.schema.json#/$defs/IssueInvoiceRequest'],
  ['invoice-response.json', 'invoice.schema.json#/$defs/Invoice'],
  ['credit-note-request.json', 'note.schema.json'],
  ['legacy-movement.json', 'legacy-movement.schema.json'],
  ['inventory-movement.json', 'inventory-movement.schema.json'],
  ['ledger-sales-line.json', 'ledger.schema.json#/$defs/SalesRecordLine'],
  ['ledger-inventory-line.json', 'ledger.schema.json#/$defs/InventoryRecordLine'],
];
for (const [file, ref] of examples) {
  const validate = ajv.getSchema(base + ref);
  const valid = validate(readJson(join(schemaDir, 'examples', file)));
  ok(valid, `Example ${file} does not comply with ${ref}: ${ajv.errorsText(validate.errors)}`);
}

// Negative cases: the schema MUST reject them.
const req = readJson(join(schemaDir, 'examples', 'invoice-request.json'));
const issue = ajv.getSchema(base + 'invoice.schema.json#/$defs/IssueInvoiceRequest');
const negatives = [
  ['invoice with a DNI customer', { ...req, customer: { documentType: '1', documentNumber: '12345678', legalName: 'X' } }],
  ['invoice with a B series', { ...req, series: 'B001' }],
  ['USD without exchange rate', { ...req, currency: 'USD' }],
  ['credit without installments', { ...req, paymentTerms: { type: 'Credito' } }],
  ['ISC system 02 without fixed amount', { ...req, items: [{ ...req.items[1], isc: { system: '02' } }] }],
  ['non-existent affectation 99', { ...req, items: [{ ...req.items[0], igvAffectation: '99' }] }],
  ['amount as a number', { ...req, items: [{ ...req.items[0], unitValue: 20 }] }],
  ['free-of-charge line with a value', { ...req, items: [{ ...req.items[0], igvAffectation: '15', unitValue: '20.00', referenceUnitValue: '20.00' }] }],
  ['free-of-charge line without reference value', { ...req, items: [{ ...req.items[0], igvAffectation: '15', unitValue: '0' }] }],
  ['reference value on an onerous line', { ...req, items: [{ ...req.items[0], referenceUnitValue: '20.00' }] }],
];
for (const [name, data] of negatives) ok(!issue(data), `The schema should have rejected: ${name}`);
const salesLine = ajv.getSchema(base + 'ledger.schema.json#/$defs/SalesRecordLine');
const saleExample = readJson(join(schemaDir, 'examples', 'ledger-sales-line.json'));
ok(!salesLine({ ...saleExample, documentType: '07' }), 'The schema should have rejected a 14.1 credit note without modifiedDocument');
const { entryNumber: _unused, ...saleWithoutEntry } = saleExample;
ok(!salesLine({ ...saleWithoutEntry, status: '8' }), 'The schema should have rejected a 14.1 status 8 record without entryNumber');
const inventoryLine = ajv.getSchema(base + 'ledger.schema.json#/$defs/InventoryRecordLine');
const inventoryExample = readJson(join(schemaDir, 'examples', 'ledger-inventory-line.json'));
ok(!inventoryLine({ ...inventoryExample, unitOfMeasure: 'NIU' }), 'The schema should have rejected a 12.1 record with a UN/ECE unit instead of table 6');
const noteSchema = ajv.getSchema(base + 'note.schema.json');
const cn = readJson(join(schemaDir, 'examples', 'credit-note-request.json'));
ok(!noteSchema({ ...cn, documentType: '08', noteType: '05' }), 'The schema should have rejected a debit note with noteType 05 (not in catalog 10)');

// ---------- 2. Catalogs ----------
const catDir = p('specs', 'catalogs');
const catalogs = {};
const catValidate = ajv.getSchema(base + 'catalog.schema.json');
for (const f of readdirSync(catDir).filter((f) => f.endsWith('.json'))) {
  const c = readJson(join(catDir, f));
  ok(catValidate(c), `Catalog ${f} is invalid: ${ajv.errorsText(catValidate.errors)}`);
  catalogs[c.number] = new Set(c.codes.map((x) => x.code));
}
const defs = schemas['common.schema.json'].$defs;
const sameSet = (enumArr, set) => enumArr.length === set.size && enumArr.every((x) => set.has(x));
for (const [def, cat] of [['IgvAffectation', '07'], ['IscSystem', '08'], ['IdentityDocumentType', '06'], ['Currency', '02'], ['UnitOfMeasure', '03'], ['OperationType', '51']]) {
  ok(sameSet(defs[def].enum, catalogs[cat]), `Enum ${def} does not match catalog ${cat}`);
}
const noteEnums = schemas['note.schema.json'].allOf.map((a) => a.then.properties.noteType.enum);
ok(sameSet(noteEnums[0], catalogs['09']), 'noteType enum (07) does not match catalog 09');
ok(sameSet(noteEnums[1], catalogs['10']), 'noteType enum (08) does not match catalog 10');
const affectation = readJson(join(catDir, 'cat-07-igv-affectation.json'));
for (const c of affectation.codes) ok(catalogs['05'].has(c.tax), `Catalog 07 code ${c.code} points to a non-existent tax ${c.tax}`);

// ---------- 3. SPEC-003 arithmetic on the example ----------
const IGV_RATE = 0.18, ICBPER = 0.5;
const equalAmount = (a, b) => Math.abs(a - b) < 0.005;
const r2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;
const f2 = (x) => r2(x).toFixed(2);
const resp = readJson(join(schemaDir, 'examples', 'invoice-response.json'));
let sumValue = 0, sumIsc = 0, sumIgvBase = 0, sumLineIgv = 0, sumIcbper = 0;
for (const l of resp.items) {
  const qty = Number(l.quantity), uv = Number(l.unitValue);
  const saleValue = r2(qty * uv - Number(l.discount ?? 0));
  let isc = 0;
  if (l.isc?.system === '01') isc = r2(saleValue * Number(l.isc.rate));
  if (l.isc?.system === '02') isc = r2(qty * Number(l.isc.unitConversionFactor ?? 1) * Number(l.isc.fixedAmount));
  if (l.isc?.system === '03') isc = r2(qty * (Number(l.isc.retailPrice) / (1 + IGV_RATE)) * Number(l.isc.rate));
  const igvBase = r2(saleValue + isc);
  const igv = ['10', '17'].includes(l.igvAffectation) ? r2(igvBase * IGV_RATE) : 0;
  const icbper = r2((l.icbperBagCount ?? 0) * ICBPER);
  const line = `line ${l.lineNumber}`;
  ok(l.saleValue === f2(saleValue), `${line}: saleValue ${l.saleValue} ≠ ${f2(saleValue)} (SPEC-003 R-01)`);
  ok(l.iscAmount === f2(isc), `${line}: iscAmount ${l.iscAmount} ≠ ${f2(isc)} (SPEC-003 R-02)`);
  ok(l.igvBase === f2(igvBase), `${line}: igvBase ${l.igvBase} ≠ ${f2(igvBase)} (SPEC-003 R-03)`);
  ok(l.igv === f2(igv), `${line}: igv ${l.igv} ≠ ${f2(igv)} (SPEC-003 R-04)`);
  ok(l.icbper === f2(icbper), `${line}: icbper ${l.icbper} ≠ ${f2(icbper)} (SPEC-003 R-06)`);
  ok(l.totalTaxes === f2(isc + igv + icbper), `${line}: totalTaxes ${l.totalTaxes} ≠ ${f2(isc + igv + icbper)}`);
  const up = (saleValue + isc + igv) / qty;
  ok(Math.abs(Number(l.unitPrice) - up) < 0.0001, `${line}: unitPrice ${l.unitPrice} ≠ ${up} (SPEC-003 R-08)`);
  sumValue += saleValue; sumIsc += isc; sumIgvBase += igvBase; sumLineIgv += igv; sumIcbper += icbper;
}
const t = resp.totals;
const globalIgv = r2(sumIgvBase * IGV_RATE);
ok(t.taxedTotal === f2(sumValue), `taxedTotal ${t.taxedTotal} ≠ ${f2(sumValue)}`);
ok(t.iscTotal === f2(sumIsc), `iscTotal ${t.iscTotal} ≠ ${f2(sumIsc)}`);
ok(t.igvTotal === f2(globalIgv), `igvTotal ${t.igvTotal} ≠ ${f2(globalIgv)} (SPEC-003 R-09)`);
ok(Math.abs(globalIgv - sumLineIgv) <= 1, 'Σ line IGV differs from the global IGV by more than 1.00 (SPEC-003 R-09)');
ok(t.icbperTotal === f2(sumIcbper), `icbperTotal ${t.icbperTotal} ≠ ${f2(sumIcbper)}`);
ok(t.taxTotal === f2(sumIsc + globalIgv + sumIcbper), `taxTotal ${t.taxTotal} is wrong`);
ok(t.payableAmount === f2(sumValue + sumIsc + globalIgv + sumIcbper), `payableAmount ${t.payableAmount} ≠ ${f2(sumValue + sumIsc + globalIgv + sumIcbper)} (INV-04)`);
ok(t.salePriceTotal === t.payableAmount, 'salePriceTotal must equal payableAmount when there are no discounts or charges');

// RUC modulus 11 (SPEC-004 R-01) on the example RUCs.
const validRuc = (ruc) => {
  if (!/^(10|15|16|17|20)\d{9}$/.test(ruc)) return false;
  const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const sum = weights.reduce((s, w, i) => s + w * Number(ruc[i]), 0);
  let dv = 11 - (sum % 11);
  if (dv === 10) dv = 0;
  if (dv === 11) dv = 1;
  return dv === Number(ruc[10]);
};
ok(validRuc(resp.issuer.ruc), `Issuer RUC ${resp.issuer.ruc} fails modulus 11`);
ok(validRuc(resp.customer.documentNumber), `Customer RUC ${resp.customer.documentNumber} fails modulus 11`);
ok(validRuc('20123456786') && !validRuc('20123456787') && !validRuc('30123456786'), 'SPEC-004 AC-1/AC-2 cases do not hold');

// ---------- 4. Traceability matrix ----------
const roots = {
  Invoice: { file: 'invoice.schema.json', ptr: '#/$defs/Invoice' },
  IssuedNote: { file: 'note.schema.json', ptr: '#/$defs/IssuedNote' },
  SalesRecordLine: { file: 'ledger.schema.json', ptr: '#/$defs/SalesRecordLine' },
  InventoryRecordLine: { file: 'ledger.schema.json', ptr: '#/$defs/InventoryRecordLine' },
  Note: { file: 'note.schema.json', ptr: '#' },
  Product: { file: 'product.schema.json', ptr: '#' },
  Cdr: { file: 'cdr-response.schema.json', ptr: '#' },
  InventoryMovement: { file: 'inventory-movement.schema.json', ptr: '#' },
};
const deref = (file, ptr) => {
  let node = schemas[file];
  for (const seg of ptr.replace(/^#\/?/, '').split('/').filter(Boolean)) node = node[seg];
  return { file, node };
};
const follow = ({ file, node }) => {
  if (node?.$ref) {
    const [f, ptr = ''] = node.$ref.split('#');
    return follow(deref(f || file, '#' + ptr));
  }
  return { file, node };
};
// Visible properties of a node (follows $ref and allOf).
const propsOf = (ctx) => {
  const { file, node } = follow(ctx);
  const out = {};
  for (const [k, v] of Object.entries(node.properties ?? {})) out[k] = { file, node: v };
  for (const sub of node.allOf ?? []) Object.assign(out, propsOf({ file, node: sub }));
  return out;
};
const resolvePath = (path) => {
  const [rootName, ...segs] = path.split('.');
  if (!roots[rootName]) return false;
  let ctx = deref(roots[rootName].file, roots[rootName].ptr);
  for (const raw of segs) {
    const isArray = raw.endsWith('[]');
    const name = raw.replace('[]', '');
    const props = propsOf(ctx);
    if (!props[name]) return false;
    ctx = props[name];
    if (isArray) ctx = { file: follow(ctx).file, node: follow(ctx).node.items };
  }
  return true;
};
const matrix = readText(p('docs', '05-traceability-matrix.md'));
const rows = matrix.split('\n').filter((l) => /^\| \**T-\d{2}/.test(l));
ok(rows.length >= 50, `The matrix has only ${rows.length} T-nn rows`);
const ids = new Set();
for (const row of rows) {
  const cols = row.split(' | ');
  const id = cols[0].replace(/[|* ]/g, '');
  ok(!ids.has(id), `Duplicate row in the matrix: ${id}`);
  ids.add(id);
  for (const m of cols[2].matchAll(/`cat-(\d{2}):([^`]+)`/g)) {
    ok(catalogs[m[1]]?.has(m[2]), `${id}: code cat-${m[1]}:${m[2]} does not exist in specs/catalogs`);
  }
  for (const m of cols[5].matchAll(/`([A-Za-z]+\.[A-Za-z.\[\]]+)`/g)) {
    ok(resolvePath(m[1]), `${id}: DTO path ${m[1]} does not exist in the JSON Schemas`);
  }
  ok(/^\d{3}$/.test(cols[6].replace(/[| ]/g, '')), `${id}: invalid spec "${cols[6]}"`);
}
// Coverage (warnings): Invoice leaves without a matrix row.
// Fields justified in section 10 of the matrix; `cdr.*` is covered by the Cdr rows (T-70…T-72).
const noUbl = new Set(['id', 'status', 'sequenceNumber', 'series', 'ubigeo', 'email', 'fixedAmount', 'unitConversionFactor', 'retailPrice', 'exportTotal', 'exchangeRate', 'referenceUnitValue']);
const noUblSubtrees = ['cdr.', 'links.'];
const used = new Set([...matrix.matchAll(/`Invoice\.([A-Za-z.\[\]]+)`/g)].map((m) => m[1].split('.').pop().replace('[]', '')));
const leaves = (ctx, prefix, depth = 0) => {
  if (depth > 4) return [];
  return Object.entries(propsOf(ctx)).flatMap(([k, v]) => {
    const n = follow(v).node;
    if (n.type === 'array' && n.items) return leaves({ file: follow(v).file, node: n.items }, `${prefix}${k}[].`, depth + 1);
    if (n.properties || n.allOf) return leaves(v, `${prefix}${k}.`, depth + 1);
    return [`${prefix}${k}`];
  });
};
for (const h of leaves(deref('invoice.schema.json', '#/$defs/Invoice'), '')) {
  const leaf = h.split('.').pop().replace('[]', '');
  if (noUblSubtrees.some((s) => h.startsWith(s))) continue;
  if (!used.has(leaf) && !noUbl.has(leaf)) warnings.push(`Field Invoice.${h} has no matrix row`);
}

// ---------- 5. Rule references and links ----------
const mdFiles = [];
const walk = (dir) => {
  for (const f of readdirSync(dir)) {
    if (f === 'node_modules' || f.startsWith('.')) continue;
    const full = join(dir, f);
    if (statSync(full).isDirectory()) walk(full);
    else if (f.endsWith('.md')) mdFiles.push(full);
  }
};
walk(root);
const specFiles = Object.fromEntries(readdirSync(p('specs', 'features')).map((f) => [f.slice(0, 3), readText(p('specs', 'features', f))]));
for (const file of mdFiles) {
  const text = readText(file);
  for (const m of text.matchAll(/SPEC-(\d{3})(?:\/| )([RM]-\d{2})/g)) {
    ok(specFiles[m[1]]?.includes(`| ${m[2]} |`), `${file.replace(root, '')}: reference to non-existent SPEC-${m[1]} ${m[2]}`);
  }
  for (const m of text.matchAll(/\]\(([^)#\s]+)(#[^)]*)?\)/g)) {
    if (/^(https?:|mailto:)/.test(m[1])) continue;
    ok(existsSync(resolve(dirname(file), m[1])), `${file.replace(root, '')}: broken link → ${m[1]}`);
  }
}
for (const [num, text] of Object.entries(specFiles)) {
  ok(/\*\*AC-1:\*\*/.test(text), `SPEC-${num} has no acceptance criteria`);
}
// Rule references from the schemas and openapi must exist as well.
for (const f of [...Object.keys(schemas).map((s) => join(schemaDir, s)), p('specs', 'api', 'openapi.yaml')]) {
  for (const m of readText(f).matchAll(/SPEC-(\d{3})\/([RM]-\d{2})/g)) {
    ok(specFiles[m[1]]?.includes(`| ${m[2]} |`), `${f.replace(root, '')}: reference to non-existent SPEC-${m[1]}/${m[2]}`);
  }
}

// ---------- 6. PLE books ----------
const tableDir = p('specs', 'ple-tables');
const pleTables = {};
for (const f of readdirSync(tableDir).filter((f) => f.startsWith('table-'))) {
  const c = readJson(join(tableDir, f));
  ok(catValidate(c), `PLE table ${f} is invalid: ${ajv.errorsText(catValidate.errors)}`);
  pleTables[c.number] = new Set(c.codes.map((x) => x.code));
}
for (const [def, table] of [['PleIdentityDocumentType', '02'], ['ExistenceType', '05'], ['PleUnitOfMeasure', '06'], ['PleDocumentType', '10'], ['InventoryOperationType', '12']]) {
  ok(sameSet(defs[def].enum, pleTables[table]), `Enum ${def} does not match PLE table ${table}`);
}
const unitMap = new Map(readJson(join(tableDir, 'unit-mapping-cat03-to-table06.json')).mappings.map((m) => [m.catalog03, m]));
ok(sameSet([...unitMap.keys()], catalogs['03']), 'The unit mapping must cover exactly the catalog 03 codes');
for (const m of unitMap.values()) {
  if (m.table06 === null) ok(m.catalog03 === 'ZZ', `Only services may lack a table 6 code: ${m.catalog03}`);
  else ok(pleTables['06'].has(m.table06) && Number(m.factor) > 0, `Invalid unit mapping for ${m.catalog03}`);
}

// Matrix rows: V-01…V-35 (format 14.1) and K-01…K-19 (format 12.1).
for (const [prefix, count, rootName] of [['V', 35, 'SalesRecordLine'], ['K', 19, 'InventoryRecordLine']]) {
  const bookRows = matrix.split('\n').filter((l) => new RegExp(`^\\| ${prefix}-\\d{2} `).test(l));
  ok(bookRows.length === count, `Matrix must have ${count} ${prefix}-nn rows, found ${bookRows.length}`);
  const seen = new Set();
  bookRows.forEach((row, i) => {
    const cols = row.split(' | ');
    const expected = `${prefix}-${String(i + 1).padStart(2, '0')}`;
    ok(cols[0] === `| ${expected}`, `Matrix row out of order: ${cols[0]} (expected ${expected})`);
    for (const m of cols[2].matchAll(/`table-(\d{2}):([^`]+)`/g)) {
      ok(pleTables[m[1]]?.has(m[2]), `${expected}: code table-${m[1]}:${m[2]} does not exist in specs/ple-tables`);
    }
    for (const m of cols[4].matchAll(/`([A-Za-z]+\.[A-Za-z.\[\]]+)`/g)) {
      ok(resolvePath(m[1]), `${expected}: DTO path ${m[1]} does not exist in the JSON Schemas`);
      if (m[1].startsWith(`${rootName}.`)) seen.add(m[1].split('.')[1]);
    }
  });
  for (const field of Object.keys(propsOf(deref(roots[rootName].file, roots[rootName].ptr)))) {
    if (field === 'balance') continue; // Printed-format column; not part of the TXT.
    ok(seen.has(field), `${rootName}.${field} has no ${prefix}-nn matrix row`);
  }
}

// Sample files: name, layout and consistency with the invoice example.
const pleDir = p('specs', 'ref', 'ple');
const pleFiles = readdirSync(pleDir);
const bookFile = (code) => pleFiles.find((f) => f.includes(`00${code}00`));
const NAME = /^LE\d{11}\d{6}00(120100|140100)00[012][01][12][12]\.TXT$/;
for (const f of pleFiles) ok(NAME.test(f), `PLE file name does not follow the nomenclature: ${f}`);
const rowsOf = (f) => readText(join(pleDir, f)).split('\n').filter(Boolean).map((l) => {
  ok(l.endsWith('|'), `${f}: records must end with the field separator`);
  return l.slice(0, -1).split('|');
});
const salesRows = rowsOf(bookFile('140100'));
const sv = salesRows[0];
ok(sv.length === 35, `Format 14.1 must have 35 fields, found ${sv.length}`);
const sumFields = [13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24].reduce((s, n) => s + Number(sv[n - 1]), 0);
ok(equalAmount(sumFields, Number(sv[24])), 'Format 14.1: amount fields do not add up to field 25 (total)');
for (const [fieldNo, value] of [[1, saleExample.period], [2, saleExample.cuo], [14, t.taxedTotal], [16, t.igvTotal], [20, t.iscTotal], [23, t.icbperTotal], [25, t.payableAmount], [26, resp.currency], [35, saleExample.status]]) {
  ok(sv[fieldNo - 1] === value, `Format 14.1 field ${fieldNo}: "${sv[fieldNo - 1]}" differs from "${value}"`);
}
ok(saleExample.taxableBase === t.taxedTotal && saleExample.total === t.payableAmount, 'ledger-sales-line.json differs from invoice-response.json');
ok(sv[5] === resp.documentType && `${sv[6]}-${sv[7]}` === `${resp.series}-${resp.sequenceNumber}`, 'Format 14.1 document differs from invoice-response.json');
const inventoryRows = rowsOf(bookFile('120100'));
let stock = 0;
for (const r of inventoryRows) {
  ok(r.length === 19, `Format 12.1 must have 19 fields, found ${r.length}`);
  ok(pleTables['05'].has(r[5]), `Format 12.1 field 6: ${r[5]} not in table 5`);
  ok(pleTables['10'].has(r[10]), `Format 12.1 field 11: ${r[10]} not in table 10`);
  ok(pleTables['12'].has(r[13]), `Format 12.1 field 14: ${r[13]} not in table 12`);
  ok(pleTables['06'].has(r[15]), `Format 12.1 field 16: ${r[15]} not in table 6`);
  ok(Number(r[17]) <= 0, `Format 12.1 field 18: exits must be negative or 0.00, found ${r[17]}`);
  ok(Number(r[16]) === 0 || Number(r[17]) === 0, 'Format 12.1: entries and exits are mutually exclusive');
  if (['01', '02', '03', '04', '05', '06'].includes(r[13])) ok(r[10] !== '00', 'Format 12.1: field 11 cannot be 00 for operations 01–06');
  stock += Number(r[16]) + Number(r[17]);
}
ok(inventoryRows[0][13] === '16', 'Format 12.1: the first record must be the opening balance (table 12 code 16)');
ok(equalAmount(stock, Number(inventoryExample.balance)), `Format 12.1: resulting stock ${stock} differs from the example balance ${inventoryExample.balance}`);
const beer = resp.items.find((l) => l.productCode === inventoryExample.productCode);
ok(Number(inventoryExample.exits) === -Number(beer.quantity) * Number(unitMap.get(beer.unitOfMeasure).factor), 'ledger-inventory-line.json exits do not match the invoice quantity');
ok(inventoryExample.unitOfMeasure === unitMap.get(beer.unitOfMeasure).table06, 'ledger-inventory-line.json unit does not match the unit mapping');

// ---------- 7. OpenAPI error responses ----------
const api = parseYaml(readText(p('specs', 'api', 'openapi.yaml')));
let operations = 0;
for (const [path, item] of Object.entries(api.paths)) {
  for (const [method, op] of Object.entries(item)) {
    operations++;
    const isPublic = Array.isArray(op.security) && op.security.length === 0;
    const required = isPublic ? ['429', '503'] : ['401', '403', '429', '503'];
    for (const code of required) ok(op.responses[code], `${method.toUpperCase()} ${path} does not declare ${code}`);
    if (op.requestBody) ok(op.responses['400'], `${method.toUpperCase()} ${path} has a body but does not declare 400`);
    for (const r of Object.values(op.responses)) {
      for (const media of Object.values(r.content ?? {})) ok(!media.schema?.contentEncoding, `${method.toUpperCase()} ${path} uses contentEncoding on a binary response`);
    }
  }
}
ok(api.components.responses.TooManyRequests.headers?.['Retry-After'], 'TooManyRequests must declare Retry-After');
ok(rows.find((r) => r.startsWith('| T-44')).includes('`Invoice.items[].unitPrice`'), 'T-44 must map the reference value to unitPrice');

// ---------- Result ----------
for (const w of warnings) console.warn(`⚠  ${w}`);
if (errors.length) {
  for (const e of errors) console.error(`✗ ${e}`);
  console.error(`\n${errors.length} error(s) in ${checks} checks.`);
  process.exit(1);
}
console.log(`✓ ${checks} checks passed (${rows.length} + 54 matrix rows, ${mdFiles.length} documents, ${Object.keys(schemas).length} schemas, ${Object.keys(catalogs).length} catalogs, ${Object.keys(pleTables).length} PLE tables, ${operations} API operations).`);
