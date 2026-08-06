/**
 * compiler/atsFormatter.js
 * Synthesizes or retrieves ATS-standard bullet points (CAR, STAR, LPS, ELITE, WHO)
 * for a work experience entry.
 */

/**
 * Format a single work entry into ATS bullets based on the requested style.
 * 
 * @param {Object} job - Work entry from resume.json
 * @param {string} [style='CAR'] - CAR | STAR | LPS | ELITE | WHO
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
    const win = wins[i] || highlights[i] || responsibilities[i];
    if (!win) continue;

    const challenge = challenges[i] || challenges[0] || 'Addressing key quality and process bottlenecks';
    const resp = responsibilities[i] || responsibilities[0] || 'executed key engineering deliverables';
    const toolStr = tools.length > 0 ? tools.slice(0, 3).join(', ') : 'modern industry tooling';
    const skillStr = skills.length > 0 ? skills.slice(0, 2).join(', ') : 'technical subject matter expertise';
    const lesson = lessons[i] || lessons[0] || 'optimizing technical workflows';

    switch (normalizedStyle) {
      case 'STAR': {
        // Situation -> Task -> Action -> Result
        const situation = job.summary ? job.summary.split('.')[0] : `Targeted ${job.name} initiatives`;
        bullets.push(`[Situation] ${situation}. [Task] Focused on ${resp.toLowerCase()}. [Action] Leveraged ${toolStr} to overcome: ${challenge.toLowerCase()}. [Result] ${win}.`);
        break;
      }
      case 'LPS': {
        // Leadership -> Problem-Solving -> Strategy/Success
        const leadVerb = job.tags?.includes('leadership') ? 'Spearheaded' : 'Drove';
        bullets.push(`${leadVerb} solution for ${challenge.toLowerCase()} by applying ${skillStr}; successfully achieved: ${win}.`);
        break;
      }
      case 'ELITE': {
        // Elevate -> Leverage -> Illustrate -> Transfer -> Execute
        bullets.push(`Elevated team capacity by leveraging ${toolStr} to tackle ${challenge.toLowerCase()}; illustrated through ${win}, transferring learnings to ${lesson.toLowerCase()}.`);
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
        bullets.push(`Challenge: ${challenge}. Action: Executed ${resp.toLowerCase()} utilizing ${toolStr}. Result: ${win}.`);
        break;
      }
    }
  }

  return bullets;
}
