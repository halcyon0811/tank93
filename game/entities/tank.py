import pygame
import random
import pathlib
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
    def __init__(self, grid_x, grid_y, color, is_player=False):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * TILE_SIZE + TILE_SIZE//2
        self.y = PLAYFIELD_Y + grid_y * TILE_SIZE + TILE_SIZE//2
        # target for smooth movement snapped to tile?
        self.rect = pygame.Rect(0,0,TANK_SIZE-4, TANK_SIZE-4)
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

        self.invulnerable_timer = 0
        self.spawn_protection = 0
        self.on_ice = False

        # animation
        self.move_timer = 0
        self.track_offset = 0

    def set_position(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.x = PLAYFIELD_X + grid_x * TILE_SIZE + TILE_SIZE//2
        self.y = PLAYFIELD_Y + grid_y * TILE_SIZE + TILE_SIZE//2
        self.rect.center = (self.x, self.y)

    def get_bullet_spawn(self):
        cx, cy = self.rect.center
        offset = TANK_SIZE//2 + 4
        if self.direction == 'UP':
            return cx, cy - offset
        if self.direction == 'DOWN':
            return cx, cy + offset
        if self.direction == 'LEFT':
            return cx - offset, cy
        if self.direction == 'RIGHT':
            return cx + offset, cy
        return cx, cy

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
        self.direction = dir_name
        dx, dy = DIRS[dir_name]
        new_x = self.x + dx * self.speed
        new_y = self.y + dy * self.speed

        # check ice effect - slippery?
        if self.on_ice:
            new_x = self.x + dx * self.speed * 1.3
            new_y = self.y + dy * self.speed * 1.3

        new_rect = self.rect.copy()
        new_rect.center = (new_x, new_y)

        # bounds
        if new_rect.left < PLAYFIELD_X or new_rect.right > PLAYFIELD_X + PLAYFIELD_W:
            return False
        if new_rect.top < PLAYFIELD_Y or new_rect.bottom > PLAYFIELD_Y + PLAYFIELD_H:
            return False

        # tile collision
        tiles = tilemap.get_tiles_in_rect(new_rect)
        for ttype, gx, gy, trect in tiles:
            if new_rect.colliderect(trect):
                return False

        # tank-tank collision
        for other in other_tanks:
            if other is self or not other.alive:
                continue
            if new_rect.colliderect(other.rect):
                # small push?
                return False

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

        # check ice under
        gx = int((self.rect.centerx - PLAYFIELD_X) // TILE_SIZE)
        gy = int((self.rect.centery - PLAYFIELD_Y) // TILE_SIZE)
        if 0 <= gx < GRID_W and 0 <= gy < GRID_H:
            self.on_ice = tilemap.tiles[gy][gx] == TILE_ICE
        else:
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

                # Get sprite scaled to TANK_SIZE (32 -> 16*2) using cached version for perf
                from ..assets.sprites import get_cached_tank
                spr = get_cached_tank(sprite_color, self.direction, anim, sprite_level, TANK_SIZE)
                if spr is None:
                    # fallback to non-cached
                    from ..assets.sprites import get_tank_sprite_scaled as _g
                    spr = _g(sprite_color, self.direction, anim_frame=anim, level=sprite_level, size=TANK_SIZE)
                if spr is not None:
                    # flicker when invulnerable (original NES tanks blink when spawn protection)
                    if shield_flicker and self.invulnerable_timer % 8 < 4:
                        # skip draw for blink effect - draw only shield already
                        pass
                    else:
                        # Center blit
                        rect = spr.get_rect(center=self.rect.center)
                        screen.blit(spr, rect)

                        # player indicator small
                        if self.is_player:
                            pid = getattr(self, 'player_id', 1)
                            # small P1/P2 label above like NES?
                            # In original NES, no label, but we keep for co-op clarity small
                            font = pygame.font.Font(None, 14)
                            txt = font.render(f"P{pid}", True, COLOR_WHITE if pid==1 else (100,255,100))
                            # background black
                            txt_bg = pygame.Surface((txt.get_width()+4, txt.get_height()+2))
                            txt_bg.fill((0,0,0))
                            screen.blit(txt_bg, (self.rect.centerx - txt.get_width()//2 -2, self.rect.top - 14))
                            screen.blit(txt, (self.rect.centerx - txt.get_width()//2, self.rect.top - 14))

                        # armor health bar for armor tanks (keep for gameplay clarity)
                        if getattr(self, 'enemy_type', '') == 'armor' and getattr(self, 'health',1) > 1 and not self.is_player:
                            bar_w = 20
                            bar_h = 4
                            cx = self.rect.centerx
                            cy = self.rect.bottom + 2
                            pygame.draw.rect(screen, (0,0,0), (cx-bar_w//2-1, cy-1, bar_w+2, bar_h+2))
                            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
                            # green to red based on health
                            frac = self.health / 4.0
                            col = (int(255*(1-frac)), int(255*frac), 0)
                            pygame.draw.rect(screen, col, (cx-bar_w//2, cy, int(bar_w*frac), bar_h))

                    return  # authentic sprite drawn, skip fallback
            except Exception as e:
                # fallback to procedural if sprite fails
                # print(f"Sprite draw error {e}")
                pass

        # ---- Fallback procedural retro (if sheet missing) ----
        cx, cy = self.rect.center
        size = TANK_SIZE - 6

        # shadow
        # pygame.draw.rect(screen, (0,0,0, 100), (cx - size//2 +2, cy - size//2 +4, size, size), border_radius=3)

        # Modern simplified fallback that resembles NES yellow/gray etc.
        # Body color already set via self.color (yellow/green/silver/red)
        body_rect = pygame.Rect(0,0,size-4, size-4)
        body_rect.center = (cx, cy)
        pygame.draw.rect(screen, self.color, body_rect)
        pygame.draw.rect(screen, COLOR_BLACK, body_rect, 2)
        # turret
        cannon_len = 12
        cannon_w = 4
        if self.direction == 'UP':
            pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy - size//2, cannon_w, cannon_len))
        elif self.direction == 'DOWN':
            pygame.draw.rect(screen, (30,30,30), (cx - cannon_w//2, cy + size//2 - cannon_len, cannon_w, cannon_len))
        elif self.direction == 'LEFT':
            pygame.draw.rect(screen, (30,30,30), (cx - size//2, cy - cannon_w//2, cannon_len, cannon_w))
        elif self.direction == 'RIGHT':
            pygame.draw.rect(screen, (30,30,30), (cx + size//2 - cannon_len, cy - cannon_w//2, cannon_len, cannon_w))
        # eagle turret center
        pygame.draw.circle(screen, (20,20,20), (cx, cy), 4)
