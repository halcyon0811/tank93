// NES authentic tile rendering for VERY high quality itch.io release
// Matches Python game/tilemap.py draw_brick, draw_steel, draw_water, draw_grass, draw_ice

export function drawBrick(ctx, x, y, size, hits=0) {
  // NES red-orange bricks #D23818 with dark mortar #8C1E0A and light highlight #F07846
  // Authentic Battle City has 4 small bricks per 16x16 tile in 2x2 layout with mortar gaps
  ctx.fillStyle = '#8C1E0A'; // mortar dark
  ctx.fillRect(x, y, size, size);

  // 2x2 small bricks inside
  let gap = 2;
  let bw = (size - gap*3)/2;
  let bh = (size - gap*3)/2;

  ctx.fillStyle = '#D23818';
  // Top-left
  ctx.fillRect(x+gap, y+gap, bw, bh);
  // Top-right
  ctx.fillRect(x+gap*2+bw, y+gap, bw, bh);
  // Bottom-left
  ctx.fillRect(x+gap, y+gap*2+bh, bw, bh);
  // Bottom-right
  ctx.fillRect(x+gap*2+bw, y+gap*2+bh, bw, bh);

  // Highlight top edge of each small brick (NES had lighter top)
  ctx.fillStyle = '#F07846';
  ctx.fillRect(x+gap, y+gap, bw, 2);
  ctx.fillRect(x+gap*2+bw, y+gap, bw, 2);
  ctx.fillRect(x+gap, y+gap*2+bh, bw, 2);
  ctx.fillRect(x+gap*2+bw, y+gap*2+bh, bw, 2);

  // Damage cracks based on hits
  if (hits > 0) {
    ctx.fillStyle = 'rgba(0,0,0,0.35)';
    // Random crack lines based on hits
    let crackCount = Math.min(hits, 4);
    for(let i=0;i<crackCount;i++){
      let cx = x + gap + (i%2)*(bw+gap) + bw*0.2;
      let cy = y + gap + Math.floor(i/2)*(bh+gap) + bh*0.2;
      ctx.fillRect(cx, cy, bw*0.6, 1);
    }
  }
}

export function drawSteel(ctx, x, y, size, hits=0) {
  // NES steel: light gray #D2D2D2 border, white inner #FFF, dark gray rivets #828282
  ctx.fillStyle = '#828282';
  ctx.fillRect(x, y, size, size);

  ctx.fillStyle = '#D2D2D2';
  ctx.fillRect(x+1, y+1, size-2, size-2);

  ctx.fillStyle = '#FFF';
  ctx.fillRect(x+3, y+3, size-6, size-6);

  // Rivets at corners (NES steel has dots)
  ctx.fillStyle = '#646464';
  ctx.fillRect(x+2, y+2, 3, 3);
  ctx.fillRect(x+size-5, y+2, 3, 3);
  ctx.fillRect(x+2, y+size-5, 3, 3);
  ctx.fillRect(x+size-5, y+size-5, 3, 3);

  // Interior cross for steel texture
  ctx.fillStyle = 'rgba(0,0,0,0.15)';
  ctx.fillRect(x+size/2-1, y+3, 2, size-6);
  ctx.fillRect(x+3, y+size/2-1, size-6, 2);

  if (hits > 0) {
    ctx.fillStyle = `rgba(0,0,0,${Math.min(0.5, hits*0.15)})`;
    ctx.fillRect(x, y, size, size);
  }
}

export function drawWater(ctx, x, y, size) {
  ctx.fillStyle = '#1C5AF0';
  ctx.fillRect(x, y, size, size);

  // Animated sparkles (NES had flickering white dots)
  let t = Date.now();
  let phase = Math.floor(t/200) % 3;
  ctx.fillStyle = '#E8F0FF';
  let patterns = [
    [[3,4],[10,8],[18,14]],
    [[6,3],[14,10],[8,18]],
    [[4,12],[16,5],[12,16]]
  ];
  let pat = patterns[phase];
  for(let [dx,dy] of pat){
    ctx.fillRect(x+dx, y+dy, 3, 2);
  }
}

export function drawGrass(ctx, x, y, size) {
  // Dense forest that hides tanks - NES style mottled green
  ctx.fillStyle = '#3CA014';
  ctx.fillRect(x, y, size, size);

  // Dark leaves
  ctx.fillStyle = '#2A7A0A';
  // Seeded random based on position
  let seed = x*17 + y*31;
  let rand = (n)=>{ seed = (seed*9301 + 49297) % 233280; return (seed/r233280)*n; };

  for(let i=0;i<10;i++){
    let rx = x + rand(size-6);
    let ry = y + rand(size-6);
    ctx.fillRect(rx, ry, 4, 4);
  }

  ctx.fillStyle = '#B0E050';
  for(let i=0;i<6;i++){
    let rx = x + rand(size-4);
    let ry = y + rand(size-4);
    ctx.fillRect(rx, ry, 3, 3);
  }

  // Fully opaque to hide tanks underneath (drawn as overlay)
}

export function drawIce(ctx, x, y, size) {
  ctx.fillStyle = '#BEBEBE';
  ctx.fillRect(x, y, size, size);

  ctx.fillStyle = '#828287';
  // Diagonal hatching (NES ice had light gray stripes)
  for(let i=0;i<size;i+=6){
    ctx.fillRect(x+i, y, 1, size);
  }

  ctx.fillStyle = '#E6E6E6';
  ctx.fillRect(x+4, y+4, 8, 2);
  ctx.fillRect(x+12, y+14, 8, 2);
}

export function drawTile(ctx, type, x, y, size, hits=0) {
  // type: 0 empty, 1 brick, 2 steel, 3 water, 4 grass, 5 ice
  if(type===1) drawBrick(ctx, x, y, size, hits);
  else if(type===2) drawSteel(ctx, x, y, size, hits);
  else if(type===3) drawWater(ctx, x, y, size);
  else if(type===4) drawGrass(ctx, x, y, size);
  else if(type===5) drawIce(ctx, x, y, size);
}
