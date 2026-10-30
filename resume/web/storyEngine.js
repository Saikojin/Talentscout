/**
 * web/storyEngine.js
 * 
 * Browser-compatible Algorithmic Natural Language Generation (NLG) engine
 * that transforms structured living resume data into rich, cohesive narrative chapters.
 * Attached to window.StoryEngine.
 */

(function (root) {
  'use strict';

  // ─── Variation Banks ──────────────────────────────────────────────────────────

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

  // ─── Helpers ────────────────────────────────────────────────────────────────

  function formatDate(dateStr) {
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

  // ─── Chapter Generator ──────────────────────────────────────────────────────

  function generateChapter(job, index, total, nextJob = null, options = {}) {
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

  // ─── Back of the Book Synopsis ─────────────────────────────────────────────

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

  // ─── Full Story Odyssey ─────────────────────────────────────────────────────

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

    // Back of the Book
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

  // Export to global window object
  const StoryEngine = {
    formatDate,
    calculateDateSpan,
    generateChapter,
    generateBackOfTheBook,
    generateStoryChapters,
    generateStoryMarkdown
  };

  root.StoryEngine = StoryEngine;

})(typeof window !== 'undefined' ? window : globalThis);
