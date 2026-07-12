import chokidar from 'chokidar';
import { exec } from 'child_process';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const watchPath = resolve(ROOT, 'data', 'resume.json');
console.log(`👁  Watching ${watchPath} for changes...`);

const watcher = chokidar.watch(watchPath, { persistent: true });

watcher.on('change', (path) => {
  console.log(`📝 Detected change in ${path} — rebuilding...`);
  // Validate, build (all formats including DOCX), and re-stage
  exec('npm run validate && node compiler/build.js --docx && node scripts/deploy-web.js', { cwd: ROOT }, (err, stdout, stderr) => {
    if (err) {
      console.error('❌ Build failed:', stderr || err.message);
      return;
    }
    console.log(stdout.trim());
    console.log('✅ Rebuild complete.');
  });
});
