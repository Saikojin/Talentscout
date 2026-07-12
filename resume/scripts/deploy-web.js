import { readFileSync, writeFileSync, mkdirSync, existsSync, cpSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');
const DEPLOY = resolve(ROOT, 'deploy');

console.log('🏗 Staging web files for deployment...');

// Create deploy directories
if (existsSync(DEPLOY)) {
  console.log('🧹 Clearing old deploy directory...');
  // Simple recursive deletion
  import('fs').then(fs => fs.rmSync(DEPLOY, { recursive: true, force: true }));
}

// Ensure clean directory
setTimeout(() => {
  mkdirSync(resolve(DEPLOY, 'data'), { recursive: true });

  // Copy web assets
  cpSync(resolve(ROOT, 'web'), DEPLOY, { recursive: true });

  // Copy resume.json into data/
  cpSync(resolve(ROOT, 'data', 'resume.json'), resolve(DEPLOY, 'data', 'resume.json'));

  // Copy built artifacts if they exist
  const dist = resolve(ROOT, 'dist');
  if (existsSync(dist)) {
    mkdirSync(resolve(DEPLOY, 'dist'), { recursive: true });
    cpSync(dist, resolve(DEPLOY, 'dist'), { recursive: true });
  }

  console.log('✅ Web directory staged at D:\\DevWorkspace\\TalentScout\\resume\\deploy');
}, 100);
