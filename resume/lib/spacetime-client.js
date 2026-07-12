import { execSync } from 'child_process';

const DB_NAME = 'talentscout-resume';

// Helper to escape single quotes in strings for SQL insertion
function escapeSql(str) {
  if (!str) return '';
  return str.replace(/'/g, "''");
}

// Executes a SQL statement via the spacetime CLI synchronously
function execSql(query) {
  try {
    const stdout = execSync(`spacetime sql ${DB_NAME} "${query}"`, { encoding: 'utf8', stdio: 'pipe' });
    return stdout;
  } catch (err) {
    console.error(`⚠️  SpacetimeDB SQL Error: ${err.message}`);
    if (err.stderr) console.error(err.stderr);
    return null;
  }
}

export function logBuildRun(id, candidateName, workEntries, skillsCount, status) {
  const timestamp = Date.now() * 1000; // Microseconds
  const query = `INSERT INTO build_runs (id, timestamp, candidate_name, work_entries, skills_count, status) VALUES (${id}, ${timestamp}, '${escapeSql(candidateName)}', ${workEntries}, ${skillsCount}, '${status}')`;
  execSql(query);
}

export function logTestResult(id, buildRunId, total, passed, failed, durationMs) {
  const query = `INSERT INTO test_results (id, build_run_id, total, passed, failed, duration_ms) VALUES (${id}, ${buildRunId}, ${total}, ${passed}, ${failed}, ${durationMs})`;
  execSql(query);
}

export function logSchemaError(id, buildRunId, fieldPath, message) {
  const query = `INSERT INTO schema_errors (id, build_run_id, field_path, message) VALUES (${id}, ${buildRunId}, '${escapeSql(fieldPath)}', '${escapeSql(message)}')`;
  execSql(query);
}
