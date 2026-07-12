import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, BorderStyle } from 'docx';
import { writeFileSync } from 'fs';

export async function buildDocx(resume, outputPath) {
  const { basics, work, education, skills, projects, references } = resume;

  const children = [];

  // Header: Name
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({
          text: basics.name,
          bold: true,
          size: 32,
          font: 'Arial',
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
            color: '666666',
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

  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 240 },
      children: [
        new TextRun({
          text: contactParts.join('  |  '),
          size: 18,
          font: 'Arial',
        }),
      ],
    })
  );

  // Section divider utility
  const addSectionHeading = (title) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 240, after: 120 },
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
            size: 24,
            font: 'Arial',
            color: '111111',
          }),
        ],
      })
    );
  };

  // Summary
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

  // Experience (Work)
  if (work && work.length) {
    addSectionHeading('Professional Experience');
    for (const job of work) {
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: `${job.name} - ${job.position}`,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
            new TextRun({
              text: `\t${job.startDate} to ${job.endDate || 'Present'}`,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
          ],
        })
      );

      if (job.summary) {
        children.push(
          new Paragraph({
            spacing: { after: 80 },
            children: [
              new TextRun({
                text: job.summary,
                size: 20,
                font: 'Arial',
                italics: true,
              }),
            ],
          })
        );
      }

      if (job.highlights && job.highlights.length) {
        for (const highlight of job.highlights) {
          children.push(
            new Paragraph({
              bullet: { level: 0 },
              spacing: { after: 40 },
              children: [
                new TextRun({
                  text: highlight,
                  size: 20,
                  font: 'Arial',
                }),
              ],
            })
          );
        }
      }
    }
  }

  // Skills
  if (skills && skills.length) {
    addSectionHeading('Skills Summary');
    for (const skill of skills) {
      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [
            new TextRun({
              text: `${skill.name}: `,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
            new TextRun({
              text: skill.keywords ? skill.keywords.join(', ') : '',
              size: 20,
              font: 'Arial',
            }),
          ],
        })
      );
    }
  }

  // Projects
  if (projects && projects.length) {
    addSectionHeading('Projects');
    for (const project of projects) {
      const urlText = project.url ? ` (${project.url})` : '';
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: `${project.name}${urlText}`,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
          ],
        })
      );

      children.push(
        new Paragraph({
          spacing: { after: 80 },
          children: [
            new TextRun({
              text: project.description,
              size: 20,
              font: 'Arial',
            }),
          ],
        })
      );

      if (project.highlights && project.highlights.length) {
        for (const highlight of project.highlights) {
          children.push(
            new Paragraph({
              bullet: { level: 0 },
              spacing: { after: 40 },
              children: [
                new TextRun({
                  text: highlight,
                  size: 20,
                  font: 'Arial',
                }),
              ],
            })
          );
        }
      }
    }
  }

  // Education
  if (education && education.length) {
    addSectionHeading('Education');
    for (const edu of education) {
      children.push(
        new Paragraph({
          spacing: { before: 120, after: 40 },
          children: [
            new TextRun({
              text: `${edu.institution} - ${edu.studyType} in ${edu.area}`,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
            new TextRun({
              text: `\t${edu.startDate} to ${edu.endDate || 'Present'}`,
              bold: true,
              size: 20,
              font: 'Arial',
            }),
          ],
        })
      );
    }
  }

  const doc = new Document({
    sections: [
      {
        properties: {},
        children: children,
      },
    ],
  });

  const buffer = await Packer.toBuffer(doc);
  writeFileSync(outputPath, buffer);
}
