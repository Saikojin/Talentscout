import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle, Table, TableRow, TableCell, WidthType } from 'docx';
import { writeFileSync } from 'fs';

/**
 * compiler/buildDocx.js
 * Generates a Word-compatible .docx resume from resume.json data.
 * Supports the same --include= / --exclude= filtering as build.js via the
 * optional `fieldFilter` callback passed by the caller.
 *
 * @param {Object}   resume       Parsed resume.json object
 * @param {string}   outputPath   Absolute path for the output .docx file
 * @param {Function} [isActive]   (fieldName: string) => boolean filter;
 *                                defaults to () => true (include everything)
 */
export async function buildDocx(resume, outputPath, isActive = () => true) {
  const { basics, work, education, skills, projects, references } = resume;

  const children = [];

  // ── Helper: add a horizontal-rule style section heading ────────────────────
  const addSectionHeading = (title) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 280, after: 120 },
        border: {
          bottom: {
            color: 'cccccc',
            space: 4,
            style: BorderStyle.SINGLE,
            size: 6,
          },
        },
        children: [
          new TextRun({
            text: title.toUpperCase(),
            bold: true,
            size: 22,
            font: 'Arial',
            color: '1a1a2e',
          }),
        ],
      })
    );
  };

  // ── Helper: add a bullet list item ─────────────────────────────────────────
  const addBullet = (text, level = 0) => {
    children.push(
      new Paragraph({
        bullet: { level },
        spacing: { after: 40 },
        children: [
          new TextRun({
            text,
            size: 20,
            font: 'Arial',
          }),
        ],
      })
    );
  };

  // ── Helper: add a sub-section label + bullet list ──────────────────────────
  const addSubSection = (label, items) => {
    if (!items || items.length === 0) return;
    children.push(
      new Paragraph({
        spacing: { before: 100, after: 40 },
        children: [
          new TextRun({
            text: `${label}:`,
            bold: true,
            size: 20,
            font: 'Arial',
            color: '333333',
          }),
        ],
      })
    );
    for (const item of items) addBullet(item);
  };

  // ── Helper: add an inline "chips" line (Skills Used / Tools Used) ──────────
  const addChipLine = (label, items) => {
    if (!items || items.length === 0) return;
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

  // ─── Header: Name ──────────────────────────────────────────────────────────
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 60 },
      children: [
        new TextRun({
          text: basics.name,
          bold: true,
          size: 36,
          font: 'Arial',
          color: '0f3460',
        }),
      ],
    })
  );

  // Label / Subtitle
  if (basics.label) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
        children: [
          new TextRun({
            text: basics.label,
            italics: true,
            size: 20,
            font: 'Arial',
            color: '555555',
          }),
        ],
      })
    );
  }

  // Contact Info Line
  const contactParts = [];
  if (basics.email) contactParts.push(basics.email);
  if (basics.phone && basics.phone !== 'please email') contactParts.push(basics.phone);
  if (basics.location) {
    const loc = basics.location;
    const locParts = [loc.city, loc.region].filter(Boolean);
    if (locParts.length) contactParts.push(locParts.join(', '));
  }
  if (basics.url) contactParts.push(basics.url);

  if (contactParts.length) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 300 },
        children: [
          new TextRun({
            text: contactParts.join('  |  '),
            size: 18,
            font: 'Arial',
            color: '444444',
          }),
        ],
      })
    );
  }

  // ─── Summary ───────────────────────────────────────────────────────────────
  if (basics.summary) {
    addSectionHeading('Summary');
    children.push(
      new Paragraph({
        spacing: { after: 200 },
        children: [
          new TextRun({
            text: basics.summary,
            size: 20,
            font: 'Arial',
          }),
        ],
      })
    );
  }

  // ─── Experience (Work) ─────────────────────────────────────────────────────
  if (work && work.length) {
    addSectionHeading('Professional Experience');

    for (const job of work) {
      // Job title + date on the same paragraph, tab-separated
      const startFmt = job.startDate ? job.startDate.slice(0, 7).replace('-', '/') : '';
      const endFmt   = job.endDate   ? job.endDate.slice(0, 7).replace('-', '/')   : 'Present';
      const dateStr  = `${startFmt} – ${endFmt}`;

      children.push(
        new Paragraph({
          spacing: { before: 160, after: 40 },
          tabStops: [{ type: 'right', position: 9020 }],
          children: [
            new TextRun({ text: `${job.name}  —  ${job.position}`, bold: true, size: 22, font: 'Arial', color: '0f3460' }),
            new TextRun({ text: `\t${dateStr}`, size: 18, font: 'Arial', color: '666666' }),
          ],
        })
      );

      if (job.location && isActive('location')) {
        children.push(
          new Paragraph({
            spacing: { after: 60 },
            children: [
              new TextRun({ text: `📍 ${job.location}`, size: 18, font: 'Arial', color: '888888', italics: true }),
            ],
          })
        );
      }

      if (job.summary) {
        children.push(
          new Paragraph({
            spacing: { after: 80 },
            children: [
              new TextRun({ text: job.summary, size: 19, font: 'Arial', italics: true, color: '444444' }),
            ],
          })
        );
      }

      if (job.highlights && job.highlights.length && isActive('highlights')) {
        for (const highlight of job.highlights) addBullet(highlight);
      }

      if (isActive('keyResponsibilities')) addSubSection('Key Responsibilities', job.keyResponsibilities);
      if (isActive('skillsUsed'))          addChipLine('Skills Used', job.skillsUsed);
      if (isActive('toolsUsed'))           addChipLine('Tools Used', job.toolsUsed);
      if (isActive('challenges'))          addSubSection('Challenges', job.challenges);
      if (isActive('wins'))                addSubSection('Wins', job.wins);
      if (isActive('lessonsLearned'))      addSubSection('Lessons Learned', job.lessonsLearned);

      // Spacer between jobs
      children.push(new Paragraph({ spacing: { after: 80 } }));
    }
  }

  // ─── Skills ────────────────────────────────────────────────────────────────
  if (skills && skills.length) {
    addSectionHeading('Skills Summary');
    for (const skill of skills) {
      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [
            new TextRun({ text: `${skill.name}: `, bold: true, size: 20, font: 'Arial' }),
            new TextRun({ text: skill.keywords ? skill.keywords.join(', ') : '', size: 20, font: 'Arial' }),
          ],
        })
      );
    }
  }

  // ─── Projects ──────────────────────────────────────────────────────────────
  if (projects && projects.length) {
    addSectionHeading('Projects');
    for (const project of projects) {
      const urlText = project.url ? ` (${project.url})` : '';
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({ text: `${project.name}${urlText}`, bold: true, size: 20, font: 'Arial', color: '0f3460' }),
          ],
        })
      );
      if (project.description) {
        children.push(
          new Paragraph({
            spacing: { after: 80 },
            children: [
              new TextRun({ text: project.description, size: 20, font: 'Arial' }),
            ],
          })
        );
      }
      if (project.highlights && project.highlights.length) {
        for (const h of project.highlights) addBullet(h);
      }
    }
  }

  // ─── Education ─────────────────────────────────────────────────────────────
  if (education && education.length) {
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
      if (edu.score) {
        children.push(
          new Paragraph({
            spacing: { after: 60 },
            children: [new TextRun({ text: `GPA: ${edu.score}`, size: 18, font: 'Arial', color: '888888' })],
          })
        );
      }
    }
  }

  // ─── References ────────────────────────────────────────────────────────────
  if (references && references.length) {
    addSectionHeading('References');
    for (const ref of references) {
      children.push(
        new Paragraph({
          spacing: { before: 80, after: 40 },
          children: [
            new TextRun({ text: `"${ref.reference}"`, size: 19, font: 'Arial', italics: true, color: '444444' }),
          ],
        })
      );
      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [
            new TextRun({ text: `— ${ref.name}`, size: 18, font: 'Arial', bold: true }),
          ],
        })
      );
    }
  }

  // ─── Assemble and write ────────────────────────────────────────────────────
  const doc = new Document({
    creator: basics.name,
    title: `${basics.name} — Resume`,
    description: `Resume of ${basics.name}`,
    styles: {
      default: {
        document: {
          run: { font: 'Arial', size: 20 },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            margin: { top: 720, right: 900, bottom: 720, left: 900 },
          },
        },
        children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  writeFileSync(outputPath, buffer);
}
