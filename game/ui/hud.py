import pygame
from ..settings import *

class HUD:
    def __init__(self):
        self.font_small = pygame.font.Font(None, 22)
        self.font_mid = pygame.font.Font(None, 26)
        self.font_big = pygame.font.Font(None, 32)
        self.font_huge = pygame.font.Font(None, 48)

    def draw(self, screen, game):
        # sidebar panel
        panel_rect = pygame.Rect(HUD_X, PLAYFIELD_Y, HUD_W, PLAYFIELD_H)
        pygame.draw.rect(screen, (28, 28, 38), panel_rect, border_radius=8)
        pygame.draw.rect(screen, (60, 60, 80), panel_rect, 2, border_radius=8)

        y = HUD_X + 10  # actually using y as vertical pos, rename
        # Let's use ypos
        ypos = PLAYFIELD_Y + 15
        xpos = HUD_X + 12

        # Title
        title = self.font_big.render("TANK 90", True, COLOR_YELLOW)
        screen.blit(title, (xpos, ypos))
        ypos += 26

        # Joystick status (so user knows Joy-Con connected)
        joy_count = len(game.joysticks) if hasattr(game, 'joysticks') else 0
        if joy_count > 0:
            joy_names = []
            for js in game.joysticks:
                try:
                    n = js.get_name()
                    if 'joy-con' in n.lower():
                        # shorten
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
        # Calibration status for Joy-Con fix - per side
        try:
            import game.settings as settings_mod
            cal_lines = []
            # Show per-side for debugging right issue
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

        # Level
        lvl_txt = self.font_mid.render(f"STAGE {game.current_level+1}", True, COLOR_WHITE)
        screen.blit(lvl_txt, (xpos, ypos))
        ypos += 28

        # Divider
        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 2)
        ypos += 12

        # Enemies remaining
        remaining = game.enemies_total - game.enemies_killed
        en_txt = self.font_mid.render(f"ENEMY {remaining}", True, (200,200,200))
        screen.blit(en_txt, (xpos, ypos))
        ypos += 22
        # icons grid 2 cols
        icon_size = 16
        gap = 4
        # draw enemy icons
        cols = 2
        for i in range(remaining):
            row = i // cols
            col = i % cols
            ix = xpos + col*(icon_size+gap+8)
            iy = ypos + row*(icon_size+gap)
            pygame.draw.rect(screen, (180,180,180), (ix, iy, icon_size, icon_size//2 +4), border_radius=2)
            # mini turret
            pygame.draw.rect(screen, (120,120,120), (ix+icon_size//2-1, iy-3, 2, 6))
        ypos += ((remaining+1)//cols)*(icon_size+gap) + 12
        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
        ypos += 12

        # Players info
        for idx, p in enumerate(game.players):
            if idx >= 2:
                break
            color = PLAYER_COLORS[idx]
            # P indicator box
            pygame.draw.rect(screen, color, (xpos, ypos, 22, 22), border_radius=4)
            p_num = self.font_small.render(f"P{idx+1}", True, COLOR_BLACK)
            screen.blit(p_num, (xpos+2, ypos+3))
            # lives
            lives_txt = self.font_mid.render(f"x {p.lives if p.alive else max(0,p.lives)}", True, COLOR_WHITE)
            screen.blit(lives_txt, (xpos+28, ypos))

            # score
            ypos += 22
            score_txt = self.font_small.render(f"Score {p.score}", True, (200,200,200))
            screen.blit(score_txt, (xpos, ypos))
            ypos += 18

            # star level
            star_txt = self.font_small.render(f"Power {'★'*p.star_level}{'☆'*(3-p.star_level)}", True, COLOR_YELLOW)
            screen.blit(star_txt, (xpos, ypos))
            ypos += 16

            # status
            statuses = []
            if p.helmet_timer > 0:
                statuses.append("SHIELD")
            if p.spawn_protection > 0:
                statuses.append("SPAWN")
            if statuses:
                stat = self.font_small.render(",".join(statuses), True, (80,200,255))
                screen.blit(stat, (xpos, ypos))
                ypos += 16
            ypos += 18

            pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
            ypos += 12

        # Arcade Coin Display
        coin_txt = self.font_mid.render(f"COINS: {game.coins}", True, COLOR_YELLOW)
        screen.blit(coin_txt, (xpos, ypos))
        ypos += 18
        coin_hint = self.font_small.render(f"Each coin = {COIN_LIVES} lives", True, (200,200,100))
        screen.blit(coin_hint, (xpos, ypos))
        ypos += 18
        # show if any player needs coin
        for p in game.players:
            if not p.alive and p.lives < 0:
                need_txt = self.font_small.render(f"P{p.player_id} NEED COIN! Press C/5", True, COLOR_RED)
                screen.blit(need_txt, (xpos, ypos))
                ypos += 16

        ypos += 6
        pygame.draw.line(screen, (60,60,80), (xpos, ypos), (xpos+HUD_W-24, ypos), 1)
        ypos += 10

        # Controls hint
        hints = [
            "P1: WASD+SPACE",
            "P2: ARROWS+ENTER",
            "C/5: Coin 1/2: Join",
            "P: Pause ESC: Menu",
            "Joy: -:Coin +=Start",
            "J:Rescan I:InvY U:InvX",
            "O:Swap K:RotDpad",
        ]
        for h in hints:
            txt = self.font_small.render(h, True, (140,140,160))
            screen.blit(txt, (xpos, ypos))
            ypos += 16

        # shovel timer
        if game.tilemap and game.tilemap.shovel_timer > 0:
            secs = game.tilemap.shovel_timer // FPS
            sh_txt = self.font_mid.render(f"BASE STEEL {secs}s", True, (255,220,80))
            screen.blit(sh_txt, (xpos, PLAYFIELD_Y+PLAYFIELD_H-70))

        # clock freeze indicator
        if game.freeze_timer > 0:
            secs = game.freeze_timer // FPS
            f_txt = self.font_mid.render(f"FREEZE {secs}s", True, (150,200,255))
            screen.blit(f_txt, (xpos, PLAYFIELD_Y+PLAYFIELD_H-50))

        # coin hint when dead waiting
        if any(not p.alive and p.lives < 0 for p in game.players):
            urgent = self.font_mid.render("INSERT COIN!", True, COLOR_RED)
            screen.blit(urgent, (xpos, PLAYFIELD_Y+PLAYFIELD_H-30))

        # top info bar
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
        # background
        screen.fill(COLOR_BG)
        # title
        big_font = pygame.font.Font(None, 72)
        title = big_font.render("TANK 90", True, COLOR_YELLOW)
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH//2, 160)))
        # subtitle
        small = pygame.font.Font(None, 28)
        sub = small.render("Enhanced Edition - Battle City Tribute", True, (180,180,200))
        screen.blit(sub, sub.get_rect(center=(SCREEN_WIDTH//2, 200)))

        # Tank decoration
        pygame.draw.rect(screen, PLAYER_COLORS[0], (SCREEN_WIDTH//2 - 60, 260, 40, 32), border_radius=4)
        pygame.draw.rect(screen, (40,40,40), (SCREEN_WIDTH//2 - 64, 260, 6, 32))
        pygame.draw.rect(screen, (40,40,40), (SCREEN_WIDTH//2 - 22, 260, 6, 32))
        pygame.draw.rect(screen, (30,30,30), (SCREEN_WIDTH//2 - 42, 240, 4, 20))
        pygame.draw.circle(screen, (20,20,20), (SCREEN_WIDTH//2 - 40, 276), 8)

        pygame.draw.rect(screen, (180,180,180), (SCREEN_WIDTH//2 + 20, 260, 40, 32), border_radius=4)
        pygame.draw.rect(screen, (40,40,40), (SCREEN_WIDTH//2 + 16, 260, 6, 32))
        pygame.draw.rect(screen, (40,40,40), (SCREEN_WIDTH//2 + 58, 260, 6, 32))
        pygame.draw.rect(screen, (30,30,30), (SCREEN_WIDTH//2 + 38, 240, 4, 20))

        options_main = [
            "1 PLAYER",
            "2 PLAYERS CO-OP",
            "LEVEL SELECT",
            "HOW TO PLAY",
            "QUIT",
        ]
        options_level = [f"STAGE {i+1}" for i in range(5)] + ["BACK"]
        options = options_level if mode == 'level' else options_main

        for i, opt in enumerate(options):
            color = COLOR_YELLOW if i == selected else (200,200,200)
            font = pygame.font.Font(None, 38) if i == selected else pygame.font.Font(None, 32)
            txt = font.render(opt, True, color)
            y = 340 + i*44
            # selector arrow
            if i == selected:
                arrow = pygame.font.Font(None, 32).render(">", True, COLOR_YELLOW)
                screen.blit(arrow, (SCREEN_WIDTH//2 - 130, y))
            screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))

        # footer for publishing info
        footer = pygame.font.Font(None, 20).render("Prototype for PC - Nintendo Switch port requires Unity/Godot + Nintendo SDK", True, (100,100,120))
        screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-30)))

        if mode == 'howto':
            # overlay howto
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT-100), pygame.SRCALPHA)
            overlay.fill((0,0,0,200))
            screen.blit(overlay, (0,100))
            lines = [
                "HOW TO PLAY - TANK 90",
                "",
                "Goal: Protect your base (Eagle) and destroy all enemy tanks.",
                "Movement: P1 WASD / P2 Arrows / Gamepad Stick / Joy-Con",
                "Shoot: SPACE / ENTER / Gamepad A / Joy-Con Any",
                "",
                "Tiles: Brick=breakable, Steel=needs power gun, Water=blocked",
                "Forest=hides tank, Ice=slippery",
                "Powerups:",
                " Star=upgrade tank (3 levels) gun+speed",
                " Helmet=10s shield, Clock=freeze enemies 5s",
                " Shovel=steel walls around base 15s",
                " Tank=+1 life, Grenade=kill all enemies",
                " Gun=steel-breaking bullets",
                "",
                "ARCADE COIN SYSTEM:",
                " Each coin = 10 lives, Press C or 5 to Insert Coin",
                " Press 1 = P1 Join, Press 2 = P2 Join (late join OK)",
                " Joy-Con: Minus (-) = Coin, Plus (+) = Start/Join",
                " After Game Over, 15 sec to insert coin and continue same stage",
                " Base repaired on continue, score kept",
                "",
                "Press ESC to go back",
            ]
            y = 140
            for line in lines:
                f = pygame.font.Font(None, 22)
                c = COLOR_YELLOW if "HOW TO" in line else (200,200,200)
                txt = f.render(line, True, c)
                screen.blit(txt, (SCREEN_WIDTH//2 - 260, y))
                y += 22

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
            # Arcade Continue Screen with Coin system
            if game:
                secs = max(0, game.continue_timer // FPS)
                # flashing INSERT COIN
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

                # Per player status
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

                # countdown bar
                bar_w = 200
                bar_h = 12
                bx = SCREEN_WIDTH//2 - bar_w//2
                by = y + 10
                pygame.draw.rect(screen, (60,60,60), (bx, by, bar_w, bar_h))
                if game.continue_timer > 0:
                    fill_w = int(bar_w * (game.continue_timer / CONTINUE_TIME))
                    pygame.draw.rect(screen, COLOR_YELLOW, (bx, by, fill_w, bar_h))

            # fallback instructions
            cont2 = pygame.font.Font(None, 20).render("ESC = Menu  |  Timer 0 = Return to Menu", True, (120,120,140))
            screen.blit(cont2, cont2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-40)))
