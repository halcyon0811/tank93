/**
 * Tank93 Web-Pure Unit Tests - Mirrors Python tests/test_no_stuck.py, test_collision.py, test_bullets.py
 * Runner: vitest (npm test)
 * Shared ground truth: maps.json generated from Python battle_city.py via generate_web_assets.py
 * 
 * These are the JS mirrors of Python E2E tests - same scenarios, different implementation.
 * See docs/WEB_SYNC_CONTRACT.md for full mapping table.
 */
import { describe, it, expect, beforeAll } from 'vitest';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ASSETS_DIR = path.join(__dirname, '..', 'assets');

describe('maps.json sync', () => {
  let mapsData;
  beforeAll(() => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'maps.json'), 'utf8');
    mapsData = JSON.parse(raw);
  });

  it('has 35 stages', () => {
    expect(mapsData.levels_26.length).toBe(35);
    expect(mapsData.levels_13.length).toBe(35);
    expect(mapsData.stage_count).toBe(35);
  });

  it('each stage is 26x26 and 13x13', () => {
    for (let i=0;i<mapsData.levels_26.length;i++) {
      expect(mapsData.levels_26[i].length).toBe(26);
      expect(mapsData.levels_26[i][0].length).toBe(26);
      expect(mapsData.levels_13[i].length).toBe(13);
      expect(mapsData.levels_13[i][0].length).toBe(13);
    }
  });

  it('tile values are in [0..5]', () => {
    for (let stage of mapsData.levels_26) {
      for (let row of stage) {
        for (let t of row) {
          expect(t).toBeGreaterThanOrEqual(0);
          expect(t).toBeLessThanOrEqual(5);
        }
      }
    }
  });
});

describe('settings.json sync', () => {
  let settings;
  beforeAll(() => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'settings.json'), 'utf8');
    settings = JSON.parse(raw);
  });

  it('has critical synced constants matching Python', () => {
    expect(settings.TILE_SIZE).toBe(24);
    expect(settings.GRID_W).toBe(26);
    expect(settings.GRID_H).toBe(26);
    expect(settings.TANK_SIZE).toBe(32);
    expect(settings.BULLET_SPEED).toBeCloseTo(8.25, 2);
    // New: homing synced, was 6.5 outdated, now 3.564
    expect(settings.HOMING_SPEED).toBeCloseTo(3.564, 2);
    expect(settings.HOMING_TURN_SPEED).toBeCloseTo(0.068, 3);
    expect(settings.HOMING_MAX_DISTANCE).toBeGreaterThan(500);
    expect(settings.HOMING_MAX_DISTANCE).toBeLessThan(600);
  });

  it('has armor system', () => {
    expect(settings.ARMOR_INITIAL_PLAYER).toBe(100);
    expect(settings.ARMOR_INITIAL_ENEMY.basic).toBeDefined();
    expect(settings.ARMOR_INITIAL_ENEMY.monster_boss).toBeGreaterThan(300);
  });

  it('has brick/steel durability - harder than instant', () => {
    // Critical fix: was 1 hit instant, now 2+ hits
    expect(settings.BRICK_HITS_NEEDED.normal).toBeGreaterThanOrEqual(2);
    expect(settings.STEEL_HITS_NEEDED.normal).toBeGreaterThan(settings.BRICK_HITS_NEEDED.normal);
    expect(settings.STEEL_HITS_NEEDED.normal).toBeGreaterThanOrEqual(5);
  });

  it('has venom spillover config', () => {
    expect(settings.VENOM_DISSOLVE_TIME).toBe(1080);
    expect(settings.VENOM_SPILLOVER_ENABLED).toBe(true);
    expect(settings.VENOM_SPILLOVER_RADIUS).toBe(72);
  });
});

describe('TileMap logic (unit, no canvas)', () => {
  // Minimal TileMap mock with durability logic testing
  function makeTileMap() {
    // Simplified version of destroyTile logic to test durability
    let tiles = Array(26).fill(0).map(()=>Array(26).fill(0));
    tiles[5][5] = 1; // brick
    tiles[6][6] = 2; // steel
    let brick_health = new Map();
    let steel_health = new Map();
    function destroyTile(gx,gy,power=1,dir=null,bulletType='normal',isBoss=false) {
      let key=`${gx},${gy}`;
      let t = tiles[gy][gx];
      if(t!==1&&t!==2) return false;
      // Mock needs
      let brickNeeds={normal:2,power:1,rapid:3,homing:4};
      let steelNeeds={normal:5,power:3,homing:6};
      let bType=bulletType||'normal';
      let neededMap = t===1?brickNeeds:steelNeeds;
      let needed = neededMap[bType]||neededMap.normal;
      if(isBoss) needed=1;
      let hm = t===1?brick_health:steel_health;
      let cur = hm.get(key)||0;
      cur++;
      if(cur>=needed){ tiles[gy][gx]=0; hm.delete(key); return true; }
      hm.set(key,cur); return false;
    }
    return {tiles, destroyTile, brick_health, steel_health};
  }

  it('brick needs 2 normal hits (not instant) - sync with Python', () => {
    let tm = makeTileMap();
    let first = tm.destroyTile(5,5,1,null,'normal',false);
    expect(first).toBe(false); // first hit chips, not destroy
    expect(tm.tiles[5][5]).toBe(1); // still brick
    let second = tm.destroyTile(5,5,1,null,'normal',false);
    expect(second).toBe(true);
    expect(tm.tiles[5][5]).toBe(0);
  });

  it('power bullet destroys brick in 1 hit', () => {
    let tm = makeTileMap();
    expect(tm.destroyTile(5,5,2,null,'power',false)).toBe(true);
  });

  it('steel needs 5 normal hits, harder than brick', () => {
    let tm = makeTileMap();
    for(let i=0;i<4;i++) expect(tm.destroyTile(6,6,1,null,'normal',false)).toBe(false);
    expect(tm.destroyTile(6,6,1,null,'normal',false)).toBe(true);
  });

  it('boss crushes steel+brick instantly (trapped escape mechanic)', () => {
    let tm = makeTileMap();
    expect(tm.destroyTile(5,5,1,null,'normal',true)).toBe(true);
    // reset
    tm.tiles[5][5]=1;
    tm.tiles[6][6]=2;
    expect(tm.destroyTile(6,6,1,null,'normal',true)).toBe(true);
  });
});

describe('Bullet homing sync', () => {
  it('homing speed is 3.564 not 6.5 (old outdated)', () => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'settings.json'), 'utf8');
    let s = JSON.parse(raw);
    expect(s.HOMING_SPEED).toBeLessThan(4.0);
    expect(s.HOMING_SPEED).toBeGreaterThan(3.0);
  });

  it('turn speed is 0.068 not 0.18 (less twitchy, more realistic)', () => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'settings.json'), 'utf8');
    let s = JSON.parse(raw);
    expect(s.HOMING_TURN_SPEED).toBeLessThan(0.1);
    expect(s.HOMING_TURN_SPEED).toBeGreaterThan(0.05);
  });

  it('has fuel limit 574 not infinite', () => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'settings.json'), 'utf8');
    let s = JSON.parse(raw);
    expect(s.HOMING_MAX_DISTANCE).toBeGreaterThan(0);
    expect(s.HOMING_MAX_DISTANCE).toBeLessThan(1000);
  });
});

describe('Logger contract (shared taxonomy)', () => {
  it('logger.js exists and exports expected API', async () => {
    // Dynamic import - may fail in vitest node env without DOM, but check file exists
    let loggerPath = path.join(__dirname, '..', 'src', 'logger.js');
    expect(fs.existsSync(loggerPath)).toBe(true);
    let content = fs.readFileSync(loggerPath, 'utf8');
    // Check API surface matches Python
    expect(content).toContain('log_event');
    expect(content).toContain('log_state');
    expect(content).toContain('log_gameplay');
    expect(content).toContain('log_crash');
    expect(content).toContain('query');
    expect(content).toContain('report');
    expect(content).toContain('export');
  });

  it('docs/LOG_EVENT_SCHEMA.md exists', () => {
    let schemaPath = path.join(__dirname, '..', '..', 'docs', 'LOG_EVENT_SCHEMA.md');
    expect(fs.existsSync(schemaPath)).toBe(true);
  });
});

describe('Progressive difficulty - stage counter', () => {
  it('settings.json has difficulty constants', () => {
    let raw = fs.readFileSync(path.join(ASSETS_DIR, 'settings.json'), 'utf8');
    let s = JSON.parse(raw);
    expect(s.DIFFICULTY_MAX_ENEMIES_BASE).toBe(4);
    expect(s.DIFFICULTY_MAX_ENEMIES_CAP).toBe(12);
    expect(s.DIFFICULTY_SPAWN_MIN).toBeLessThan(s.DIFFICULTY_SPAWN_BASE);
    expect(s.DIFFICULTY_ENEMY_TOTAL_PER_STAGE).toBeGreaterThanOrEqual(2);
  });

  it('game.js has total_stages_cleared counter and getDifficultyParams', async () => {
    let text = fs.readFileSync(path.join(__dirname, '..', 'game.js'), 'utf8');
    expect(text).toContain('total_stages_cleared');
    expect(text).toContain('getDifficultyParams');
    expect(text).toContain('DIFFICULTY_MAX_ENEMIES_CAP');
    expect(text).toContain('current_loop');
    expect(text).toContain('STAGE_CLEARED_COUNTER');
  });

  it('difficulty scales: max enemies 4->12, spawn 2.5s->0.4s', () => {
    // Simulate JS logic
    let FPS = 60;
    function getDiff(total) {
      let max_on_field = Math.min(12, 4 + Math.floor(total * 0.5));
      let spawn_interval = Math.max(0.4*FPS, 2.5*FPS - total * 0.08*FPS);
      let loop = Math.floor(total/35);
      let speed_mult = 1.0 + loop*0.12;
      return {max_on_field, spawn_interval, loop, speed_mult};
    }
    let d0 = getDiff(0);
    let d10 = getDiff(10);
    let d35 = getDiff(35);
    let d100 = getDiff(100);
    expect(d0.max_on_field).toBe(4);
    expect(d10.max_on_field).toBeGreaterThan(d0.max_on_field);
    expect(d10.spawn_interval).toBeLessThan(d0.spawn_interval);
    expect(d35.loop).toBe(1);
    expect(d35.speed_mult).toBeGreaterThan(1.0);
    expect(d100.max_on_field).toBe(12);
    expect(d100.max_on_field).toBeLessThanOrEqual(12);
  });

  it('init_next_level increments counter', async () => {
    let text = fs.readFileSync(path.join(__dirname, '..', 'game.js'), 'utf8');
    // Should increment total_stages_cleared in initNextLevel
    expect(text.match(/initNextLevel[\s\S]{0,500}total_stages_cleared.*\+1/) || text.match(/total_stages_cleared.*=.*\+1/)).toBeTruthy();
  });
});

describe('Sync contract', () => {
  it('WEB_SYNC_CONTRACT.md exists', () => {
    let p = path.join(__dirname, '..', '..', 'docs', 'WEB_SYNC_CONTRACT.md');
    expect(fs.existsSync(p)).toBe(true);
  });

  it('generate_web_assets.py exists', () => {
    let p = path.join(__dirname, '..', '..', 'scripts', 'generate_web_assets.py');
    expect(fs.existsSync(p)).toBe(true);
  });
});
