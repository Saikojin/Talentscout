import { logTestResult } from '../lib/spacetime-client.js';

export default class SpacetimeReporter {
  onFinished(files) {
    let total = 0;
    let passed = 0;
    let failed = 0;
    let duration = 0;

    for (const file of files) {
      duration += file.result?.duration ?? 0;
      for (const task of file.tasks) {
        total++;
        if (task.result?.state === 'pass') {
          passed++;
        } else if (task.result?.state === 'fail') {
          failed++;
        }
      }
    }

    const buildRunId = Date.now();
    try {
      logTestResult(Date.now(), buildRunId, total, passed, failed, Math.round(duration));
      console.log(`\n📊 Test results logged to SpacetimeDB: ${passed}/${total} passed.`);
    } catch (err) {
      console.warn('⚠️  Could not log test results to SpacetimeDB:', err.message);
    }
  }
}
