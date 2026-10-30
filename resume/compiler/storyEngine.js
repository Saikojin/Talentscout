/**
 * compiler/storyEngine.js
 * 
 * Algorithmic Natural Language Generation (NLG) engine that transforms
 * structured living resume data (challenges, tools, wins, lessons, dates)
 * into a rich, cohesive narrative without relying on any external LLM.
 * 
 * Capabilities:
 * - Deterministic slot-filling with combinatorial variation banks (anti-repetition)
 * - Chronological bridging & date calculations
 * - Perspective switching: Third-person ("Thomas / He") or First-person ("I / My")
 * - Chronological or reverse-chronological narrative flow
 * - Outputs structured Chapter objects, Markdown, and standalone HTML
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { fileURLToPath } from 'url';
import { resolve, dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const DIST = resolve(ROOT, 'dist');

// ─── Variation & Sentence Banks ───────────────────────────────────────────────

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

// ─── Helpers ──────────────────────────────────────────────────────────────────

export function formatDate(dateStr) {
  if (!dateStr) return 'Present';
  const match = String(dateStr).match(/^(\d{4})-(\d{2})/);
  if (!match) return dateStr;
  try {
    return new Date(Number(match[1]), Number(match[2]) - 1, 1)
      .toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
  } catch {
    return dateStr;
  }
}

export function calculateDateSpan(startDateStr, endDateStr) {
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

// ─── Chapter Generator ────────────────────────────────────────────────────────

/**
 * Generate a structured Chapter for a single work entry.
 * 
 * @param {Object} job - Work entry from resume.json
 * @param {number} index - Index of this chapter (0-based)
 * @param {number} total - Total count of jobs
 * @param {Object} [nextJob] - The subsequent chronological job (for transitions)
 * @param {Object} [options] - Options: perspective ('third'|'first'), candidateName
 * @returns {Object} Structured chapter object
 */
export function generateChapter(job, index, total, nextJob = null, options = {}) {
  const perspective = options.perspective === 'first' ? 'first' : 'third';
  const name = options.candidateName || 'Thomas';
  const chapterNumber = index + 1;

  const dateSpan = `${formatDate(job.startDate)} – ${formatDate(job.endDate)}`;
  const duration = calculateDateSpan(job.startDate, job.endDate);

  // 1. Hook & Opening
  const openBank = perspective === 'first' ? OPENING_TEMPLATES_FIRST : OPENING_TEMPLATES_THIRD;
  const openFn = openBank[index % openBank.length];
  const openingSentence = perspective === 'first'
    ? openFn(job.position, job.name, job.location, formatDate(job.startDate))
    : openFn(name, job.position, job.name, job.location, formatDate(job.startDate));

  // Context sentence from summary
  const contextSentence = job.summary ? cleanSentence(job.summary) : '';

  // 2. The Conflict / Crucible (Challenges)
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

  // Secondary challenge or responsibility detail
  let secondaryDetail = '';
  if (job.challenges && job.challenges.length > 1) {
    secondaryDetail = `Compounding this, ${lowerFirst(cleanSentence(job.challenges[1]))}`;
  } else if (job.keyResponsibilities && job.keyResponsibilities.length > 1) {
    secondaryDetail = `Key operational duties encompassed ${lowerFirst(cleanSentence(job.keyResponsibilities[1]))}`;
  }

  // 3. The Technical Quest / Strategy (Tools + Skills)
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

  // 4. The Breakthrough / Climax (Wins)
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

  // 5. The Moral / Reflection (Lessons Learned)
  let lessonNarrative = '';
  const rawLesson = job.lessonsLearned?.[0] || '';
  if (rawLesson) {
    const lessonBank = perspective === 'first' ? LESSON_LEAD_INS_FIRST : LESSON_LEAD_INS_THIRD;
    const lessonLead = lessonBank[index % lessonBank.length];
    lessonNarrative = lessonLead + lowerFirst(cleanSentence(rawLesson));
  }

  // 6. Transition to Next Chapter
  let transitionNarrative = '';
  if (nextJob) {
    const transBank = perspective === 'first' ? TRANSITION_TEMPLATES_FIRST : TRANSITION_TEMPLATES_THIRD;
    const transFn = transBank[index % transBank.length];
    transitionNarrative = transFn(nextJob.name);
  }

  // Construct readable paragraph bodies
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

// ─── Back of the Book Synopsis ───────────────────────────────────────────────

/**
 * Generates an executive "Back of the Book" synopsis capturing the essence of the entire odyssey.
 * 
 * @param {Object} resumeData - Parsed resume.json
 * @param {Object} [options] - Options (perspective: 'third'|'first')
 * @returns {Object} Structured Back of the Book object
 */
export function generateBackOfTheBook(resumeData, options = {}) {
  const perspective = options.perspective === 'first' ? 'first' : 'third';
  const basics = resumeData.basics || {};
  const candidateName = basics.name || 'Thomas S. Snyder';
  const workEntries = resumeData.work || [];

  // Calculate career duration
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

// ─── Full Story Odyssey ───────────────────────────────────────────────────────

/**
 * Generates all chapters for the resume.
 * 
 * @param {Object} resumeData - Parsed resume.json
 * @param {Object} [options]
 * @returns {Object} Object with metadata, prologue, chapters, and epilogue
 */
export function generateStoryChapters(resumeData, options = {}) {
  const perspective = options.perspective === 'first' ? 'first' : 'third';
  const order = options.order === 'reverse' ? 'reverse' : 'chronological';
  const basics = resumeData.basics || {};
  const candidateName = basics.name || 'Thomas S. Snyder';

  let workEntries = [...(resumeData.work || [])];
  
  // Sort chronologically (oldest first) if chronological
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

  // Calculate career span
  const firstJob = order === 'chronological' ? workEntries[0] : workEntries[workEntries.length - 1];
  const lastJob = order === 'chronological' ? workEntries[workEntries.length - 1] : workEntries[0];
  const careerDuration = firstJob && lastJob ? calculateDateSpan(firstJob.startDate, lastJob.endDate) : '25+ years';

  // Back of the Book synopsis
  const backOfTheBook = generateBackOfTheBook(resumeData, { perspective });

  // Generate Prologue
  let prologue = '';
  if (perspective === 'first') {
    prologue = `Over the course of ${careerDuration || 'more than two decades'}, my career has been defined by an obsession with software quality, technical resilience, and pragmatic automation. From testing foundational console games and operating system platforms to architecting modern web frameworks and integrating autonomous AI tooling, this is the story of challenges confronted, systems transformed, and lessons learned along the journey.`;
  } else {
    prologue = `Over the course of ${careerDuration || 'more than two decades'}, ${candidateName} has traversed the evolving landscape of software quality engineering. From the high-stakes discipline of early console titles and operating systems to cloud APIs, enterprise test automation, and AI-assisted workflows, this narrative chronicles the technical crucible, key milestones, and architectural insights that shaped ${candidateName}'s career.`;
  }

  // Generate Epilogue
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

// ─── Markdown Generator ───────────────────────────────────────────────────────

/**
 * Convert story chapters to GitHub Flavored Markdown.
 * 
 * @param {Object} resumeData 
 * @param {Object} [options] 
 * @returns {string} Markdown text
 */
export function generateStoryMarkdown(resumeData, options = {}) {
  const story = generateStoryChapters(resumeData, options);
  const lines = [];

  lines.push(`# ${story.candidateName} — The Career Odyssey`);
  if (story.label) lines.push(`*${story.label}*`);
  lines.push('');
  lines.push('---');
  lines.push('');

  // Back of the Book synopsis
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

// ─── HTML Generator ───────────────────────────────────────────────────────────

/**
 * Builds a standalone reader-friendly HTML document.
 */
export function generateStoryHtml(markdownContent, candidateName) {
  let md = markdownContent;

  // Wrap Back of the Book section in card container
  md = md.replace(/^## 📕 Back of the Book\n([\s\S]*?)\n---/m, (match, inner) => {
    return `<div class="back-of-book-card">\n<h2>📕 Back of the Book</h2>\n${inner}\n</div>\n---`;
  });

  // Simple markdown-to-html replacement for headings and blockquotes
  let bodyHtml = md
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^\*([^\*]+)\*$/gm, '<p class="lead"><em>$1</em></p>')
    .replace(/^> 💡 \*\*Core (?:Takeaway|Mantra):\*\* "(.+)"$/gm, '<div class="lesson-callout"><span class="lesson-icon">💡</span><strong>Core Takeaway:</strong> <em>“$1”</em></div>')
    .replace(/^> \*"([^\*]+)"\*$/gm, '<blockquote class="tagline-quote">“$1”</blockquote>')
    .replace(/^---$/gm, '<hr class="chapter-divider" />')
    .split('\n\n')
    .map(p => {
      p = p.trim();
      if (!p) return '';
      if (p.startsWith('<h') || p.startsWith('<div') || p.startsWith('</div>') || p.startsWith('<hr') || p.startsWith('<blockquote')) {
        return p;
      }
      if (p.includes('\n- ') || p.startsWith('- ')) {
        const items = p.split('\n').filter(line => line.startsWith('- ')).map(line => {
          const itemText = line.slice(2).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
          return `<li>${itemText}</li>`;
        });
        return `<ul class="stats-list">${items.join('')}</ul>`;
      }
      return `<p>${p.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/\*([^*]+)\*/g, '<em>$1</em>')}</p>`;
    })
    .filter(Boolean)
    .join('\n');

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${candidateName} — The Career Odyssey</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700&family=Inter:wght@400;500;600&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;1,6..72,400&display=swap');
    
    :root {
      --bg: #0d1117;
      --card-bg: #161b22;
      --text: #e6edf3;
      --text-muted: #8b949e;
      --accent: #58a6ff;
      --gold: #d29922;
      --border: #30363d;
    }
    
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    
    body {
      background-color: var(--bg);
      color: var(--text);
      font-family: 'Newsreader', Georgia, serif;
      font-size: 1.18rem;
      line-height: 1.8;
      max-width: 780px;
      margin: 0 auto;
      padding: 60px 24px 100px;
    }
    
    h1 {
      font-family: 'Cinzel', serif;
      font-size: 2.4rem;
      font-weight: 700;
      color: #fff;
      text-align: center;
      letter-spacing: 0.04em;
      margin-bottom: 8px;
    }
    
    .lead {
      text-align: center;
      font-family: 'Inter', sans-serif;
      font-size: 0.95rem;
      color: var(--accent);
      margin-bottom: 40px;
    }
    
    h2 {
      font-family: 'Inter', sans-serif;
      font-size: 1.35rem;
      font-weight: 600;
      color: var(--gold);
      margin-top: 48px;
      margin-bottom: 8px;
      letter-spacing: -0.01em;
    }
    
    p {
      margin-bottom: 22px;
      color: #c9d1d9;
    }
    
    .chapter-divider {
      border: none;
      height: 1px;
      background: linear-gradient(90deg, transparent, var(--border), transparent);
      margin: 48px 0;
    }
    
    .back-of-book-card {
      background: linear-gradient(145deg, #161b22, #0d1117);
      border: 1px solid rgba(210, 153, 34, 0.4);
      border-radius: 12px;
      padding: 32px;
      margin: 32px 0 48px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    }
    
    .back-of-book-card h2 {
      margin-top: 0;
      color: var(--gold);
    }
    
    .tagline-quote {
      font-size: 1.22rem;
      font-style: italic;
      color: #fff;
      border-left: 3px solid var(--accent);
      padding-left: 16px;
      margin: 16px 0 24px;
    }
    
    .lesson-callout {
      background: rgba(210, 153, 34, 0.08);
      border-left: 3px solid var(--gold);
      padding: 16px 20px;
      border-radius: 0 8px 8px 0;
      margin: 24px 0 32px;
      font-family: 'Inter', sans-serif;
      font-size: 0.95rem;
      color: var(--text);
    }
    
    .lesson-icon {
      margin-right: 8px;
    }
    
    @media print {
      body { background: #fff; color: #111; font-size: 11pt; padding: 0; }
      h1 { color: #000; font-size: 18pt; }
      h2 { color: #222; font-size: 13pt; }
      p { color: #333; }
      .lesson-callout { background: #f9f9f9; border-color: #666; }
    }
  </style>
</head>
<body>
  ${bodyHtml}
</body>
</html>`;
}

// ─── CLI Entry Point ──────────────────────────────────────────────────────────

async function runCli() {
  const resumeRaw = readFileSync(resolve(ROOT, 'data', 'resume.json'), 'utf8');
  const resume = JSON.parse(resumeRaw);
  const perspective = process.argv.includes('--first') ? 'first' : 'third';
  const order = process.argv.includes('--reverse') ? 'reverse' : 'chronological';

  console.log(`📖 Generating Career Story for ${resume.basics?.name || 'User'} (${perspective}-person, ${order})...`);

  if (!existsSync(DIST)) mkdirSync(DIST, { recursive: true });

  const md = generateStoryMarkdown(resume, { perspective, order });
  const mdPath = resolve(DIST, 'story.md');
  writeFileSync(mdPath, md, 'utf8');
  console.log(`✅ dist/story.md`);

  const html = generateStoryHtml(md, resume.basics?.name || 'Resume Story');
  const htmlPath = resolve(DIST, 'story.html');
  writeFileSync(htmlPath, html, 'utf8');
  console.log(`✅ dist/story.html`);
}

if (process.argv[1] && process.argv[1].endsWith('storyEngine.js')) {
  runCli().catch(err => {
    console.error('Story generation failed:', err);
    process.exit(1);
  });
}
