/**
 * web/app.js
 * TalentScout — Dynamic Resume Portfolio
 *
 * Responsibilities:
 * 1. Loads resume.json and renders all sections dynamically.
 * 2. Manages the Focus Selector (All/Frontend/Backend/Leadership/Open Source).
 * 3. Applies micro-animation highlighting/dimming to sections/cards by tag relevance.
 * 4. Provides MCP URL clipboard copy and PDF/export button behavior.
 * 5. Manages toast notifications.
 */

'use strict';

// ─── Configuration ────────────────────────────────────────────────────────────
// When loaded from the repo root via index.html, window.__RESUME_CONFIG__ overrides
// these values so the correct relative URLs are used. The standalone resume/web/index.html
// does not set this global, so the defaults apply there as-is.
//
// mcpUrl: set to null on the public GitHub Pages site to hide the clipboard button
//         (localhost:3001 is meaningless to external visitors). Set to a real URL only
//         when the MCP server is publicly reachable behind HTTPS.
const MCP_URL     = window.__RESUME_CONFIG__?.mcpUrl !== undefined
                    ? window.__RESUME_CONFIG__.mcpUrl
                    : 'http://localhost:3001/mcp';
const RESUME_PATH = window.__RESUME_CONFIG__?.resumePath ?? './data/resume.json';
const DIST_PATH   = window.__RESUME_CONFIG__?.distPath   ?? '../dist';

const FOCUS_TAGS = {
  all:        null,   // No filtering
  frontend:   ['frontend'],
  backend:    ['backend', 'devops'],
  leadership: ['leadership'],
  'open-source': ['open-source'],
};

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
  try {
    const d = new Date(dateStr + '-01');
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  } catch { return dateStr; }
}

function initials(name) {
  return (name || '?').split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase();
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

  // Update all sections
  document.querySelectorAll('.resume-section[data-tags]').forEach((section) => {
    const sectionTags = JSON.parse(section.dataset.tags || '[]');
    const relevant = !tags || tags.some((t) => sectionTags.includes(t));
    section.classList.toggle('section--dimmed', !relevant);
    section.classList.toggle('section--highlighted', relevant && focusKey !== 'all');
  });

  // Update individual cards
  document.querySelectorAll('.card[data-tags], .skill-card[data-tags]').forEach((card) => {
    const cardTags = JSON.parse(card.dataset.tags || '[]');
    const relevant = !tags || tags.some((t) => cardTags.includes(t));
    card.classList.toggle('highlighted-card', relevant && focusKey !== 'all');
  });

  // Update focus buttons
  document.querySelectorAll('.focus-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.focus === focusKey);
    btn.setAttribute('aria-pressed', btn.dataset.focus === focusKey);
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

function renderActionBar(basics) {
  const bar = el('div', { class: 'action-bar', role: 'toolbar', 'aria-label': 'Resume actions' });

  // PDF Download
  const pdfBtn = el('a', {
    class: 'btn btn-primary',
    href: `${DIST_PATH}/resume.pdf`,
    download: `${basics.name?.replace(/\s+/g, '_')}_Resume.pdf`,
    id: 'btn-download-pdf',
    'aria-label': 'Download resume as PDF',
  });
  pdfBtn.innerHTML = '⬇ Download PDF';

  // Markdown Download
  const mdBtn = el('a', {
    class: 'btn btn-secondary',
    href: `${DIST_PATH}/resume.md`,
    download: `${basics.name?.replace(/\s+/g, '_')}_Resume.md`,
    id: 'btn-download-md',
    'aria-label': 'Download resume as Markdown',
  });
  mdBtn.innerHTML = '📄 Download Markdown';

  // DOCX Download
  const docxBtn = el('a', {
    class: 'btn btn-secondary',
    href: `${DIST_PATH}/resume.docx`,
    download: `${basics.name?.replace(/\s+/g, '_')}_Resume.docx`,
    id: 'btn-download-docx',
    'aria-label': 'Download resume as Word Document',
  });
  docxBtn.innerHTML = '📝 Download DOCX';

  // MCP Button — only shown as an active clipboard button when MCP_URL is a live
  // address (local dev). On the public GitHub Pages site mcpUrl is set to null so
  // we render a passive informational link to the repo instead.
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
    // Public site: show a neutral link to the MCP integration docs on GitHub
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

  if (job.highlights?.length) {
    const ul = el('ul', { class: 'card-highlights' });
    for (const h of job.highlights) {
      const li = el('li');
      li.textContent = h;
      ul.appendChild(li);
    }
    card.appendChild(ul);
  }

  if (job.tags?.length) {
    const tags = el('div', { class: 'card-tags' });
    for (const t of job.tags) {
      const tag = el('span', { class: 'tag' });
      tag.textContent = t;
      tags.appendChild(tag);
    }
    card.appendChild(tags);
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

  // Summary
  if (resume.basics?.summary) {
    const summaryEl = el('p', { class: 'summary-text' });
    summaryEl.textContent = resume.basics.summary;
    main.appendChild(renderSection('Summary', '💡', [], [summaryEl]));
  }

  // Experience
  if (resume.work?.length) {
    const tags = [...new Set(resume.work.flatMap((w) => w.tags || []))];
    const cards = resume.work.map((job, i) => renderWorkCard(job, i * 60));
    main.appendChild(renderSection('Experience', '💼', tags, cards));
  }

  // Skills
  if (resume.skills?.length) {
    const allTags = [...new Set(resume.skills.flatMap((s) => s.tags || []))];
    const grid = el('div', { class: 'skills-grid' });
    resume.skills.forEach((skill, i) => grid.appendChild(renderSkillCard(skill, i * 50)));
    main.appendChild(renderSection('Skills', '⚡', allTags, [grid]));
  }

  // Projects
  if (resume.projects?.length) {
    const allTags = [...new Set(resume.projects.flatMap((p) => p.tags || []))];
    const cards = resume.projects.map((p, i) => renderProjectCard(p, i * 60));
    main.appendChild(renderSection('Projects', '🚀', allTags, cards));
  }

  // Education
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

  // Languages
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

  // References
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
    // Fallback: try to read embedded resume from window.__RESUME__
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

  const app = document.getElementById('app');
  if (!app) return;

  // Update page metadata
  document.title = `${resume.basics.name} — Portfolio`;
  document.querySelector('meta[name="description"]')?.setAttribute(
    'content',
    `Portfolio and resume of ${resume.basics.name}, ${resume.basics.label}.`
  );

  // Render all sections
  app.appendChild(renderHero(resume.basics));
  app.appendChild(renderActionBar(resume.basics));
  app.appendChild(renderFocusSelector());
  app.appendChild(renderResume(resume));

  // Footer
  const footer = el('footer');
  const footerText = el('p', { class: 'footer-text' });
  const mcpFooterHref = MCP_URL || 'https://github.com/Saikojin/Talentscout#readme';
  const mcpFooterLabel = MCP_URL ? 'MCP Server' : 'MCP Integration';
  footerText.innerHTML = `Built with <a href="https://github.com/nathanfox/resume-as-code" target="_blank" rel="noopener">resume-as-code</a> · <a href="${mcpFooterHref}" target="_blank" rel="noopener">${mcpFooterLabel}</a>`;
  footer.appendChild(footerText);
  app.appendChild(footer);

  // Apply initial focus (all)
  applyFocus('all');
}

document.addEventListener('DOMContentLoaded', boot);
