/**
 * compiler/atsFormatter.js
 * Synthesizes or retrieves ATS-standard bullet points (CAR, CARL, STAR, LPS, ELITE, WHO)
 * for a work experience entry.
 */

export const ATS_STYLES = ['CAR', 'CARL', 'STAR', 'LPS', 'ELITE', 'WHO'];

export const ATS_STYLE_META = {
  CAR: {
    label: 'CAR',
    name: 'Challenge · Action · Result',
    description: 'Concise problem-to-outcome bullets ideal for technical ATS scanning.',
  },
  CARL: {
    label: 'CARL',
    name: 'Context · Action · Result · Learning',
    description: 'High-impact bullets ending with concrete learnings that pre-empt interview follow-ups.',
  },
  STAR: {
    label: 'STAR',
    name: 'Situation · Task · Action · Result',
    description: 'Structured behavioral framing mapping scope, ownership, execution, and measurable win.',
  },
  LPS: {
    label: 'LPS',
    name: 'Leadership · Problem-Solving · Success',
    description: 'Ownership-forward bullets emphasizing initiative and technical problem resolution.',
  },
  ELITE: {
    label: 'ELITE',
    name: 'Elevate · Leverage · Illustrate · Transfer · Execute',
    description: 'Senior/Staff framing highlighting force-multiplication and knowledge transfer.',
  },
  WHO: {
    label: 'WHO',
    name: 'What · How · Outcome',
    description: 'Ultra-scannable recruiter format pairing deliverables, tooling, and results.',
  },
};

function cleanClause(str) {
  return String(str || '').trim().replace(/\.+$/, '');
}

function lowerFirst(str) {
  const s = cleanClause(str);
  if (!s) return '';
  // Preserve acronyms like AWS, API, QA, MCP, SDK, CI/CD, WTT, HLK, etc.
  if (/^[A-Z]{2,}/.test(s)) return s;
  return s.charAt(0).toLowerCase() + s.slice(1);
}

/**
 * Format a single work entry into ATS bullets based on the requested style.
 *
 * @param {Object} job - Work entry from resume.json
 * @param {string} [style='CAR'] - CAR | CARL | STAR | LPS | ELITE | WHO
 * @returns {string[]} Array of formatted bullet points
 */
export function formatWorkEntryAts(job, style = 'CAR') {
  const normalizedStyle = style ? style.toUpperCase() : 'CAR';

  // 1. Check if pre-authored bullets exist for this style
  if (job.atsBullets && Array.isArray(job.atsBullets[normalizedStyle]) && job.atsBullets[normalizedStyle].length > 0) {
    return job.atsBullets[normalizedStyle];
  }

  // 2. Fallback Synthesis Logic
  const challenges = job.challenges || [];
  const responsibilities = job.keyResponsibilities || [];
  const wins = job.wins || [];
  const highlights = job.highlights || [];
  const tools = job.toolsUsed || [];
  const skills = job.skillsUsed || [];
  const lessons = job.lessonsLearned || [];

  const bullets = [];
  const maxCount = Math.max(wins.length, highlights.length, responsibilities.length, 1);

  for (let i = 0; i < maxCount; i++) {
    const rawWin = wins[i] || highlights[i] || responsibilities[i];
    if (!rawWin) continue;

    const win = cleanClause(rawWin);
    const challenge = cleanClause(challenges[i] || challenges[0] || 'Addressing key quality and process bottlenecks');
    const resp = cleanClause(responsibilities[i] || responsibilities[0] || 'executed key engineering deliverables');
    const toolStr = tools.length > 0 ? tools.slice(0, 3).join(', ') : 'modern industry tooling';
    const skillStr = skills.length > 0 ? skills.slice(0, 2).join(', ') : 'technical subject matter expertise';
    const lesson = cleanClause(lessons[i] || lessons[0] || 'Standardizing repeatable quality workflows and transparent documentation accelerates engineering velocity');
    const summaryFirst = job.summary ? cleanClause(job.summary.split('.')[0]) : `Targeted ${job.name} initiatives`;

    switch (normalizedStyle) {
      case 'CARL': {
        // Context -> Action -> Result -> Learning
        const context = challenges[i]
          ? `${summaryFirst}; faced ${lowerFirst(challenges[i])}`
          : `${summaryFirst} while addressing ${lowerFirst(challenge)}`;
        bullets.push(
          `Context: ${context}. Action: ${resp} utilizing ${toolStr}. Result: ${win}. Learning: ${lesson}.`
        );
        break;
      }
      case 'STAR': {
        // Situation -> Task -> Action -> Result
        bullets.push(
          `[Situation] ${summaryFirst}. [Task] Focused on ${lowerFirst(resp)}. [Action] Leveraged ${toolStr} to overcome: ${lowerFirst(challenge)}. [Result] ${win}.`
        );
        break;
      }
      case 'LPS': {
        // Leadership -> Problem-Solving -> Strategy/Success
        const leadVerb = job.tags?.includes('leadership') ? 'Spearheaded' : 'Drove';
        bullets.push(
          `${leadVerb} solution for ${lowerFirst(challenge)} by applying ${skillStr}; successfully achieved: ${win}.`
        );
        break;
      }
      case 'ELITE': {
        // Elevate -> Leverage -> Illustrate -> Transfer -> Execute
        bullets.push(
          `Elevated team capacity by leveraging ${toolStr} to tackle ${lowerFirst(challenge)}; illustrated through ${win}, transferring learnings to ${lowerFirst(lesson)}.`
        );
        break;
      }
      case 'WHO': {
        // What did you do? How did you do it? Outcome achieved
        bullets.push(`What: ${resp}. How: Utilized ${toolStr} and ${skillStr}. Outcome: ${win}.`);
        break;
      }
      case 'CAR':
      default: {
        // Challenge -> Action -> Result
        bullets.push(`Challenge: ${challenge}. Action: ${resp} utilizing ${toolStr}. Result: ${win}.`);
        break;
      }
    }
  }

  return bullets;
}
