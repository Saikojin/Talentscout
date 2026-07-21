#!/usr/bin/env node
/**
 * scripts/export-clean-resume.js
 * Converts CleanResume.txt → resume JSON → dist/CleanResume.docx + dist/CleanResume.pdf
 * Usage: node scripts/export-clean-resume.js
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const DIST = resolve(ROOT, 'dist');
const SRC_TXT = 'C:\\Users\\saiko\\Documents\\Job docs\\resume stuff\\CleanResume.txt';

function ensureDist() {
  if (!existsSync(DIST)) mkdirSync(DIST, { recursive: true });
}

/**
 * Parse the plain-text resume into a JSON Resume schema object.
 * This is a hand-tuned parser for Thomas Snyder's CleanResume.txt format.
 */
function parseTxt(txt) {
  // Normalize line endings
  const lines = txt.replace(/\r\n/g, '\n').split('\n');

  const resume = {
    basics: {
      name: 'Thomas S. Snyder',
      label: 'Senior QA Engineer',
      email: 'Mr.Thomas.Snyder@gmail.com',
      phone: 'please email',
      url: 'https://www.linkedin.com/in/mr-thomas-snyder/',
      location: {
        address: '17325 NE 85th PL Apt C-105',
        postalCode: '98052',
        city: 'Redmond',
        countryCode: 'US',
        region: 'Washington',
      },
      profiles: [
        { network: 'LinkedIn', username: 'mr-thomas-snyder', url: 'https://www.linkedin.com/in/mr-thomas-snyder/' },
        { network: 'GitHub', username: 'Mr-Thomas-Snyder', url: 'https://github.com/Mr-Thomas-Snyder?tab=repositories' },
        { network: 'GitHub', username: 'Saikojin', url: 'https://github.com/Saikojin/seikoclaw-harness' },
        { network: 'Living Resume', username: 'TalentScout', url: 'https://saikojin.github.io/Talentscout/' },
      ],
      summary: lines
        .slice(5, 12)
        .filter(l => l.trim())
        .join(' '),
    },
    skills: parseSkills(lines),
    work: parseWork(lines),
  };

  return resume;
}

function parseSkills(lines) {
  const startIdx = lines.findIndex(l => l.includes('Skills Summary'));
  const endIdx = lines.findIndex(l => l.includes('Professional Experience'));
  if (startIdx === -1 || endIdx === -1) return [];
  const skillLines = lines
    .slice(startIdx + 1, endIdx)
    .map(l => l.trim())
    .filter(l => l.length > 0);
  return [{ name: 'Core QA Skills', level: 'Master', keywords: skillLines }];
}

function parseWork(lines) {
  const startIdx = lines.findIndex(l => l.includes('Professional Experience'));
  if (startIdx === -1) return [];

  const workLines = lines.slice(startIdx + 1);

  // Known company+location patterns in the file (order matters)
  const companyBlocks = [
    { name: 'Smartsheet', location: 'Seattle, WA', title: 'Senior QA', dates: '11/21 to 12/25' },
    { name: 'OpenMarket', location: 'Seattle, WA', title: 'Senior QA', dates: '01/19 to 06/21' },
    { name: 'Apptio', location: 'Bellevue, WA', title: 'Senior QA', dates: '04/18 to 12/18' },
    { name: 'Placed Inc.', location: 'Seattle, WA', title: 'STE', dates: '11/15 to 1/18' },
    { name: 'Array Health', location: 'Seattle, WA', title: 'STE', dates: '11/14 to 10/15' },
    { name: 'Microsoft', location: 'Redmond, WA', title: 'STE3 (Device & App Compatibility)', dates: '7/11 to 9/14' },
    { name: 'Microsoft', location: 'Redmond, WA', title: 'STE3 (Mobile Applications)', dates: '11/10 to 4/11' },
    { name: 'Hewlett-Packard', location: 'Bellevue, WA', title: 'Software/Hardware Engineer', dates: '1/09 to 9/10' },
    { name: 'Medio Systems', location: 'Seattle, WA', title: 'STE3', dates: '08/08 to 11/08' },
    { name: 'Microsoft', location: 'Redmond, WA', title: 'STE3 (Mobile Lync/Nokia)', dates: '11/07 to 6/08' },
    { name: 'AT&T Wireless', location: 'Redmond, WA', title: 'STE', dates: '08/07 to 11/07' },
    { name: 'Microsoft', location: 'Redmond, WA', title: 'STE2 (Windows Media Center)', dates: '08/06 to 08/07' },
    { name: 'NVIDIA', location: 'Redmond, WA', title: 'STE (Mobile Devices)', dates: '02/06 to 08/06' },
    { name: 'Microsoft', location: 'Redmond, WA', title: 'STE (Game Studios)', dates: '08/05 to 02/06' },
    { name: 'Monolith', location: 'Kirkland, WA', title: 'Bug Association Rep/Game Master', dates: '02/05 to 7/05' },
    { name: 'VMC Consulting', location: 'Redmond, WA', title: 'STE (Xbox)', dates: '08/01 to 01/05' },
    { name: 'Keane', location: 'Redmond, WA', title: 'Technical Support Representative', dates: '08/2000 to 06/01' },
    { name: 'Nintendo of America', location: 'Redmond, WA', title: 'QA Engineer', dates: '08/1999 to 03/2000' },
  ];

  // Extract block text between company headers
  const work = [];

  // Find each block by scanning for company name in the lines
  const companySearchPatterns = companyBlocks.map(c => ({
    ...c,
    pattern: c.name.toUpperCase().split(' ')[0], // e.g. "SMARTSHEET", "OPENMARKET"
  }));

  // Map company line indexes
  const headerIndexes = [];
  for (let i = 0; i < workLines.length; i++) {
    const upper = workLines[i].toUpperCase();
    for (const cb of companySearchPatterns) {
      // Use the first word of name as a strong enough anchor
      const key = cb.name.toUpperCase().replace(/[^A-Z]/g, '');
      if (upper.replace(/[^A-Z]/g, '').includes(key) && upper === upper.toUpperCase() && upper.trim().length > 3) {
        if (!headerIndexes.find(h => h.idx === i)) {
          headerIndexes.push({ idx: i, company: cb });
        }
        break;
      }
    }
  }

  // Build entries from blocks between headers
  for (let h = 0; h < headerIndexes.length; h++) {
    const { idx, company } = headerIndexes[h];
    const nextIdx = h + 1 < headerIndexes.length ? headerIndexes[h + 1].idx : workLines.length;
    const blockLines = workLines.slice(idx + 1, nextIdx).map(l => l.trim()).filter(l => l.length > 0);

    // Extract summary: first non-date paragraph
    const summaryLines = [];
    const highlights = [];
    let inHighlights = false;
    for (const l of blockLines) {
      if (l.startsWith('Results:') || l.startsWith('Responsibilities included:')) {
        inHighlights = true;
        continue;
      }
      if (inHighlights) {
        highlights.push(l.replace(/^[-•]\s*/, ''));
      } else if (!l.match(/^\d{2}\/\d{2}/) && !l.match(/^STE|^Senior|^Software|^Principal|^QA|^Bug|^Technical/)) {
        summaryLines.push(l);
      }
    }

    // Parse dates from company block
    const dateMatch = company.dates.match(/(\d{1,2})\/(\d{2,4}) to (\d{1,2})\/(\d{2,4})/);
    let startDate = null;
    let endDate = null;
    if (dateMatch) {
      const startMonth = dateMatch[1].padStart(2, '0');
      const startYear = dateMatch[2].length === 2 ? `20${dateMatch[2]}` : dateMatch[2];
      const endMonth = dateMatch[3].padStart(2, '0');
      const endYear = dateMatch[4].length === 2 ? `20${dateMatch[4]}` : dateMatch[4];
      startDate = `${startYear}-${startMonth}-01`;
      endDate = `${endYear}-${endMonth}-01`;
    }

    work.push({
      name: company.name,
      position: company.title,
      location: company.location,
      startDate,
      endDate,
      summary: summaryLines.join(' ').trim(),
      highlights: highlights.filter(h => h.length > 0),
    });
  }

  return work;
}

async function buildPdf(htmlContent, pdfPath) {
  const { default: puppeteer } = await import('puppeteer');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();

  // Write temp HTML file
  const tmpHtmlPath = resolve(DIST, '_clean_resume_tmp.html');
  writeFileSync(tmpHtmlPath, htmlContent, 'utf8');

  const fileUrl = `file:///${tmpHtmlPath.replace(/\\/g, '/')}`;
  await page.goto(fileUrl, { waitUntil: 'networkidle0' });
  const pdfBuffer = await page.pdf({
    format: 'Letter',
    margin: { top: '36px', right: '36px', bottom: '36px', left: '36px' },
  });
  await browser.close();
  writeFileSync(pdfPath, pdfBuffer);
  return Math.ceil(pdfBuffer.length / 15000);
}

function buildHtml(txt) {
  // Render the plain text in a nicely styled HTML shell for PDF export
  const escaped = txt
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  // Basic section detection for visual structure
  const htmlLines = escaped.split('\n').map(line => {
    const trimmed = line.trim();
    // Name line (first line)
    if (trimmed === 'THOMAS S. SNYDER') return `<h1>${trimmed}</h1>`;
    // All-caps section headers
    if (trimmed && trimmed === trimmed.toUpperCase() && trimmed.length > 5 && !trimmed.match(/^\d/)) {
      return `<h2>${trimmed}</h2>`;
    }
    // Section labels like "Value Summary:", "Skills Summary"
    if (trimmed.endsWith(':') && trimmed.length < 40) {
      return `<h3>${trimmed}</h3>`;
    }
    if (trimmed === '') return '<br/>';
    return `<p>${line}</p>`;
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Thomas S. Snyder — Resume</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
      font-size: 11px;
      line-height: 1.55;
      color: #1a1a2e;
      max-width: 820px;
      margin: 30px auto;
      padding: 0 28px;
      background: #fff;
    }
    h1 { font-size: 1.6rem; font-weight: 700; color: #0f3460; margin-bottom: 4px; }
    h2 { font-size: 1rem; font-weight: 700; color: #16213e; margin-top: 14px; margin-bottom: 3px;
         border-bottom: 1.5px solid #e2e8f0; padding-bottom: 3px; }
    h3 { font-size: 0.9rem; font-weight: 600; color: #0f3460; margin-top: 8px; }
    p { color: #374151; margin: 1px 0; }
    a { color: #2563eb; text-decoration: none; }
    @media print {
      body { margin: 0; font-size: 10px; }
      h1 { font-size: 1.3rem; }
    }
  </style>
</head>
<body>
${htmlLines.join('\n')}
</body>
</html>`;
}

async function main() {
  console.log('📄  Reading CleanResume.txt...');
  const txt = readFileSync(SRC_TXT, 'utf8');

  ensureDist();

  // ── DOCX ─────────────────────────────────────────────────────────────────
  console.log('📝  Parsing resume data...');
  const resumeJson = parseTxt(txt);

  const docxPath = resolve(DIST, 'CleanResume.docx');
  console.log('📦  Building DOCX...');
  try {
    const { buildDocx } = await import('../compiler/buildDocx.js');
    await buildDocx(resumeJson, docxPath);
    console.log(`✅  dist/CleanResume.docx`);
  } catch (err) {
    console.warn(`⚠️   DOCX generation failed: ${err.message}`);
    console.warn(err.stack);
  }

  // ── PDF ──────────────────────────────────────────────────────────────────
  const pdfPath = resolve(DIST, 'CleanResume.pdf');
  console.log('🖨️   Building PDF...');
  try {
    const html = buildHtml(txt);
    const pages = await buildPdf(html, pdfPath);
    console.log(`✅  dist/CleanResume.pdf  (estimated ${pages} page(s))`);
    if (pages > 3) {
      console.warn(`⚠️   PDF is ${pages} pages — consider trimming the source.`);
    }
  } catch (err) {
    console.warn(`⚠️   PDF generation failed: ${err.message}`);
    console.warn(err.stack);
  }

  console.log('\n✨  Done. Files written to resume/dist/');
}

main().catch(err => {
  console.error('Fatal error:', err.message);
  process.exit(1);
});
