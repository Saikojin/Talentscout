#!/usr/bin/env node
/**
 * compiler/adapters/workday.js
 * Exports resume.json as a Workday integration profile object.
 * Output: dist/workday_profile.json
 */
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..', '..');
const DIST = resolve(ROOT, 'dist');

if (!existsSync(DIST)) mkdirSync(DIST, { recursive: true });

const resume = JSON.parse(readFileSync(resolve(ROOT, 'data', 'resume.json'), 'utf8'));
const { basics, work, education, skills } = resume;

const nameParts = (basics?.name ?? '').split(' ');

const workday = {
  legalName: {
    firstName: nameParts[0] ?? '',
    lastName: nameParts.slice(1).join(' ') ?? '',
    formattedName: basics?.name ?? '',
  },
  contactInformation: {
    primaryEmail: basics?.email ?? null,
    primaryPhone: basics?.phone ?? null,
    primaryUrl: basics?.url ?? null,
    city: basics?.location?.city ?? null,
    state: basics?.location?.region ?? null,
    country: basics?.location?.countryCode ?? null,
    socialProfiles: (basics?.profiles ?? []).map((p) => ({
      type: p.network,
      url: p.url,
      username: p.username,
    })),
  },
  workExperience: (work ?? []).map((job) => ({
    employer: job.name,
    jobTitle: job.position,
    startDate: job.startDate ?? null,
    endDate: job.endDate || null,
    isCurrent: !job.endDate || job.endDate === '',
    description: job.summary ?? '',
    achievements: job.highlights ?? [],
    tags: job.tags ?? [],
  })),
  education: (education ?? []).map((edu) => ({
    school: edu.institution,
    degree: edu.studyType,
    fieldOfStudy: edu.area,
    startDate: edu.startDate ?? null,
    endDate: edu.endDate ?? null,
    gpa: edu.score ?? null,
    courses: edu.courses ?? [],
  })),
  skills: (skills ?? []).map((s) => ({
    skillCategory: s.name,
    proficiencyLevel: s.level ?? 'Unknown',
    skillKeywords: s.keywords ?? [],
    tags: s.tags ?? [],
  })),
  summary: basics?.summary ?? '',
};

const outPath = resolve(DIST, 'workday_profile.json');
writeFileSync(outPath, JSON.stringify(workday, null, 2), 'utf8');

console.log(`✅  dist/workday_profile.json`);
console.log(`    Name      : ${workday.legalName.formattedName}`);
console.log(`    Email     : ${workday.contactInformation.primaryEmail}`);
console.log(`    Jobs      : ${workday.workExperience.length}`);
console.log(`    Skills    : ${workday.skills.length}`);
