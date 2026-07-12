/**
 * mcp-server/src/index.ts
 * TalentScout MCP Server
 * Exposes resume data as MCP tools for AI agent interoperability.
 * Supports both stdio (local) and HTTP (remote) transports.
 *
 * Tools:
 *   get_basics          - Returns candidate contact/profile info
 *   get_experience      - Returns work history (optional company filter)
 *   get_skills          - Returns skills (optional keyword search)
 *   get_education       - Returns education entries
 *   get_projects        - Returns projects (optional tag filter)
 *   search_capabilities - Full-text search across skills, work, projects
 *   generate_ats_profile - Returns a flat ATS-ready object
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { readFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, "..", "..");

// ─── Load Resume Data ─────────────────────────────────────────────────────────
interface ResumeBasics {
  name: string;
  label?: string;
  email: string;
  phone?: string;
  url?: string;
  summary?: string;
  location?: {
    city?: string;
    region?: string;
    countryCode?: string;
  };
  profiles?: Array<{ network: string; username: string; url?: string }>;
}

interface WorkEntry {
  name: string;
  position: string;
  url?: string;
  startDate: string;
  endDate?: string;
  summary?: string;
  highlights?: string[];
  tags?: string[];
}

interface SkillEntry {
  name: string;
  level?: string;
  keywords?: string[];
  tags?: string[];
}

interface EducationEntry {
  institution: string;
  area: string;
  studyType: string;
  startDate?: string;
  endDate?: string;
  score?: string;
  courses?: string[];
}

interface ProjectEntry {
  name: string;
  description: string;
  highlights?: string[];
  keywords?: string[];
  url?: string;
  tags?: string[];
  roles?: string[];
}

interface Resume {
  basics: ResumeBasics;
  work?: WorkEntry[];
  skills?: SkillEntry[];
  education?: EducationEntry[];
  projects?: ProjectEntry[];
  awards?: Array<{ title: string; awarder: string; date?: string; summary?: string }>;
  languages?: Array<{ language: string; fluency: string }>;
}

let resume: Resume;
try {
  resume = JSON.parse(readFileSync(resolve(ROOT, "data", "resume.json"), "utf8"));
} catch (err: unknown) {
  const msg = err instanceof Error ? err.message : String(err);
  console.error(`Failed to load resume.json: ${msg}`);
  process.exit(1);
}

// ─── MCP Server Setup ─────────────────────────────────────────────────────────
const server = new McpServer({
  name: "talentscout-resume-mcp",
  version: "1.0.0",
});

// ─── Tool: get_basics ─────────────────────────────────────────────────────────
server.registerTool(
  "get_basics",
  {
    description:
      "Returns the candidate's basic information: name, title, contact details, location, and social profiles.",
    inputSchema: {},
  },
  async () => {
    const { basics } = resume;
    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(
            {
              name: basics.name,
              label: basics.label,
              email: basics.email,
              phone: basics.phone,
              url: basics.url,
              summary: basics.summary,
              location: basics.location,
              profiles: basics.profiles,
            },
            null,
            2
          ),
        },
      ],
    };
  }
);

// ─── Tool: get_experience ─────────────────────────────────────────────────────
server.registerTool(
  "get_experience",
  {
    description:
      "Returns all work history entries. Optionally filter by company name (partial, case-insensitive match).",
    inputSchema: {
      company: z
        .string()
        .optional()
        .describe("Optional company name to filter by (case-insensitive partial match)"),
    },
  },
  async ({ company }) => {
    let work = resume.work ?? [];
    if (company) {
      const q = company.toLowerCase();
      work = work.filter((w) => w.name.toLowerCase().includes(q));
    }
    return {
      content: [{ type: "text", text: JSON.stringify(work, null, 2) }],
    };
  }
);

// ─── Tool: get_skills ─────────────────────────────────────────────────────────
server.registerTool(
  "get_skills",
  {
    description:
      "Returns the candidate's skills. Optionally search by keyword (searches skill names and keywords).",
    inputSchema: {
      keyword: z
        .string()
        .optional()
        .describe("Optional keyword to filter skills (case-insensitive)"),
    },
  },
  async ({ keyword }) => {
    let skills = resume.skills ?? [];
    if (keyword) {
      const q = keyword.toLowerCase();
      skills = skills.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.keywords?.some((k) => k.toLowerCase().includes(q))
      );
    }
    return {
      content: [{ type: "text", text: JSON.stringify(skills, null, 2) }],
    };
  }
);

// ─── Tool: get_education ─────────────────────────────────────────────────────
server.registerTool(
  "get_education",
  {
    description: "Returns the candidate's education history.",
    inputSchema: {},
  },
  async () => {
    return {
      content: [
        { type: "text", text: JSON.stringify(resume.education ?? [], null, 2) },
      ],
    };
  }
);

// ─── Tool: get_projects ───────────────────────────────────────────────────────
server.registerTool(
  "get_projects",
  {
    description:
      "Returns the candidate's projects. Optionally filter by tag (e.g. 'frontend', 'open-source', 'backend').",
    inputSchema: {
      tag: z
        .string()
        .optional()
        .describe("Optional tag to filter projects (e.g. 'frontend', 'open-source')"),
    },
  },
  async ({ tag }) => {
    let projects = resume.projects ?? [];
    if (tag) {
      const q = tag.toLowerCase();
      projects = projects.filter((p) => p.tags?.some((t) => t.toLowerCase().includes(q)));
    }
    return {
      content: [{ type: "text", text: JSON.stringify(projects, null, 2) }],
    };
  }
);

// ─── Tool: search_capabilities ────────────────────────────────────────────────
server.registerTool(
  "search_capabilities",
  {
    description:
      "Full-text search across the candidate's skills, work experience highlights, and project descriptions. Returns matching items with source context.",
    inputSchema: {
      query: z.string().describe("Search query string (case-insensitive)"),
    },
  },
  async ({ query }) => {
    const q = query.toLowerCase();
    const results: Array<{ source: string; item: unknown; matchedIn: string }> = [];

    // Search skills
    for (const skill of resume.skills ?? []) {
      if (
        skill.name.toLowerCase().includes(q) ||
        skill.keywords?.some((k) => k.toLowerCase().includes(q))
      ) {
        results.push({ source: "skills", item: skill, matchedIn: skill.name });
      }
    }

    // Search work highlights
    for (const job of resume.work ?? []) {
      const matchingHighlights = (job.highlights ?? []).filter((h) =>
        h.toLowerCase().includes(q)
      );
      if (job.summary?.toLowerCase().includes(q) || matchingHighlights.length > 0) {
        results.push({
          source: "work",
          item: { ...job, highlights: matchingHighlights.length ? matchingHighlights : job.highlights },
          matchedIn: `${job.position} at ${job.name}`,
        });
      }
    }

    // Search projects
    for (const project of resume.projects ?? []) {
      if (
        project.description.toLowerCase().includes(q) ||
        project.name.toLowerCase().includes(q) ||
        project.keywords?.some((k) => k.toLowerCase().includes(q)) ||
        project.highlights?.some((h) => h.toLowerCase().includes(q))
      ) {
        results.push({ source: "projects", item: project, matchedIn: project.name });
      }
    }

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ query, totalResults: results.length, results }, null, 2),
        },
      ],
    };
  }
);

// ─── Tool: generate_ats_profile ───────────────────────────────────────────────
server.registerTool(
  "generate_ats_profile",
  {
    description:
      "Generates a flat ATS-compatible profile object ready for import into systems like Greenhouse or Workday. Includes name, contact, work history, education, and skills.",
    inputSchema: {
      format: z
        .enum(["greenhouse", "workday", "generic"])
        .optional()
        .default("generic")
        .describe("Target ATS format"),
    },
  },
  async ({ format }) => {
    const { basics, work, education, skills } = resume;
    const nameParts = (basics.name ?? "").split(" ");

    const generic = {
      firstName: nameParts[0] ?? "",
      lastName: nameParts.slice(1).join(" ") ?? "",
      email: basics.email,
      phone: basics.phone ?? null,
      location: basics.location
        ? [basics.location.city, basics.location.region, basics.location.countryCode]
            .filter(Boolean)
            .join(", ")
        : null,
      currentTitle: basics.label ?? null,
      summary: basics.summary ?? null,
      workExperience: (work ?? []).map((j) => ({
        company: j.name,
        title: j.position,
        start: j.startDate,
        end: j.endDate || "Present",
        current: !j.endDate || j.endDate === "",
        highlights: j.highlights ?? [],
      })),
      education: (education ?? []).map((e) => ({
        school: e.institution,
        degree: `${e.studyType} in ${e.area}`,
        start: e.startDate,
        end: e.endDate,
        gpa: e.score ?? null,
      })),
      skills: (skills ?? []).map((s) => s.keywords ?? []).flat(),
      skillCategories: (skills ?? []).map((s) => s.name),
      githubUrl: basics.profiles?.find((p) => p.network === "GitHub")?.url ?? null,
      linkedinUrl: basics.profiles?.find((p) => p.network === "LinkedIn")?.url ?? null,
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify({ format, profile: generic }, null, 2),
        },
      ],
    };
  }
);

// ─── Start Server ─────────────────────────────────────────────────────────────
const useHttp = process.argv.includes("--http");

if (useHttp) {
  // Streamable HTTP transport for remote/web connections
  const { default: express } = await import("express");
  const { default: cors } = await import("cors");
  const { StreamableHTTPServerTransport } = await import(
    "@modelcontextprotocol/sdk/server/streamableHttp.js"
  );

  const app = express();
  app.use(cors());
  app.use(express.json());

  app.all("/mcp", async (req, res) => {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: () => `session-${Date.now()}`,
    });
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });

  const PORT = 3001;
  app.listen(PORT, () => {
    console.log(`🚀  TalentScout MCP Server (HTTP) running at http://localhost:${PORT}/mcp`);
    console.log(`    Candidate: ${resume.basics.name}`);
    console.log(`    Tools: get_basics, get_experience, get_skills, get_education, get_projects, search_capabilities, generate_ats_profile`);
  });
} else {
  // stdio transport for local Claude Desktop / Cursor integration
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error(`🚀  TalentScout MCP Server (stdio) started for: ${resume.basics.name}`);
}
