#!/usr/bin/env node
/**
 * compiler/validate.js
 * Validates data/resume.json against schema/resume.schema.json using AJV.
 * Exit 0 on success, exit 1 on failure with human-readable error table.
 */
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const schemaPath = resolve(ROOT, 'schema', 'resume.schema.json');
const dataPath = resolve(ROOT, 'data', 'resume.json');

let schema, data;

try {
  schema = JSON.parse(readFileSync(schemaPath, 'utf8'));
} catch (err) {
  console.error(`❌  Failed to load schema: ${schemaPath}`);
  console.error(err.message);
  process.exit(1);
}

try {
  data = JSON.parse(readFileSync(dataPath, 'utf8'));
} catch (err) {
  console.error(`❌  Failed to load resume data: ${dataPath}`);
  console.error(err.message);
  process.exit(1);
}

const ajv = new Ajv({ allErrors: true, strict: false });
addFormats(ajv);

const validate = ajv.compile(schema);
const valid = validate(data);

if (valid) {
  console.log('✅  resume.json is valid against schema.');
  console.log(`    Candidate: ${data?.basics?.name ?? '(unknown)'}`);
  process.exit(0);
} else {
  console.error('❌  resume.json failed schema validation:\n');
  const rows = (validate.errors ?? []).map((e) => ({
    Path: e.instancePath || '(root)',
    Keyword: e.keyword,
    Message: e.message,
  }));
  // Print as a simple table
  const colWidths = { Path: 30, Keyword: 15, Message: 60 };
  const header = Object.keys(colWidths).map((k) => k.padEnd(colWidths[k])).join(' | ');
  const divider = Object.values(colWidths).map((w) => '-'.repeat(w)).join('-+-');
  console.error(header);
  console.error(divider);
  for (const row of rows) {
    const line = Object.entries(colWidths)
      .map(([k, w]) => String(row[k] ?? '').slice(0, w).padEnd(w))
      .join(' | ');
    console.error(line);
  }
  console.error(`\n${rows.length} error(s) found.`);

  try {
    const { logSchemaError } = await import('../lib/spacetime-client.js');
    const buildRunId = Date.now();
    for (const e of validate.errors ?? []) {
      logSchemaError(Date.now() + Math.floor(Math.random() * 1000), buildRunId, e.instancePath || '(root)', e.message || '');
    }
  } catch {}

  process.exit(1);
}
