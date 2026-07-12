#!/usr/bin/env node
/**
 * compiler/adapters/greenhouse.js
 * Exports resume.json as a Greenhouse Harvest API candidate object.
 * Output: dist/greenhouse_application.json
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
const { basics, work, education, skills, projects } = resume;

const [firstName, ...lastParts] = (basics?.name ?? 'Unknown Unknown').split(' ');
const lastName = lastParts.join(' ') || 'Unknown';

const greenhouse = {
  first_name: firstName,
  last_name: lastName,
  email_addresses: [{ value: basics?.email, type: 'personal' }].filter((e) => e.value),
  phone_numbers: basics?.phone ? [{ value: basics.phone, type: 'mobile' }] : [],
  addresses: basics?.location
    ? [
        {
          value: [basics.location.address, basics.location.city, basics.location.region, basics.location.countryCode]
            .filter(Boolean)
            .join(', '),
          type: 'home',
        },
      ]
    : [],
  websites: (basics?.profiles ?? []).map((p) => ({ url: p.url, type: p.network.toLowerCase() })).concat(
    basics?.url ? [{ url: basics.url, type: 'personal' }] : []
  ),
  educations: (education ?? []).map((edu) => ({
    school_name: edu.institution,
    degree: edu.studyType,
    discipline: edu.area,
    start_date: edu.startDate?.slice(0, 10) ?? null,
    end_date: edu.endDate?.slice(0, 10) ?? null,
  })),
  employments: (work ?? []).map((job) => ({
    company_name: job.name,
    title: job.position,
    start_date: job.startDate?.slice(0, 10) ?? null,
    end_date: job.endDate?.slice(0, 10) ?? null,
    current: !job.endDate || job.endDate === '',
    body: [job.summary, ...(job.highlights ?? [])].filter(Boolean).join('\n- '),
  })),
  custom_fields: {
    skills_summary: (skills ?? []).map((s) => s.name).join('; '),
    github_url: basics?.profiles?.find((p) => p.network === 'GitHub')?.url ?? null,
    linkedin_url: basics?.profiles?.find((p) => p.network === 'LinkedIn')?.url ?? null,
    notable_projects: (projects ?? [])
      .slice(0, 3)
      .map((p) => p.name)
      .join(', '),
  },
};

const outPath = resolve(DIST, 'greenhouse_application.json');
writeFileSync(outPath, JSON.stringify(greenhouse, null, 2), 'utf8');

console.log(`✅  dist/greenhouse_application.json`);
console.log(`    Candidate : ${greenhouse.first_name} ${greenhouse.last_name}`);
console.log(`    Emails    : ${greenhouse.email_addresses.map((e) => e.value).join(', ')}`);
console.log(`    Jobs      : ${greenhouse.employments.length}`);
console.log(`    Education : ${greenhouse.educations.length}`);
