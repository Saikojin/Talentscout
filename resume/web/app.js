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
  app.appendChild(renderFocusSelector());
  app.appendChild(renderContentFilter());
  app.appendChild(renderResume(resume));

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
