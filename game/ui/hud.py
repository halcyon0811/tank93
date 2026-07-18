import pygame
from ..settings import *

class HUD:
    def __init__(self):
        self.font_small = pygame.font.Font(None, 22)
        self.font_mid = pygame.font.Font(None, 26)
        self.font_big = pygame.font.Font(None, 32)
        self.font_huge = pygame.font.Font(None, 48)

    def draw(self, screen, game):
        panel_rect = pygame.Rect(HUD_X, PLAYFIELD_Y, HUD_W, PLAYFIELD_H)
        pygame.draw.rect(screen, (28, 28, 38), panel_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), panel_rect, 2, border_radius=8)

        ypos = PLAYFIELD_Y + 15
        xpos = HUD_X + 12

        title = self.font_big.render("TANK 93", True, COLOR_YELLOW)
        screen.blit(title, (xpos, ypos))
        ypos += 26

        joy_count = len(game.joysticks) if hasattr(game, 'joysticks') else 0
        if joy_count > 0:
            joy_names = []
            for js in game.joysticks:
                try:
                    n = js.get_name()
                    if 'joy-con' in n.lower():
                        if '(l)' in n.lower():
                            joy_names.append("JC(L)")
                        elif '(r)' in n.lower():
                            joy_names.append("JC(R)")
                        else:
                            joy_names.append("JC")
                    elif 'pro' in n.lower():
                        joy_names.append("Pro")
                    else:
                        joy_names.append(n[:8])
                except:
                    joy_names.append("?")
            joy_txt = self.font_small.render(f"Joy: {joy_count} {','.join(joy_names)}", True, (100,255,100))
        else:
            joy_txt = self.font_small.render("Joy: 0 (Press J to rescan)", True, (200,100,100))
        screen.blit(joy_txt, (xpos, ypos))
        ypos += 14
        # LAN Multiplayer status
        try:
            if hasattr(game, 'network_host_ip') and game.network_host_ip:
                ip_txt = self.font_small.render(f"LAN Host: {game.network_host_ip}:9999", True, (100,200,255))
                screen.blit(ip_txt, (xpos, ypos))
                ypos += 14
                if hasattr(game, 'network_host') and game.network_host and game.network_host.is_client_connected():
                    conn_txt = self.font_small.render("Remote P2: CONNECTED via WiFi", True, (100,255,100))
                else:
                    conn_txt = self.font_small.render("Remote P2: python3 remote_client.py --host "+str(game.network_host_ip), True, (150,150,150))
                screen.blit(conn_txt, (xpos, ypos))
                ypos += 14
            # Projector status - for projecting to projector via local network browser
            if hasattr(game, 'projector_ip') and game.projector_ip:
                proj_txt = self.font_small.render(f"PROJECTOR: http://{game.projector_ip}:8080", True, (255,200,100))
                screen.blit(proj_txt, (xpos, ypos))
                ypos += 14
                proj_hint = self.font_small.render("Open on projector browser / laptop HDMI -> F11", True, (180,180,120))
                screen.blit(proj_hint, (xpos, ypos))
                ypos += 14
        except:
            pass
        ypos += 4
        # Calibration status
        try:
            import game.settings as settings_mod
            cal_lines = []
            l_swap = getattr(settings_mod, 'JOYCON_L_SWAP', False)
            l_invx = getattr(settings_mod, 'JOYCON_L_INVERT_X', False)
            l_invy = getattr(settings_mod, 'JOYCON_L_INVERT_Y', False)
            r_swap = getattr(settings_mod, 'JOYCON_R_SWAP', False)
            r_invx = getattr(settings_mod, 'JOYCON_R_INVERT_X', False)
            r_invy = getattr(settings_mod, 'JOYCON_R_INVERT_Y', False)
            cal_lines.append(f"L:{'S' if l_swap else ''}{'X' if l_invx else ''}{'Y' if l_invy else '' or 'OK'}")
            cal_lines.append(f"R:{'S' if r_swap else ''}{'X' if r_invx else ''}{'Y' if r_invy else '' or 'OK'}")
            cal_txt = self.font_small.render("Cal " + " ".join(cal_lines) + " I:InvY U:InvX O:Swap", True, (255,200,100))
            screen.blit(cal_txt, (xpos, ypos))
            ypos += 14
        except:
            pass
        ypos += 4

        lvl_txt = self.font_mid.render(f"STAGE {game.current_level+1}", True, COLOR_WHITE)
        screen.blit(lvl_txt, (xpos, ypos))
        ypos += 28

        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 2)
        ypos += 12

        remaining = game.enemies_total - game.enemies_killed
        en_txt = self.font_mid.render(f"ENEMY {remaining}", True, (200,200,200))
        screen.blit(en_txt, (xpos, ypos))
        ypos += 22
        # Gradual increase info (from origin 7304b5b)
        try:
            max_on = getattr(game, 'max_enemies_on_field', 4)
            total = getattr(game, 'enemies_total', 20)
            ramp_txt = self.font_small.render(f"TOTAL {total} (BASE 20+LVL) MAX {max_on}", True, (180,220,180))
            screen.blit(ramp_txt, (xpos, ypos))
            ypos += 16
            spawn_int = getattr(game, 'dynamic_spawn_interval', 0) / FPS if hasattr(game, 'dynamic_spawn_interval') else 2.5
            interval_txt = self.font_small.render(f"SPAWN {spawn_int:.1f}s RAMP {game.difficulty_ramp_timer//FPS if hasattr(game, 'difficulty_ramp_timer') else 0}s", True, (150,180,200))
            screen.blit(interval_txt, (xpos, ypos))
            ypos += 16
        except:
            pass
        icon_size = 16
        gap = 4
        cols = 2
        for i in range(remaining):
            row = i // cols
            col = i % cols
            ix = xpos + col*(icon_size+gap+8)
            iy = ypos + row*(icon_size+gap)
            pygame.draw.rect(screen, (180,180,180), (ix, iy, icon_size, icon_size//2 +4), border_radius=2)
            pygame.draw.rect(screen, (120,120,120), (ix+icon_size//2-1, iy-3, 2, 6))
        ypos += ((remaining+1)//cols)*(icon_size+gap) + 12
        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
        ypos += 12

        for idx, p in enumerate(game.players):
            if idx >= 2:
                break
            color = PLAYER_COLORS[idx]
            pygame.draw.rect(screen, color, (xpos, ypos, 22, 22), border_radius=4)
            p_num = self.font_small.render(f"P{idx+1}", True, COLOR_BLACK)
            screen.blit(p_num, (xpos+2, ypos+3))
            lives_txt = self.font_mid.render(f"x {p.lives if p.alive else max(0,p.lives)}", True, COLOR_WHITE)
            screen.blit(lives_txt, (xpos+28, ypos))

            ypos += 22
            score_txt = self.font_small.render(f"Score {p.score}", True, (200,200,200))
            screen.blit(score_txt, (xpos, ypos))
            ypos += 18

            star_txt = self.font_small.render(f"Power {'★'*p.star_level}{'☆'*(3-p.star_level)}", True, COLOR_YELLOW)
            screen.blit(star_txt, (xpos, ypos))
            ypos += 16

            statuses = []
            if p.helmet_timer > 0:
                statuses.append("SHIELD")
            if p.spawn_protection > 0:
                statuses.append("SPAWN")
            homing_t = getattr(p, 'homing_timer', 0)
            if getattr(p, 'homing_active', False) or homing_t != 0:
                if homing_t == -1:
                    statuses.append(f"MISSILE PERM")
                elif homing_t > 0:
                    secs = homing_t // FPS
                    statuses.append(f"MISSILE {secs}s")
                elif getattr(p, 'homing_active', False):
                    statuses.append(f"MISSILE")
            spread_t = getattr(p, 'spread_timer', 0)
            if getattr(p, 'spread_active', False) or spread_t != 0:
                if spread_t == -1:
                    statuses.append(f"8-WAY PERM")
                elif spread_t > 0:
                    secs = spread_t // FPS
                    statuses.append(f"8-WAY {secs}s")
                elif getattr(p, 'spread_active', False):
                    statuses.append(f"8-WAY")
            rapid_t = getattr(p, 'rapid_timer', 0)
            if getattr(p, 'rapid_active', False) or rapid_t != 0:
                if rapid_t == -1:
                    statuses.append(f"RAPID x3 PERM")
                elif rapid_t > 0:
                    secs = rapid_t // FPS
                    statuses.append(f"RAPID x3 {secs}s")
                elif getattr(p, 'rapid_active', False):
                    statuses.append(f"RAPID x3")
            if getattr(p, 'shrink_timer', 0) > 0:
                secs = p.shrink_timer // FPS
                statuses.append(f"MINI 2xSPD {secs}s")
            if getattr(p, 'giant_timer', 0) > 0:
                secs = p.giant_timer // FPS
                statuses.append(f"GIANT CRUSH {secs}s")
            if getattr(p, 'venom_timer', 0) > 0:
                secs = p.venom_timer // FPS
                lv = int(getattr(p, 'venom_level', 0)*100)
                statuses.append(f"VENOM {lv}% {secs}s")

            if statuses:
                for st in statuses:
                    if "MISSILE" in st:
                        col = (255,140,0)
                    elif "8-WAY" in st:
                        col = (160,80,255)
                    elif "RAPID" in st:
                        col = (255,50,150)
                    elif "MINI" in st:
                        col = (80,220,255)
                    elif "GIANT" in st:
                        col = (255,80,80)
                    elif "VENOM" in st:
                        col = (80,220,80)
                    else:
                        col = (80,200,255)
                    stat = self.font_small.render(st, True, col)
                    screen.blit(stat, (xpos, ypos))
                    ypos += 16
            ypos += 12

            pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
            ypos += 12

        coin_txt = self.font_mid.render(f"COINS: {game.coins}", True, COLOR_YELLOW)
        screen.blit(coin_txt, (xpos, ypos))
        ypos += 18
        coin_hint = self.font_small.render(f"Each coin = {COIN_LIVES} lives", True, (200,200,100))
        screen.blit(coin_hint, (xpos, ypos))
        ypos += 18
        for p in game.players:
            if not p.alive and p.lives < 0:
                need_txt = self.font_small.render(f"P{p.player_id} NEED COIN! Press C/5", True, COLOR_RED)
                screen.blit(need_txt, (xpos, ypos))
                ypos += 16

        ypos += 6
        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
        ypos += 10

        hints = [
            "P1: WASD+SPACE",
            "P2: ARROWS+ENTER",
            "C/5: Coin 1/2: Join",
            "P: Pause ESC: Menu",
            "F11: Full | Cmd+F Mac",
            "Fn+F11 Mac | F10 Win",
            "Joy: -:Coin +=Start",
            "J:Rescan I:InvY U:InvX",
        ]
        for h in hints:
            txt = self.font_small.render(h, True, (140,140,160))
            screen.blit(txt, (xpos, ypos))
            ypos += 16

        if game.tilemap and game.tilemap.shovel_timer > 0:
            secs = game.tilemap.shovel_timer // FPS
            sh_txt = self.font_mid.render(f"BASE STEEL {secs}s", True, (255,220,80))
            screen.blit(sh_txt, (xpos, PLAYFIELD_Y+PLAYFIELD_H-70))

        if game.freeze_timer > 0:
            secs = game.freeze_timer // FPS
            f_txt = self.font_mid.render(f"FREEZE {secs}s", True, (150,200,255))
            screen.blit(f_txt, (xpos, PLAYFIELD_Y+PLAYFIELD_H-50))

        if getattr(game, 'boss_released', False) and getattr(game, 'boss_enemy', None) and game.boss_enemy.alive:
            boss = game.boss_enemy
            b_txt = self.font_mid.render(f"BOSS HP {boss.health}/18", True, (255,50,50))
            screen.blit(b_txt, (xpos, PLAYFIELD_Y+PLAYFIELD_H-90))
            bar_w = 80
            bar_h = 10
            bx = xpos
            by = PLAYFIELD_Y+PLAYFIELD_H-70
            pygame.draw.rect(screen, (0,0,0), (bx-1, by-1, bar_w+2, bar_h+2))
            pygame.draw.rect(screen, (60,0,0), (bx, by, bar_w, bar_h))
            frac = boss.health / 18.0
            pygame.draw.rect(screen, (0,255,0) if frac>0.5 else (255,255,0) if frac>0.25 else (255,0,0), (bx, by, int(bar_w*frac), bar_h))

        if any(not p.alive and p.lives < 0 for p in game.players):
            urgent = self.font_mid.render("INSERT COIN!", True, COLOR_RED)
            screen.blit(urgent, (xpos, PLAYFIELD_Y+PLAYFIELD_H-30))

        if game.players:
            p1_score = game.players[0].score if len(game.players)>0 else 0
            p2_score = game.players[1].score if len(game.players)>1 else 0
            top_text = f"SCORE P1:{p1_score} P2:{p2_score} HI:{game.high_score} COINS:{game.coins}"
        else:
            top_text = f"HI:{game.high_score} COINS:{game.coins}"
        top_surf = self.font_small.render(top_text, True, (180,180,200))
        screen.blit(top_surf, (PLAYFIELD_X, PLAYFIELD_Y-28))

    def draw_pause(self, screen):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0,0,0,120))
        screen.blit(overlay, (0,0))
        txt = self.font_huge.render("PAUSED", True, COLOR_WHITE)
        screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 20)))
        sub = self.font_mid.render("Press P to resume", True, (180,180,200))
        screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + 30)))

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
            screen.fill(COLOR_BG)
            pygame.draw.rect(screen, (40,40,60), (0,0,SCREEN_WIDTH, SCREEN_HEIGHT), 4)
            inner_rect = pygame.Rect(20, 20, SCREEN_WIDTH-40, 120)
            pygame.draw.rect(screen, (0,0,0), inner_rect, border_radius=8)
            pygame.draw.rect(screen, (70,70,90), inner_rect, 2, border_radius=8)

            t = pygame.time.get_ticks()
            for i in range(6):
                x = (t//20 + i*160) % (SCREEN_WIDTH+100) - 50
                y = 24 + (i%2)*80
                pygame.draw.rect(screen, (30,30,40), (x, y, 18, 12), border_radius=2)

            big_font = pygame.font.Font(None, 84)
            title = big_font.render("TANK 93", True, COLOR_YELLOW)
            shadow = big_font.render("TANK 93", True, (0,0,0))
            screen.blit(shadow, shadow.get_rect(center=(SCREEN_WIDTH//2+4, 84)))
            screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 80)))
            small = pygame.font.Font(None, 24)
            sub = small.render(f"ENHANCED EDITION - {TOTAL_STAGES} ORIGINAL NES MAPS - AUTHENTIC TRIBUTE", True, (200,200,220))
            screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, 114)))
            sub2 = self.font_small.render("NEW: HOMING MISSILE + 8-WAY + RAPID + MINI + GIANT + VENOM BOSS + LAN P2", True, (255,140,0))
            screen.blit(sub2, sub2.get_rect(center=(SCREEN_WIDTH//2, 134)))

            card_w, card_h = 280, 180
            gap = 40
            total_w = card_w*2 + gap
            start_x = SCREEN_WIDTH//2 - total_w//2
            start_y = 160

            cards = [
                {"title": "1 PLAYER", "sub": f"{TOTAL_STAGES} STAGES", "detail": "ORIGINAL NES MAPS", "color": PLAYER_COLORS[0], "icon": "P1", "enemies": "20 TANKS/STAGE", "maps": "700 ENEMIES TOTAL"},
                {"title": "2 PLAYERS", "sub": f"{TOTAL_STAGES} STAGES CO-OP", "detail": "ORIGINAL NES MAPS", "color": PLAYER_COLORS[1], "icon": "P1+P2", "enemies": "20 TANKS/STAGE", "maps": "2P CO-OP - FRIENDLY FIRE OFF"},
            ]

            for idx, card in enumerate(cards):
                x = start_x + idx*(card_w+gap)
                y = start_y
                is_selected = (selected == idx)
                bg_col = (60,60,90) if not is_selected else (80,80,120)
                border_col = COLOR_YELLOW if is_selected else (100,100,130)
                border_w = 4 if is_selected else 2
                pulse = 0
                if is_selected:
                    pulse = int(3 * abs((t % 1000) / 1000 - 0.5))
                rect = pygame.Rect(x, y, card_w, card_h)
                pygame.draw.rect(screen, bg_col, rect, border_radius=12)
                pygame.draw.rect(screen, border_col, rect.inflate(pulse*2, pulse*2), border_w, border_radius=12)

                tank_cx = x + card_w//2
                tank_cy = y + 50
                if idx == 0:
                    pygame.draw.rect(screen, card["color"], (tank_cx-30, tank_cy-12, 60, 32), border_radius=6)
                    pygame.draw.rect(screen, (40,40,40), (tank_cx-36, tank_cy-12, 8, 32), border_radius=2)
                    pygame.draw.rect(screen, (40,40,40), (tank_cx+28, tank_cy-12, 8, 32), border_radius=2)
                    pygame.draw.rect(screen, (30,30,30), (tank_cx-3, tank_cy-28, 6, 22))
                    pygame.draw.circle(screen, (20,20,20), (tank_cx, tank_cy+4), 8)
                else:
                    pygame.draw.rect(screen, PLAYER_COLORS[0], (tank_cx-50, tank_cy-10, 40, 24), border_radius=4)
                    pygame.draw.rect(screen, (30,30,30), (tank_cx-35, tank_cy-20, 4, 14))
                    pygame.draw.rect(screen, PLAYER_COLORS[1], (tank_cx+10, tank_cy-10, 40, 24), border_radius=4)
                    pygame.draw.rect(screen, (30,30,30), (tank_cx+25, tank_cy-20, 4, 14))

                f_title = pygame.font.Font(None, 36)
                txt = f_title.render(card["title"], True, COLOR_YELLOW if is_selected else COLOR_WHITE)
                screen.blit(txt, txt.get_rect(center=(tank_cx, y+90)))

                f_sub = pygame.font.Font(None, 22)
                sub_txt = f_sub.render(card["sub"], True, (200,200,200))
                screen.blit(sub_txt, sub_txt.get_rect(center=(tank_cx, y+112)))

                f_det = self.font_small
                det = f_det.render(card["detail"], True, (160,220,160))
                screen.blit(det, det.get_rect(center=(tank_cx, y+130)))

                en = f_det.render(card["enemies"], True, (180,180,180))
                screen.blit(en, en.get_rect(center=(tank_cx, y+148)))

                mp = f_det.render(card["maps"], True, (200,180,100))
                screen.blit(mp, mp.get_rect(center=(tank_cx, y+164)))

                if is_selected:
                    arrow = pygame.font.Font(None, 32).render("▶", True, COLOR_YELLOW)
                    screen.blit(arrow, (x-28, y+card_h//2-10))

            if selected in (0,1):
                card_hint = self.font_small.render("PRESS ENTER / A / START TO BEGIN", True, COLOR_YELLOW)
                screen.blit(card_hint, card_hint.get_rect(center=(SCREEN_WIDTH//2, start_y + card_h + 18)))

            if LVLS_13_PREVIEW and len(LVLS_13_PREVIEW) > 0:
                preview = LVLS_13_PREVIEW[0]
                p_tile = 6
                p_w = 13 * p_tile
                p_h = 13 * p_tile
                p_x = SCREEN_WIDTH - p_w - 20
                p_y = 160
                pygame.draw.rect(screen, (0,0,0), (p_x-4, p_y-16, p_w+8, p_h+20), border_radius=4)
                pygame.draw.rect(screen, (70,70,90), (p_x-4, p_y-16, p_w+8, p_h+20), 1, border_radius=4)
                lab = self.font_small.render("MAP 1 PREVIEW", True, (180,180,100))
                screen.blit(lab, (p_x, p_y-14))
                for ry in range(13):
                    for rx in range(13):
                        tt = preview[ry][rx]
                        if tt == 0:
                            continue
                        tx = p_x + rx * p_tile
                        ty = p_y + ry * p_tile
                        col = COLOR_BRICK if tt==1 else COLOR_STEEL if tt==2 else COLOR_WATER if tt==3 else COLOR_GRASS if tt==4 else COLOR_ICE
                        pygame.draw.rect(screen, col, (tx, ty, p_tile, p_tile))

            options_main = [
                "LEVEL SELECT - 35 ORIGINAL NES MAPS",
                "HOW TO PLAY",
                "QUIT",
            ]
            sec_start_y = start_y + card_h + 42
            for i, opt in enumerate(options_main):
                main_idx = i + 2
                is_sel = (selected == main_idx)
                color = COLOR_YELLOW if is_sel else (170,170,180)
                font = pygame.font.Font(None, 26) if is_sel else pygame.font.Font(None, 20)
                txt = font.render(opt, True, color)
                y = sec_start_y + i*26
                if i == 0:
                    box_rect = pygame.Rect(SCREEN_WIDTH//2-190, y-3, 380, 22)
                    box_col = (50,50,80) if not is_sel else (70,70,100)
                    pygame.draw.rect(screen, box_col, box_rect, border_radius=6)
                    pygame.draw.rect(screen, color, box_rect, 2 if is_sel else 1, border_radius=6)
                if is_sel:
                    arrow = pygame.font.Font(None, 20).render(">", True, COLOR_YELLOW)
                    screen.blit(arrow, (SCREEN_WIDTH//2 - 210, y-1))
                screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))

            footer_y = SCREEN_HEIGHT - 88
            banner_rect = pygame.Rect(20, footer_y-8, SCREEN_WIDTH-40, 78)
            pygame.draw.rect(screen, (0,0,0), banner_rect, border_radius=6)
            pygame.draw.rect(screen, (50,50,70), banner_rect, 1, border_radius=6)
            try:
                from ..network import get_local_ip
                local_ip = get_local_ip()
            except:
                local_ip = "127.0.0.1"
            footer_lines = [
                f"{TOTAL_STAGES} ORIGINAL NES MAPS - 700 ENEMIES - AUTHENTIC TILES | P1 WASD+SPACE P2 ARROWS+ENTER",
                f"LAN: {local_ip}:9999 | P2 REMOTE: python3 remote_client.py --host {local_ip}",
                f"PROJECTOR: http://{local_ip}:8080 on same WiFi - open on projector/browser -> F11 fullscreen",
                f"NEW: HOMING + 8-WAY + RAPID + BOSS + FREEZE FIX + GRADUAL ENEMIES",
            ]
            for j, line in enumerate(footer_lines):
                f = pygame.font.Font(None, 14)
                if j == 0:
                    c = (200,200,100)
                elif j == 1:
                    c = (100,200,255)
                elif j == 2:
                    c = (255,200,100)
                else:
                    c = (255,140,0)
                txt = f.render(line, True, c)
                screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, footer_y + 2 + j*15)))

            if (t // 500) % 2 == 0:
                coin_txt = pygame.font.Font(None, 18).render("INSERT COIN C/5 FOR 10 LIVES - PRESS ENTER TO START", True, (255,220,80))
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
                    "  Press 1 = P1 Join / Continue  |  Press 2 = P2 Join",
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
                    if p.lives < 0 and not p.alive:
                        status = f"P{p.player_id} DEAD - Press C/5 for {COIN_LIVES} Lives or {p.player_id} to Join"
                        c = COLOR_RED
                    else:
                        status = f"P{p.player_id} Lives: {p.lives}"
                        c = COLOR_WHITE
                    txt = pygame.font.Font(None, 22).render(status, True, c)
                    screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
                    y += 20
                if len(game.players) < 2:
                    txt = pygame.font.Font(None, 22).render("P2 not playing - Press 2 to Join (+10 Lives)", True, (100,200,100))
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
