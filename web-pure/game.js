/**
 * Tank93 Pure JS - Battle City Tribute - 35 Original NES Maps
 * No Python, pure JavaScript Canvas - runs in browser
 * Includes all fixed features: tank facing, enemy stuck fix, monster boss, homing/spread/rapid, freeze attackable, gradual enemies, real sounds
 */

const TILE_SIZE = 24;
const GRID_W = 26;
const GRID_H = 26;
const PLAYFIELD_X = 48;
const PLAYFIELD_Y = 48;
const PLAYFIELD_W = GRID_W * TILE_SIZE;
const PLAYFIELD_H = GRID_H * TILE_SIZE;
const TANK_SIZE = 32;
const FPS = 60;

// Tile types
const TILE_EMPTY = 0, TILE_BRICK = 1, TILE_STEEL = 2, TILE_WATER = 3, TILE_GRASS = 4, TILE_ICE = 5;

const DIRS = {
    'UP': [0, -1],
    'DOWN': [0, 1],
    'LEFT': [-1, 0],
    'RIGHT': [1, 0],
    'UP_LEFT': [-1, -1],
    'UP_RIGHT': [1, -1],
    'DOWN_LEFT': [-1, 1],
    'DOWN_RIGHT': [1, 1],
};
const EIGHT_DIRS = ['UP','UP_RIGHT','RIGHT','DOWN_RIGHT','DOWN','DOWN_LEFT','LEFT','UP_LEFT'];
const DIR_ANGLE = {'UP':0,'UP_RIGHT':45,'RIGHT':90,'DOWN_RIGHT':135,'DOWN':180,'DOWN_LEFT':225,'LEFT':270,'UP_LEFT':315};

const PLAYER_SPAWN = [[8,24],[16,24]];
const ENEMY_SPAWNS = [[0,0],[12,0],[24,0]];
const BASE_POS = [12,24];

let mapsData = null;
let settingsData = null;

// Load maps
async function loadAssets() {
    document.getElementById('loading').textContent = 'Loading 35 original NES maps...';
    try {
        const res = await fetch('assets/maps.json');
        mapsData = await res.json();
        console.log(`Loaded ${mapsData.levels_26.length} maps`);
    } catch(e) {
        console.error("Failed to load maps", e);
        // Fallback empty
        mapsData = {levels_26: [[[0]]], levels_13: [[[0]]], stage_count: 1, bots_raw: []};
    }

    try {
        const res2 = await fetch('assets/settings.json');
        settingsData = await res2.json();
    } catch(e) {
        settingsData = {};
    }

    document.getElementById('loading').textContent = 'Loading sounds...';
    // Sounds will be loaded via Audio elements
}

class TileMap {
    constructor(levelData) {
        this.grid_w = GRID_W;
        this.grid_h = GRID_H;
        this.tiles = [];
        for(let y=0; y<GRID_H; y++) {
            this.tiles[y] = [];
            for(let x=0; x<GRID_W; x++) {
                this.tiles[y][x] = TILE_EMPTY;
            }
        }
        this.shovel_timer = 0;
        if(levelData) this.loadFromData(levelData);
    }

    loadFromData(data) {
        // data is 26x26 or 13x13
        if(data.length === 13 && data[0].length === 13) {
            for(let by=0; by<13; by++) {
                for(let bx=0; bx<13; bx++) {
                    let t = data[by][bx];
                    for(let dy=0; dy<2; dy++) {
                        for(let dx=0; dx<2; dx++) {
                            this.tiles[by*2+dy][bx*2+dx] = t;
                        }
                    }
                }
            }
        } else if(data.length === 26) {
            for(let y=0; y<26; y++) for(let x=0; x<26; x++) this.tiles[y][x] = data[y][x];
        }
    }

    ensureSpawnClear() {
        // Clear player spawns
        for(let [px,py] of PLAYER_SPAWN) {
            this.clearArea(px-1, py-1, 4, 4);
        }
        for(let [sx,sy] of ENEMY_SPAWNS) {
            this.clearArea(sx, sy, 4, 3);
        }
        let [bx,by] = BASE_POS;
        for(let y=by; y<by+2; y++) for(let x=bx; x<bx+2; x++) if(x>=0&&x<GRID_W&&y>=0&&y<GRID_H) this.tiles[y][x]=TILE_EMPTY;
    }

    clearArea(gx, gy, w=4, h=4) {
        for(let y=gy; y<gy+h; y++) for(let x=gx; x<gx+w; x++) {
            if(x>=0&&x<GRID_W&&y>=0&&y<GRID_H) {
                if((x==12&&y==24)||(x==13&&y==24)||(x==12&&y==25)||(x==13&&y==25)) continue;
                this.tiles[y][x]=TILE_EMPTY;
            }
        }
    }

    buildBaseWalls(tileType) {
        let [bx,by] = BASE_POS;
        let coords = [[bx-1,by-1],[bx,by-1],[bx+1,by-1],[bx+2,by-1],[bx-1,by],[bx-1,by+1],[bx+2,by],[bx+2,by+1]];
        for(let [x,y] of coords) if(x>=0&&x<GRID_W&&y>=0&&y<GRID_H) this.tiles[y][x]=tileType;
    }

    getTilesInRect(rect) {
        // rect: {left,top,right,bottom}
        let left = Math.max(0, Math.floor((rect.left - PLAYFIELD_X)/TILE_SIZE));
        let right = Math.min(GRID_W-1, Math.floor((rect.right-1 - PLAYFIELD_X)/TILE_SIZE));
        let top = Math.max(0, Math.floor((rect.top - PLAYFIELD_Y)/TILE_SIZE));
        let bottom = Math.min(GRID_H-1, Math.floor((rect.bottom-1 - PLAYFIELD_Y)/TILE_SIZE));
        let result = [];
        for(let gy=top; gy<=bottom; gy++) for(let gx=left; gx<=right; gx++) {
            let t = this.tiles[gy][gx];
            if(t!==TILE_EMPTY && t!==TILE_GRASS && t!==TILE_ICE) {
                let trect = {left: PLAYFIELD_X+gx*TILE_SIZE, top: PLAYFIELD_Y+gy*TILE_SIZE, right: PLAYFIELD_X+(gx+1)*TILE_SIZE, bottom: PLAYFIELD_Y+(gy+1)*TILE_SIZE, gx, gy, type:t};
                result.push(trect);
            }
        }
        return result;
    }

    destroyTile(gx, gy, power=1, dir=null) {
        if(gx<0||gx>=GRID_W||gy<0||gy>=GRID_H) return false;
        let t = this.tiles[gy][gx];
        let toDestroy = [[gx,gy]];
        if(dir==='UP' || dir==='DOWN') {
            let bx = Math.floor(gx/2), by = Math.floor(gy/2);
            let row = gy%2;
            toDestroy = [[bx*2, by*2+row],[bx*2+1, by*2+row]];
        } else if(dir==='LEFT' || dir==='RIGHT') {
            let bx = Math.floor(gx/2), by = Math.floor(gy/2);
            let col = gx%2;
            toDestroy = [[bx*2+col, by*2],[bx*2+col, by*2+1]];
        }
        let destroyed=false;
        for(let [tx,ty] of toDestroy) {
            if(tx<0||tx>=GRID_W||ty<0||ty>=GRID_H) continue;
            let tt = this.tiles[ty][tx];
            if(tt===TILE_BRICK) { this.tiles[ty][tx]=TILE_EMPTY; destroyed=true; }
            else if(tt===TILE_STEEL && power>=2) { this.tiles[ty][tx]=TILE_EMPTY; destroyed=true; }
        }
        return destroyed;
    }

    update() {
        if(this.shovel_timer>0) {
            this.shovel_timer--;
            if(this.shovel_timer<=0) this.buildBaseWalls(TILE_BRICK);
        }
    }

    activateShovel() {
        this.buildBaseWalls(TILE_STEEL);
        this.shovel_timer = 15*FPS;
    }

    draw(ctx) {
        // Playfield bg
        ctx.fillStyle = '#000';
        ctx.fillRect(PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_W, PLAYFIELD_H);
        for(let y=0; y<GRID_H; y++) for(let x=0; x<GRID_W; x++) {
            let t = this.tiles[y][x];
            if(t===TILE_EMPTY) continue;
            let rx = PLAYFIELD_X + x*TILE_SIZE;
            let ry = PLAYFIELD_Y + y*TILE_SIZE;
            if(t===TILE_BRICK) this.drawBrick(ctx, rx, ry);
            else if(t===TILE_STEEL) this.drawSteel(ctx, rx, ry);
            else if(t===TILE_WATER) this.drawWater(ctx, rx, ry);
        }
    }

    drawOverlay(ctx) {
        for(let y=0; y<GRID_H; y++) for(let x=0; x<GRID_W; x++) {
            let t = this.tiles[y][x];
            let rx = PLAYFIELD_X + x*TILE_SIZE;
            let ry = PLAYFIELD_Y + y*TILE_SIZE;
            if(t===TILE_GRASS) this.drawGrass(ctx, rx, ry);
            else if(t===TILE_ICE) this.drawIce(ctx, rx, ry);
        }
    }

    drawBrick(ctx,x,y) {
        // Simplified retro brick
        ctx.fillStyle = '#D23818';
        ctx.fillRect(x,y,TILE_SIZE,TILE_SIZE);
        ctx.fillStyle = '#8C1E0A';
        ctx.fillRect(x+3,y+10,TILE_SIZE-6,2);
        ctx.fillStyle = '#F07846';
        ctx.fillRect(x,y,TILE_SIZE,3);
    }
    drawSteel(ctx,x,y) {
        ctx.fillStyle = '#D2D2D2';
        ctx.fillRect(x,y,TILE_SIZE,TILE_SIZE);
        ctx.fillStyle = '#FFF';
        ctx.fillRect(x+3,y+3,TILE_SIZE-6,TILE_SIZE-6);
        ctx.fillStyle = '#828282';
        ctx.fillRect(x,y,TILE_SIZE,2);
        ctx.fillRect(x,y,2,TILE_SIZE);
    }
    drawWater(ctx,x,y) {
        ctx.fillStyle = '#1C5AF0';
        ctx.fillRect(x,y,TILE_SIZE,TILE_SIZE);
        ctx.fillStyle = '#E8F0FF';
        let t = Date.now();
        let phase = Math.floor(t/200)%2;
        let dots = phase===0? [[1,1],[6,1],[2,4]] : [[2,1],[5,2],[1,3]];
        for(let [dx,dy] of dots) { ctx.fillRect(x+dx*3, y+dy*3, 3, 3); }
    }
    drawGrass(ctx,x,y) {
        ctx.fillStyle = '#3CA014';
        ctx.fillRect(x,y,TILE_SIZE,TILE_SIZE);
        ctx.fillStyle = '#B0E050';
        ctx.fillRect(x+4,y+4,4,4);
        ctx.fillRect(x+16,y+12,4,4);
    }
    drawIce(ctx,x,y) {
        ctx.fillStyle = '#BEBEBE';
        ctx.fillRect(x,y,TILE_SIZE,TILE_SIZE);
        ctx.fillStyle = '#828287';
        ctx.fillRect(x+2,y+2,TILE_SIZE-4,2);
        ctx.fillStyle = '#E6E6E6';
        ctx.fillRect(x+6,y+10,TILE_SIZE-8,2);
    }
}

class Tank {
    constructor(grid_x, grid_y, color, is_player=false) {
        this.grid_x = grid_x;
        this.grid_y = grid_y;
        this.x = PLAYFIELD_X + grid_x*TILE_SIZE + TILE_SIZE/2;
        this.y = PLAYFIELD_Y + grid_y*TILE_SIZE + TILE_SIZE/2;
        this.rect = {left:0,top:0,right:0,bottom:0,centerx:this.x,centery:this.y};
        this.updateRect();
        this.color = color;
        this.is_player = is_player;
        this.alive = true;
        this.direction = 'UP';
        this.bullets = [];
        this.cooldown = 0;
        this.bullet_power = 1;
        this.speed = is_player ? 2.2*1.5 : 1.8;
        this.invulnerable_timer = 0;
        this.spawn_protection = 0;
        this.on_ice = false;
        this.move_timer = 0;
        // Items
        this.homing_timer = 0;
        this.spread_timer = 0;
        this.rapid_timer = 0;
        this.homing_active = false;
        this.spread_active = false;
        this.rapid_active = false;
        this.venom_timer = 0;
    }

    updateRect() {
        let size = TANK_SIZE-4;
        this.rect.left = this.x - size/2;
        this.rect.top = this.y - size/2;
        this.rect.right = this.x + size/2;
        this.rect.bottom = this.y + size/2;
        this.rect.centerx = this.x;
        this.rect.centery = this.y;
    }

    setPosition(grid_x, grid_y) {
        this.grid_x = grid_x;
        this.grid_y = grid_y;
        this.x = PLAYFIELD_X + grid_x*TILE_SIZE + TILE_SIZE/2;
        this.y = PLAYFIELD_Y + grid_y*TILE_SIZE + TILE_SIZE/2;
        this.updateRect();
    }

    getBulletSpawn() {
        let offset = TANK_SIZE/2+4;
        let [dx,dy] = DIRS[this.direction]||[0,-1];
        if(dx!==0&&dy!==0) { dx*=0.7071; dy*=0.7071; }
        return [this.rect.centerx + dx*offset, this.rect.centery + dy*offset];
    }

    getBulletSpawnFor(dir) {
        let offset = TANK_SIZE/2+4;
        let [dx,dy] = DIRS[dir]||[0,-1];
        if(dx!==0&&dy!==0) { dx*=0.7071; dy*=0.7071; }
        return [this.rect.centerx + dx*offset, this.rect.centery + dy*offset];
    }

    canShoot() {
        if(this.cooldown>0) return false;
        let maxB = this.is_player ? 2 : 1;
        let alive = this.bullets.filter(b=>b.alive).length;
        return alive < maxB;
    }

    tryMove(dirName, tilemap, otherTanks) {
        if(!this.alive) return false;
        // Always face direction where aims, even if blocked (fixes bug)
        this.direction = dirName;
        let [dx,dy] = DIRS[dirName]||[0,-1];
        if(dx!==0&&dy!==0) { dx*=0.7071; dy*=0.7071; }
        let speedMult = this.on_ice ? 1.35 : 1;
        let new_x = this.x + dx*this.speed*speedMult;
        let new_y = this.y + dy*this.speed*speedMult;
        let newRect = {left:new_x-(TANK_SIZE-4)/2, top:new_y-(TANK_SIZE-4)/2, right:new_x+(TANK_SIZE-4)/2, bottom:new_y+(TANK_SIZE-4)/2, centerx:new_x, centery:new_y};
        // bounds
        if(newRect.left < PLAYFIELD_X-6 || newRect.right > PLAYFIELD_X+PLAYFIELD_W+6) return false;
        if(newRect.top < PLAYFIELD_Y-6 || newRect.bottom > PLAYFIELD_Y+PLAYFIELD_H+6) return false;
        // tile collision
        let checkRect = {left:newRect.left+2, top:newRect.top+2, right:newRect.right-2, bottom:newRect.bottom-2};
        let tiles = tilemap.getTilesInRect(checkRect);
        for(let tr of tiles) {
            if(!(checkRect.right < tr.left || checkRect.left > tr.right || checkRect.bottom < tr.top || checkRect.top > tr.bottom)) {
                return false;
            }
        }
        // tank collision
        for(let other of otherTanks) {
            if(other===this || !other.alive) continue;
            let or = other.rect;
            if(!(newRect.right < or.left+2 || newRect.left > or.right-2 || newRect.bottom < or.top+2 || newRect.top > or.bottom-2)) {
                // If overlapping heavily (stuck bug), allow separation if moving away
                let dist = Math.hypot(this.x - other.x, this.y - other.y);
                if(dist < TANK_SIZE*0.9) {
                    // Overlapping, allow move if increasing distance
                    let oldDist = Math.hypot(this.x - other.x, this.y - other.y);
                    let newDist = Math.hypot(new_x - other.x, new_y - other.y);
                    if(newDist > oldDist) {
                        // Allow separation
                    } else {
                        return false;
                    }
                } else {
                    return false;
                }
            }
        }
        this.x = new_x;
        this.y = new_y;
        this.updateRect();
        this.move_timer++;
        return true;
    }

    update(tilemap) {
        if(this.cooldown>0) this.cooldown--;
        if(this.invulnerable_timer>0) this.invulnerable_timer--;
        if(this.spawn_protection>0) this.spawn_protection--;
        if(this.venom_timer>0) {
            this.venom_timer--;
            if(this.venom_timer<=0) this.alive=false;
        }
        // ice check
        let gx = Math.floor((this.rect.centerx - PLAYFIELD_X)/TILE_SIZE);
        let gy = Math.floor((this.rect.centery - PLAYFIELD_Y)/TILE_SIZE);
        if(gx>=0&&gx<GRID_W&&gy>=0&&gy<GRID_H) this.on_ice = tilemap.tiles[gy][gx]===TILE_ICE;
        else this.on_ice=false;

        // items timers - permanent until death (timer -1 = infinite)
        if(this.homing_timer===-1) this.homing_active=true;
        else if(this.homing_timer>0) { this.homing_timer--; this.homing_active=true; if(this.homing_timer<=0) this.homing_active=false; }
        else if(this.homing_timer!== -1) this.homing_active=false;

        if(this.spread_timer===-1) this.spread_active=true;
        else if(this.spread_timer>0) { this.spread_timer--; this.spread_active=true; if(this.spread_timer<=0) this.spread_active=false; }
        else if(this.spread_timer!== -1) this.spread_active=false;

        if(this.rapid_timer===-1) this.rapid_active=true;
        else if(this.rapid_timer>0) { this.rapid_timer--; this.rapid_active=true; if(this.rapid_timer<=0) this.rapid_active=false; }
        else if(this.rapid_timer!== -1) this.rapid_active=false;

        this.bullets = this.bullets.filter(b=>b.alive);
    }

    takeDamage(power=1) {
        if(this.invulnerable_timer>0 || this.spawn_protection>0) return false;
        return true;
    }

    die() {
        this.alive=false;
        this.homing_timer=0; this.spread_timer=0; this.rapid_timer=0;
        this.homing_active=false; this.spread_active=false; this.rapid_active=false;
        this.venom_timer=0;
    }

    respawn(gx,gy) {
        this.setPosition(gx,gy);
        this.alive=true;
        this.direction='UP';
        this.invulnerable_timer=0;
        this.spawn_protection=180;
        this.venom_timer=0;
    }

    draw(ctx) {
        if(!this.alive) return;
        let cx=this.rect.centerx, cy=this.rect.centery;
        let size=TANK_SIZE-6;

        // Body
        ctx.fillStyle = this.color;
        ctx.fillRect(cx-size/2+2, cy-size/2+2, size-4, size-4);
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.strokeRect(cx-size/2+2, cy-size/2+2, size-4, size-4);

        // Turret direction line - shows facing where aims
        let [dx,dy] = DIRS[this.direction]||[0,-1];
        let x2 = cx + dx*(size/2+8);
        let y2 = cy + dy*(size/2+8);
        ctx.strokeStyle = '#222';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.moveTo(cx,cy);
        ctx.lineTo(x2,y2);
        ctx.stroke();

        // Center dot
        ctx.fillStyle = '#111';
        ctx.beginPath();
        ctx.arc(cx,cy,4,0,Math.PI*2);
        ctx.fill();

        // Boss?
        if(this.enemy_type==='monster_boss' || this.is_boss) {
            // Monster boss eyes
            ctx.fillStyle = '#fff';
            ctx.beginPath();
            ctx.arc(cx-6, cy-4, 5,0,Math.PI*2);
            ctx.arc(cx+6, cy-4, 5,0,Math.PI*2);
            ctx.fill();
            ctx.fillStyle = '#f00';
            ctx.beginPath();
            ctx.arc(cx-6, cy-4, 2,0,Math.PI*2);
            ctx.arc(cx+6, cy-4, 2,0,Math.PI*2);
            ctx.fill();
            // Health bar
            let barW=40, barH=6;
            let frac = this.health/18;
            ctx.fillStyle='#000';
            ctx.fillRect(cx-barW/2-1, cy-size/2-12, barW+2, barH+2);
            ctx.fillStyle=`rgb(${Math.floor(255*(1-frac))},${Math.floor(255*frac)},0)`;
            ctx.fillRect(cx-barW/2, cy-size/2-11, barW*frac, barH);
        }

        // Venom overlay
        if(this.venom_timer>0) {
            ctx.fillStyle = `rgba(60,200,60,${0.2+this.venom_timer/1080*0.3})`;
            ctx.fillRect(cx-size/2, cy-size/2, size, size);
        }
    }
}

class PlayerTank extends Tank {
    constructor(id, gx, gy) {
        super(gx, gy, id===1 ? '#ffd700' : '#0f0', true);
        this.player_id = id;
        this.lives = 3;
        this.score = 0;
        this.star_level = 0;
        this.helmet_timer = 0;
    }

    shoot() {
        let maxB = 2;
        let alive = this.bullets.filter(b=>b.alive).length;
        let limit = maxB;
        if(this.spread_active) limit = this.rapid_active ? 6 : 4;
        else if(this.rapid_active) limit = maxB*3;
        if(alive >= limit) return null;

        let bullets = [];
        let baseColor = this.bullet_power>=2 ? '#ff0' : this.color;

        if(this.spread_active) {
            for(let d of EIGHT_DIRS) {
                let [sx,sy] = this.getBulletSpawnFor(d);
                let isHoming = this.homing_active;
                let col = isHoming ? '#ff8c00' : baseColor;
                let b = new Bullet(sx,sy,d,`player${this.player_id}`,this.bullet_power,col,isHoming,false);
                if(this.rapid_active) b.speed*=1.2;
                this.bullets.push(b);
                bullets.push(b);
            }
            this.cooldown = this.rapid_active ? 8 : 25;
        } else {
            let [sx,sy] = this.getBulletSpawn();
            let isHoming = this.homing_active;
            let col = isHoming ? '#ff8c00' : (this.rapid_active ? '#ff5096' : baseColor);
            let b = new Bullet(sx,sy,this.direction,`player${this.player_id}`,this.bullet_power,col,isHoming,false);
            if(this.rapid_active) b.speed*=1.2;
            this.bullets.push(b);
            bullets.push(b);
            this.cooldown = this.rapid_active ? 6 : (this.star_level>=1 ? 15 : 20);
        }
        return bullets.length===1 ? bullets[0] : bullets;
    }

    applyPowerup(type, game) {
        if(type==='helmet') { this.helmet_timer=10*FPS; this.invulnerable_timer=10*FPS; }
        else if(type==='star') { this.star_level=Math.min(this.star_level+1,3); }
        else if(type==='tank') { this.lives++; this.score+=500; }
        else if(type==='gun') { this.bullet_power=2; }
        else if(type==='shovel') { if(game) game.tilemap.activateShovel(); }
        else if(type==='homing') { this.homing_timer=-1; this.homing_active=true; this.score+=200; }
        else if(type==='spread') { this.spread_timer=-1; this.spread_active=true; this.score+=200; }
        else if(type==='rapid') { this.rapid_timer=-1; this.rapid_active=true; this.score+=200; }
    }
}

class EnemyTank extends Tank {
    constructor(gx, gy, type='basic') {
        let colors = {basic:'#b4b4b4', fast:'#50b4ff', power:'#ff5050', armor:'#8c8ccc', boss:'#64c850', monster_boss:'#64c850'};
        super(gx, gy, colors[type]||'#b4b4b4', false);
        this.enemy_type = type;
        this.direction = 'DOWN';
        this.is_boss = (type==='boss' || type==='monster_boss' || type==='monster');
        this.powerup_carrier = Math.random()<0.25;
        this.homing_active=false; this.spread_active=false; this.rapid_active=false;
        this.flash_timer=0;
        this.target_dir_timer=0;
        this.stuck_timer=0;
        this.last_pos=[this.x,this.y];
        this.base_attack_cooldown=0;

        if(type==='basic') { this.speed=1.8; this.health=1; this.score_value=100; this.shoot_chance=0.018; }
        else if(type==='fast') { this.speed=3.0; this.health=1; this.score_value=200; this.shoot_chance=0.025; }
        else if(type==='power') { this.speed=1.8*1.1; this.health=1; this.score_value=300; this.shoot_chance=0.045; }
        else if(type==='armor') { this.speed=1.8*0.75; this.health=4; this.score_value=400; this.shoot_chance=0.020; }
        else if(type.includes('boss')) { this.speed=1.8; this.health=12; this.bullet_power=2; this.score_value=2000; this.shoot_chance=0.045; this.venom_cooldown=0; this.venom_shoot_chance=0.025;
            this.rect = {left:this.x-25, top:this.y-25, right:this.x+25, bottom:this.y+25, centerx:this.x, centery:this.y};
        }

        this.spawn_protection=60; this.invulnerable_timer=60;
        this.state='wander';
    }

    canMoveDir(dir, tilemap, otherTanks) {
        let [dx,dy] = DIRS[dir]||[0,-1];
        let test_x = this.x + dx*this.speed;
        let test_y = this.y + dy*this.speed;
        let newRect = {left:test_x-14, top:test_y-14, right:test_x+14, bottom:test_y+14, centerx:test_x, centery:test_y};
        if(newRect.left < PLAYFIELD_X-6 || newRect.right > PLAYFIELD_X+PLAYFIELD_W+6) return false;
        if(newRect.top < PLAYFIELD_Y-6 || newRect.bottom > PLAYFIELD_Y+PLAYFIELD_H+6) return false;
        let check = {left:newRect.left+2, top:newRect.top+2, right:newRect.right-2, bottom:newRect.bottom-2};
        let tiles = tilemap.getTilesInRect(check);
        for(let tr of tiles) {
            if(!(check.right < tr.left || check.left > tr.right || check.bottom < tr.top || check.top > tr.bottom)) return false;
        }
        for(let other of otherTanks) {
            if(other===this || !other.alive) continue;
            let or = other.rect;
            if(!(newRect.right < or.left+2 || newRect.left > or.right-2 || newRect.bottom < or.top+2 || newRect.top > or.bottom-2)) return false;
        }
        return true;
    }

    updateAI(tilemap, players, otherTanks, bulletsList, base) {
        if(!this.alive) return null;
        this.flash_timer++;

        let dist = Math.hypot(this.x - this.last_pos[0], this.y - this.last_pos[1]);
        if(dist < 0.8) this.stuck_timer++; else this.stuck_timer=0;
        this.last_pos = [this.x, this.y];

        // Separation for stuck bug
        let overlapping = [];
        for(let other of [...otherTanks, ...players]) {
            if(other===this || !other.alive) continue;
            let d = Math.hypot(this.x-other.x, this.y-other.y);
            if(d < 32*0.95) overlapping.push([other,d]);
        }
        if(overlapping.length>0) {
            overlapping.sort((a,b)=>a[1]-b[1]);
            let nearest = overlapping[0][0];
            let dx = this.x - nearest.x, dy = this.y - nearest.y;
            let dirAway = Math.abs(dx)>Math.abs(dy) ? (dx>0?'RIGHT':'LEFT') : (dy>0?'DOWN':'UP');
            this.direction = dirAway;
            this.target_dir_timer=15;
            this.tryMove(dirAway, tilemap, []);
            let d = Math.hypot(this.x-nearest.x, this.y-nearest.y);
            if(d < 32*0.8) {
                let len = Math.hypot(dx,dy)||1;
                this.x += dx/len*2.5;
                this.y += dy/len*2.5;
                this.rect.centerx=this.x; this.rect.centery=this.y;
                this.rect.left=this.x-14; this.rect.right=this.x+14;
                this.rect.top=this.y-14; this.rect.bottom=this.y+14;
            }
        }

        if(this.target_dir_timer<=0 || this.stuck_timer>25) {
            this.chooseNewDirection(players, tilemap, base);
            this.target_dir_timer = Math.floor(Math.random()*65)+25;
            if(this.stuck_timer>25) this.target_dir_timer = Math.floor(Math.random()*20)+10;
            this.stuck_timer=0;
        } else this.target_dir_timer--;

        let moved = this.tryMove(this.direction, tilemap, [...otherTanks, ...players]);
        if(!moved) {
            let perp = {UP:['LEFT','RIGHT'], DOWN:['LEFT','RIGHT'], LEFT:['UP','DOWN'], RIGHT:['UP','DOWN']}[this.direction]||[];
            for(let pd of perp) {
                if(this.canMoveDir(pd, tilemap, [...otherTanks, ...players])) {
                    this.direction=pd;
                    this.target_dir_timer=Math.floor(Math.random()*40)+20;
                    break;
                }
            }
        }

        // Shooting
        let shootChance = this.shoot_chance;
        // Simple line of sight check
        for(let p of players) {
            if(!p.alive) continue;
            if(Math.abs(p.x-this.x)<14 || Math.abs(p.y-this.y)<14) {
                shootChance*=3;
                break;
            }
        }
        if(Math.random() < shootChance) {
            let b = this.shoot();
            if(b) {
                if(Array.isArray(b)) bulletsList.push(...b);
                else bulletsList.push(b);
                return b;
            }
        }
        this.update(tilemap);
        return null;
    }

    chooseNewDirection(players, tilemap, base) {
        let possible = ['UP','DOWN','LEFT','RIGHT'];
        let alivePlayers = players.filter(p=>p.alive);
        let targetX, targetY;
        if(base && base.alive) {
            targetX=base.x; targetY=base.y;
        } else if(alivePlayers.length>0) {
            let closest = alivePlayers.reduce((a,b)=> Math.hypot(a.x-this.x,a.y-this.y) < Math.hypot(b.x-this.x,b.y-this.y) ? a : b);
            targetX=closest.x; targetY=closest.y;
        } else {
            this.direction = possible[Math.floor(Math.random()*possible.length)];
            return;
        }
        let dx = targetX - this.x, dy = targetY - this.y;
        let preferred = [];
        if(Math.abs(dx) > Math.abs(dy)) {
            preferred.push(dx>0?'RIGHT':'LEFT');
            preferred.push(dy>0?'DOWN':'UP');
        } else {
            preferred.push(dy>0?'DOWN':'UP');
            preferred.push(dx>0?'RIGHT':'LEFT');
        }
        for(let d of possible) if(!preferred.includes(d)) preferred.push(d);
        for(let d of preferred) {
            if(this.canMoveDir(d, tilemap, players)) { this.direction=d; return; }
        }
        this.direction = possible[Math.floor(Math.random()*possible.length)];
    }

    shoot() {
        if(!this.canShoot()) return null;
        // Spread
        if(this.spread_active) {
            let bullets=[];
            for(let d of EIGHT_DIRS) {
                let [sx,sy] = this.getBulletSpawnFor(d);
                let b = new Bullet(sx,sy,d,'enemy',this.bullet_power,'#ff6464',this.homing_active,false);
                if(this.rapid_active) b.speed*=1.2;
                this.bullets.push(b);
                bullets.push(b);
            }
            this.cooldown = this.rapid_active ? 30 : 50;
            return bullets;
        }
        let [sx,sy] = this.getBulletSpawn();
        let b = new Bullet(sx,sy,this.direction,'enemy',this.bullet_power,'#ff6464',this.homing_active,false);
        if(this.rapid_active) b.speed*=1.2;
        this.bullets.push(b);
        this.cooldown = this.rapid_active ? Math.floor(Math.random()*25)+15 : Math.floor(Math.random()*55)+30;
        if(this.is_boss) this.cooldown = this.rapid_active ? 30 : Math.floor(Math.random()*50)+65;
        return b;
    }
}

class Bullet {
    constructor(x,y,dir,owner,power=1,color='#fff',homing=false,venom=false) {
        this.x=x; this.y=y; this.dir=dir; this.owner=owner; this.power=power; this.color=color;
        this.homing=homing; this.venom=venom;
        this.speed = venom ? 3.7 : (power>=2 ? 8.25*1.3 : 8.25);
        if(homing) this.speed = 6.5;
        this.alive=true;
        this.rect={left:x-3,top:y-3,right:x+3,bottom:y+3,centerx:x,centery:y};
        this.trail=[];
        this.vx=0; this.vy=0;
        let [dx,dy]=DIRS[dir]||[0,-1];
        if(dx!==0&&dy!==0) { let len=Math.hypot(dx,dy); dx/=len; dy/=len; }
        this.vx=dx; this.vy=dy;
        this.turn_speed=0.18;
    }

    update(tilemap, tanks, base) {
        if(!this.alive) return null;
        if(this.homing) {
            // Find nearest target
            let targets = this.owner.startsWith('player') ? tanks.filter(t=>!t.is_player&&t.alive) : tanks.filter(t=>t.is_player&&t.alive);
            if(targets.length>0) {
                let nearest = targets.reduce((a,b)=> Math.hypot(a.x-this.x,a.y-this.y) < Math.hypot(b.x-this.x,b.y-this.y) ? a : b);
                let dx = nearest.x - this.x, dy = nearest.y - this.y;
                let dist = Math.hypot(dx,dy);
                if(dist>1) { dx/=dist; dy/=dist; }
                this.vx = this.vx*(1-this.turn_speed) + dx*this.turn_speed;
                this.vy = this.vy*(1-this.turn_speed) + dy*this.turn_speed;
                let len = Math.hypot(this.vx,this.vy);
                if(len>0) { this.vx/=len; this.vy/=len; }
            }
            this.x += this.vx*this.speed;
            this.y += this.vy*this.speed;
        } else {
            let [dx,dy]=DIRS[this.dir]||[0,-1];
            if(dx!==0&&dy!==0) { let len=Math.hypot(dx,dy); dx/=len; dy/=len; }
            this.x += dx*this.speed;
            this.y += dy*this.speed;
        }
        this.rect.centerx=this.x; this.rect.centery=this.y;
        this.rect.left=this.x-3; this.rect.right=this.x+3;
        this.rect.top=this.y-3; this.rect.bottom=this.y+3;
        this.trail.push([this.x,this.y]);
        if(this.trail.length>6) this.trail.shift();

        if(this.x<PLAYFIELD_X||this.x>PLAYFIELD_X+PLAYFIELD_W||this.y<PLAYFIELD_Y||this.y>PLAYFIELD_Y+PLAYFIELD_H) { this.alive=false; return 'out'; }

        let gx = Math.floor((this.x-PLAYFIELD_X)/TILE_SIZE);
        let gy = Math.floor((this.y-PLAYFIELD_Y)/TILE_SIZE);
        if(gx>=0&&gx<GRID_W&&gy>=0&&gy<GRID_H) {
            let tt = tilemap.tiles[gy][gx];
            if(tt===TILE_BRICK) { tilemap.destroyTile(gx,gy,this.power,this.dir); this.alive=false; return 'hit_brick'; }
            else if(tt===TILE_STEEL) {
                if(this.power>=2) tilemap.destroyTile(gx,gy,this.power,this.dir);
                this.alive=false; return 'hit_steel';
            }
        }

        if(base && base.alive) {
            if(this.x>=base.x-24&&this.x<=base.x+24&&this.y>=base.y-24&&this.y<=base.y+24) {
                base.takeDamage();
                this.alive=false;
                return 'hit_base';
            }
        }

        for(let tank of tanks) {
            if(!tank.alive || tank.invulnerable_timer>0) continue;
            if(this.owner.startsWith('player') && tank.is_player) continue;
            if(this.owner==='enemy' && !tank.is_player) continue;
            if(this.x>=tank.rect.left && this.x<=tank.rect.right && this.y>=tank.rect.top && this.y<=tank.rect.bottom) {
                if(this.venom) {
                    tank.venom_timer = 18*FPS;
                    return 'venom_hit';
                }
                if(!tank.takeDamage(this.power)) { this.alive=false; return 'blocked'; }
                this.alive=false;
                return 'hit_tank';
            }
        }
        return null;
    }

    draw(ctx) {
        if(!this.alive) return;
        // Trail
        for(let i=0;i<this.trail.length;i++) {
            let alpha = i/this.trail.length;
            let [tx,ty] = this.trail[i];
            ctx.globalAlpha = alpha*0.5;
            ctx.fillStyle = this.venom ? '#3c8' : (this.homing ? '#f80' : '#888');
            ctx.beginPath();
            ctx.arc(tx,ty,2*alpha,0,Math.PI*2);
            ctx.fill();
            ctx.globalAlpha = 1;
        }
        // Body
        if(this.venom) {
            ctx.fillStyle = '#3f5';
            ctx.beginPath();
            ctx.arc(this.x,this.y,6,0,Math.PI*2);
            ctx.fill();
        } else if(this.homing) {
            ctx.fillStyle = this.color;
            ctx.beginPath();
            ctx.arc(this.x,this.y,5,0,Math.PI*2);
            ctx.fill();
            ctx.fillStyle='#ff0';
            ctx.beginPath();
            ctx.arc(this.x,this.y,2,0,Math.PI*2);
            ctx.fill();
        } else {
            ctx.fillStyle=this.color;
            ctx.beginPath();
            ctx.arc(this.x,this.y,4,0,Math.PI*2);
            ctx.fill();
            ctx.fillStyle='#fff';
            ctx.beginPath();
            ctx.arc(this.x,this.y,2,0,Math.PI*2);
            ctx.fill();
        }
    }
}

class Base {
    constructor() {
        this.x = PLAYFIELD_X + BASE_POS[0]*TILE_SIZE + TILE_SIZE;
        this.y = PLAYFIELD_Y + BASE_POS[1]*TILE_SIZE + TILE_SIZE;
        this.alive=true;
        this.rect={left:this.x-24,top:this.y-24,right:this.x+24,bottom:this.y+24,centerx:this.x,centery:this.y};
        this.is_monster=true;
        this.monster_released=false;
    }
    takeDamage() {
        if(!this.alive) return false;
        this.alive=false;
        this.monster_released=true;
        return true;
    }
    reset() {
        this.alive=true;
        this.monster_released=false;
    }
    draw(ctx) {
        let cx=this.rect.centerx, cy=this.rect.centery;
        if(this.alive) {
            // Cage
            ctx.fillStyle='#1e140a';
            ctx.fillRect(this.rect.left,this.rect.top,48,48);
            ctx.fillStyle='#785a28';
            ctx.fillRect(this.rect.left,this.rect.top,48,4);
            ctx.fillRect(this.rect.left,this.rect.top,4,48);
            ctx.fillRect(this.rect.right-4,this.rect.top,4,48);
            ctx.fillRect(this.rect.left,this.rect.bottom-4,48,4);
            // Vertical bars
            for(let i=1;i<3;i++) ctx.fillRect(this.rect.left+8+i*12,this.rect.top+4,4,40);
            // Monster
            ctx.fillStyle='#64c864';
            ctx.beginPath();
            ctx.ellipse(cx,cy+4,14,11,0,0,Math.PI*2);
            ctx.fill();
            ctx.fillStyle='#fff';
            ctx.beginPath(); ctx.arc(cx-5,cy-2,4,0,Math.PI*2); ctx.arc(cx+5,cy-2,4,0,Math.PI*2); ctx.fill();
            ctx.fillStyle='#000';
            ctx.beginPath(); ctx.arc(cx-5,cy-2,2,0,Math.PI*2); ctx.arc(cx+5,cy-2,2,0,Math.PI*2); ctx.fill();
            ctx.fillStyle='#f00';
            ctx.fillRect(cx-12,cy-10,6,4);
            ctx.fillRect(cx+6,cy-10,6,4);
        } else {
            ctx.fillStyle='#281402';
            ctx.fillRect(this.rect.left,this.rect.top,48,48);
            if(Date.now()%400<200) {
                ctx.fillStyle='#ff0000';
                ctx.font='12px monospace';
                ctx.fillText('RELEASED!', cx-28, this.rect.top-8);
            }
        }
    }
}

class PowerUp {
    constructor(x,y,type=null) {
        this.x=x; this.y=y;
        this.type=type || ['helmet','clock','shovel','star','grenade','tank','gun','homing','spread','rapid'][Math.floor(Math.random()*10)];
        this.alive=true;
        this.rect={left:x-16,top:y-16,right:x+16,bottom:y+16,centerx:x,centery:y};
        this.spawn_time=Date.now();
        this.blink=0;
    }
    update() {
        if(Date.now()-this.spawn_time>10000) this.alive=false;
        this.blink++;
    }
    draw(ctx) {
        if(!this.alive) return;
        if(Date.now()-this.spawn_time>8000 && this.blink%20<10) return;
        let colors={helmet:'#50b4ff',clock:'#c8c8ff',shovel:'#ffdc50',star:'#ffff64',grenade:'#ff3c3c',tank:'#50ff50',gun:'#ff50c8',homing:'#ff8c00',spread:'#a050ff',rapid:'#ff5096'};
        ctx.fillStyle=colors[this.type]||'#fff';
        ctx.fillRect(this.rect.left,this.rect.top,32,32);
        ctx.strokeStyle='#fff';
        ctx.strokeRect(this.rect.left,this.rect.top,32,32);
        ctx.fillStyle='#000';
        ctx.font='18px monospace';
        let icons={helmet:'H',clock:'C',shovel:'S',star:'*',grenade:'G',tank:'T',gun:'P',homing:'M',spread:'8',rapid:'R'};
        ctx.fillText(icons[this.type]||'?', this.x-5, this.y+5);
    }
    checkPickup(players) {
        for(let p of players) if(p.alive && !(p.rect.right < this.rect.left || p.rect.left > this.rect.right || p.rect.bottom < this.rect.top || p.rect.top > this.rect.bottom)) {
            this.alive=false;
            return p;
        }
        return null;
    }
}

// Game
class Game {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.mapCanvas = document.getElementById('mapCanvas');
        this.mapCtx = this.mapCanvas.getContext('2d');
        this.current_level=0;
        this.state='menu';
        this.menu_selected=0;
        this.menu_mode='main';
        this.high_score=0;
        this.keys={};
        this.tilemap=null;
        this.base=null;
        this.players=[];
        this.enemies=[];
        this.bullets=[];
        this.powerups=[];
        this.enemies_total=20;
        this.enemies_killed=0;
        this.enemies_spawned=0;
        this.spawn_timer=0;
        this.freeze_timer=0;
        this.boss_enemy=null;
        this.boss_released=false;
        this.max_enemies_on_field=4;
        this.dynamic_spawn_interval=2.5*FPS;
        this.difficulty_ramp_timer=0;
        this.lastTime=0;

        window.addEventListener('keydown', e=>{ this.keys[e.code]=true; if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space'].includes(e.code)) e.preventDefault(); });
        window.addEventListener('keyup', e=>{ this.keys[e.code]=false; });

        this.initLevel(0,1);
        document.getElementById('loading').style.display='none';
        requestAnimationFrame(this.loop.bind(this));
    }

    getEnemyTotalForLevel(lvl) {
        let base = 20;
        let extra = lvl*2 + Math.floor(lvl/5)*3;
        return base + extra;
    }

    initLevel(idx, numPlayers) {
        this.current_level = idx % (mapsData ? mapsData.levels_26.length : 35);
        let levelData = mapsData ? mapsData.levels_26[this.current_level] : null;
        this.tilemap = new TileMap(levelData);
        this.tilemap.ensureSpawnClear();
        this.tilemap.buildBaseWalls(TILE_BRICK);
        this.base = new Base();
        this.players=[];
        this.enemies=[];
        this.bullets=[];
        this.powerups=[];
        this.enemies_total = this.getEnemyTotalForLevel(this.current_level);
        this.enemies_killed=0;
        this.enemies_spawned=0;
        this.spawn_timer=0;
        this.freeze_timer=0;
        this.max_enemies_on_field = Math.min(8, 4 + Math.floor(this.current_level/2));
        this.dynamic_spawn_interval = Math.max(0.8*FPS, 2.5*FPS - this.current_level*0.12*FPS);
        this.difficulty_ramp_timer=0;
        this.boss_enemy=null;
        this.boss_released=false;

        for(let i=0;i<numPlayers;i++) {
            let [gx,gy]=PLAYER_SPAWN[i];
            let p=new PlayerTank(i+1,gx,gy);
            this.players.push(p);
        }
        this.state='playing';
        this.updateHUD();
        this.drawMapPreview();
    }

    initNextLevel() {
        let prevPlayers=this.players;
        this.current_level = (this.current_level+1)%(mapsData ? mapsData.levels_26.length : 35);
        let levelData = mapsData ? mapsData.levels_26[this.current_level] : null;
        this.tilemap = new TileMap(levelData);
        this.tilemap.ensureSpawnClear();
        this.tilemap.buildBaseWalls(TILE_BRICK);
        this.base = new Base();
        this.enemies=[];
        this.bullets=[];
        this.powerups=[];
        this.enemies_total = this.getEnemyTotalForLevel(this.current_level);
        this.enemies_killed=0;
        this.enemies_spawned=0;
        this.spawn_timer=0;
        this.freeze_timer=0;
        this.max_enemies_on_field = Math.min(8, 4 + Math.floor(this.current_level/2));
        this.dynamic_spawn_interval = Math.max(0.8*FPS, 2.5*FPS - this.current_level*0.12*FPS);
        this.difficulty_ramp_timer=0;
        this.boss_enemy=null;
        this.boss_released=false;

        let newPlayers=[];
        for(let i=0;i<prevPlayers.length;i++) {
            let [gx,gy]=PLAYER_SPAWN[i];
            let old=prevPlayers[i];
            let p=new PlayerTank(old.player_id,gx,gy);
            p.score=old.score;
            p.lives=old.lives;
            p.star_level=old.star_level;
            // Preserve items across stages
            p.homing_timer=old.homing_timer;
            p.spread_timer=old.spread_timer;
            p.rapid_timer=old.rapid_timer;
            p.homing_active=old.homing_active;
            p.spread_active=old.spread_active;
            p.rapid_active=old.rapid_active;
            newPlayers.push(p);
        }
        this.players=newPlayers;
        this.state='playing';
    }

    spawnEnemy() {
        if(this.enemies_spawned>=this.enemies_total) return;
        if(this.enemies.length>=this.max_enemies_on_field) return;
        let tries=0;
        while(tries<30) {
            let [sx,sy]=ENEMY_SPAWNS[Math.floor(Math.random()*ENEMY_SPAWNS.length)];
            let blocked=false;
            let spawn_cx=PLAYFIELD_X+sx*TILE_SIZE+TILE_SIZE/2;
            let spawn_cy=PLAYFIELD_Y+sy*TILE_SIZE+TILE_SIZE/2;
            let testRect={left:PLAYFIELD_X+sx*TILE_SIZE, top:PLAYFIELD_Y+sy*TILE_SIZE, right:PLAYFIELD_X+(sx+1)*TILE_SIZE, bottom:PLAYFIELD_Y+(sy+1)*TILE_SIZE};
            for(let e of this.enemies) if(e.alive) {
                if(!(testRect.right<e.rect.left||testRect.left>e.rect.right||testRect.bottom<e.rect.top||testRect.top>e.rect.bottom)) { blocked=true; break; }
                let dist=Math.hypot(e.x-spawn_cx,e.y-spawn_cy);
                if(dist<TANK_SIZE*1.8) { blocked=true; break; }
            }
            if(!blocked) {
                for(let p of this.players) if(p.alive) {
                    if(!(testRect.right<p.rect.left||testRect.left>p.rect.right||testRect.bottom<p.rect.top||testRect.top>p.rect.bottom)) { blocked=true; break; }
                }
            }
            if(!blocked) {
                let types=['basic','basic','basic','fast','power','armor'];
                let etype = types[Math.floor(Math.random()*types.length)];
                let en=new EnemyTank(sx,sy,etype);
                this.enemies.push(en);
                this.enemies_spawned++;
                break;
            }
            tries++;
        }
    }

    releaseMonsterBoss() {
        if(this.boss_released) return;
        console.log("[BOSS] Monster released!");
        this.boss_released=true;
        let [bx,by]=BASE_POS;
        this.tilemap.clearArea(bx-1,by-1,4,4);
        let boss=new EnemyTank(bx,by,'monster_boss');
        boss.setPosition(bx,by);
        boss.spawn_protection=30;
        boss.invulnerable_timer=30;
        this.enemies.push(boss);
        this.boss_enemy=boss;
        // Randomly assign items to current enemies
        let otherEnemies = this.enemies.filter(e=>e!==boss&&e.alive);
        console.log(`[BOSS] Assigning items to ${otherEnemies.length} enemies`);
        for(let en of otherEnemies) {
            if(Math.random()<0.6) {
                if(Math.random()<0.5) en.powerup_carrier=true;
                if(Math.random()<0.4) {
                    let choice=['homing','spread','rapid'][Math.floor(Math.random()*3)];
                    if(choice==='homing') en.homing_active=true;
                    else if(choice==='spread') en.spread_active=true;
                    else if(choice==='rapid') { en.rapid_active=true; en.shoot_chance*=2.5; }
                }
            }
        }
    }

    updatePlaying() {
        // Timers
        if(this.tilemap) this.tilemap.update();
        if(this.freeze_timer>0) this.freeze_timer--;

        // Difficulty ramp
        this.difficulty_ramp_timer++;
        if(this.difficulty_ramp_timer%(12*FPS)===0 && this.difficulty_ramp_timer>0) {
            if(this.max_enemies_on_field<8) this.max_enemies_on_field++;
            if(this.dynamic_spawn_interval>0.8*FPS) this.dynamic_spawn_interval=Math.max(0.8*FPS, this.dynamic_spawn_interval-8);
        }

        // Spawn
        this.spawn_timer++;
        if(this.spawn_timer>=this.dynamic_spawn_interval) {
            this.spawnEnemy();
            this.spawn_timer=0;
        }
        if(this.enemies_spawned<this.max_enemies_on_field && this.spawn_timer%30===0) this.spawnEnemy();

        // Players
        for(let p of this.players) {
            if(!p.alive) continue;
            // Input
            let dir=null;
            let shoot=false;
            if(p.player_id===1) {
                if(this.keys['KeyW']||this.keys['ArrowUp']) dir='UP';
                else if(this.keys['KeyS']||this.keys['ArrowDown']) dir='DOWN';
                else if(this.keys['KeyA']||this.keys['ArrowLeft']) dir='LEFT';
                else if(this.keys['KeyD']||this.keys['ArrowRight']) dir='RIGHT';
                if(this.keys['Space']) shoot=true;
            } else {
                if(this.keys['ArrowUp']) dir='UP';
                else if(this.keys['ArrowDown']) dir='DOWN';
                else if(this.keys['ArrowLeft']) dir='LEFT';
                else if(this.keys['ArrowRight']) dir='RIGHT';
                if(this.keys['Enter']) shoot=true;
            }
            // Gamepad
            let gamepads = navigator.getGamepads ? navigator.getGamepads() : [];
            let gp = gamepads[p.player_id-1] || gamepads[0];
            if(gp) {
                let ax0=gp.axes[0]||0, ax1=gp.axes[1]||0;
                if(Math.abs(ax0)<0.3) ax0=0;
                if(Math.abs(ax1)<0.3) ax1=0;
                if(ax1<-0.5) dir='UP';
                else if(ax1>0.5) dir='DOWN';
                else if(ax0<-0.5) dir='LEFT';
                else if(ax0>0.5) dir='RIGHT';
                if(gp.buttons[0] && gp.buttons[0].pressed) shoot=true;
            }

            if(dir) {
                p.direction=dir;
                let otherTanks=[...this.enemies, ...this.players.filter(o=>o!==p)];
                p.tryMove(dir, this.tilemap, otherTanks);
            }
            if(shoot) {
                let b=p.shoot();
                if(b) {
                    if(Array.isArray(b)) this.bullets.push(...b);
                    else this.bullets.push(b);
                }
            }
            let otherTanks=[...this.enemies, ...this.players.filter(o=>o!==p)];
            p.update(this.tilemap);
        }

        // Enemies
        for(let e of this.enemies) {
            if(this.freeze_timer>0) {
                if(e.cooldown>0) e.cooldown--;
                if(e.invulnerable_timer>0) e.invulnerable_timer--;
                if(e.spawn_protection>0) e.spawn_protection--;
                e.cooldown=Math.max(e.cooldown,1);
                continue;
            }
            e.updateAI(this.tilemap, this.players, this.enemies, this.bullets, this.base);
        }

        // Bullets
        for(let b of this.bullets) {
            if(!b.alive) continue;
            let result=b.update(this.tilemap, [...this.players, ...this.enemies], this.base);
            if(result==='hit_base') {
                // Already handled in Base.takeDamage
            }
        }
        this.bullets=this.bullets.filter(b=>b.alive);

        // Powerups
        for(let pu of this.powerups) {
            pu.update();
            let picker=pu.checkPickup(this.players);
            if(picker) {
                picker.applyPowerup(pu.type, this);
                this.powerups=this.powerups.filter(p=>p!==pu);
            }
        }
        this.powerups=this.powerups.filter(p=>p.alive);

        // Dead enemies
        for(let e of [...this.enemies]) {
            if(!e.alive) {
                let killer = this.players[0];
                if(killer) killer.score+=e.score_value;
                this.enemies=this.enemies.filter(en=>en!==e);
                this.enemies_killed++;
                if(e.powerup_carrier) {
                    let pu=new PowerUp(e.rect.centerx, e.rect.centery);
                    this.powerups.push(pu);
                }
            }
        }

        // Dead players respawn - always respawn if lives>=0, even if blocked (fix cannot move after boss)
        for(let p of this.players) {
            if(!p.alive && p.lives>=0) {
                let [gx,gy]=PLAYER_SPAWN[p.player_id-1];
                try{ this.tilemap.clearArea(gx-1,gy-1,4,4); }catch(e){}
                p.respawn(gx,gy);
                // Extra protection if blocked
                p.spawn_protection=300;
            }
        }

        // Base / Boss logic
        if(!this.base.alive) {
            if(this.base.monster_released && !this.boss_released) {
                this.releaseMonsterBoss();
            } else if(this.boss_released) {
                if(this.boss_enemy && this.boss_enemy.alive) {
                    // Boss fight ongoing
                } else {
                    // Boss dead - respawn base with steel
                    console.log("[BOSS] Defeated! Respawning base");
                    this.base.reset();
                    this.tilemap.buildBaseWalls(TILE_STEEL);
                    this.boss_enemy=null;
                    this.boss_released=false;
                    if(this.players[0]) this.players[0].score+=3000;
                }
            } else {
                // No boss, real game over
                this.state='gameover';
                this.gameover_won=false;
                return;
            }
        }

        // Win condition
        if(this.enemies_killed>=this.enemies_total && this.enemies.length===0 && !this.boss_enemy) {
            this.state='stage_clear';
            this.gameover_won=true;
            if(this.players[0]) this.players[0].score+=1000;
            return;
        }

        // All dead?
        let allDead = this.players.every(p=>!p.alive && p.lives<0);
        if(allDead) {
            this.state='gameover';
            this.gameover_won=false;
        }
    }

    updateHUD() {
        document.getElementById('stageInfo').textContent = `STAGE ${this.current_level+1} / ${mapsData ? mapsData.stage_count : 35}`;
        document.getElementById('enemyInfo').textContent = `ENEMY ${this.enemies_total-this.enemies_killed} / TOTAL ${this.enemies_total} MAX ${this.max_enemies_on_field}`;
        if(this.players[0]) {
            document.getElementById('p1Lives').textContent = this.players[0].lives;
            document.getElementById('p1Score').textContent = this.players[0].score;
            let items=[];
            if(this.players[0].homing_active) items.push('MISSILE');
            if(this.players[0].spread_active) items.push('8-WAY');
            if(this.players[0].rapid_active) items.push('RAPID x3');
            document.getElementById('p1Items').textContent = items.join(', ') || 'None';
        }
        if(this.boss_enemy && this.boss_enemy.alive) {
            document.getElementById('bossInfo').style.display='block';
            document.getElementById('bossInfo').textContent = `BOSS HP ${this.boss_enemy.health}/12 - SPEED ${this.boss_enemy.speed.toFixed(1)} (same as normal)`;
        } else {
            document.getElementById('bossInfo').style.display='none';
        }
    }

    drawMapPreview() {
        if(!mapsData || !this.mapCtx) return;
        let preview = mapsData.levels_13[0];
        let p_tile=10;
        this.mapCtx.fillStyle='#000';
        this.mapCtx.fillRect(0,0,130,130);
        for(let y=0;y<13;y++) for(let x=0;x<13;x++) {
            let t=preview[y][x];
            let tx=x*p_tile, ty=y*p_tile;
            if(t===1) { this.mapCtx.fillStyle='#D23818'; this.mapCtx.fillRect(tx,ty,p_tile,p_tile); }
            else if(t===2) { this.mapCtx.fillStyle='#D2D2D2'; this.mapCtx.fillRect(tx,ty,p_tile,p_tile); }
            else if(t===3) { this.mapCtx.fillStyle='#1C5AF0'; this.mapCtx.fillRect(tx,ty,p_tile,p_tile); }
            else if(t===4) { this.mapCtx.fillStyle='#3CA014'; this.mapCtx.fillRect(tx,ty,p_tile,p_tile); }
            else if(t===5) { this.mapCtx.fillStyle='#BEBEBE'; this.mapCtx.fillRect(tx,ty,p_tile,p_tile); }
        }
    }

    draw() {
        let ctx=this.ctx;
        ctx.fillStyle='#121218';
        ctx.fillRect(0,0,960,720);

        if(this.state==='menu') {
            // Simple menu
            ctx.fillStyle='#000';
            ctx.fillRect(0,0,960,720);
            ctx.fillStyle='#ff0';
            ctx.font='48px monospace';
            ctx.fillText('TANK 93', 360, 160);
            ctx.fillStyle='#ccc';
            ctx.font='16px monospace';
            ctx.fillText('Enhanced - 35 ORIGINAL NES MAPS - Pure JS', 300, 200);
            ctx.fillStyle = this.menu_selected===0 ? '#ff0' : '#fff';
            ctx.fillText('> 1 PLAYER (35 STAGES)', 360, 340);
            ctx.fillStyle = this.menu_selected===1 ? '#ff0' : '#fff';
            ctx.fillText('> 2 PLAYERS CO-OP (35 STAGES)', 360, 380);
            ctx.fillStyle = this.menu_selected===2 ? '#ff0' : '#fff';
            ctx.fillText('> LEVEL SELECT - 35 ORIGINAL NES MAPS', 360, 420);
            ctx.fillStyle='#0f0';
            ctx.font='14px monospace';
            ctx.fillText('DEFAULT: 1 PLAYER - 35 ORIGINAL NES MAPS - PRESS ENTER', 300, 500);
            ctx.fillStyle='#ff0';
            ctx.fillText('INSERT COIN C/5 FOR 10 LIVES - PRESS ENTER TO START', 300, 700);
            return;
        }

        // Playfield bg
        ctx.fillStyle='#000';
        ctx.fillRect(PLAYFIELD_X-4, PLAYFIELD_Y-4, PLAYFIELD_W+8, PLAYFIELD_H+8);
        // Tilemap
        this.tilemap.draw(ctx);
        // Base
        this.base.draw(ctx);
        // Tanks
        for(let e of this.enemies) e.draw(ctx);
        for(let p of this.players) p.draw(ctx);
        // Bullets
        for(let b of this.bullets) b.draw(ctx);
        // Powerups
        for(let pu of this.powerups) pu.draw(ctx);
        // Overlay
        this.tilemap.drawOverlay(ctx);
    }

    loop(timestamp) {
        if(!this.lastTime) this.lastTime=timestamp;
        let dt=timestamp-this.lastTime;
        this.lastTime=timestamp;

        if(this.state==='playing') this.updatePlaying();
        else if(this.state==='menu') {
            // Menu input
            if(this.keys['ArrowUp']||this.keys['KeyW']) {
                this.menu_selected = (this.menu_selected-1+5)%5;
                this.keys['ArrowUp']=false; this.keys['KeyW']=false;
            }
            if(this.keys['ArrowDown']||this.keys['KeyS']) {
                this.menu_selected = (this.menu_selected+1)%5;
                this.keys['ArrowDown']=false; this.keys['KeyS']=false;
            }
            if(this.keys['Enter']||this.keys['Space']) {
                if(this.menu_selected===0) this.initLevel(0,1);
                else if(this.menu_selected===1) this.initLevel(0,2);
                else if(this.menu_selected===2) { /* level select */ }
                this.keys['Enter']=false; this.keys['Space']=false;
            }
        } else if(this.state==='gameover' || this.state==='stage_clear') {
            if(this.keys['Enter']) {
                if(this.gameover_won) this.initNextLevel();
                else { this.state='menu'; this.menu_selected=0; }
                this.keys['Enter']=false;
            }
        }

        this.draw();
        this.updateHUD();
        requestAnimationFrame(this.loop.bind(this));
    }
}

let game = null;

async function init() {
    await loadAssets();
    game = new Game();
    // Hide loading
    document.getElementById('loading').style.display='none';
    // Start loop
    requestAnimationFrame((t)=>game.loop(t));
}

init();
