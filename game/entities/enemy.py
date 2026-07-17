import pygame
import random
import math
from .tank import Tank
from .bullet import Bullet
from ..settings import *

class EnemyTank(Tank):
    def __init__(self, grid_x, grid_y, enemy_type='basic'):
        color = ENEMY_COLORS.get(enemy_type, ENEMY_COLORS['basic'])
        super().__init__(grid_x, grid_y, color, is_player=False)
        self.enemy_type = enemy_type
        self.direction = 'DOWN'
        self.is_player = False

        # stats by type
        if enemy_type == 'basic':
            self.speed = TANK_SPEED['enemy']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 100
            self.shoot_chance = 0.02
        elif enemy_type == 'fast':
            self.speed = TANK_SPEED['fast']
            self.health = 1
            self.bullet_power = 1
            self.score_value = 200
            self.shoot_chance = 0.03
        elif enemy_type == 'power':
            self.speed = TANK_SPEED['enemy'] * 1.1
            self.health = 1
            self.bullet_power = 1
            self.score_value = 300
            self.shoot_chance = 0.04
        elif enemy_type == 'armor':
            self.speed = TANK_SPEED['enemy'] * 0.8
            self.health = 4
            self.bullet_power = 1
            self.score_value = 400
            self.shoot_chance = 0.02

        self.spawn_protection = 60
        self.invulnerable_timer = 60
        self.powerup_carrier = random.random() < 0.25  # 25% carry powerup

        self.state = 'wander'
        self.target_dir_timer = 0
        self.stuck_timer = 0
        self.last_pos = (self.x, self.y)

        # flashing for powerup carrier (classic red)
        self.flash_timer = 0

    def update_ai(self, tilemap, players, other_tanks, bullets_list):
        if not self.alive:
            return None

        self.flash_timer += 1
        # update timers
        self.target_dir_timer -= 1
        # check if stuck
        dist = math.hypot(self.x - self.last_pos[0], self.y - self.last_pos[1])
        if dist < 0.5:
            self.stuck_timer += 1
        else:
            self.stuck_timer = 0
        self.last_pos = (self.x, self.y)

        # decide direction
        if self.target_dir_timer <= 0 or self.stuck_timer > 30:
            self.choose_new_direction(players, tilemap)
            self.target_dir_timer = random.randint(30, 120)
            self.stuck_timer = 0

        # try move
        moved = self.try_move(self.direction, tilemap, other_tanks + players)

        # if blocked, pick new direction sooner
        if not moved:
            self.target_dir_timer = 0

        # shooting
        new_bullet = None
        # higher chance if aligned with player or base
        aligned = self.is_aligned_with_target(players)
        chance = self.shoot_chance * (3 if aligned else 1)
        if random.random() < chance:
            new_bullet = self.shoot()
            if new_bullet:
                bullets_list.append(new_bullet)

        super().update(tilemap, other_tanks + players)
        self.bullets = [b for b in self.bullets if b.alive]
        return new_bullet

    def choose_new_direction(self, players, tilemap):
        # simple AI: try to go towards nearest player or base with some randomness
        possible = ['UP', 'DOWN', 'LEFT', 'RIGHT']
        # avoid opposite if not stuck
        opposite = {'UP':'DOWN','DOWN':'UP','LEFT':'RIGHT','RIGHT':'LEFT'}
        if self.direction in opposite and self.stuck_timer < 20:
            if opposite[self.direction] in possible:
                # reduce chance to go back
                if random.random() < 0.7:
                    possible.remove(opposite[self.direction])

        # weighted towards target
        if players and any(p.alive for p in players):
            alive_players = [p for p in players if p.alive]
            closest = min(alive_players, key=lambda p: math.hypot(p.x - self.x, p.y - self.y))
            dx = closest.x - self.x
            dy = closest.y - self.y
            # bias
            if abs(dx) > abs(dy):
                preferred = 'RIGHT' if dx>0 else 'LEFT'
            else:
                preferred = 'DOWN' if dy>0 else 'UP'
            if preferred in possible and random.random() < 0.6:
                self.direction = preferred
                return

        self.direction = random.choice(possible)

    def is_aligned_with_target(self, players):
        for p in players:
            if not p.alive:
                continue
            # check if same row/col roughly
            if abs(p.x - self.x) < 20 and (
                (self.direction == 'DOWN' and p.y > self.y) or
                (self.direction == 'UP' and p.y < self.y)
            ):
                return True
            if abs(p.y - self.y) < 20 and (
                (self.direction == 'RIGHT' and p.x > self.x) or
                (self.direction == 'LEFT' and p.x < self.x)
            ):
                return True
        return False

    def shoot(self):
        if not self.can_shoot():
            return None
        sx, sy = self.get_bullet_spawn()
        b = Bullet(sx, sy, self.direction, 'enemy', power=self.bullet_power, color=(255, 100, 100))
        self.bullets.append(b)
        self.cooldown = random.randint(40, 90)
        return b

    def take_damage(self, power=1):
        if self.invulnerable_timer > 0 or self.spawn_protection > 0:
            return False
        self.health -= power
        if self.health <= 0:
            self.die()
            return True
        else:
            # flash armor hit
            self.invulnerable_timer = 10
            return False

    def draw(self, screen):
        if not self.alive:
            return
        # flash if carrier or invuln
        if self.powerup_carrier:
            # classic flashing red
            if (self.flash_timer // 8) % 2 == 0:
                orig_color = self.color
                self.color = (255, 50, 50)
                super().draw(screen)
                self.color = orig_color
                return
        super().draw(screen)
        # armor indicator
        if self.enemy_type == 'armor' and self.health > 1:
            # health bar
            bar_w = 20
            bar_h = 3
            cx, cy = self.rect.centerx, self.rect.top - 6
            pygame.draw.rect(screen, (60,60,60), (cx-bar_w//2, cy, bar_w, bar_h))
            pygame.draw.rect(screen, (0,255,0), (cx-bar_w//2, cy, int(bar_w*(self.health/4)), bar_h))
