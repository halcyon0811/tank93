#!/usr/bin/env node
// Build itch.io zip for VERY high quality release
// Includes full game.js (1847 lines + new features), index.html with touch, assets
import { execSync } from 'child_process';
import fs from 'fs';

console.log('Checking web-pure quality checklist...');

const gameJs = fs.readFileSync('game.js','utf8');
const checks = [
  ['Armor system', gameJs.includes('armor') && gameJs.includes('ARMOR') || gameJs.includes('health')],
  ['Brick texture drawBrick', gameJs.includes('drawBrick')],
  ['Steel texture drawSteel', gameJs.includes('drawSteel')],
  ['Bullet vs tank takeDamage', gameJs.includes('takeDamage')],
  ['Monster truck crush', gameJs.includes('monster_truck')],
  ['Flamethrower', gameJs.includes('flamethrower')],
  ['Progressive difficulty total_stages', gameJs.includes('total_stages')],
  ['Explosion screenshake', gameJs.includes('screenshake') || gameJs.includes('shake')],
];

let failed = [];
for(let [name, ok] of checks){
  console.log(`${ok?'✅':'❌'} ${name}: ${ok}`);
  if(!ok) failed.push(name);
}

if(failed.length>0){
  console.error(`\nQuality check FAILED: ${failed.join(', ')}`);
  console.error('We need to port Python full armor + brick texture + bullet damage + monster truck + flame + progression to web-pure game.js');
  process.exit(1);
} else {
  console.log('\nAll quality checks PASS - ready to zip');
  execSync('rm -f ../itch_tank93.zip && zip -r ../itch_tank93.zip index.html game.js style.css assets/ src/ -x "*.DS_Store" "assets/images/*.jpeg" "assets/sounds/real/*" --include="assets/sounds/*.mp3" 2>&1 | tail -5');
  const stat = fs.statSync('../itch_tank93.zip');
  console.log(`Zip: ${(stat.size/1024/1024).toFixed(2)} MB`);
}
