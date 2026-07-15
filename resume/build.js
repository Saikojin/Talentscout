#!/usr/bin/env node
/**
 * compiler/build.js
 * Compiles data/resume.json → dist/resume.md, dist/resume.html, (optionally) dist/resume.pdf
 * Usage:
 *   node compiler/build.js           → md + html
 *   node compiler/build.js --pdf     → md + html + pdf
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import { marked } from 'marked';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const DIST = resolve(ROOT, 'dist');
const PDF_MODE = process.argv.includes('--pdf');

const includeArg = process.argv.find(arg => arg.startsWith('--include='));
const excludeArg = process.argv.find(arg => arg.startsWith('--exclude='));
const includeFields = includeArg ? includeArg.split('=')[1].split(',') : null;
const excludeFields = excludeArg ? excludeArg.split('=')[1].split(',') : null;

function isFieldActive(fieldName) {
  if (includeFields && !includeFields.includes(fieldName)) return false;
  if (excludeFields && excludeFields.includes(fieldName)) return false;
  return true;
}

function ensureDist() {
  if (!existsSync(DIST)) mkdirSync(DIST, { recursive: true });
}

function loadResume() {
  const raw = readFileSync(resolve(ROOT, 'data', 'resume.json'), 'utf8');
  return JSON.parse(raw);
}

function formatDate(dateStr) {
  if (!dateStr) return 'Present';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
}

function buildMarkdown(r) {
  const lines = [];
  const { basics, work, education, skills, projects, awards, certificates, publications, languages, references, volunteer } = r;

  // Header
  lines.push(`# ${basics.name}`);
  if (basics.label) lines.push(`**${basics.label}**`);
  lines.push('');
  const contact = [basics.email, basics.phone, basics.url].filter(Boolean);
  if (contact.length) lines.push(contact.join(' · '));
  if (basics.location) {
    const loc = basics.location;
    const locStr = [loc.city, loc.region, loc.countryCode].filter(Boolean).join(', ');
    if (locStr) lines.push(locStr);
  }
  if (basics.profiles?.length) {
    const profiles = basics.profiles.map((p) => `[${p.network}](${p.url})`).join(' · ');
    lines.push(profiles);
  }
  lines.push('');

  // Summary
  if (basics.summary) {
    lines.push('## Summary');
    lines.push(basics.summary);
    lines.push('');
  }

  // Work
  if (work?.length) {
    lines.push('## Experience');
    for (const job of work) {
      const dates = `${formatDate(job.startDate)} – ${formatDate(job.endDate)}`;
      const jobLocation = job.location && isFieldActive('location') ? ` (${job.location})` : '';
      lines.push(`### ${job.position} · ${job.name}${jobLocation}`);
      lines.push(`*${dates}*`);
      if (job.summary) lines.push(job.summary);
      if (job.highlights?.length && isFieldActive('highlights')) {
        for (const h of job.highlights) lines.push(`- ${h}`);
      }
      if (job.keyResponsibilities?.length && isFieldActive('keyResponsibilities')) {
        lines.push('\n**Key Responsibilities:**');
        for (const r of job.keyResponsibilities) lines.push(`- ${r}`);
      }
      if (job.skillsUsed?.length && isFieldActive('skillsUsed')) {
        lines.push(`\n**Skills Used:** ${job.skillsUsed.join(', ')}`);
      }
      if (job.toolsUsed?.length && isFieldActive('toolsUsed')) {
        lines.push(`\n**Tools Used:** ${job.toolsUsed.join(', ')}`);
      }
      if (job.challenges?.length && isFieldActive('challenges')) {
        lines.push('\n**Challenges:**');
        for (const c of job.challenges) lines.push(`- ${c}`);
      }
      if (job.wins?.length && isFieldActive('wins')) {
        lines.push('\n**Wins:**');
        for (const w of job.wins) lines.push(`- ${w}`);
      }
      if (job.lessonsLearned?.length && isFieldActive('lessonsLearned')) {
        lines.push('\n**Lessons Learned:**');
        for (const l of job.lessonsLearned) lines.push(`- ${l}`);
      }
      lines.push('');
    }
  }

  // Education
  if (education?.length) {
    lines.push('## Education');
    for (const edu of education) {
      lines.push(`### ${edu.studyType} in ${edu.area} · ${edu.institution}`);
      const dates = `${formatDate(edu.startDate)} – ${formatDate(edu.endDate)}`;
      lines.push(`*${dates}*`);
      if (edu.score) lines.push(`GPA: ${edu.score}`);
      lines.push('');
    }
  }

  // Skills
  if (skills?.length) {
    lines.push('## Skills');
    for (const s of skills) {
      lines.push(`**${s.name}** *(${s.level})*: ${s.keywords?.join(', ')}`);
    }
    lines.push('');
  }

  // Projects
  if (projects?.length) {
    lines.push('## Projects');
    for (const p of projects) {
      lines.push(`### ${p.name}`);
      if (p.url) lines.push(`[${p.url}](${p.url})`);
      lines.push(p.description);
      if (p.highlights?.length) {
        for (const h of p.highlights) lines.push(`- ${h}`);
      }
      if (p.keywords?.length) lines.push(`*Tech: ${p.keywords.join(', ')}*`);
      lines.push('');
    }
  }

  // Awards
  if (awards?.length) {
    lines.push('## Awards');
    for (const a of awards) {
      lines.push(`- **${a.title}** (${a.awarder}, ${formatDate(a.date)}): ${a.summary}`);
    }
    lines.push('');
  }

  // Certificates
  if (certificates?.length) {
    lines.push('## Certifications');
    for (const c of certificates) {
      lines.push(`- **${c.name}** – ${c.issuer} (${formatDate(c.date)})`);
    }
    lines.push('');
  }

  // Publications
  if (publications?.length) {
    lines.push('## Publications');
    for (const pub of publications) {
      lines.push(`- **${pub.name}** – ${pub.publisher} (${formatDate(pub.releaseDate)})`);
      if (pub.summary) lines.push(`  ${pub.summary}`);
    }
    lines.push('');
  }

  // Volunteer
  if (volunteer?.length) {
    lines.push('## Volunteer');
    for (const v of volunteer) {
      lines.push(`- **${v.position}** at ${v.organization}: ${v.summary}`);
    }
    lines.push('');
  }

  // Languages
  if (languages?.length) {
    lines.push('## Languages');
    lines.push(languages.map((l) => `${l.language} (${l.fluency})`).join(', '));
    lines.push('');
  }

  // References
  if (references?.length) {
    lines.push('## References');
    for (const ref of references) {
      lines.push(`> "${ref.reference}"\n> — ${ref.name}`);
      lines.push('');
    }
  }

  return lines.join('\n');
}

function buildHtml(markdownContent, candidateName) {
  const bodyHtml = marked.parse(markdownContent);
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="description" content="Resume of ${candidateName}" />
  <title>${candidateName} — Resume</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: #1a1a2e;
      max-width: 860px;
      margin: 40px auto;
      padding: 0 24px;
      background: #fff;
    }
    h1 { font-size: 2rem; font-weight: 700; color: #0f3460; }
    h2 { font-size: 1.15rem; font-weight: 600; color: #16213e; margin-top: 2rem; border-bottom: 2px solid #e2e8f0; padding-bottom: 4px; }
    h3 { font-size: 1rem; font-weight: 600; margin-top: 1rem; color: #0f3460; }
    p, li { color: #374151; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    ul { padding-left: 1.25rem; }
    blockquote { border-left: 3px solid #e2e8f0; padding-left: 1rem; color: #6b7280; margin: 0.5rem 0; }
    strong { color: #1a1a2e; }
    em { color: #6b7280; }
    @media print {
      body { margin: 0; font-size: 11px; }
      h1 { font-size: 1.5rem; }
      h2 { margin-top: 1rem; }
    }
  </style>
</head>
<body>
${bodyHtml}
</body>
</html>`;
}

async function buildPdf(htmlPath, pdfPath) {
  const { default: puppeteer } = await import('puppeteer');
  const browser = await puppeteer.launch({ headless: 'new' });
  const page = await browser.newPage();
  const fileUrl = `file:///${htmlPath.replace(/\\/g, '/')}`;
  await page.goto(fileUrl, { waitUntil: 'networkidle0' });
  const pdfBuffer = await page.pdf({ format: 'Letter', margin: { top: '32px', right: '32px', bottom: '32px', left: '32px' } });
  await browser.close();
  writeFileSync(pdfPath, pdfBuffer);
  // Estimate page count (rough: ~700 bytes per page compressed)
  const estimatedPages = Math.ceil(pdfBuffer.length / 15000);
  return estimatedPages;
}

async function main() {
  ensureDist();
  const resume = loadResume();
  const candidateName = resume?.basics?.name ?? 'Unknown';

  console.log(`🔨  Building resume for: ${candidateName}`);

  // Markdown
  const md = buildMarkdown(resume);
  const mdPath = resolve(DIST, 'resume.md');
  writeFileSync(mdPath, md, 'utf8');
  console.log(`✅  dist/resume.md`);

  // HTML
  const html = buildHtml(md, candidateName);
  const htmlPath = resolve(DIST, 'resume.html');
  writeFileSync(htmlPath, html, 'utf8');
  console.log(`✅  dist/resume.html`);

  // PDF
  if (PDF_MODE) {
    const pdfPath = resolve(DIST, 'resume.pdf');
    try {
      const pages = await buildPdf(htmlPath, pdfPath);
      console.log(`✅  dist/resume.pdf  (estimated ${pages} page(s))`);
      if (pages > 2) {
        console.warn(`⚠️   PDF exceeds 2 pages (${pages} pages). Consider trimming.`);
      }
    } catch (err) {
      console.warn(`⚠️   PDF generation failed: ${err.message}`);
      console.warn('    Ensure puppeteer is installed and Chrome is available.');
    }
  }

  console.log('\n📋  Build summary:');
  console.log(`    Sections: ${Object.keys(resume).join(', ')}`);
  console.log(`    Work entries: ${resume.work?.length ?? 0}`);
  console.log(`    Skills: ${resume.skills?.length ?? 0}`);
  console.log(`    Projects: ${resume.projects?.length ?? 0}`);
}

main().catch((err) => {
  console.error('Build failed:', err.message);
  process.exit(1);
});
