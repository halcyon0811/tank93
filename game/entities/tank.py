import pygame
import random
import pathlib
import math
from ..settings import *

# Try to load authentic NES sprite sheet
try:
    from ..assets.sprites import get_tank_sprite_scaled
    HAS_AUTHENTIC_SPRITES = True
except Exception:
    HAS_AUTHENTIC_SPRITES = False
    def get_tank_sprite_scaled(*a, **k):
        return None

class Tank:
    def __init__(self, grid_x, grid_y, color, is_player=False, is_mega=None):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.is_mega = is_mega if is_mega is not None else MEGA_ENABLED
        self.tile_size = MEGA_TILE_SIZE if self.is_mega else TILE_SIZE
        self.x = PLAYFIELD_X + grid_x * self.tile_size + self.tile_size//2
        self.y = PLAYFIELD_Y + grid_y * self.tile_size + self.tile_size//2
        # Use full TANK_SIZE for collision to avoid visual overlapping with bricks
        self.base_size = TANK_SIZE
        self.current_scale = 1.0
        self.rect = pygame.Rect(0,0,self.base_size, self.base_size)
        self.rect.center = (self.x, self.y)

        self.color = color
        self.is_player = is_player
        self.alive = True
        self.direction = 'UP'
        self.next_direction = None

        self.bullets = []
        self.cooldown = 0
        self.bullet_power = 1
        self.speed = TANK_SPEED['player'] if is_player else TANK_SPEED['enemy']
        self.base_speed = self.speed

        self.invulnerable_timer = 0
        self.spawn_protection = 0
        self.on_ice = False

        # size effects
        self.shrink_timer = 0
        self.giant_timer = 0
        self.is_shrunk = False
        self.is_giant = False

        # venom
        self.venom_timer = 0
        self.venom_level = 0

        # animation
        self.move_timer = 0
        self.track_offset = 0

    def update_size_state(self):
        # Handle shrink/giant timers
        if self.shrink_timer > 0:
            self.shrink_timer -= 1
            self.is_shrunk = True
            self.current_scale = SHRINK_SCALE
            self.speed = self.base_speed * SHRINK_SPEED_MULT
            if self.shrink_timer == 0:
                self.is_shrunk = False
                self.current_scale = 1.0 if not self.is_giant else GIANT_SCALE
                self.speed = self.base_speed * (2.0 if self.is_giant else 1.0)
                self._update_rect_size()
        if self.giant_timer > 0:
            self.giant_timer -= 1
            self.is_giant = True
            self.current_scale = GIANT_SCALE
            if self.giant_timer == 0:
                self.is_giant = False
                self.current_scale = SHRINK_SCALE if self.is_shrunk else 1.0
                # speed back to normal or shrunk
                if self.is_shrunk:
                    self.speed = self.base_speed * SHRINK_SPEED_MULT
                else:
                    self.speed = self.base_speed
                self._update_rect_size()
        # update rect size based on scale
        self._update_rect_size()

    def _update_rect_size(self):
        sz = int(self.base_size * self.current_scale)
        # prevent too tiny
        sz = max(12, sz)
        self.rect = pygame.Rect(0,0,sz,sz)
        self.rect.center = (self.x, self.y)

    def set_position(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * self.tile_size + self.tile_size//2
        self.y = PLAYFIELD_Y + grid_y * self.tile_size + self.tile_size//2
        self.rect.center = (self.x, self.y)

    def get_bullet_spawn(self):
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        offset = int((TANK_SIZE//2 + 4) * scale)
        dx, dy = DIRS.get(self.direction, (0, -1))
        return cx + dx * offset, cy + dy * offset

    def can_shoot(self):
        if self.cooldown > 0:
            return False
        max_b = MAX_BULLETS['player'] if self.is_player else MAX_BULLETS['enemy']
        # count alive bullets
        alive = len([b for b in self.bullets if b.alive])
        return alive < max_b

    def try_move(self, dir_name, tilemap, other_tanks):
        if not self.alive:
            return False

        # Authentic turning: try to snap to grid when turning (original NES 8-pixel alignment)
        # Store previous direction to detect turn
        prev_dir = self.direction
        is_turn = prev_dir != dir_name and prev_dir is not None

        # Determine snap attempt for turning
        snap_x = self.x
        snap_y = self.y
        if is_turn:
            # When turning from vertical to horizontal, snap Y to nearest half-tile
            # When turning from horizontal to vertical, snap X
            # Half-tile = TILE_SIZE//2 = 12 px, center offset = TILE_SIZE//2
            # Formula: nearest = PLAYFIELD + round((pos - PLAYFIELD - TILE_SIZE//2)/ (TILE_SIZE//2)) * (TILE_SIZE//2) + TILE_SIZE//2
            half = TILE_SIZE // 2
            if prev_dir in ('UP','DOWN') and dir_name in ('LEFT','RIGHT'):
                # Snap Y
                rel_y = self.y - PLAYFIELD_Y - TILE_SIZE//2
                # nearest half-tile
                snapped_rel = round(rel_y / half) * half
                snap_y = PLAYFIELD_Y + snapped_rel + TILE_SIZE//2
                # Only snap if close enough (within 8 px) to avoid jumping
                if abs(snap_y - self.y) > 8:
                    snap_y = self.y  # too far, don't snap
            elif prev_dir in ('LEFT','RIGHT') and dir_name in ('UP','DOWN'):
                rel_x = self.x - PLAYFIELD_X - TILE_SIZE//2
                snapped_rel = round(rel_x / half) * half
                snap_x = PLAYFIELD_X + snapped_rel + TILE_SIZE//2
                if abs(snap_x - self.x) > 8:
                    snap_x = self.x

        self.direction = dir_name
        dx, dy = DIRS[dir_name]
        # Normalize diagonal speed so diagonal not faster than cardinal
        if dx != 0 and dy != 0:
            # Diagonal: normalize to 0.707
            dx *= 0.7071
            dy *= 0.7071

        # Ice effect - authentic: higher speed + slight slide
        speed_mult = 1.35 if self.on_ice else 1.0
        new_x = snap_x + dx * self.speed * speed_mult
        new_y = snap_y + dy * self.speed * speed_mult

        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # bounds - authentic: tanks cannot go outside playfield, allow 4px tolerance for smooth edge movement
        # Original NES allows tank to go slightly outside when spawning
        if new_rect.left < PLAYFIELD_X - 6 or new_rect.right > PLAYFIELD_X + PLAYFIELD_W + 6:
            return False
        if new_rect.top < PLAYFIELD_Y - 6 or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H + 6:
            return False

        # tile collision - FIXED overlap bug: previous rect was 28 and check was 20 (inflate -4-4) causing 6px visual overlap with brick
        # Now use full TANK_SIZE (32) for collision and 0 shrink for strict no-overlap, draw is 30 for visual gap
        is_giant = getattr(self, 'is_giant', False) and getattr(self, 'giant_timer', 0) > 0
        # Strict collision - no shrink, so no visual overlap at all. Giant also uses full rect but crushes bricks.
        check_rect = new_rect.copy()
        tiles = tilemap.get_tiles_in_rect(check_rect)
        crushed_bricks = []
        for ttype, gx, gy, trect in tiles:
            if check_rect.colliderect(trect):
                if ttype == TILE_BRICK and is_giant:
                    crushed_bricks.append((gx, gy))
                    continue
                if is_turn and (abs(snap_x - self.x) > 0.1 or abs(snap_y - self.y) > 0.1):
                    # Try without snap (original position + movement only) to allow turning near walls without clipping
                    new_rect2 = self.rect.copy()
                    new_rect2.center = (self.x + dx * self.speed * speed_mult, self.y + dy * self.speed * speed_mult)
                    check_rect2 = new_rect2.copy()
                    tiles2 = tilemap.get_tiles_in_rect(check_rect2)
                    blocked2 = False
                    for t2, gx2, gy2, tr2b in tiles2:
                        if not check_rect2.colliderect(tr2b):
                            continue
                        if t2 == TILE_BRICK and is_giant:
                            continue
                        blocked2 = True
                        break
                    if not blocked2:
                        snap_x, snap_y = self.x, self.y
                        new_x = self.x + dx * self.speed * speed_mult
                        new_y = self.y + dy * self.speed * speed_mult
                        new_rect = new_rect2
                        check_rect = check_rect2
                        tiles = tiles2
                        # collect crushed bricks for new_rect2
                        for t2, gx2, gy2, _ in tiles2:
                            if t2 == TILE_BRICK and is_giant and check_rect2.colliderect(_):
                                if (gx2, gy2) not in crushed_bricks:
                                    crushed_bricks.append((gx2, gy2))
                    else:
                        return False
                else:
                    return False

        for gx, gy in crushed_bricks:
            try:
                tilemap.destroy_tile(gx, gy, 2, dir_name)
            except:
                try:
                    tilemap.destroy_tile(gx, gy, 2)
                except:
                    pass

        # tank-tank collision - strict full rects to prevent any visual overlap, giant can run over enemies
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect):
                # If self is player giant and other is enemy, crush it
                if is_giant and self.is_player and not other.is_player:
                    # Crush enemy
                    try:
                        other.die()
                        # score?
                        if hasattr(self, 'score'):
                            self.score += getattr(other, 'score_value', 100)
                    except:
                        other.alive = False
                    continue  # don't block, ran over
                # Shrink can go through smaller gaps? No, still block
                return False

        # Move successful - apply snap if any
        self.x = new_x
        self.y = new_y
        self.rect.center = (self.x, self.y)
        self.move_timer += 1
        self.track_offset = (self.track_offset + self.speed) % 8
        return True

    def update(self, tilemap, other_tanks):
        if self.cooldown > 0:
            self.cooldown -= 1
        if self.invulnerable_timer > 0:
            self.invulnerable_timer -= 1
        if self.spawn_protection > 0:
            self.spawn_protection -= 1

        # size effects
        self.update_size_state()

        # venom dissolve over 10s
        if getattr(self, 'venom_timer', 0) > 0:
            self.venom_timer -= 1
            self.venom_level = 1.0 - (self.venom_timer / VENOM_DISSOLVE_TIME)
            if self.venom_timer <= 0:
                # destroyed by venom
                self.alive = False
                self.venom_level = 1.0

        # check ice under
        try:
            gx = int((self.rect.centerx - PLAYFIELD_X) // TILE_SIZE)
            gy = int((self.rect.centery - PLAYFIELD_Y) // TILE_SIZE)
            if 0 <= gx < GRID_W and 0 <= gy < GRID_H and tilemap is not None:
                self.on_ice = tilemap.tiles[gy][gx] == TILE_ICE
            else:
                self.on_ice = False
        except:
            self.on_ice = False

    def take_damage(self, power=1):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        # armor logic in subclass
        return True

    def die(self):
        self.alive = False

    def draw(self, screen):
        if not self.alive:
            return

        # Venom dissolve visual - tank gradually dissolves/green slime over 10s
        venom_t = getattr(self, 'venom_timer', 0)
        venom_lv = getattr(self, 'venom_level', 0)
        if venom_t > 0 and hasattr(self, 'venom_timer'):
            # flicker green and shrink visually
            diss = venom_lv  # 0->1
            # green overlay
            if int(pygame.time.get_ticks()/100) % 2 == 0 or diss > 0.5:
                # will draw extra below
                pass

        # If authentic NES sprites available, use them for true retro look matching downloaded_maps
        # This matches General-Sprites.png ripped from NES ROM (yellow player, green P2, silver enemy, red power)
        shield_flicker = self.invulnerable_timer > 0 and (self.invulnerable_timer // 4) % 2 == 0
        if shield_flicker:
            # draw shield (NES had blinking shield)
            pygame.draw.circle(screen, (200,200,200), self.rect.center, TANK_SIZE//2+6, 2)

        # Determine which sprite color to use based on downloaded_maps + original NES sheet
        # P1 = yellow, P2 = green, Enemy basic = silver (gray), fast = gray but faster, power = red, armor = red/purple (we use red)
        # Star levels: for player, increasing power shows bigger gun – we will map level to sprite row
        sprite_color = None
        sprite_level = 0

        # Check for powerup carrier flashing (original NES flashes red/silver) – we already flash red in subclass but here handle base
        is_powerup_flash = getattr(self, 'powerup_carrier', False) and getattr(self, 'flash_timer', 0) % 16 < 8 and hasattr(self, 'flash_timer') and ((self.flash_timer // 8) % 2 == 0) if hasattr(self, 'flash_timer') else False

        if self.is_player:
            # P1 yellow, P2 green
            pid = getattr(self, 'player_id', 1)
            if pid == 1:
                sprite_color = 'yellow'
            else:
                sprite_color = 'green'
            # star level mapping: 0 basic (small gun), 1 fast? Actually armor level shows bigger? Use star_level as level index
            sprite_level = getattr(self, 'star_level', 0)  # 0-3
        else:
            # enemy
            etype = getattr(self, 'enemy_type', 'basic')
            if etype == 'basic':
                sprite_color = 'silver'
                sprite_level = 0
            elif etype == 'fast':
                sprite_color = 'silver'  # same but faster – in NES fast is same gray but we could offset?
                sprite_level = 1
            elif etype == 'power':
                sprite_color = 'red'
                sprite_level = 0
            elif etype == 'armor':
                sprite_color = 'red'
                # armor health 4 -> 1 etc. map to row for visual damage? Use health-1 inverse? Let's use 4-health as level for armor stages
                hp = getattr(self, 'health', 1)
                sprite_level = max(0, 4 - hp)  # 0 = full, 3 = damaged but in NES armor uses same sprite with flashing colors
            else:
                sprite_color = 'silver'

            # flashing red for powerup carrier (like original)
            if getattr(self, 'powerup_carrier', False):
                # original flashes red/silver every 8 frames
                if (getattr(self, 'flash_timer', 0) // 8) % 2 == 0:
                    sprite_color = 'red'

        # Try authentic sprite - now with verified DIR_OFFSETS UP,RIGHT,DOWN,LEFT *2 frames
        if HAS_AUTHENTIC_SPRITES and sprite_color:
            try:
                # Anim frame based on movement (tread animation) - NES toggles every ~8 frames
                anim = 0
                if hasattr(self, 'move_timer') and self.move_timer:
                    # use move_timer // 6 for faster tread like NES (2 frames)
                    anim = (self.move_timer // 6) % 2

                # For authentic retro tanks we also want to mirror powerup flashing like original (red/silver flashing)
                # Already handled color flashing above

                # Get sprite scaled to current size (shrink/giant) - draw slightly smaller than collision rect for visual gap
                scale = getattr(self, 'current_scale', 1.0)
                draw_size = int((TANK_SIZE - 2) * scale)  # 2px smaller than collision rect = 1px gap around
                from ..assets.sprites import get_cached_tank
                spr = get_cached_tank(sprite_color, self.direction, anim, sprite_level, draw_size)
                if spr is None:
                    from ..assets.sprites import get_tank_sprite_scaled as _g
                    spr = _g(sprite_color, self.direction, anim_frame=anim, level=sprite_level, size=draw_size)
                if spr is not None:
                    if shield_flicker and self.invulnerable_timer % 8 < 4:
                        pass
                    else:
                        # Apply venom dissolve alpha
                        venom_t = getattr(self, 'venom_timer', 0)
                        venom_lv = getattr(self, 'venom_level', 0)
                        draw_spr = spr
                        if venom_t > 0:
                            # make sprite greener and partially transparent as it dissolves
                            # create tinted copy
                            try:
                                tinted = spr.copy()
                                # green overlay with alpha based on level
                                overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
                                alpha = int(120 * min(1.0, venom_lv*1.5 + 0.2))
                                overlay.fill((40, 200, 40, alpha))
                                tinted.blit(overlay, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
                                # dissolve: shrink alpha over time
                                if venom_lv > 0.5:
                                    fade_alpha = int(255 * (1.0 - (venom_lv-0.5)*2))
                                    tinted.set_alpha(max(30, fade_alpha))
                                draw_spr = tinted
                            except:
                                draw_spr = spr
                        rect = draw_spr.get_rect(center=self.rect.center)
                        screen.blit(draw_spr, rect)

                        if self.is_player:
                            pid = getattr(self, 'player_id', 1)
                            font = pygame.font.Font(None, 14)
                            # show size effect
                            extra = ""
                            if getattr(self, 'is_giant', False):
                                extra = " GIANT"
                            elif getattr(self, 'is_shrunk', False):
                                extra = " MINI"
                            if venom_t > 0:
                                extra += f" VENOM {venom_t//FPS}s"
                            label = f"P{pid}{extra}"
                            txt = font.render(label, True, COLOR_WHITE if pid==1 else (100,255,100))
                            txt_bg = pygame.Surface((txt.get_width()+4, txt.get_height()+2))
                            txt_bg.fill((0,0,0))
                            screen.blit(txt_bg, (self.rect.centerx - txt.get_width()//2 -2, self.rect.top - 14))
                            screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.top - 14))

                        if getattr(self, 'enemy_type', '') == 'armor' and getattr(self, 'health',1) > 1 and not self.is_player:
                            bar_w = 20
                            bar_h = 4
                            cx = self.rect.centerx
                            cy = self.rect.bottom + 2
                            pygame.draw.rect(screen, (0,0,0), (cx-bar_w//2-1, cy-1, bar_w+2, bar_h+2))
                            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
                            frac = self.health / 4.0
                            col = (int(255*(1-frac)), int(255*frac), 0)
                            pygame.draw.rect(screen, col, (cx-bar_w//2, cy, int(bar_w*frac), bar_h))

                        # Giant aura / shrink sparkles
                        if getattr(self, 'is_giant', False):
                            pygame.draw.rect(screen, (255, 80, 80), self.rect, 2, border_radius=4)
                        if getattr(self, 'is_shrunk', False):
                            for _ in range(2):
                                sx = self.rect.centerx + random.randint(-6,6)
                                sy = self.rect.centery + random.randint(-6,6)
                                pygame.draw.circle(screen, (150, 220, 255), (sx, sy), 1)
                        if venom_t > 0:
                            # dripping slime
                            for i in range(int(3 + venom_lv*4)):
                                sx = self.rect.centerx + random.randint(-8,8)
                                sy = self.rect.bottom - 4 + int(venom_lv*6) + i*3
                                pygame.draw.circle(screen, (60, 200, 60), (sx, sy), max(1, int(3-venom_lv*2)))

                    return
            except Exception as e:
                # fallback to procedural if sprite fails
                # print(f"Sprite draw error {e}")
                pass

        # ---- Fallback procedural retro (if sheet missing) ----
        cx, cy = self.rect.center
        scale = getattr(self, 'current_scale', 1.0)
        size = int((TANK_SIZE - 8) * scale)  # 8px smaller for visual gap

        # Modern simplified fallback that resembles NES yellow/gray etc.
        body_rect = pygame.Rect(0,0,size-4, size-4)
        body_rect.center = (cx, cy)
        pygame.draw.rect(screen, self.color, body_rect)
        pygame.draw.rect(screen, COLOR_BLACK, body_rect, 2)
        # turret - now supports 8 directions
        import math
        cannon_len = 12
        cannon_w = 4
        # Use DIR_ANGLE for cannon direction
        angle_map = DIR_ANGLE if 'DIR_ANGLE' in globals() else {}
        if self.direction in angle_map:
            ang_deg = angle_map[self.direction]
            ang_rad = math.radians(ang_deg - 90)  # UP is -90 deg in math coords? Actually 0 deg UP means pointing up (negative Y)
            # For UP (0 deg), direction vector is (0,-1)
            # Convert: angle 0 = UP, 90=RIGHT, etc. So vector = (sin(angle), -cos(angle))
            vx = math.sin(math.radians(ang_deg))
            vy = -math.cos(math.radians(ang_deg))
            # draw line for cannon
            x2 = cx + vx * (size//2 + 2)
            y2 = cy + vy * (size//2 + 2)
            pygame.draw.line(screen, (30,30,30), (cx, cy), (x2, y2), cannon_w)
        else:
            # fallback cardinal check
            if self.direction == 'UP':
                pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy - size//2, cannon_w, cannon_len))
            elif self.direction == 'DOWN':
                pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy + size//2 - cannon_len, cannon_w, cannon_len))
            elif self.direction == 'LEFT':
                pygame.draw.rect(screen, (30,30,30), (cx - size//2, cy - cannon_w//2, cannon_len, cannon_w))
            elif self.direction == 'RIGHT':
                pygame.draw.rect(screen, (30,30,30), (cx + size//2 - cannon_len, cy - cannon_w//2, cannon_len, cannon_w))
            else:
                # diagonal fallback: draw line using DIRS
                dx, dy = DIRS.get(self.direction, (0,-1))
                x2 = cx + dx * (size//2 + 4)
                y2 = cy + dy * (size//2 + 4)
                pygame.draw.line(screen, (30,30,30), (cx, cy), (x2, y2), cannon_w)

        # turret center
        pygame.draw.circle(screen, (20,20,20), (cx, cy), 4)
