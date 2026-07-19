import pygame
import math
from ..settings import *

class HUD:
    def __init__(self, is_mega=False):
        self.is_mega = is_mega
        self.font_small = pygame.font.Font(None, 22)
        self.font_mid = pygame.font.Font(None, 26)
        self.font_big = pygame.font.Font(None, 32)
        self.font_huge = pygame.font.Font(None, 48)

    def draw(self, screen, game):
        # Redesigned HUD - concise, no overflow, only game-relevant info
        # User request: lives, enemy left, points, damage per player, items on map, what they do
        hud_x = HUD_X
        hud_w = HUD_W
        hud_h = PLAYFIELD_H
        try:
            if getattr(game, 'is_mega', False):
                hud_x = MEGA_PLAYFIELD_W + MEGA_PLAYFIELD_X + 20
                hud_w = 260
                hud_h = MEGA_PLAYFIELD_H
            elif hasattr(game, 'tilemap') and game.tilemap:
                hud_x = game.tilemap.grid_w * game.tilemap.tile_size + PLAYFIELD_X + 20
                hud_w = max(200, HUD_W)
                hud_h = game.tilemap.grid_h * game.tilemap.tile_size
        except:
            pass
        # Keep HUD inside screen
        hud_w = min(hud_w, SCREEN_WIDTH - hud_x - 10)
        panel_rect = pygame.Rect(hud_x, PLAYFIELD_Y, hud_w, hud_h)
        pygame.draw.rect(screen, (22, 22, 32), panel_rect, border_radius=10)
        pygame.draw.rect(screen, (50, 50, 70), panel_rect, 2, border_radius=10)

        # Fonts - smaller to fit
        xpos = hud_x + 10
        right_limit = hud_x + hud_w - 10
        ypos = PLAYFIELD_Y + 10

        # Helper to render with wrapping/truncation
        def draw_line(text, color, font=None, indent=0):
            nonlocal ypos
            if font is None:
                font = self.font_small
            # Truncate if too long for panel
            surf = font.render(text, True, color)
            if surf.get_width() > (right_limit - xpos - indent):
                # Try smaller font or truncate
                max_chars = int((right_limit - xpos - indent) / 7)  # approx
                if max_chars > 3:
                    text = text[:max_chars-3] + "..."
                    surf = font.render(text, True, color)
            screen.blit(surf, (xpos + indent, ypos))
            ypos += surf.get_height() + 2
            return ypos

        def draw_divider():
            nonlocal ypos
            ypos += 4
            pygame.draw.line(screen, (50,50,70), (xpos, ypos), (right_limit, ypos), 1)
            ypos += 8

        # 1. Header - concise
        draw_line("TANK 93", COLOR_YELLOW, self.font_big)
        ypos += 2
        draw_line(f"STAGE {game.current_level+1}", (200,200,200), self.font_mid)
        draw_divider()

        # 2. Enemies - lives left concise
        remaining = game.enemies_total - game.enemies_killed
        draw_line(f"ENEMY LEFT: {remaining}/{game.enemies_total}", (220,220,200), self.font_mid)
        # Small icons grid - compact, max 10 rows
        icon_size = 10
        gap = 3
        cols = 4
        max_icons = min(remaining, 40)  # cap to avoid overflow
        start_y = ypos
        for i in range(max_icons):
            row = i // cols
            col = i % cols
            ix = xpos + col*(icon_size+gap+4)
            iy = ypos + row*(icon_size+gap)
            if iy + icon_size > PLAYFIELD_Y + hud_h - 100:  # avoid overflow
                break
            pygame.draw.rect(screen, (160,160,160), (ix, iy, icon_size, icon_size), border_radius=2)
        ypos = start_y + ((min(max_icons, 40)+cols-1)//cols)*(icon_size+gap) + 6
        if remaining > 40:
            draw_line(f"+{remaining-40} more", (150,150,150), self.font_small)
        draw_divider()

        # 3. Players - lives, score, damage, armor
        for idx, p in enumerate(game.players[:2]):  # max 2
            try:
                from ..settings import PLAYER_NAMES
                display_name = PLAYER_NAMES[idx] if idx < len(PLAYER_NAMES) else f"P{idx+1}"
            except:
                display_name = ["Chad", "Lida"][idx] if idx < 2 else f"P{idx+1}"
            color = PLAYER_COLORS[idx] if idx < len(PLAYER_COLORS) else COLOR_WHITE

            # Name + lives
            pygame.draw.rect(screen, color, (xpos, ypos, 16, 16), border_radius=3)
            draw_line(f" {display_name}  LIFE x{max(0, p.lives if p.alive else p.lives)}", COLOR_WHITE, self.font_mid, indent=20)
            # Score = points, damage approximated as score (each enemy 100-500)
            # Also show kills if we can compute from score? Use score as damage
            draw_line(f"Score: {p.score}  DMG: ~{p.score//10}", (200,200,200), self.font_small)
            # Power stars
            stars = '★'*p.star_level + '☆'*(3-p.star_level)
            draw_line(f"Power: {stars}", COLOR_YELLOW, self.font_small)
            # Armor bar - compact
            if hasattr(p, 'armor') and hasattr(p, 'max_armor') and p.max_armor>0:
                pct = max(0, p.armor/max(0.001,p.max_armor))
                bar_w = right_limit - xpos - 70
                bar_h = 8
                bx = xpos
                by = ypos
                pygame.draw.rect(screen, (40,40,50), (bx, by, bar_w, bar_h), border_radius=3)
                col = (80,200,100) if pct>0.5 else (220,200,80) if pct>0.25 else (220,80,80)
                pygame.draw.rect(screen, col, (bx, by, int(bar_w*pct), bar_h), border_radius=3)
                # text overlay
                armor_txt = self.font_small.render(f"{int(p.armor)}/{p.max_armor}", True, (220,220,220))
                screen.blit(armor_txt, (bx+bar_w+4, by-3))
                ypos += bar_h + 6

            # Active buffs - concise tags
            buffs = []
            if getattr(p, 'homing_active', False):
                buffs.append("MISSILE")
            if getattr(p, 'spread_active', False):
                buffs.append("8-WAY")
            if getattr(p, 'rapid_active', False):
                buffs.append("RAPID")
            if getattr(p, 'is_giant', False):
                buffs.append("GIANT")
            if getattr(p, 'is_shrunk', False):
                buffs.append("MINI")
            if getattr(p, 'helmet_timer', 0)>0:
                buffs.append("SHIELD")
            if buffs:
                tag_line = " ".join(buffs)
                draw_line(tag_line, (80,200,255), self.font_small)

            ypos += 4
            draw_divider()

        # 4. Items on map - what are they, what do they do
        # Powerup descriptions
        desc_map = {
            'star': '★ Star: Upgrade power+speed',
            'gun': 'Gun: Steel breaker (2 hits steel)',
            'helmet': 'Helmet: 10s shield',
            'clock': 'Clock: Freeze enemies 5s',
            'shovel': 'Shovel: Steel walls base 15s',
            'tank': 'Tank: +1 life + armor',
            'grenade': 'Bomb: 100 armor dmg all enemies',
            'homing': 'Missile: Tracking enemy',
            'spread': 'Spread: 8-direction shot',
            'rapid': 'Rapid: 3x fire rate',
            'shrink': 'Shrink: Half size 2x speed',
            'giant': 'Giant: Crush bricks/enemies',
        }
        # Current powerups on map
        try:
            powerups = getattr(game, 'powerups', [])
            if powerups:
                draw_line(f"ITEMS ON MAP ({len(powerups)}):", (180,220,255), self.font_mid)
                for pu in powerups[:6]:  # show max 6 to avoid overflow, top 6 nearest?
                    t = getattr(pu, 'type', 'unknown')
                    # short icon
                    icon = {
                        'star': '★', 'gun': 'G', 'helmet': 'H', 'clock': 'C', 'shovel': 'S',
                        'tank': 'T', 'grenade': 'B', 'homing': 'M', 'spread': '8', 'rapid': 'R',
                        'shrink': 'm', 'giant': 'G!'
                    }.get(t, '?')
                    short_desc = desc_map.get(t, f"{t}: powerup")
                    # truncate to fit
                    line = f"{icon} {short_desc}"
                    draw_line(line, (200,200,160), self.font_small)
                if len(powerups) > 6:
                    draw_line(f"+{len(powerups)-6} more", (150,150,150), self.font_small)
            else:
                draw_line("No items on map", (120,120,120), self.font_small)
        except:
            pass
        draw_divider()

        # 5. Coins - minimal
        draw_line(f"COINS: {game.coins} (C/5 = +10 lives)", COLOR_YELLOW, self.font_small)

        # 6. Network status - very minimal, no long URLs (was cut off)
        try:
            if hasattr(game, '_network_starting') and game._network_starting:
                draw_line("LAN: starting...", (100,200,255), self.font_small)
            elif hasattr(game, 'network_host') and game.network_host and game.network_host.is_client_connected():
                draw_line("Lida: CONNECTED (N kick)", (100,255,100), self.font_small)
            elif hasattr(game, 'network_host_ip') and game.network_host_ip and game.network_host_ip != "starting...":
                # Only show IP, not full command (was cut off)
                draw_line(f"LAN: {game.network_host_ip}:9999", (100,200,255), self.font_small)
                draw_line("P2: remote_client.py --host IP", (150,150,150), self.font_small)
        except:
            pass

        # 7. Boss if active
        try:
            if getattr(game, 'boss_released', False) and getattr(game, 'boss_enemy', None) and game.boss_enemy.alive:
                boss = game.boss_enemy
                hp_pct = getattr(boss, 'health', 0) / 18.0 if hasattr(boss, 'health') else 0
                draw_line(f"BOSS HP {getattr(boss, 'health', '?')}/18", (255,80,80), self.font_mid)
                bar_w = right_limit - xpos - 10
                bar_h = 8
                pygame.draw.rect(screen, (60,0,0), (xpos, ypos, bar_w, bar_h), border_radius=3)
                pygame.draw.rect(screen, (80,255,80) if hp_pct>0.5 else (255,220,80) if hp_pct>0.25 else (255,80,80), (xpos, ypos, int(bar_w*hp_pct), bar_h), border_radius=3)
                ypos += bar_h + 6
        except:
            pass

        # 8. Needs coin warning - compact
        try:
            need = [p for p in game.players if not p.alive and p.lives < 0]
            if need:
                draw_line("NEED COIN! C/5", COLOR_RED, self.font_mid)
        except:
            pass

        # 9. Top bar - score concise
        try:
            if game.players:
                p1 = game.players[0].score if len(game.players)>0 else 0
                p2 = game.players[1].score if len(game.players)>1 else 0
                from ..settings import PLAYER_NAMES
                n1 = PLAYER_NAMES[0] if len(PLAYER_NAMES)>0 else "Chad"
                n2 = PLAYER_NAMES[1] if len(PLAYER_NAMES)>1 else "Lida"
                top_text = f"{n1}:{p1} {n2}:{p2} HI:{game.high_score} C:{game.coins}"
            else:
                top_text = f"HI:{game.high_score} C:{game.coins}"
            top_surf = self.font_small.render(top_text, True, (180,180,200))
            screen.blit(top_surf, (PLAYFIELD_X, PLAYFIELD_Y-24))
        except:
            pass

    def draw_pause(self, screen, game=None):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,160))
        screen.blit(overlay, (0,0))
        # Title
        txt = self.font_huge.render("PAUSED", True, COLOR_YELLOW)
        screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 100)))
        # Subtitle robust instructions
        sub = self.font_mid.render("Press P / ESC / ENTER / SPACE / Joy A/B/Plus to resume", True, (200,200,220))
        screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 60)))
        
        # If game provided, show Chad/Lida stats
        y = SCREEN_HEIGHT//2 - 20
        if game and hasattr(game, 'players'):
            for idx, p in enumerate(game.players):
                try:
                    from ..settings import PLAYER_NAMES, get_player_display_name
                    dname = get_player_display_name(p.player_id) if hasattr(p, 'player_id') else PLAYER_NAMES[idx]
                except:
                    dname = ["Chad", "Lida"][idx] if idx < 2 else f"P{idx+1}"
                color = PLAYER_COLORS[idx] if idx < len(PLAYER_COLORS) else COLOR_WHITE
                info = f"{dname}: Lives x{p.lives} | Score {p.score} | Armor {int(getattr(p, 'armor', 0))} | Power {'★'*p.star_level}"
                surf = self.font_mid.render(info, True, color)
                screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, y)))
                y += 28
                # Show active items
                active = []
                if getattr(p, 'homing_active', False):
                    active.append("HOMING")
                if getattr(p, 'spread_active', False):
                    active.append("SPREAD")
                if getattr(p, 'rapid_active', False):
                    active.append("RAPIDx3")
                if getattr(p, 'is_giant', False):
                    active.append("GIANT")
                if getattr(p, 'is_shrunk', False):
                    active.append("MINI")
                if getattr(p, 'venom_timer', 0) > 0:
                    active.append(f"VENOM {p.venom_timer//FPS}s")
                if active:
                    act_surf = self.font_small.render(f"  Items: {', '.join(active)}", True, (180,220,255))
                    screen.blit(act_surf, act_surf.get_rect(center=(SCREEN_WIDTH//2, y)))
                    y += 20
                y += 8
        
        # Life sharing hint for 2P
        y += 10
        hint = self.font_mid.render("Chad & Lida - 2P Life Sharing: Press L to give life (if you have more)", True, (100,255,150))
        screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH//2, y)))
        y += 30
        hint2 = self.font_small.render(f"Stage {game.current_level+1 if game else '?'} | Enemies {game.enemies_total - game.enemies_killed if game else '?'} left | Coins {game.coins if game else '?'}", True, (150,150,180))
        screen.blit(hint2, hint2.get_rect(center=(SCREEN_WIDTH//2, y)))

    def draw_menu(self, screen, selected, mode='main'):
        try:
            from ..levels.battle_city import STAGE_COUNT as TOTAL_STAGES, BOTS_RAW as BOTS_RAW_ALL, LEVELS_13 as LVLS_13_PREVIEW
        except ImportError:
            try:
                from ..tilemap import ORIGINAL_STAGE_COUNT as TOTAL_STAGES
                from ..tilemap import BOTS_RAW_ORIGINAL as BOTS_RAW_ALL, LEVELS_13_ORIGINAL as LVLS_13_PREVIEW
            except ImportError:
                TOTAL_STAGES = 5
                BOTS_RAW_ALL = []
                LVLS_13_PREVIEW = []

        if mode == 'main':
            # Clean minimal landing page - no clutter
            screen.fill((14, 14, 20))
            t = pygame.time.get_ticks()

            # Subtle background haze
            bg = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for i in range(20):
                a = 10 + i
                pygame.draw.circle(bg, (60, 60, 90, a), (SCREEN_WIDTH//2 + int(200*math.sin(i*0.3 + t*0.0005)), 120 + i*30), 2)
            screen.blit(bg, (0,0))

            # Title
            big_font = pygame.font.Font(None, 96)
            title = big_font.render("TANK 93", True, COLOR_YELLOW)
            shadow = big_font.render("TANK 93", True, (0,0,0))
            screen.blit(shadow, shadow.get_rect(center=(SCREEN_WIDTH//2+3, 86)))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 84)))
            
            # Simple subtitle - minimal
            small = pygame.font.Font(None, 22)
            sub = small.render("Battle City Tribute  •  35 Stages", True, (160,160,180))
            screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, 118)))

            # Cards - minimal info, larger gap for breathing room
            card_w, card_h = 260, 150
            gap = 50
            total_w = card_w*2 + gap
            start_x = SCREEN_WIDTH//2 - total_w//2
            start_y = 150

            cards = [
                {"title": "CHAD", "color": PLAYER_COLORS[0]},  # was 1 PLAYER - now Chad
                {"title": "CHAD & LIDA", "color": PLAYER_COLORS[1]},  # was 2 PLAYERS - now Chad & Lida co-op
            ]

            for idx, card in enumerate(cards):
                x = start_x + idx*(card_w+gap)
                y = start_y
                is_selected = (selected == idx)
                bg_col = (44, 44, 64) if not is_selected else (68, 68, 96)
                border_col = COLOR_YELLOW if is_selected else (70, 70, 90)
                border_w = 3 if is_selected else 1
                rect = pygame.Rect(x, y, card_w, card_h)
                # soft shadow
                shadow_rect = rect.move(3,3)
                pygame.draw.rect(screen, (0,0,0, 60), shadow_rect, border_radius=14)
                pygame.draw.rect(screen, bg_col, rect, border_radius=14)
                pygame.draw.rect(screen, border_col, rect, border_w, border_radius=14)

                tank_cx = x + card_w//2
                tank_cy = y + 52
                if idx == 0:
                    # minimal single tank icon
                    pygame.draw.rect(screen, card["color"], (tank_cx-24, tank_cy-10, 48, 24), border_radius=5)
                    pygame.draw.rect(screen, (40,40,40), (tank_cx-30, tank_cy-10, 6, 24), border_radius=2)
                    pygame.draw.rect(screen, (40,40,40), (tank_cx+24, tank_cy-10, 6, 24), border_radius=2)
                    pygame.draw.rect(screen, (30,30,30), (tank_cx-2, tank_cy-24, 4, 18))
                    pygame.draw.circle(screen, (20,20,20), (tank_cx, tank_cy+2), 6)
                else:
                    pygame.draw.rect(screen, PLAYER_COLORS[0], (tank_cx-34, tank_cy-8, 28, 18), border_radius=4)
                    pygame.draw.rect(screen, PLAYER_COLORS[1], (tank_cx+6, tank_cy-8, 28, 18), border_radius=4)

                f_title = pygame.font.Font(None, 32)
                txt = f_title.render(card["title"], True, COLOR_WHITE if not is_selected else COLOR_YELLOW)
                screen.blit(txt, txt.get_rect(center=(tank_cx, y+100)))

                f_sub = pygame.font.Font(None, 18)
                sub_txt = f_sub.render("CO-OP" if idx==1 else f"{TOTAL_STAGES} STAGES", True, (140,140,160))
                screen.blit(sub_txt, sub_txt.get_rect(center=(tank_cx, y+122)))

                if is_selected:
                    # subtle glow + arrow
                    glow = pygame.Surface((card_w+12, card_h+12), pygame.SRCALPHA)
                    pygame.draw.rect(glow, (COLOR_YELLOW[0], COLOR_YELLOW[1], COLOR_YELLOW[2], 22), (0,0,card_w+12,card_h+12), border_radius=16)
                    screen.blit(glow, (x-6, y-6))
                    arrow = pygame.font.Font(None, 28).render("▶", True, COLOR_YELLOW)
                    screen.blit(arrow, (x-22, y+card_h//2-9))

            # Single clean hint, no overlap
            hint_y = start_y + card_h + 32
            if selected in (0,1):
                hint = pygame.font.Font(None, 22).render("PRESS ENTER TO START", True, (220, 200, 80))
                screen.blit(hint, hint.get_rect(center=(SCREEN_WIDTH//2, hint_y)))

            # Menu options - clean list, no boxes, good spacing
            options_main = ["LEVEL SELECT", "HOW TO PLAY", "QUIT"]
            sec_start_y = hint_y + 36
            for i, opt in enumerate(options_main):
                main_idx = i + 2
                is_sel = (selected == main_idx)
                color = COLOR_YELLOW if is_sel else (130,130,150)
                font = pygame.font.Font(None, 24) if is_sel else pygame.font.Font(None, 20)
                txt = font.render(opt, True, color)
                y = sec_start_y + i*30
                if is_sel:
                    # underline marker
                    pygame.draw.rect(screen, (60,60,80), (SCREEN_WIDTH//2-90, y-2, 180, 22), border_radius=6)
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
                    arr = pygame.font.Font(None, 18).render(">", True, COLOR_YELLOW)
                    screen.blit(arr, (SCREEN_WIDTH//2 - 78, y-4))
                else:
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))

            # Minimal footer - single line, no clutter
            footer_y = SCREEN_HEIGHT - 28
            footer_font = pygame.font.Font(None, 16)
            footer_txt = footer_font.render("LEFT/RIGHT: 1P/2P  •  UP/DOWN: Menu  •  ENTER  •  F11 Fullscreen  •  C Coin", True, (90,90,110))
            screen.blit(footer_txt, footer_txt.get_rect(center=(SCREEN_WIDTH//2, footer_y)))

            # Coin hint - subtle blinking at very bottom, no box
            if (t // 600) % 2 == 0:
                coin_font = pygame.font.Font(None, 16)
                coin_txt = coin_font.render("INSERT COIN C / 5  •  1 / 2 TO JOIN", True, (100, 100, 120))
                screen.blit(coin_txt, coin_txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-10)))
        elif mode == 'level':
            header_font = pygame.font.Font(None, 30)
            header = header_font.render(f"SELECT STAGE - {TOTAL_STAGES} ORIGINAL NES MAPS (Arrows:Move L/R:+5 PgUp/Dn:+10)", True, COLOR_WHITE)
            screen.blit(header, header.get_rect(center=(SCREEN_WIDTH//2, 315)))

            cols = 7
            cell_w, cell_h = 104, 38
            gap_x, gap_y = 10, 8
            grid_w = cols*cell_w + (cols-1)*gap_x
            start_x = SCREEN_WIDTH//2 - grid_w//2
            start_y = 340

            for idx in range(TOTAL_STAGES):
                c = idx % cols
                r = idx // cols
                x = start_x + c*(cell_w+gap_x)
                y = start_y + r*(cell_h+gap_y)
                is_sel = (selected == idx)
                bg_col = (60,60,90) if not is_sel else COLOR_YELLOW
                border_col = COLOR_WHITE if not is_sel else COLOR_BLACK
                pygame.draw.rect(screen, bg_col, (x, y, cell_w, cell_h), border_radius=6)
                pygame.draw.rect(screen, border_col, (x, y, cell_w, cell_h), 2, border_radius=6)
                txt_color = COLOR_BLACK if is_sel else COLOR_WHITE
                f = pygame.font.Font(None, 26) if is_sel else pygame.font.Font(None, 22)
                label = f"STAGE {idx+1}"
                txt_surf = f.render(label, True, txt_color)
                screen.blit(txt_surf, txt_surf.get_rect(center=(x+cell_w//2, y+cell_h//2 - 6)))
                if BOTS_RAW_ALL and idx < len(BOTS_RAW_ALL):
                    raw = BOTS_RAW_ALL[idx]
                    tiny = self.font_small.render(" ".join(raw), True, (200,200,100) if not is_sel else (40,40,20))
                    screen.blit(tiny, (x+6, y+cell_h-14))

            back_idx = TOTAL_STAGES
            is_back_sel = (selected == back_idx)
            back_y = start_y + 5*(cell_h+gap_y) + 12
            back_x = SCREEN_WIDTH//2 - cell_w//2
            pygame.draw.rect(screen, (90,40,40) if not is_back_sel else COLOR_YELLOW, (back_x, back_y, cell_w, cell_h), border_radius=6)
            pygame.draw.rect(screen, (200,100,100) if not is_back_sel else COLOR_BLACK, (back_x, back_y, cell_w, cell_h), 2, border_radius=6)
            back_col = COLOR_WHITE if not is_back_sel else COLOR_BLACK
            back_txt = pygame.font.Font(None, 24).render("BACK", True, back_col)
            screen.blit(back_txt, back_txt.get_rect(center=(back_x+cell_w//2, back_y+cell_h//2)))
            if is_back_sel:
                arrow = pygame.font.Font(None, 28).render(">", True, COLOR_YELLOW)
                screen.blit(arrow, (back_x-20, back_y+8))

            if selected < TOTAL_STAGES and LVLS_13_PREVIEW and selected < len(LVLS_13_PREVIEW):
                preview = LVLS_13_PREVIEW[selected]
                p_tile = 10
                p_w = 13 * p_tile
                p_h = 13 * p_tile
                p_x = SCREEN_WIDTH - p_w - 30
                p_y = start_y
                pygame.draw.rect(screen, (10,10,10), (p_x-4, p_y-4, p_w+8, p_h+8))
                pygame.draw.rect(screen, (100,100,120), (p_x-4, p_y-4, p_w+8, p_h+8), 2)
                for ry in range(13):
                    for rx in range(13):
                        t = preview[ry][rx]
                        tx = p_x + rx * p_tile
                        ty = p_y + ry * p_tile
                        if t == 0:
                            continue
                        elif t == 1:
                            pygame.draw.rect(screen, COLOR_BRICK, (tx, ty, p_tile, p_tile))
                        elif t == 2:
                            pygame.draw.rect(screen, COLOR_STEEL, (tx, ty, p_tile, p_tile))
                        elif t == 3:
                            pygame.draw.rect(screen, COLOR_WATER, (tx, ty, p_tile, p_tile))
                        elif t == 4:
                            pygame.draw.rect(screen, COLOR_GRASS, (tx, ty, p_tile, p_tile))
                        elif t == 5:
                            pygame.draw.rect(screen, COLOR_ICE, (tx, ty, p_tile, p_tile))
                if BOTS_RAW_ALL and selected < len(BOTS_RAW_ALL):
                    bot_text = "Enemies: " + " ".join(BOTS_RAW_ALL[selected])
                    bt = self.font_small.render(bot_text, True, (200,200,200))
                    screen.blit(bt, (p_x - 20, p_y + p_h + 8))
                    legend = self.font_small.render("B=Brick S=Steel ~=Water F=Forest I=Ice", True, (160,160,160))
                    screen.blit(legend, (p_x - 20, p_y + p_h + 26))

                sel_label = pygame.font.Font(None, 26).render(f"> SELECTED: STAGE {selected+1} <", True, COLOR_YELLOW)
                screen.blit(sel_label, sel_label.get_rect(center=(SCREEN_WIDTH//2, back_y + 40)))

        footer = pygame.font.Font(None, 18).render("35 Original NES Maps + Authentic NES SFX (feichao93 pack) - Bricks/Water/Forest/Steel/Ice + Tank Move Engine + Explosions + Powerups", True, (100,100,120))
        screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-30)))

        footer2 = pygame.font.Font(None, 16).render("Stage 1: 18*basic 2*fast ... Stage 35: 4*power 6*fast 10*armor (700 enemies total) - Authentic Battle City 1985", True, (80,80,100))
        screen.blit(footer2, footer2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-14)))

        if mode == 'howto':
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT-100), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            screen.blit(overlay, (0,100))
            lines = [
                "HOW TO PLAY - TANK 93 - 35 ORIGINAL NES MAPS",
                "",
                "Goal: Protect your base (Eagle) and destroy all enemy tanks.",
                "Movement: P1 WASD / P2 Arrows / Gamepad Stick / Joy-Con",
                "Shoot: SPACE / ENTER / Gamepad A / Joy-Con Any - Tank always faces aim",
                "",
                "Tiles: Brick=breakable, Steel=needs power gun, Water=blocked",
                "Forest=hides tank, Ice=slippery",
                "Powerups (Original + New):",
                " Star=upgrade tank (3 levels) gun+speed - kept across stages",
                " Helmet=10s shield, Clock=freeze enemies 5s (now attackable while frozen)",
                " Shovel=steel walls around base 15s",
                " Tank=+1 life, Grenade=kill all enemies",
                " Gun=steel-breaking bullets",
                " Homing Missile (orange missile icon)=tracking nearest enemy - PERM until death",
                " Spread Shot (purple 8 arrows)=8 directions at once - PERM until death",
                " Rapid Fire (pink 3 bullets)=attack speed x3 - PERM until death",
                " Shrink (light blue small tank)=half size 2x speed 15s",
                " Giant (red giant crushing brick)=double size crush bricks+enemies 15s",
                " Venom Boss: shoots green goo that dissolves tank in 10s",
                " Bullet Counter: shoot enemy bullets to counter them!",
                "      Combo: M+8+R = 8 homing missiles at 3x speed!",
                "",
                "ARCADE COIN SYSTEM:",
                " Each coin = 10 lives, Press C or 5 to Insert Coin",
                " Press 1 = P1 Join, Press 2 = P2 Join (late join OK)",
                " Joy-Con: Minus (-) = Coin, Plus (+) = Start/Join",
                " LAN: Host shows IP, remote P2 runs remote_client.py --host <ip> (same WiFi)",
                " PROJECTOR: Open http://<host_ip>:8080 on projector browser / laptop HDMI -> F11",
                "   - Game streams live 10 FPS, works for any smart projector with browser",
                "   - Or use Mac AirPlay: Screen Mirroring to Apple TV + Projector",
                "   - For network projector (Epson/BenQ): open browser on projector if supported",
                " FULLSCREEN: Press F11 / F10 or Alt+Enter to toggle fullscreen, ESC exits fullscreen",
                "   - For projector: Set Mac to mirror display, F11 fullscreen, or use browser F11",
                " After Game Over, 15 sec to insert coin and continue same stage",
                " Base repaired on continue, score kept",
                "",
                "Press ESC to go back",
            ]
            y = 120
            for line in lines:
                f = pygame.font.Font(None, 20)
                c = COLOR_YELLOW if "HOW TO" in line else (200,200,200)
                txt = f.render(line, True, c)
                screen.blit(txt, (SCREEN_WIDTH//2 - 280, y))
                y += 19

    def draw_game_over(self, screen, won, score, game=None):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,180))
        screen.blit(overlay, (0,0))
        font_big = pygame.font.Font(None, 64)
        text = "STAGE CLEAR!" if won else "GAME OVER"
        col = (100,255,100) if won else (255,80,80)
        surf = font_big.render(text, True, col)
        screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 120)))
        sc = pygame.font.Font(None, 32).render(f"Score: {score}", True, COLOR_WHITE)
        screen.blit(sc, sc.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 70)))

        if won:
            cont = pygame.font.Font(None, 24).render("Press ENTER to continue, ESC for menu", True, (180,180,200))
            screen.blit(cont, cont.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 60)))
        else:
            if game:
                secs = max(0, game.continue_timer // FPS)
                flash = (pygame.time.get_ticks() // 300) % 2 == 0
                if flash:
                    coin_big = pygame.font.Font(None, 48).render("INSERT COIN! CONTINUE?", True, COLOR_YELLOW)
                    screen.blit(coin_big, coin_big.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20)))

                details = [
                    f"Coins Inserted: {game.coins}  (Each coin = {COIN_LIVES} lives)",
                    f"Continue Timer: {secs}s",
                    "",
                    "CONTROLS:",
                    "  Press C or 5 = Insert Coin (+10 Lives)",
                    "  Press 1 = Chad Join / Continue  |  Press 2 = Lida Join",
                    "  Joy-Con: Minus (-) = Coin  |  Plus (+) = Start/Join",
                    "",
                    "Current Status:",
                ]
                y = SCREEN_HEIGHT//2 + 10
                for line in details:
                    f = pygame.font.Font(None, 22)
                    col = (200,200,100) if "CONTROLS" in line else (180,180,200)
                    txt = f.render(line, True, col)
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
                    y += 20

                y += 5
                for p in game.players:
                    try:
                        from ..settings import get_player_display_name
                        dname = get_player_display_name(p.player_id)
                    except:
                        dname = ["Chad", "Lida"][p.player_id-1] if 1 <= p.player_id <= 2 else f"P{p.player_id}"
                    if p.lives < 0 and not p.alive:
                        status = f"{dname} DEAD - Press C/5 for {COIN_LIVES} Lives or {p.player_id} to Join"
                        c = COLOR_RED
                    else:
                        status = f"{dname} Lives: {p.lives}"
                        c = COLOR_WHITE
                    txt = pygame.font.Font(None, 22).render(status, True, c)
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
                    y += 20
                if len(game.players) < 2:
                    txt = pygame.font.Font(None, 22).render("Lida (P2) not playing - Press 2 to Join (+10 Lives)", True, (100,200,100))
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
                    y += 20

                bar_w = 200
                bar_h = 12
                bx = SCREEN_WIDTH//2 - bar_w//2
                by = y + 10
                pygame.draw.rect(screen, (60,60,60), (bx, by, bar_w, bar_h))
                if game.continue_timer > 0:
                    fill_w = int(bar_w * (game.continue_timer / CONTINUE_TIME))
                    pygame.draw.rect(screen, COLOR_YELLOW, (bx, by, fill_w, bar_h))

            cont2 = pygame.font.Font(None, 20).render("ESC = Menu  |  Timer 0 = Return to Menu", True, (120,120,140))
            screen.blit(cont2, cont2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-40)))
