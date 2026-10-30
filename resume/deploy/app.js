/**
 * web/app.js
 * TalentScout — Dynamic Resume Portfolio
 *
 * Responsibilities:
 * 1. Loads resume.json and renders all sections dynamically.
 * 2. Manages the Focus Selector (All/Frontend/Backend/Leadership/Open Source).
 * 3. Applies micro-animation highlighting/dimming to sections/cards by tag relevance.
 * 4. Content Filter Panel — toggle chips to show/hide individual work sub-fields.
 * 5. Filtered client-side exports:
 *    - PDF  → window.print() (filtered DOM, @media print CSS cleans up chrome)
 *    - MD   → generated in-browser from live data + active fields → Blob download
 *    - DOCX → generated in-browser via docx library (CDN) + active fields → Blob download
 * 6. Manages toast notifications.
 */

'use strict';

// ─── Configuration ────────────────────────────────────────────────────────────
const MCP_URL     = window.__RESUME_CONFIG__?.mcpUrl !== undefined
                    ? window.__RESUME_CONFIG__.mcpUrl
                    : 'http://localhost:3001/mcp';
const RESUME_PATH = window.__RESUME_CONFIG__?.resumePath ?? './data/resume.json';

// ─── Focus Tags ───────────────────────────────────────────────────────────────
// Each key maps to a list of tags that will *match* when scanning work/skill cards.
// We include both the canonical focus-area tags AND the natural domain tags that
// were already present in the resume.json so older entries still light up.
const FOCUS_TAGS = {
  all:           null,   // No filtering
  frontend:      ['frontend', 'web', 'drupal'],
  backend:       ['backend', 'api', 'devops', 'aws', 'sms', 'linux'],
  leadership:    ['leadership', 'process'],
  'open-source': ['open-source'],
};

// ─── Content Filter Fields ────────────────────────────────────────────────────
// Each entry defines a chip in the Content Filter bar and the DOM/data field it controls.
const CONTENT_FIELDS = [
  { key: 'highlights',        label: 'Highlights' },
  { key: 'keyResponsibilities', label: 'Responsibilities' },
  { key: 'skillsUsed',        label: 'Skills Used' },
  { key: 'toolsUsed',         label: 'Tools Used' },
  { key: 'challenges',        label: 'Challenges' },
  { key: 'wins',              label: 'Wins' },
  { key: 'lessonsLearned',    label: 'Lessons Learned' },
];

// Active field state — all on by default
const activeFields = new Set(CONTENT_FIELDS.map((f) => f.key));

// ─── Utility Helpers ──────────────────────────────────────────────────────────
function el(tag, attrs = {}, ...children) {
  const elem = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') elem.className = v;
    else if (k === 'html') elem.innerHTML = v;
    else elem.setAttribute(k, v);
  }
  for (const child of children) {
    if (child) elem.appendChild(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return elem;
}

function text(str) { return document.createTextNode(str || ''); }

function formatDate(dateStr) {
  if (!dateStr) return 'Present';
  const match = dateStr.match(/^(\d{4})-(\d{2})/);
  if (!match) return dateStr;
  try {
    return new Date(Number(match[1]), Number(match[2]) - 1, 1)
      .toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  } catch { return dateStr; }
}

function initials(name) {
  return (name || '?').split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase();
}

function safeFilename(name) {
  return (name || 'Resume').replace(/\s+/g, '_');
}

// ─── Toast System ─────────────────────────────────────────────────────────────
const toastContainer = el('div', { id: 'toast-container', role: 'status', 'aria-live': 'polite' });

function showToast(message, type = 'success', duration = 3000) {
  const icons = { success: '✅', warning: '⚠️', info: 'ℹ️' };
  const toast = el('div', { class: `toast toast-${type}` });
  toast.appendChild(text(`${icons[type] || '✅'} ${message}`));
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('hiding');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Focus Selector State ─────────────────────────────────────────────────────
let activeFocus = 'all';

function applyFocus(focusKey) {
  activeFocus = focusKey;
  const tags = FOCUS_TAGS[focusKey];

  document.querySelectorAll('.resume-section[data-tags]').forEach((section) => {
    const sectionTags = JSON.parse(section.dataset.tags || '[]');
    const relevant = !tags || tags.some((t) => sectionTags.includes(t));
    section.classList.toggle('section--dimmed', !relevant);
    section.classList.toggle('section--highlighted', relevant && focusKey !== 'all');
  });

  document.querySelectorAll('.card[data-tags], .skill-card[data-tags]').forEach((card) => {
    const cardTags = JSON.parse(card.dataset.tags || '[]');
    const relevant = !tags || tags.some((t) => cardTags.includes(t));
    card.classList.toggle('highlighted-card', relevant && focusKey !== 'all');
  });

  document.querySelectorAll('.focus-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.focus === focusKey);
    btn.setAttribute('aria-pressed', btn.dataset.focus === focusKey);
  });
}

// ─── Content Filter Logic ─────────────────────────────────────────────────────
/**
 * Show or hide .work-sub-section elements whose h4 data-field matches a toggled field.
 * We use data-field attributes set during renderWorkCard to avoid fragile text matching.
 */
function applyContentFilter() {
  document.querySelectorAll('.work-sub-section[data-field]').forEach((div) => {
    const field = div.dataset.field;
    div.style.display = activeFields.has(field) ? '' : 'none';
  });

  // Also toggle highlights ul (which has no wrapper div, just a ul with data-field)
  document.querySelectorAll('.card-highlights[data-field]').forEach((ul) => {
    const field = ul.dataset.field;
    ul.style.display = activeFields.has(field) ? '' : 'none';
  });
}

// ─── Rendering ────────────────────────────────────────────────────────────────
function renderHero(basics) {
  const avatar = el('div', { class: 'hero-avatar', 'aria-hidden': 'true' });
  avatar.textContent = initials(basics.name);

  const name = el('h1', { class: 'hero-name' });
  name.textContent = basics.name;

  const label = el('p', { class: 'hero-label' });
  label.textContent = basics.label || '';

  const contact = el('div', { class: 'hero-contact' });
  if (basics.email) {
    const a = el('a', { href: `mailto:${basics.email}`, 'aria-label': `Email ${basics.email}` });
    a.textContent = `✉ ${basics.email}`;
    contact.appendChild(a);
  }
  if (basics.phone) {
    const s = el('span', { 'aria-label': `Phone ${basics.phone}` });
    s.textContent = `📞 ${basics.phone}`;
    contact.appendChild(s);
  }
  if (basics.location?.city) {
    const s = el('span');
    const loc = [basics.location.city, basics.location.region].filter(Boolean).join(', ');
    s.textContent = `📍 ${loc}`;
    contact.appendChild(s);
  }
  if (basics.profiles?.length) {
    for (const profile of basics.profiles) {
      const a = el('a', { href: profile.url, target: '_blank', rel: 'noopener noreferrer' });
      const icons = { GitHub: '🐙', LinkedIn: '💼', Twitter: '🐦' };
      a.textContent = `${icons[profile.network] || '🔗'} ${profile.network}`;
      contact.appendChild(a);
    }
  }

  const hero = el('header', { class: 'hero', role: 'banner' });
  hero.append(avatar, name, label, contact);
  return hero;
}

// ─── Filtered Markdown Generator ──────────────────────────────────────────────
function buildFilteredMarkdown(resume) {
  const lines = [];
  const { basics, work, education, skills, projects, languages, references } = resume;
  const has = (field) => activeFields.has(field);

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
    lines.push(basics.profiles.map((p) => `[${p.network}](${p.url})`).join(' · '));
  }
  lines.push('');

  if (basics.summary) {
    lines.push('## Summary');
    lines.push(basics.summary);
    lines.push('');
  }

  if (work?.length) {
    lines.push('## Experience');
    for (const job of work) {
      const dates = `${formatDate(job.startDate)} – ${formatDate(job.endDate)}`;
      lines.push(`### ${job.position} · ${job.name}`);
      lines.push(`*${dates}*`);
      if (job.summary) lines.push(job.summary);
      if (job.highlights?.length && has('highlights')) {
        for (const h of job.highlights) lines.push(`- ${h}`);
      }
      if (job.keyResponsibilities?.length && has('keyResponsibilities')) {
        lines.push('\n**Key Responsibilities:**');
        for (const r of job.keyResponsibilities) lines.push(`- ${r}`);
      }
      if (job.skillsUsed?.length && has('skillsUsed')) {
        lines.push(`\n**Skills Used:** ${job.skillsUsed.join(', ')}`);
      }
      if (job.toolsUsed?.length && has('toolsUsed')) {
        lines.push(`\n**Tools Used:** ${job.toolsUsed.join(', ')}`);
      }
      if (job.challenges?.length && has('challenges')) {
        lines.push('\n**Challenges:**');
        for (const c of job.challenges) lines.push(`- ${c}`);
      }
      if (job.wins?.length && has('wins')) {
        lines.push('\n**Wins:**');
        for (const w of job.wins) lines.push(`- ${w}`);
      }
      if (job.lessonsLearned?.length && has('lessonsLearned')) {
        lines.push('\n**Lessons Learned:**');
        for (const l of job.lessonsLearned) lines.push(`- ${l}`);
      }
      lines.push('');
    }
  }

  if (education?.length) {
    lines.push('## Education');
    for (const edu of education) {
      lines.push(`### ${edu.studyType} in ${edu.area} · ${edu.institution}`);
      lines.push(`*${formatDate(edu.startDate)} – ${formatDate(edu.endDate)}*`);
      if (edu.score) lines.push(`GPA: ${edu.score}`);
      lines.push('');
    }
  }

  if (skills?.length) {
    lines.push('## Skills');
    for (const s of skills) {
      lines.push(`**${s.name}** *(${s.level})*: ${s.keywords?.join(', ')}`);
    }
    lines.push('');
  }

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

  if (languages?.length) {
    lines.push('## Languages');
    lines.push(languages.map((l) => `${l.language} (${l.fluency})`).join(', '));
    lines.push('');
  }

  if (references?.length) {
    lines.push('## References');
    for (const ref of references) {
      lines.push(`> "${ref.reference}"\n> — ${ref.name}`);
      lines.push('');
    }
  }

  return lines.join('\n');
}

// ─── Filtered DOCX Generator (browser-side via docx CDN) ─────────────────────
const DOCX_CDN = 'https://esm.sh/docx@9';
let _docxLib = null;

async function loadDocxLib() {
  if (_docxLib) return _docxLib;
  // Import via dynamic ESM; the CDN build exposes a named export `docx`
  try {
    const mod = await import(/* webpackIgnore: true */ DOCX_CDN);
    // jsdelivr CDN build may be CJS-wrapped; try common access patterns
    _docxLib = mod.default ?? mod.docx ?? mod;
    return _docxLib;
  } catch (e) {
    throw new Error(`Could not load docx library from CDN: ${e.message}`);
  }
}

async function buildFilteredDocx(resume) {
  const lib = await loadDocxLib();
  const {
    Document, Packer, Paragraph, TextRun, HeadingLevel,
    AlignmentType, BorderStyle,
  } = lib;

  const { basics, work, education, skills, projects, references } = resume;
  const has = (field) => activeFields.has(field);
  const children = [];

  const addSectionHeading = (title) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 280, after: 120 },
        border: { bottom: { color: 'cccccc', space: 4, style: BorderStyle.SINGLE, size: 6 } },
        children: [
          new TextRun({ text: title.toUpperCase(), bold: true, size: 22, font: 'Arial', color: '1a1a2e' }),
        ],
      })
    );
  };

  const addBullet = (txt) => {
    children.push(
      new Paragraph({
        bullet: { level: 0 },
        spacing: { after: 40 },
        children: [new TextRun({ text: txt, size: 20, font: 'Arial' })],
      })
    );
  };

  const addSubSection = (label, items) => {
    if (!items?.length) return;
    children.push(
      new Paragraph({
        spacing: { before: 100, after: 40 },
        children: [new TextRun({ text: `${label}:`, bold: true, size: 20, font: 'Arial', color: '333333' })],
      })
    );
    for (const item of items) addBullet(item);
  };

  const addChipLine = (label, items) => {
    if (!items?.length) return;
    children.push(
      new Paragraph({
        spacing: { before: 100, after: 60 },
        children: [
          new TextRun({ text: `${label}: `, bold: true, size: 20, font: 'Arial' }),
          new TextRun({ text: items.join(' · '), size: 20, font: 'Arial', color: '444444' }),
        ],
      })
    );
  };

  // Header
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [new TextRun({ text: basics.name, bold: true, size: 36, font: 'Arial', color: '0f3460' })],
    })
  );
  if (basics.label) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [new TextRun({ text: basics.label, italics: true, size: 20, font: 'Arial', color: '555555' })],
      })
    );
  }

  const contactParts = [];
  if (basics.email) contactParts.push(basics.email);
  if (basics.phone && basics.phone !== 'please email') contactParts.push(basics.phone);
  if (basics.location) {
    const lp = [basics.location.city, basics.location.region].filter(Boolean);
    if (lp.length) contactParts.push(lp.join(', '));
  }
  if (basics.url) contactParts.push(basics.url);
  if (contactParts.length) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 300 },
        children: [new TextRun({ text: contactParts.join('  |  '), size: 18, font: 'Arial', color: '444444' })],
      })
    );
  }

  // Summary
  if (basics.summary) {
    addSectionHeading('Summary');
    children.push(
      new Paragraph({
        spacing: { after: 200 },
        children: [new TextRun({ text: basics.summary, size: 20, font: 'Arial' })],
      })
    );
  }

  // Experience
  if (work?.length) {
    addSectionHeading('Professional Experience');
    for (const job of work) {
      const startFmt = job.startDate ? job.startDate.slice(0, 7).replace('-', '/') : '';
      const endFmt   = job.endDate   ? job.endDate.slice(0, 7).replace('-', '/')   : 'Present';

      children.push(
        new Paragraph({
          spacing: { before: 160, after: 40 },
          tabStops: [{ type: 'right', position: 9020 }],
          children: [
            new TextRun({ text: `${job.name}  —  ${job.position}`, bold: true, size: 22, font: 'Arial', color: '0f3460' }),
            new TextRun({ text: `\t${startFmt} – ${endFmt}`, size: 18, font: 'Arial', color: '666666' }),
          ],
        })
      );

      if (job.summary) {
        children.push(
          new Paragraph({
            spacing: { after: 80 },
            children: [new TextRun({ text: job.summary, size: 19, font: 'Arial', italics: true, color: '444444' })],
          })
        );
      }

      if (has('highlights'))          for (const h of (job.highlights || []))      addBullet(h);
      if (has('keyResponsibilities')) addSubSection('Key Responsibilities', job.keyResponsibilities);
      if (has('skillsUsed'))          addChipLine('Skills Used', job.skillsUsed);
      if (has('toolsUsed'))           addChipLine('Tools Used', job.toolsUsed);
      if (has('challenges'))          addSubSection('Challenges', job.challenges);
      if (has('wins'))                addSubSection('Wins', job.wins);
      if (has('lessonsLearned'))      addSubSection('Lessons Learned', job.lessonsLearned);

      children.push(new Paragraph({ spacing: { after: 80 } }));
    }
  }

  // Skills
  if (skills?.length) {
    addSectionHeading('Skills Summary');
    for (const skill of skills) {
      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [
            new TextRun({ text: `${skill.name}: `, bold: true, size: 20, font: 'Arial' }),
            new TextRun({ text: skill.keywords?.join(', ') || '', size: 20, font: 'Arial' }),
          ],
        })
      );
    }
  }

  // Projects
  if (projects?.length) {
    addSectionHeading('Projects');
    for (const project of projects) {
      const urlText = project.url ? ` (${project.url})` : '';
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [new TextRun({ text: `${project.name}${urlText}`, bold: true, size: 20, font: 'Arial', color: '0f3460' })],
        })
      );
      if (project.description) {
        children.push(
          new Paragraph({
            spacing: { after: 80 },
            children: [new TextRun({ text: project.description, size: 20, font: 'Arial' })],
          })
        );
      }
      if (project.highlights?.length) {
        for (const h of project.highlights) addBullet(h);
      }
    }
  }

  // Education
  if (education?.length) {
    addSectionHeading('Education');
    for (const edu of education) {
      const startFmt = edu.startDate ? edu.startDate.slice(0, 7).replace('-', '/') : '';
      const endFmt   = edu.endDate   ? edu.endDate.slice(0, 7).replace('-', '/')   : 'Present';
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          tabStops: [{ type: 'right', position: 9020 }],
          children: [
            new TextRun({ text: `${edu.institution}  —  ${edu.studyType} in ${edu.area}`, bold: true, size: 20, font: 'Arial' }),
            new TextRun({ text: `\t${startFmt} – ${endFmt}`, size: 18, font: 'Arial', color: '666666' }),
          ],
        })
      );
    }
  }

  // References
  if (references?.length) {
    addSectionHeading('References');
    for (const ref of references) {
      children.push(
        new Paragraph({
          spacing: { before: 80, after: 40 },
          children: [new TextRun({ text: `"${ref.reference}"`, size: 19, font: 'Arial', italics: true, color: '444444' })],
        })
      );
      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [new TextRun({ text: `— ${ref.name}`, size: 18, font: 'Arial', bold: true })],
        })
      );
    }
  }

  const doc = new Document({
    creator: basics.name,
    title: `${basics.name} — Resume`,
    styles: {
      default: { document: { run: { font: 'Arial', size: 20 } } },
    },
    sections: [{
      properties: { page: { margin: { top: 720, right: 900, bottom: 720, left: 900 } } },
      children,
    }],
  });

  return await Packer.toBuffer(doc);
}

// ─── Action Bar ───────────────────────────────────────────────────────────────
let _resumeData = null; // Set after load so download buttons can access it

function renderActionBar(basics) {
  const bar = el('div', { class: 'action-bar', role: 'toolbar', 'aria-label': 'Resume actions' });

  // PDF — window.print() respects the current filtered DOM + @media print CSS
  const pdfBtn = el('button', {
    class: 'btn btn-primary',
    type: 'button',
    id: 'btn-download-pdf',
    'aria-label': 'Download resume as PDF',
    title: 'Prints only the currently visible fields',
  });
  pdfBtn.innerHTML = '⬇ Download PDF';
  pdfBtn.addEventListener('click', () => {
    showToast('Opening print dialog — choose "Save as PDF" to export', 'info', 4000);
    setTimeout(() => window.print(), 200);
  });

  // Markdown — generated client-side from live data + active fields
  const mdBtn = el('button', {
    class: 'btn btn-secondary',
    type: 'button',
    id: 'btn-download-md',
    'aria-label': 'Download resume as Markdown',
    title: 'Downloads only the currently visible fields',
  });
  mdBtn.innerHTML = '📄 Download Markdown';
  mdBtn.addEventListener('click', () => {
    if (!_resumeData) { showToast('Resume data not loaded yet', 'warning'); return; }
    try {
      const md = buildFilteredMarkdown(_resumeData);
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeFilename(basics.name)}_Resume.md`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
      showToast('Markdown downloaded with active fields', 'success');
    } catch (err) {
      showToast(`Markdown export failed: ${err.message}`, 'warning');
    }
  });

  // DOCX — generated client-side via docx CDN library + active fields
  const docxBtn = el('button', {
    class: 'btn btn-secondary',
    type: 'button',
    id: 'btn-download-docx',
    'aria-label': 'Download resume as Word Document',
    title: 'Downloads only the currently visible fields',
  });
  docxBtn.innerHTML = '📝 Download DOCX';
  docxBtn.addEventListener('click', async () => {
    if (!_resumeData) { showToast('Resume data not loaded yet', 'warning'); return; }
    docxBtn.disabled = true;
    docxBtn.innerHTML = '⏳ Generating…';
    try {
      const buffer = await buildFilteredDocx(_resumeData);
      // Convert ArrayBuffer/Buffer to Blob
      const blob = new Blob([buffer], {
        type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${safeFilename(basics.name)}_Resume.docx`;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
      showToast('DOCX downloaded with active fields', 'success');
    } catch (err) {
      showToast(`DOCX export failed: ${err.message}`, 'warning', 6000);
      console.error('DOCX error:', err);
    } finally {
      docxBtn.disabled = false;
      docxBtn.innerHTML = '📝 Download DOCX';
    }
  });

  // MCP Button
  if (MCP_URL) {
    const mcpBtn = el('button', {
      class: 'btn btn-mcp',
      id: 'btn-mcp',
      type: 'button',
      'aria-label': 'Copy MCP server URL to clipboard',
      title: `Copy MCP URL: ${MCP_URL}`,
    });
    mcpBtn.innerHTML = '🔌 Plug into MCP';
    mcpBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(MCP_URL);
        showToast(`MCP URL copied! ${MCP_URL}`, 'success');
        mcpBtn.innerHTML = '✅ Copied!';
        setTimeout(() => { mcpBtn.innerHTML = '🔌 Plug into MCP'; }, 2000);
      } catch {
        showToast('Could not copy — MCP URL: ' + MCP_URL, 'warning', 5000);
      }
    });
    bar.append(pdfBtn, mdBtn, docxBtn, mcpBtn);
  } else {
    const mcpLink = el('a', {
      class: 'btn btn-mcp',
      id: 'btn-mcp',
      href: 'https://github.com/Saikojin/Talentscout#readme',
      target: '_blank',
      rel: 'noopener noreferrer',
      'aria-label': 'Learn about MCP server integration',
      title: 'MCP server runs locally — see README for setup',
    });
    mcpLink.innerHTML = '🔌 MCP Integration ↗';
    bar.append(pdfBtn, mdBtn, docxBtn, mcpLink);
  }
  return bar;
}

function renderFocusSelector() {
  const wrap = el('div', { class: 'focus-selector-wrap', role: 'navigation', 'aria-label': 'Focus selector' });
  const label = el('p', { class: 'focus-selector-label' });
  label.textContent = 'Focus Area';
  const selector = el('div', { class: 'focus-selector', role: 'group', 'aria-label': 'Select focus area' });

  const focuses = [
    { key: 'all', label: '🌐 All' },
    { key: 'frontend', label: '🖥 Frontend' },
    { key: 'backend', label: '⚙️ Backend' },
    { key: 'leadership', label: '🏆 Leadership' },
    { key: 'open-source', label: '🔓 Open Source' },
  ];

  for (const { key, label: focusLabel } of focuses) {
    const btn = el('button', {
      class: `focus-btn${key === 'all' ? ' active' : ''}`,
      'data-focus': key,
      type: 'button',
      'aria-pressed': key === 'all' ? 'true' : 'false',
      id: `focus-${key}`,
    });
    btn.textContent = focusLabel;
    btn.addEventListener('click', () => applyFocus(key));
    selector.appendChild(btn);
  }

  wrap.append(label, selector);
  return wrap;
}

// ─── Content Filter Panel ─────────────────────────────────────────────────────
function renderContentFilter() {
  const wrap = el('div', {
    class: 'content-filter-wrap',
    role: 'group',
    'aria-label': 'Content filter',
    id: 'content-filter',
  });

  const label = el('p', { class: 'content-filter-label' });
  label.textContent = 'Show in Work History';

  const chipsRow = el('div', { class: 'content-filter-chips' });

  for (const { key, label: chipLabel } of CONTENT_FIELDS) {
    const chip = el('button', {
      class: 'filter-chip',
      type: 'button',
      'data-field': key,
      'aria-pressed': 'true',
      id: `chip-${key}`,
      'aria-label': `Toggle ${chipLabel} visibility`,
    });
    chip.appendChild(text(chipLabel));

    chip.addEventListener('click', () => {
      if (activeFields.has(key)) {
        activeFields.delete(key);
        chip.classList.add('chip--off');
        chip.setAttribute('aria-pressed', 'false');
      } else {
        activeFields.add(key);
        chip.classList.remove('chip--off');
        chip.setAttribute('aria-pressed', 'true');
      }
      applyContentFilter();
    });

    chipsRow.appendChild(chip);
  }

  wrap.append(label, chipsRow);
  return wrap;
}

// ─── Section Builder ──────────────────────────────────────────────────────────
function renderSection(title, icon, tags, children) {
  const section = el('section', {
    class: 'resume-section',
    'data-tags': JSON.stringify(tags),
    'aria-label': title,
  });
  const heading = el('h2', { class: 'section-title' });
  heading.innerHTML = `<span class="section-icon" aria-hidden="true">${icon}</span> ${title}`;
  section.append(heading, ...children);
  return section;
}

function renderWorkCard(job, delay) {
  const card = el('article', {
    class: 'card',
    'data-tags': JSON.stringify(job.tags || []),
    style: `animation-delay: ${delay}ms`,
    'aria-label': `${job.position} at ${job.name}`,
  });

  const header = el('div', { class: 'card-header' });
  const titleGroup = el('div');
  const title = el('h3', { class: 'card-title' });
  title.textContent = job.name;

  const subtitle = el('div', { class: 'card-subtitle' });
  subtitle.textContent = job.position;
  if (job.location) {
    const locSpan = el('span', { class: 'card-location' });
    locSpan.textContent = ` 📍 ${job.location}`;
    subtitle.appendChild(locSpan);
  }
  titleGroup.append(title, subtitle);

  const date = el('span', { class: 'card-date' });
  date.textContent = `${formatDate(job.startDate)} – ${formatDate(job.endDate)}`;
  header.append(titleGroup, date);
  card.appendChild(header);

  if (job.summary) {
    const summary = el('p', { class: 'card-summary' });
    summary.textContent = job.summary;
    card.appendChild(summary);
  }

  // Highlights — use data-field so applyContentFilter() can find it
  if (job.highlights?.length) {
    const ul = el('ul', { class: 'card-highlights', 'data-field': 'highlights' });
    for (const h of job.highlights) {
      const li = el('li');
      li.textContent = h;
      ul.appendChild(li);
    }
    card.appendChild(ul);
  }

  // All other sub-fields — wrapped in .work-sub-section with data-field
  const subFields = [
    { key: 'keyResponsibilities', label: 'Key Responsibilities', type: 'list' },
    { key: 'skillsUsed',          label: 'Skills Used',          type: 'tags', tagClass: 'tag-skill' },
    { key: 'toolsUsed',           label: 'Tools Used',           type: 'tags', tagClass: 'tag-tool' },
    { key: 'challenges',          label: 'Challenges',           type: 'list' },
    { key: 'wins',                label: 'Wins',                 type: 'list' },
    { key: 'lessonsLearned',      label: 'Lessons Learned',      type: 'list' },
  ];

  for (const { key, label, type, tagClass } of subFields) {
    const items = job[key];
    if (!items?.length) continue;

    const div = el('div', { class: 'work-sub-section', 'data-field': key });
    div.appendChild(el('h4', { class: 'work-sub-title' }, label));

    if (type === 'list') {
      const ul = el('ul', { class: 'card-highlights' });
      for (const item of items) {
        const li = el('li');
        li.textContent = item;
        ul.appendChild(li);
      }
      div.appendChild(ul);
    } else if (type === 'tags') {
      const tagsEl = el('div', { class: 'card-tags' });
      for (const item of items) {
        const tag = el('span', { class: `tag ${tagClass || ''}` });
        tag.textContent = item;
        tagsEl.appendChild(tag);
      }
      div.appendChild(tagsEl);
    }

    card.appendChild(div);
  }

  // Domain tags row
  if (job.tags?.length) {
    const tagsEl = el('div', { class: 'card-tags' });
    // Only show the non-focus-area tags to keep it clean
    const displayTags = job.tags.filter(
      (t) => !['frontend', 'backend', 'leadership', 'open-source'].includes(t)
    );
    for (const t of displayTags) {
      const tag = el('span', { class: 'tag' });
      tag.textContent = t;
      tagsEl.appendChild(tag);
    }
    if (displayTags.length) card.appendChild(tagsEl);
  }

  return card;
}

function renderSkillCard(skill, delay) {
  const card = el('div', {
    class: 'skill-card',
    'data-tags': JSON.stringify(skill.tags || []),
    style: `animation-delay: ${delay}ms`,
    role: 'article',
    'aria-label': `Skill: ${skill.name}`,
  });

  const name = el('div', { class: 'skill-name' });
  name.textContent = skill.name;
  const level = el('div', { class: 'skill-level' });
  level.textContent = skill.level || '';

  const keywords = el('div', { class: 'skill-keywords' });
  for (const kw of skill.keywords || []) {
    const k = el('span', { class: 'skill-keyword' });
    k.textContent = kw;
    keywords.appendChild(k);
  }

  card.append(name, level, keywords);
  return card;
}

function renderProjectCard(project, delay) {
  const card = el('article', {
    class: 'card',
    'data-tags': JSON.stringify(project.tags || []),
    style: `animation-delay: ${delay}ms`,
    'aria-label': `Project: ${project.name}`,
  });

  const header = el('div', { class: 'card-header' });
  const titleGroup = el('div');
  const title = el('h3', { class: 'card-title' });
  title.textContent = project.name;

  if (project.url) {
    const link = el('a', { href: project.url, target: '_blank', rel: 'noopener noreferrer', class: 'card-subtitle' });
    link.textContent = '↗ View Project';
    titleGroup.append(title, link);
  } else {
    titleGroup.appendChild(title);
  }

  header.appendChild(titleGroup);
  card.appendChild(header);

  const desc = el('p', { class: 'card-summary' });
  desc.textContent = project.description;
  card.appendChild(desc);

  if (project.highlights?.length) {
    const ul = el('ul', { class: 'card-highlights' });
    for (const h of project.highlights) {
      const li = el('li');
      li.textContent = h;
      ul.appendChild(li);
    }
    card.appendChild(ul);
  }

  if (project.keywords?.length || project.tags?.length) {
    const tags = el('div', { class: 'card-tags' });
    for (const t of [...(project.keywords || []), ...(project.tags || [])]) {
      const tag = el('span', { class: 'tag' });
      tag.textContent = t;
      tags.appendChild(tag);
    }
    card.appendChild(tags);
  }

  return card;
}

function renderResume(resume) {
  const main = el('main', { class: 'main-content', id: 'main-content' });

  if (resume.basics?.summary) {
    const summaryEl = el('p', { class: 'summary-text' });
    summaryEl.textContent = resume.basics.summary;
    main.appendChild(renderSection('Summary', '💡', [], [summaryEl]));
  }

  if (resume.work?.length) {
    const tags = [...new Set(resume.work.flatMap((w) => w.tags || []))];
    const cards = resume.work.map((job, i) => renderWorkCard(job, i * 60));
    main.appendChild(renderSection('Experience', '💼', tags, cards));
  }

  if (resume.skills?.length) {
    const allTags = [...new Set(resume.skills.flatMap((s) => s.tags || []))];
    const grid = el('div', { class: 'skills-grid' });
    resume.skills.forEach((skill, i) => grid.appendChild(renderSkillCard(skill, i * 50)));
    main.appendChild(renderSection('Skills', '⚡', allTags, [grid]));
  }

  if (resume.projects?.length) {
    const allTags = [...new Set(resume.projects.flatMap((p) => p.tags || []))];
    const cards = resume.projects.map((p, i) => renderProjectCard(p, i * 60));
    main.appendChild(renderSection('Projects', '🚀', allTags, cards));
  }

  if (resume.education?.length) {
    const eduCards = resume.education.map((edu) => {
      const card = el('div', { class: 'edu-card' });
      const icon = el('span', { class: 'edu-icon', 'aria-hidden': 'true' });
      icon.textContent = '🎓';
      const info = el('div', { class: 'edu-info' });
      const inst = el('div', { class: 'edu-institution' });
      inst.textContent = edu.institution;
      const deg = el('div', { class: 'edu-degree' });
      deg.textContent = `${edu.studyType} in ${edu.area}`;
      const meta = el('div', { class: 'edu-meta' });
      meta.textContent = [
        `${formatDate(edu.startDate)} – ${formatDate(edu.endDate)}`,
        edu.score ? `GPA: ${edu.score}` : null,
      ].filter(Boolean).join(' · ');
      info.append(inst, deg, meta);
      card.append(icon, info);
      return card;
    });
    main.appendChild(renderSection('Education', '🎓', [], eduCards));
  }

  if (resume.languages?.length) {
    const pills = el('div', { class: 'lang-pills' });
    for (const lang of resume.languages) {
      const pill = el('div', { class: 'lang-pill' });
      const name = el('span', { class: 'lang-name' });
      name.textContent = lang.language;
      const fluency = el('span', { class: 'lang-fluency' });
      fluency.textContent = lang.fluency;
      pill.append(name, fluency);
      pills.appendChild(pill);
    }
    main.appendChild(renderSection('Languages', '🌍', [], [pills]));
  }

  if (resume.references?.length) {
    const refCards = resume.references.map((ref) => {
      const card = el('div', { class: 'reference-card' });
      const quote = el('p', { class: 'reference-quote' });
      quote.textContent = `"${ref.reference}"`;
      const name = el('p', { class: 'reference-name' });
      name.textContent = `— ${ref.name}`;
      card.append(quote, name);
      return card;
    });
    main.appendChild(renderSection('References', '💬', [], refCards));
  }

  return main;
}

// ─── Embedded Story Engine (Self-Contained Browser Engine) ────────────────────
if (typeof window !== 'undefined' && !window.StoryEngine) {
  (function () {
    const OPENING_TEMPLATES_THIRD = [
      (name, pos, comp, loc, dateStr) => `In ${dateStr}, ${name} stepped into ${comp} as ${pos}${loc ? ` in ${loc}` : ''}.`,
      (name, pos, comp, loc, dateStr) => `The next chapter began in ${dateStr} at ${comp}, where ${name} assumed the role of ${pos}${loc ? ` (${loc})` : ''}.`,
      (name, pos, comp, loc, dateStr) => `Joining ${comp} in ${dateStr}, ${name} took on key responsibilities as ${pos}${loc ? ` based in ${loc}` : ''}.`,
      (name, pos, comp, loc, dateStr) => `${comp} marked an impactful milestone starting in ${dateStr}, with ${name} serving as ${pos}${loc ? ` in ${loc}` : ''}.`,
      (name, pos, comp, loc, dateStr) => `In ${dateStr}, ${name} brought technical expertise to ${comp} as ${pos}${loc ? ` in ${loc}` : ''}.`,
    ];

    const OPENING_TEMPLATES_FIRST = [
      (pos, comp, loc, dateStr) => `In ${dateStr}, I stepped into ${comp} as ${pos}${loc ? ` in ${loc}` : ''}.`,
      (pos, comp, loc, dateStr) => `My next chapter began in ${dateStr} at ${comp}, where I took on the role of ${pos}${loc ? ` (${loc})` : ''}.`,
      (pos, comp, loc, dateStr) => `Joining ${comp} in ${dateStr}, I focused my efforts as ${pos}${loc ? ` based in ${loc}` : ''}.`,
      (pos, comp, loc, dateStr) => `${comp} marked an important milestone in my career starting in ${dateStr}, working as ${pos}${loc ? ` in ${loc}` : ''}.`,
      (pos, comp, loc, dateStr) => `In ${dateStr}, I brought my technical background to ${comp} as ${pos}${loc ? ` in ${loc}` : ''}.`,
    ];

    const CHALLENGE_LEAD_INS_THIRD = [
      'The operational reality presented immediate headwinds: ',
      'The core obstacle centered on ',
      'Stepping onto the team meant confronting a significant challenge: ',
      'At the heart of the engagement lay a demanding hurdle: ',
      'Engineering progress required directly addressing ',
    ];

    const CHALLENGE_LEAD_INS_FIRST = [
      'The primary headwind I faced was ',
      'My biggest hurdle centered on ',
      'Stepping onto the team, I was immediately confronted with ',
      'At the heart of my day-to-day work was a demanding challenge: ',
      'Making real progress meant directly tackling ',
    ];

    const STRATEGY_TEMPLATES_THIRD = [
      (tools, skills) => `To overcome this, a systematic strategy was executed, combining ${skills} while actively applying ${tools}.`,
      (tools, skills) => `Addressing the bottleneck required leveraging ${tools} and anchoring the workflow in ${skills}.`,
      (tools, skills) => `The technical response was disciplined: deploying ${tools} to champion ${skills}.`,
      (tools, skills) => `Meeting this challenge head-on, technical capabilities were focused on ${tools}, reinforced by ${skills}.`,
    ];

    const STRATEGY_TEMPLATES_FIRST = [
      (tools, skills) => `To overcome this, I executed a systematic strategy, combining ${skills} while actively applying ${tools}.`,
      (tools, skills) => `I tackled this bottleneck by leveraging ${tools} and anchoring our workflow in ${skills}.`,
      (tools, skills) => `My technical response was disciplined: I deployed ${tools} and championed ${skills}.`,
      (tools, skills) => `Meeting this challenge head-on, I focused my technical capabilities on ${tools}, reinforced by ${skills}.`,
    ];

    const WIN_LEAD_INS_THIRD = [
      'The breakthrough was decisive: ',
      'This disciplined execution delivered tangible impact: ',
      'The effort culminated in a major milestone: ',
      'The results yielded immediate, measurable dividends: ',
      'The payoff was substantial: ',
    ];

    const WIN_LEAD_INS_FIRST = [
      'The breakthrough was decisive: ',
      'My execution delivered tangible impact: ',
      'The effort culminated in a proud milestone: ',
      'The results produced immediate, measurable dividends: ',
      'The payoff was substantial: ',
    ];

    const LESSON_LEAD_INS_THIRD = [
      'Beyond the technical metrics, this tenure cemented an enduring principle: ',
      'Reflecting on this chapter, the defining takeaway became clear: ',
      'The engagement forged a lasting operational insight: ',
      'Looking back, this experience solidified a core working philosophy: ',
    ];

    const LESSON_LEAD_INS_FIRST = [
      'Beyond the technical metrics, this role cemented an enduring principle for me: ',
      'Reflecting on this chapter, my defining takeaway became clear: ',
      'This tenure forged a lasting operational insight in my engineering career: ',
      'Looking back, the experience solidified my core working philosophy: ',
    ];

    const TRANSITION_TEMPLATES_THIRD = [
      (nextComp) => `With these lessons cemented, the stage was set for the next endeavor at ${nextComp}.`,
      (nextComp) => `Carrying these battle-tested competencies forward, the journey continued onward to ${nextComp}.`,
      (nextComp) => `These accomplishments formed the foundational springboard for what came next at ${nextComp}.`,
    ];

    const TRANSITION_TEMPLATES_FIRST = [
      (nextComp) => `With these lessons cemented, I carried this momentum forward into my next endeavor at ${nextComp}.`,
      (nextComp) => `Carrying these battle-tested competencies forward, my journey continued onward to ${nextComp}.`,
      (nextComp) => `These accomplishments formed the foundational springboard for what I tackled next at ${nextComp}.`,
    ];

    function calculateDateSpan(startDateStr, endDateStr) {
      if (!startDateStr) return '';
      const start = new Date(startDateStr);
      const end = endDateStr ? new Date(endDateStr) : new Date();
      if (isNaN(start.getTime()) || isNaN(end.getTime())) return '';
      const totalMonths = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth());
      if (totalMonths <= 0) return '';
      const years = Math.floor(totalMonths / 12);
      const months = totalMonths % 12;
      const parts = [];
      if (years > 0) parts.push(`${years} ${years === 1 ? 'year' : 'years'}`);
      if (months > 0) parts.push(`${months} ${months === 1 ? 'month' : 'months'}`);
      return parts.join(', ');
    }

    function cleanSentence(str) {
      if (!str) return '';
      let trimmed = str.trim();
      if (!/[.!?]$/.test(trimmed)) trimmed += '.';
      return trimmed;
    }

    function lowerFirst(str) {
      if (!str) return '';
      return str.charAt(0).toLowerCase() + str.slice(1);
    }

    function joinList(arr, defaultFallback = '') {
      if (!arr || !arr.length) return defaultFallback;
      if (arr.length === 1) return arr[0];
      if (arr.length === 2) return `${arr[0]} and ${arr[1]}`;
      return `${arr.slice(0, -1).join(', ')}, and ${arr[arr.length - 1]}`;
    }

    function generateChapter(job, index, total, nextJob = null, options = {}) {
      const perspective = options.perspective === 'first' ? 'first' : 'third';
      const name = options.candidateName || 'Thomas';
      const chapterNumber = index + 1;

      const dateSpan = `${formatDate(job.startDate)} – ${formatDate(job.endDate)}`;
      const duration = calculateDateSpan(job.startDate, job.endDate);

      const openBank = perspective === 'first' ? OPENING_TEMPLATES_FIRST : OPENING_TEMPLATES_THIRD;
      const openFn = openBank[index % openBank.length];
      const openingSentence = perspective === 'first'
        ? openFn(job.position, job.name, job.location, formatDate(job.startDate))
        : openFn(name, job.position, job.name, job.location, formatDate(job.startDate));

      const contextSentence = job.summary ? cleanSentence(job.summary) : '';

      let challengeNarrative = '';
      const rawChallenge = job.challenges?.[0] || '';
      if (rawChallenge) {
        const chalBank = perspective === 'first' ? CHALLENGE_LEAD_INS_FIRST : CHALLENGE_LEAD_INS_THIRD;
        const chalLead = chalBank[index % chalBank.length];
        challengeNarrative = chalLead + lowerFirst(cleanSentence(rawChallenge));
      } else if (job.keyResponsibilities?.length) {
        const lead = perspective === 'first'
          ? 'My core objective required orchestrating '
          : 'The immediate priority focused on orchestrating ';
        challengeNarrative = lead + lowerFirst(cleanSentence(job.keyResponsibilities[0]));
      }

      let secondaryDetail = '';
      if (job.challenges && job.challenges.length > 1) {
        secondaryDetail = `Compounding this, ${lowerFirst(cleanSentence(job.challenges[1]))}`;
      } else if (job.keyResponsibilities && job.keyResponsibilities.length > 1) {
        secondaryDetail = `Key operational duties encompassed ${lowerFirst(cleanSentence(job.keyResponsibilities[1]))}`;
      }

      let strategyNarrative = '';
      const tools = job.toolsUsed?.length ? joinList(job.toolsUsed.slice(0, 4)) : '';
      const skills = job.skillsUsed?.length ? joinList(job.skillsUsed.slice(0, 3)) : '';

      if (tools && skills) {
        const stratBank = perspective === 'first' ? STRATEGY_TEMPLATES_FIRST : STRATEGY_TEMPLATES_THIRD;
        const stratFn = stratBank[index % stratBank.length];
        strategyNarrative = stratFn(tools, skills);
      } else if (tools) {
        strategyNarrative = perspective === 'first'
          ? `I anchored my technical implementation in ${tools}.`
          : `The implementation was anchored in ${tools}.`;
      } else if (skills) {
        strategyNarrative = perspective === 'first'
          ? `I drew heavily upon ${skills} to steer the deliverables forward.`
          : `Steering the deliverables forward required deep application of ${skills}.`;
      }

      let winNarrative = '';
      const rawWin = job.wins?.[0] || job.highlights?.[0] || '';
      if (rawWin) {
        const winBank = perspective === 'first' ? WIN_LEAD_INS_FIRST : WIN_LEAD_INS_THIRD;
        const winLead = winBank[index % winBank.length];
        winNarrative = winLead + lowerFirst(cleanSentence(rawWin));
      }

      let secondaryWin = '';
      if (job.wins && job.wins.length > 1) {
        secondaryWin = `Furthermore, ${lowerFirst(cleanSentence(job.wins[1]))}`;
      }

      let lessonNarrative = '';
      const rawLesson = job.lessonsLearned?.[0] || '';
      if (rawLesson) {
        const lessonBank = perspective === 'first' ? LESSON_LEAD_INS_FIRST : LESSON_LEAD_INS_THIRD;
        const lessonLead = lessonBank[index % lessonBank.length];
        lessonNarrative = lessonLead + lowerFirst(cleanSentence(rawLesson));
      }

      let transitionNarrative = '';
      if (nextJob) {
        const transBank = perspective === 'first' ? TRANSITION_TEMPLATES_FIRST : TRANSITION_TEMPLATES_THIRD;
        const transFn = transBank[index % transBank.length];
        transitionNarrative = transFn(nextJob.name);
      }

      const act1 = [openingSentence, contextSentence].filter(Boolean).join(' ');
      const act2 = [challengeNarrative, secondaryDetail, strategyNarrative].filter(Boolean).join(' ');
      const act3 = [winNarrative, secondaryWin].filter(Boolean).join(' ');
      const act4 = [lessonNarrative, transitionNarrative].filter(Boolean).join(' ');

      return {
        chapterNumber,
        company: job.name,
        position: job.position,
        location: job.location || '',
        dateSpan,
        duration,
        tags: job.tags || [],
        raw: {
          challenge: rawChallenge,
          win: rawWin,
          lesson: rawLesson,
          tools: job.toolsUsed || [],
          skills: job.skillsUsed || []
        },
        paragraphs: [act1, act2, act3, act4].filter(Boolean)
      };
    }

    function generateBackOfTheBook(resumeData, options = {}) {
      const perspective = options.perspective === 'first' ? 'first' : 'third';
      const basics = resumeData.basics || {};
      const candidateName = basics.name || 'Thomas S. Snyder';
      const workEntries = resumeData.work || [];

      const sorted = [...workEntries].sort((a, b) => (a.startDate || '').localeCompare(b.startDate || ''));
      const firstDate = sorted[0]?.startDate;
      const lastDate = sorted[sorted.length - 1]?.endDate;
      const careerDuration = firstDate ? calculateDateSpan(firstDate, lastDate) || '26+ years' : '26+ years';

      const totalChapters = workEntries.length;

      let tagline = '';
      let synopsis = [];
      let motto = '';

      if (perspective === 'first') {
        tagline = `From cartridge burners and bare-metal debuggers to cloud APIs and autonomous AI agents: my ${careerDuration} on the software quality frontier.`;

        synopsis = [
          `In an industry that moves fast and breaks things, I have dedicated more than a quarter-century to making sure software actually delivers. From the unforgiving release demands of Nintendo 64 cartridges and the original Xbox console to enterprise cloud messaging and modern AI agent pipelines, this is the inside account of an engineering journey that treats software quality not as a final roadblock, but as the primary catalyst for organizational velocity.`,
          `Across eighteen distinct chapters—spanning Microsoft, NVIDIA, Monolith Productions, and Smartsheet—I repeatedly confronted the quintessential crucible of software development: engineering teams paralyzed by manual regression testing, entrenched skepticism toward automation, and elusive defects lurking between hardware drivers and distributed microservices. Armed with frameworks like Karate DSL, diagnostic forensics, and relentless tenacity, I repeatedly built automation suites from a dead-zero baseline to over 1,500 tests, restoring developer speed and proving that test automation creates the freedom for high-impact exploratory testing.`,
          `More than a chronological record, this career odyssey captures a hard-won philosophy of technical leadership: the most potent defense against software entropy isn't academic perfectionism—it is speaking up early, building transparent feedback loops from day zero, and championing resilient quality across every layer of the stack.`
        ];

        motto = `Quality is never an afterthought or a bureaucratic gate. It is an active discipline engineered into every commit—freeing developers to build with unwavering confidence.`;
      } else {
        tagline = `From cartridge burners and bare-metal debuggers to cloud APIs and autonomous AI agents: 26+ years on the software quality frontier.`;

        synopsis = [
          `In an industry that moves fast and breaks things, ${candidateName} has spent more than a quarter-century making sure software actually delivers. From the unforgiving release demands of Nintendo 64 cartridges and the original Xbox console to enterprise cloud messaging and modern AI agent pipelines, this is the inside account of an engineering journey that treats software quality not as a final roadblock, but as the primary catalyst for organizational velocity.`,
          `Across eighteen distinct chapters—spanning Microsoft, NVIDIA, Monolith Productions, and Smartsheet—${candidateName} repeatedly confronted the quintessential crucible of software development: engineering teams paralyzed by manual regression testing, entrenched skepticism toward automation, and elusive defects lurking between hardware drivers and distributed microservices. Armed with frameworks like Karate DSL, diagnostic forensics, and relentless tenacity, Snyder repeatedly built automation suites from a dead-zero baseline to over 1,500 tests, restoring developer speed and proving that test automation creates the freedom for high-impact exploratory testing.`,
          `More than a chronological record, The Career Odyssey captures a hard-won philosophy of technical leadership: the most potent defense against software entropy isn't academic perfectionism—it is speaking up early, building transparent feedback loops from day zero, and championing resilient quality across every layer of the stack.`
        ];

        motto = `Quality is never an afterthought or a bureaucratic gate. It is an active discipline engineered into every commit—freeing developers to build with unwavering confidence.`;
      }

      const stats = [
        { label: 'Chapters', value: `${totalChapters} Work Eras` },
        { label: 'Span', value: `${careerDuration}` },
        { label: 'Automation Baseline', value: '0 → 1,500+ Tests' },
        { label: 'Manual Coverage', value: '85% Automated' },
        { label: 'Frontier', value: 'Consoles · Cloud · MCP Agents' },
        { label: 'Generation', value: '100% LLM-Free Deterministic' },
      ];

      return {
        title: 'Back of the Book',
        subtitle: 'The Career Odyssey Synopsis',
        tagline,
        synopsis,
        motto,
        stats,
        edition: {
          candidateName,
          label: basics.label || 'Senior QA Engineer',
          genre: 'Technical Biography · Quality Engineering',
          isbn: 'ISBN 0-ENG-QUALITY-99-26',
          publisher: 'TalentScout Living Resume Engine'
        }
      };
    }

    function generateStoryChapters(resumeData, options = {}) {
      const perspective = options.perspective === 'first' ? 'first' : 'third';
      const order = options.order === 'reverse' ? 'reverse' : 'chronological';
      const basics = resumeData.basics || {};
      const candidateName = basics.name || 'Thomas S. Snyder';

      let workEntries = [...(resumeData.work || [])];
      workEntries.sort((a, b) => {
        const dateA = a.startDate || '1970-01-01';
        const dateB = b.startDate || '1970-01-01';
        return order === 'chronological' ? dateA.localeCompare(dateB) : dateB.localeCompare(dateA);
      });

      const total = workEntries.length;
      const chapters = workEntries.map((job, idx) => {
        const nextJob = idx < total - 1 ? workEntries[idx + 1] : null;
        return generateChapter(job, idx, total, nextJob, { perspective, candidateName });
      });

      const firstJob = order === 'chronological' ? workEntries[0] : workEntries[workEntries.length - 1];
      const lastJob = order === 'chronological' ? workEntries[workEntries.length - 1] : workEntries[0];
      const careerDuration = firstJob && lastJob ? calculateDateSpan(firstJob.startDate, lastJob.endDate) : '25+ years';

      const backOfTheBook = generateBackOfTheBook(resumeData, { perspective });

      let prologue = '';
      if (perspective === 'first') {
        prologue = `Over the course of ${careerDuration || 'more than two decades'}, my career has been defined by an obsession with software quality, technical resilience, and pragmatic automation. From testing foundational console games and operating system platforms to architecting modern web frameworks and integrating autonomous AI tooling, this is the story of challenges confronted, systems transformed, and lessons learned along the journey.`;
      } else {
        prologue = `Over the course of ${careerDuration || 'more than two decades'}, ${candidateName} has traversed the evolving landscape of software quality engineering. From the high-stakes discipline of early console titles and operating systems to cloud APIs, enterprise test automation, and AI-assisted workflows, this narrative chronicles the technical crucible, key milestones, and architectural insights that shaped ${candidateName}'s career.`;
      }

      let epilogue = '';
      if (perspective === 'first') {
        epilogue = `Today, the focus turns toward the next horizon: integrating intelligent agent architectures, Model Context Protocol (MCP) tooling, and autonomous testing pipelines. The technology shifts, but the foundational law remains unchanged: quality is not an afterthought or a final gate—it is an active discipline engineered from the very first line of code.`;
      } else {
        epilogue = `Looking to the present and beyond, ${candidateName} continues to bridge classical quality engineering with frontier AI paradigms—orchestrating Model Context Protocol (MCP) agents, autonomous test suites, and resilient release systems. The tools and platforms evolve, but the governing tenet remains rock-solid: exceptional software is built when quality is championed from day zero.`;
      }

      return {
        candidateName,
        label: basics.label || '',
        perspective,
        order,
        careerDuration,
        backOfTheBook,
        prologue,
        chapters,
        epilogue
      };
    }

    function generateStoryMarkdown(resumeData, options = {}) {
      const story = generateStoryChapters(resumeData, options);
      const lines = [];

      lines.push(`# ${story.candidateName} — The Career Odyssey`);
      if (story.label) lines.push(`*${story.label}*`);
      lines.push('');
      lines.push('---');
      lines.push('');

      if (story.backOfTheBook) {
        const bob = story.backOfTheBook;
        lines.push('## 📕 Back of the Book');
        lines.push(`> *"${bob.tagline}"*`);
        lines.push('');
        for (const p of bob.synopsis) {
          lines.push(p);
          lines.push('');
        }
        lines.push(`> 💡 **Core Mantra:** "${bob.motto}"`);
        lines.push('');
        lines.push('### Edition Specs & Vital Metrics');
        for (const stat of bob.stats) {
          lines.push(`- **${stat.label}:** ${stat.value}`);
        }
        lines.push('');
        lines.push('---');
        lines.push('');
      }

      lines.push('## Prologue');
      lines.push(story.prologue);
      lines.push('');

      for (const ch of story.chapters) {
        const durStr = ch.duration ? ` · (${ch.duration})` : '';
        lines.push(`## Chapter ${ch.chapterNumber}: ${ch.company} (${ch.dateSpan}${durStr})`);
        lines.push(`**${ch.position}**${ch.location ? ` — *${ch.location}*` : ''}`);
        lines.push('');

        for (const paragraph of ch.paragraphs) {
          lines.push(paragraph);
          lines.push('');
        }

        if (ch.raw.lesson) {
          lines.push(`> 💡 **Core Takeaway:** "${ch.raw.lesson}"`);
          lines.push('');
        }

        lines.push('---');
        lines.push('');
      }

      lines.push('## Epilogue: The Next Frontier');
      lines.push(story.epilogue);
      lines.push('');

      return lines.join('\n');
    }

    window.StoryEngine = {
      formatDate,
      calculateDateSpan,
      generateChapter,
      generateBackOfTheBook,
      generateStoryChapters,
      generateStoryMarkdown,
    };
  })();
}

// ─── View Mode State (Resume vs Story Mode) ──────────────────────────────────
let currentViewMode = 'resume'; // 'resume' | 'story'
let storyPerspective = 'third'; // 'third' | 'first'
let storyOrder = 'chronological'; // 'chronological' | 'reverse'
let storyDisplayMode = 'all'; // 'all' | 'back-of-book' | 'chapters'

function setViewMode(mode) {
  currentViewMode = mode;
  const isStory = mode === 'story';

  const btnResume = document.getElementById('btn-view-resume');
  const btnStory = document.getElementById('btn-view-story');
  if (btnResume) {
    btnResume.classList.toggle('active', !isStory);
    btnResume.setAttribute('aria-pressed', !isStory);
  }
  if (btnStory) {
    btnStory.classList.toggle('active', isStory);
    btnStory.setAttribute('aria-pressed', isStory);
  }

  const mainContent = document.getElementById('main-content');
  const storyContent = document.getElementById('story-content');
  const contentFilter = document.getElementById('content-filter');

  if (mainContent) mainContent.style.display = isStory ? 'none' : '';
  if (contentFilter) contentFilter.style.display = isStory ? 'none' : '';
  if (storyContent) {
    storyContent.style.display = isStory ? 'block' : 'none';
    if (isStory && _resumeData) {
      updateStoryBody(_resumeData);
    }
  }

  showToast(isStory ? 'Switched to Story Mode (Career Odyssey)' : 'Switched to Traditional Resume', 'info', 2000);
}

function renderViewSwitcher() {
  const wrap = el('div', { class: 'view-switcher-wrap', role: 'navigation', 'aria-label': 'Portfolio view modes' });
  const switcher = el('div', { class: 'view-switcher', role: 'group', 'aria-label': 'Choose display mode' });

  const btnResume = el('button', {
    class: 'view-btn active',
    id: 'btn-view-resume',
    type: 'button',
    'aria-pressed': 'true',
  });
  btnResume.innerHTML = '📋 Traditional Resume';
  btnResume.addEventListener('click', () => setViewMode('resume'));

  const btnStory = el('button', {
    class: 'view-btn',
    id: 'btn-view-story',
    type: 'button',
    'aria-pressed': 'false',
  });
  btnStory.innerHTML = '📖 Career Story (Odyssey)';
  btnStory.addEventListener('click', () => setViewMode('story'));

  switcher.append(btnResume, btnStory);
  wrap.appendChild(switcher);
  return wrap;
}

function renderStoryView(resume) {
  const storySection = el('section', {
    class: 'story-content',
    id: 'story-content',
    'aria-label': 'Career Story Odyssey',
    style: 'display: none;',
  });

  // Story Controls Toolbar
  const controls = el('div', { class: 'story-controls-wrap', role: 'toolbar', 'aria-label': 'Story controls' });

  // View Filter Controls (Complete Edition vs Back of the Book vs 18 Chapters)
  const displayGroup = el('div', { class: 'story-options-group' });
  const dLabel = el('span', { class: 'story-option-label' });
  dLabel.textContent = 'View:';
  const dBtnGroup = el('div', { class: 'story-btn-group' });

  const btnAll = el('button', {
    class: 'story-pill-btn active',
    id: 'story-view-all',
    type: 'button',
    title: 'Show complete story edition (Back of the Book + Prologue + 18 Chapters + Epilogue)',
  });
  btnAll.textContent = '📚 Complete Edition';
  btnAll.addEventListener('click', () => {
    if (storyDisplayMode === 'all') return;
    storyDisplayMode = 'all';
    btnAll.classList.add('active');
    btnBobOnly.classList.remove('active');
    btnChaptersOnly.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  const btnBobOnly = el('button', {
    class: 'story-pill-btn',
    id: 'story-view-bob',
    type: 'button',
    title: 'Show the Back of the Book synopsis summary',
  });
  btnBobOnly.textContent = '📕 Back of the Book';
  btnBobOnly.addEventListener('click', () => {
    if (storyDisplayMode === 'back-of-book') return;
    storyDisplayMode = 'back-of-book';
    btnBobOnly.classList.add('active');
    btnAll.classList.remove('active');
    btnChaptersOnly.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  const btnChaptersOnly = el('button', {
    class: 'story-pill-btn',
    id: 'story-view-chapters',
    type: 'button',
    title: 'Show the chapter-by-chapter timeline',
  });
  btnChaptersOnly.textContent = '📖 18 Chapters';
  btnChaptersOnly.addEventListener('click', () => {
    if (storyDisplayMode === 'chapters') return;
    storyDisplayMode = 'chapters';
    btnChaptersOnly.classList.add('active');
    btnAll.classList.remove('active');
    btnBobOnly.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  dBtnGroup.append(btnAll, btnBobOnly, btnChaptersOnly);
  displayGroup.append(dLabel, dBtnGroup);

  // Perspective Controls
  const perspectiveGroup = el('div', { class: 'story-options-group' });
  const pLabel = el('span', { class: 'story-option-label' });
  pLabel.textContent = 'Voice:';
  const pBtnGroup = el('div', { class: 'story-btn-group' });

  const btnThird = el('button', {
    class: 'story-pill-btn active',
    id: 'story-voice-third',
    type: 'button',
  });
  btnThird.textContent = '👤 Biography (3rd)';
  btnThird.addEventListener('click', () => {
    if (storyPerspective === 'third') return;
    storyPerspective = 'third';
    btnThird.classList.add('active');
    btnFirst.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  const btnFirst = el('button', {
    class: 'story-pill-btn',
    id: 'story-voice-first',
    type: 'button',
  });
  btnFirst.textContent = '🗣️ In My Words (1st)';
  btnFirst.addEventListener('click', () => {
    if (storyPerspective === 'first') return;
    storyPerspective = 'first';
    btnFirst.classList.add('active');
    btnThird.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  pBtnGroup.append(btnThird, btnFirst);
  perspectiveGroup.append(pLabel, pBtnGroup);

  // Order Controls
  const orderGroup = el('div', { class: 'story-options-group' });
  const oLabel = el('span', { class: 'story-option-label' });
  oLabel.textContent = 'Timeline:';
  const oBtnGroup = el('div', { class: 'story-btn-group' });

  const btnChrono = el('button', {
    class: 'story-pill-btn active',
    id: 'story-order-chrono',
    type: 'button',
  });
  btnChrono.textContent = '⏳ 1999 → Present';
  btnChrono.addEventListener('click', () => {
    if (storyOrder === 'chronological') return;
    storyOrder = 'chronological';
    btnChrono.classList.add('active');
    btnReverse.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  const btnReverse = el('button', {
    class: 'story-pill-btn',
    id: 'story-order-reverse',
    type: 'button',
  });
  btnReverse.textContent = '⌛ Present → 1999';
  btnReverse.addEventListener('click', () => {
    if (storyOrder === 'reverse') return;
    storyOrder = 'reverse';
    btnReverse.classList.add('active');
    btnChrono.classList.remove('active');
    updateStoryBody(_resumeData);
  });

  oBtnGroup.append(btnChrono, btnReverse);
  orderGroup.append(oLabel, oBtnGroup);

  // Download Story Button
  const dlStoryBtn = el('button', {
    class: 'btn btn-secondary',
    id: 'btn-download-story-md',
    type: 'button',
    title: 'Download complete story narrative as Markdown',
  });
  dlStoryBtn.innerHTML = '📄 Download Story (.md)';
  dlStoryBtn.addEventListener('click', () => {
    if (!_resumeData) return;
    downloadStoryMarkdown(_resumeData);
  });

  controls.append(displayGroup, perspectiveGroup, orderGroup, dlStoryBtn);
  storySection.appendChild(controls);

  // Story Body Container (Dynamic target)
  const storyBody = el('div', { id: 'story-body' });
  storySection.appendChild(storyBody);

  return storySection;
}

function renderBackOfTheBookCard(bob) {
  const card = el('article', {
    class: 'story-back-of-book card',
    id: 'story-back-of-book',
    'aria-label': 'Back of the Book Summary',
  });

  // Top book ribbon / metadata badge
  const ribbon = el('div', { class: 'story-bob-ribbon' });
  const badge = el('span', { class: 'story-bob-badge' });
  badge.innerHTML = '📕 BACK OF THE BOOK';
  const subtitle = el('span', { class: 'story-bob-subtitle' });
  subtitle.textContent = bob.subtitle || 'The Career Odyssey Synopsis';
  ribbon.append(badge, subtitle);

  // Tagline quote
  const tagline = el('blockquote', { class: 'story-bob-tagline' });
  tagline.textContent = `“${bob.tagline}”`;

  // Synopsis paragraphs
  const synopsisWrap = el('div', { class: 'story-bob-synopsis' });
  for (const pText of bob.synopsis) {
    const p = el('p', { class: 'story-p' });
    p.textContent = pText;
    synopsisWrap.appendChild(p);
  }

  // Stats Grid
  const statsGrid = el('div', { class: 'story-bob-stats' });
  for (const stat of bob.stats) {
    const statItem = el('div', { class: 'story-bob-stat-item' });
    const statVal = el('span', { class: 'story-bob-stat-val' });
    statVal.textContent = stat.value;
    const statLbl = el('span', { class: 'story-bob-stat-lbl' });
    statLbl.textContent = stat.label;
    statItem.append(statVal, statLbl);
    statsGrid.appendChild(statItem);
  }

  // Core Mantra Callout
  const mantraBox = el('div', { class: 'story-bob-mantra' });
  const mantraIcon = el('span', { class: 'story-takeaway-icon' });
  mantraIcon.textContent = '💡';
  const mantraContent = el('div', { class: 'story-takeaway-text' });
  const mantraLabel = el('strong', { class: 'story-takeaway-label' });
  mantraLabel.textContent = 'Core Mantra: ';
  const mantraText = el('span', { class: 'story-takeaway-quote' });
  mantraText.textContent = `“${bob.motto}”`;
  mantraContent.append(mantraLabel, mantraText);
  mantraBox.append(mantraIcon, mantraContent);

  // Footer metadata / barcode mock
  const footerBar = el('div', { class: 'story-bob-footer' });
  const genre = el('span');
  genre.textContent = bob.edition?.genre || 'Technical Biography · Quality Engineering';
  const isbn = el('span', { class: 'story-bob-isbn' });
  isbn.textContent = `${bob.edition?.isbn || 'ISBN 0-ENG-QUALITY-99-26'} · ${bob.edition?.publisher || 'TalentScout Engine'}`;
  footerBar.append(genre, isbn);

  card.append(ribbon, tagline, synopsisWrap, statsGrid, mantraBox, footerBar);
  return card;
}

function updateStoryBody(resume) {
  const storyBody = document.getElementById('story-body');
  if (!storyBody) return;
  storyBody.innerHTML = '';

  if (!window.StoryEngine) {
    storyBody.innerHTML = '<p style="color:#f85149;padding:1rem;">Story engine is still initializing...</p>';
    return;
  }

  const story = window.StoryEngine.generateStoryChapters(resume, {
    perspective: storyPerspective,
    order: storyOrder,
  });

  const showBob = storyDisplayMode === 'all' || storyDisplayMode === 'back-of-book';
  const showChapters = storyDisplayMode === 'all' || storyDisplayMode === 'chapters';

  // 1. Back of the Book Card
  if (showBob && story.backOfTheBook) {
    storyBody.appendChild(renderBackOfTheBookCard(story.backOfTheBook));
  }

  if (showChapters) {
    // 2. Prologue
    const prologueCard = el('div', { class: 'story-prologue' });
    const proTitle = el('h3');
    proTitle.innerHTML = '<span>🌟</span> Prologue: A Quarter-Century of Quality';
    const proP = el('p');
    proP.textContent = story.prologue;
    prologueCard.append(proTitle, proP);
    storyBody.appendChild(prologueCard);

    // 3. Chapters Timeline
    const timeline = el('div', { class: 'story-timeline' });
    for (const ch of story.chapters) {
      timeline.appendChild(renderStoryChapterCard(ch));
    }
    storyBody.appendChild(timeline);

    // 4. Epilogue
    const epilogueCard = el('div', { class: 'story-epilogue' });
    const epiTitle = el('h3');
    epiTitle.innerHTML = '<span>🚀</span> Epilogue: The AI & Autonomous Frontier';
    const epiP = el('p');
    epiP.textContent = story.epilogue;
    epilogueCard.append(epiTitle, epiP);
    storyBody.appendChild(epilogueCard);
  }

  // Re-apply focus highlight if a focus tag is active
  if (activeFocus && activeFocus !== 'all') {
    applyFocus(activeFocus);
  }
}

function renderStoryChapterCard(ch) {
  const card = el('article', {
    class: 'story-chapter-card card',
    'data-tags': JSON.stringify(ch.tags || []),
    id: `chapter-${ch.chapterNumber}`,
  });

  const header = el('header', { class: 'story-chapter-header' });
  const topRow = el('div', { class: 'story-chapter-top' });
  const badge = el('span', { class: 'story-chapter-badge' });
  badge.textContent = `Chapter ${ch.chapterNumber}`;
  const dates = el('span', { class: 'story-chapter-dates' });
  dates.textContent = `${ch.dateSpan}${ch.duration ? ` · (${ch.duration})` : ''}`;
  topRow.append(badge, dates);

  const titleGroup = el('div');
  const company = el('h3', { class: 'story-chapter-company' });
  company.textContent = ch.company;
  const position = el('p', { class: 'story-chapter-position' });
  position.textContent = `${ch.position}${ch.location ? ` — ${ch.location}` : ''}`;
  titleGroup.append(company, position);

  header.append(topRow, titleGroup);
  card.appendChild(header);

  // Prose paragraphs
  const prose = el('div', { class: 'story-prose' });
  for (const pText of ch.paragraphs) {
    const p = el('p', { class: 'story-p' });
    p.textContent = pText;
    prose.appendChild(p);
  }
  card.appendChild(prose);

  // Core Takeaway blockquote
  if (ch.raw.lesson) {
    const takeaway = el('blockquote', { class: 'story-takeaway' });
    const icon = el('span', { class: 'story-takeaway-icon' });
    icon.textContent = '💡';
    const textWrap = el('div', { class: 'story-takeaway-text' });
    const label = el('strong', { class: 'story-takeaway-label' });
    label.textContent = 'Core Takeaway: ';
    const quote = el('span', { class: 'story-takeaway-quote' });
    quote.textContent = `“${ch.raw.lesson}”`;
    textWrap.append(label, quote);
    takeaway.append(icon, textWrap);
    card.appendChild(takeaway);
  }

  // Tags pill row
  const allTags = [...new Set([...(ch.tags || []), ...(ch.raw.tools || []).slice(0, 3)])];
  if (allTags.length) {
    const tagWrap = el('div', { class: 'card-tags story-tags' });
    for (const t of allTags) {
      const tag = el('span', { class: 'tag' });
      tag.textContent = t;
      tagWrap.appendChild(tag);
    }
    card.appendChild(tagWrap);
  }

  return card;
}

function downloadStoryMarkdown(resume) {
  if (!window.StoryEngine) {
    showToast('StoryEngine not loaded', 'warning');
    return;
  }
  try {
    const md = window.StoryEngine.generateStoryMarkdown(resume, {
      perspective: storyPerspective,
      order: storyOrder,
    });
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${safeFilename(resume.basics.name)}_Career_Story_${storyPerspective}.md`;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
    showToast('Career Story downloaded (.md)', 'success');
  } catch (err) {
    showToast(`Story download failed: ${err.message}`, 'warning');
  }
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
async function boot() {
  document.body.appendChild(toastContainer);

  let resume;
  try {
    const response = await fetch(RESUME_PATH);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    resume = await response.json();
  } catch (err) {
    if (window.__RESUME__) {
      resume = window.__RESUME__;
    } else {
      document.querySelector('#app')?.insertAdjacentHTML(
        'beforeend',
        '<p style="color:#f85149;padding:2rem">⚠️ Could not load resume.json. Serve this page from a local server or embed the data.</p>'
      );
      console.error('Failed to load resume:', err);
      return;
    }
  }

  // Store globally so download buttons can use the data
  _resumeData = resume;

  const app = document.getElementById('app');
  if (!app) return;

  document.title = `${resume.basics.name} — Portfolio`;
  document.querySelector('meta[name="description"]')?.setAttribute(
    'content',
    `Portfolio and resume of ${resume.basics.name}, ${resume.basics.label}.`
  );

  // Render all sections
  app.appendChild(renderHero(resume.basics));
  app.appendChild(renderActionBar(resume.basics));
  app.appendChild(renderViewSwitcher());
  app.appendChild(renderFocusSelector());
  app.appendChild(renderContentFilter());
  app.appendChild(renderResume(resume));
  app.appendChild(renderStoryView(resume));

  // Initialize story content
  updateStoryBody(resume);

  // Footer
  const footer = el('footer');
  const footerText = el('p', { class: 'footer-text' });
  const mcpFooterHref = MCP_URL || 'https://github.com/Saikojin/Talentscout#readme';
  const mcpFooterLabel = MCP_URL ? 'MCP Server' : 'MCP Integration';
  footerText.innerHTML = `Built with <a href="https://github.com/nathanfox/resume-as-code" target="_blank" rel="noopener">resume-as-code</a> · <a href="${mcpFooterHref}" target="_blank" rel="noopener">${mcpFooterLabel}</a>`;
  footer.appendChild(footerText);
  app.appendChild(footer);

  // Apply initial states
  applyFocus('all');
  applyContentFilter();
}

document.addEventListener('DOMContentLoaded', boot);
