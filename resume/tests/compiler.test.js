/**
 * tests/compiler.test.js
 * Verifies compiler output integrity:
 * - dist/resume.md contains candidate name
 * - dist/resume.html is valid HTML with candidate name
 * - Output contains no undefined/null literals
 */
import { describe, it, expect, beforeAll } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const resume = JSON.parse(readFileSync(resolve(ROOT, 'data', 'resume.json'), 'utf8'));
const candidateName = resume.basics.name;

describe('Compiler — Output Integrity', () => {
  beforeAll(() => {
    // Run the compiler before tests
    execSync('node compiler/build.js', { cwd: ROOT, stdio: 'pipe' });
  });

  it('dist/resume.md exists', () => {
    expect(existsSync(resolve(ROOT, 'dist', 'resume.md'))).toBe(true);
  });

  it('dist/resume.html exists', () => {
    expect(existsSync(resolve(ROOT, 'dist', 'resume.html'))).toBe(true);
  });

  it('resume.md contains candidate name', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.md'), 'utf8');
    expect(content).toContain(candidateName);
  });

  it('resume.html contains candidate name', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).toContain(candidateName);
  });

  it('resume.html contains <html> tag', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).toContain('<html');
  });

  it('resume.html contains <meta> description tag', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).toContain('<meta name="description"');
  });

  it('resume.html does not contain literal "undefined"', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).not.toContain('>undefined<');
    expect(content).not.toContain('undefined</');
  });

  it('resume.html does not contain literal "null"', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).not.toContain('>null<');
    expect(content).not.toContain('null</');
  });

  it('resume.md contains Experience section', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.md'), 'utf8');
    expect(content).toContain('## Experience');
  });

  it('resume.md contains Skills section', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.md'), 'utf8');
    expect(content).toContain('## Skills');
  });

  it('resume.md contains first employer name', () => {
    const firstEmployer = resume.work[0].name;
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.md'), 'utf8');
    expect(content).toContain(firstEmployer);
  });

  it('resume.html title matches candidate name', () => {
    const content = readFileSync(resolve(ROOT, 'dist', 'resume.html'), 'utf8');
    expect(content).toContain(`<title>${candidateName}`);
  });
});
