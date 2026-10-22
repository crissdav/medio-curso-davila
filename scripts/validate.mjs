// Validation of the Spec-First deliverable:
//  1. JSON Schemas compile and the examples comply with them.
//  2. Catalogs comply with their schema and match the enums of common.schema.json.
//  3. The invoice example matches the SPEC-003 calculation rules.
//  4. The traceability matrix only uses existing DTO paths and catalog codes.
//  5. Cited rules (SPEC-nnn R-nn / M-nn) exist and relative links resolve.
import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import Ajv2020 from 'ajv/dist/2020.js';
import addFormats from 'ajv-formats';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const p = (...s) => join(root, ...s);
const readJson = (f) => JSON.parse(readFileSync(f, 'utf8'));

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
];
for (const [name, data] of negatives) ok(!issue(data), `The schema should have rejected: ${name}`);
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
const r2 = (x) => Math.round((x + Number.EPSILON) * 100) / 100;
const f2 = (x) => r2(x).toFixed(2);
const resp = readJson(join(schemaDir, 'examples', 'invoice-response.json'));
let sumValue = 0, sumIsc = 0, sumIgvBase = 0, sumLineIgv = 0, sumIcbper = 0;
for (const l of resp.items) {
  const qty = Number(l.quantity), uv = Number(l.unitValue);
  const saleValue = r2(qty * uv - Number(l.discount ?? 0));
  let isc = 0;
  if (l.isc?.system === '01') isc = r2(saleValue * Number(l.isc.rate));
  if (l.isc?.system === '02') isc = r2(qty * Number(l.isc.fixedAmount));
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
const matrix = readFileSync(p('docs', '05-traceability-matrix.md'), 'utf8');
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
const noUbl = new Set(['id', 'status', 'sequenceNumber', 'series', 'ubigeo', 'email', 'fixedAmount', 'retailPrice', 'exportTotal']);
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
const specFiles = Object.fromEntries(readdirSync(p('specs', 'features')).map((f) => [f.slice(0, 3), readFileSync(p('specs', 'features', f), 'utf8')]));
for (const file of mdFiles) {
  const text = readFileSync(file, 'utf8');
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
  for (const m of readFileSync(f, 'utf8').matchAll(/SPEC-(\d{3})\/([RM]-\d{2})/g)) {
    ok(specFiles[m[1]]?.includes(`| ${m[2]} |`), `${f.replace(root, '')}: reference to non-existent SPEC-${m[1]}/${m[2]}`);
  }
}

// ---------- Result ----------
for (const w of warnings) console.warn(`⚠  ${w}`);
if (errors.length) {
  for (const e of errors) console.error(`✗ ${e}`);
  console.error(`\n${errors.length} error(s) in ${checks} checks.`);
  process.exit(1);
}
console.log(`✓ ${checks} checks passed (${rows.length} matrix rows, ${mdFiles.length} documents, ${Object.keys(schemas).length} schemas, ${Object.keys(catalogs).length} catalogs).`);
