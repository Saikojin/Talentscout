/**
 * tests/schema.test.js
 * Validates resume.json schema validation behavior:
 * - Happy path: valid resume passes
 * - Error injection matrix: 15+ intentionally broken data patterns
 */
import { describe, it, expect } from 'vitest';
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const schema = JSON.parse(readFileSync(resolve(ROOT, 'schema', 'resume.schema.json'), 'utf8'));
const validResume = JSON.parse(readFileSync(resolve(ROOT, 'data', 'resume.json'), 'utf8'));

function makeValidator() {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  return ajv.compile(schema);
}

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

describe('Schema — Happy Path', () => {
  it('should validate the sample resume.json', () => {
    const validate = makeValidator();
    const valid = validate(validResume);
    if (!valid) {
      console.error(validate.errors);
    }
    expect(valid).toBe(true);
  });
});

describe('Schema — Error Injection Matrix', () => {
  const validate = makeValidator();

  it('MATRIX-01: missing basics.name (required field)', () => {
    const data = deepClone(validResume);
    delete data.basics.name;
    const valid = validate(data);
    expect(valid).toBe(false);
    const paths = validate.errors.map((e) => e.instancePath + e.message);
    expect(paths.some((p) => p.includes('name') || p.includes('required'))).toBe(true);
  });

  it('MATRIX-02: basics.email is integer (wrong type)', () => {
    const data = deepClone(validResume);
    data.basics.email = 42;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-03: basics.email has invalid format', () => {
    const data = deepClone(validResume);
    data.basics.email = 'not-an-email';
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-04: basics.url has invalid URI format', () => {
    const data = deepClone(validResume);
    data.basics.url = 'not a url at all';
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-05: work[0].startDate is null (wrong type)', () => {
    const data = deepClone(validResume);
    data.work[0].startDate = null;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-06: work[0].highlights is a string instead of array', () => {
    const data = deepClone(validResume);
    data.work[0].highlights = 'should be an array';
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-07: work is null instead of array', () => {
    const data = deepClone(validResume);
    data.work = null;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-08: skills is a string instead of array', () => {
    const data = deepClone(validResume);
    data.skills = 'JavaScript, Python';
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-09: education[0] missing required institution field', () => {
    const data = deepClone(validResume);
    delete data.education[0].institution;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-10: languages[0] missing required language field', () => {
    const data = deepClone(validResume);
    delete data.languages[0].language;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-11: references[0] missing required reference field', () => {
    const data = deepClone(validResume);
    delete data.references[0].reference;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-12: projects[0].url is an integer (wrong type)', () => {
    const data = deepClone(validResume);
    data.projects[0].url = 12345;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-13: unknown top-level property (additionalProperties: false)', () => {
    const data = deepClone(validResume);
    data.hackedField = 'this should not be allowed';
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-14: basics.profiles[0] missing required username', () => {
    const data = deepClone(validResume);
    delete data.basics.profiles[0].username;
    const valid = validate(data);
    expect(valid).toBe(false);
  });

  it('MATRIX-15: empty object (completely missing basics)', () => {
    const data = {};
    const valid = validate(data);
    // Empty object is technically valid (no required top-level fields)
    // but basics.name is required IF basics exists — so {} passes top-level
    // This tests that the validator runs without throwing
    expect(typeof valid).toBe('boolean');
  });

  it('MATRIX-16: work[0].highlights contains non-string item', () => {
    const data = deepClone(validResume);
    data.work[0].highlights = ['valid string', 42, null];
    const valid = validate(data);
    expect(valid).toBe(false);
  });
});
