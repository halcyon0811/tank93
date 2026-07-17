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
        ypos += 30

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
            "C/5: Insert Coin",
            "1/2: Join (+10 Lives)",
            "P: Pause ESC: Menu",
            "Joy: -:Coin +=Start",
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
            "1 PLAYER (35 STAGES)",
            "2 PLAYERS CO-OP (35 STAGES)",
            "LEVEL SELECT - 35 ORIGINAL NES MAPS",
            "HOW TO PLAY",
            "QUIT",
        ]

        # Try to get total stage count from battle_city module (35)
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
            options = options_main
            for i, opt in enumerate(options):
                color = COLOR_YELLOW if i == selected else (200,200,200)
                font = pygame.font.Font(None, 38) if i == selected else pygame.font.Font(None, 32)
                txt = font.render(opt, True, color)
                y = 340 + i*44
                if i == selected:
                    arrow = pygame.font.Font(None, 32).render(">", True, COLOR_YELLOW)
                    screen.blit(arrow, (SCREEN_WIDTH//2 - 160, y))
                screen.blit(txt, txt.get_rect(center=(SCREEN_WIDTH//2, y)))
        elif mode == 'level':
            # Header
            header_font = pygame.font.Font(None, 30)
            header = header_font.render(f"SELECT STAGE - {TOTAL_STAGES} ORIGINAL NES MAPS (Arrows:Move L/R:+5 PgUp/Dn:+10)", True, COLOR_WHITE)
            screen.blit(header, header.get_rect(center=(SCREEN_WIDTH//2, 315)))

            # Grid layout 7 cols x 5 rows for 35 stages
            cols = 7
            cell_w, cell_h = 104, 38
            gap_x, gap_y = 10, 8
            grid_w = cols*cell_w + (cols-1)*gap_x
            start_x = SCREEN_WIDTH//2 - grid_w//2
            start_y = 340

            # draw stage cells 0..TOTAL_STAGES-1
            for idx in range(TOTAL_STAGES):
                c = idx % cols
                r = idx // cols
                x = start_x + c*(cell_w+gap_x)
                y = start_y + r*(cell_h+gap_y)
                is_sel = (selected == idx)
                # box
                bg_col = (60,60,90) if not is_sel else COLOR_YELLOW
                border_col = COLOR_WHITE if not is_sel else COLOR_BLACK
                pygame.draw.rect(screen, bg_col, (x, y, cell_w, cell_h), border_radius=6)
                pygame.draw.rect(screen, border_col, (x, y, cell_w, cell_h), 2, border_radius=6)
                # text
                txt_color = COLOR_BLACK if is_sel else COLOR_WHITE
                f = pygame.font.Font(None, 26) if is_sel else pygame.font.Font(None, 22)
                label = f"STAGE {idx+1}"
                txt_surf = f.render(label, True, txt_color)
                screen.blit(txt_surf, txt_surf.get_rect(center=(x+cell_w//2, y+cell_h//2 - 6)))
                # small difficulty hint: count armor
                if BOTS_RAW_ALL and idx < len(BOTS_RAW_ALL):
                    # parse armor count
                    raw = BOTS_RAW_ALL[idx]
                    # e.g. ['18*basic','2*fast'] -> compact
                    tiny = self.font_small.render(" ".join(raw), True, (200,200,100) if not is_sel else (40,40,20))
                    # truncate to fit
                    # Scale down font to 14 for fit
                    # We'll just show first 12 chars
                    screen.blit(tiny, (x+6, y+cell_h-14))

            # BACK button below grid
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

            # Preview panel for selected stage (if not BACK)
            if selected < TOTAL_STAGES and LVLS_13_PREVIEW and selected < len(LVLS_13_PREVIEW):
                # mini map preview top-right
                preview = LVLS_13_PREVIEW[selected]
                # 13x13 map, tile size 10 px -> 130px
                p_tile = 10
                p_w = 13 * p_tile
                p_h = 13 * p_tile
                p_x = SCREEN_WIDTH - p_w - 30
                p_y = start_y
                # bg
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
                # bots info below preview
                if BOTS_RAW_ALL and selected < len(BOTS_RAW_ALL):
                    bot_text = "Enemies: " + " ".join(BOTS_RAW_ALL[selected])
                    bt = self.font_small.render(bot_text, True, (200,200,200))
                    screen.blit(bt, (p_x - 20, p_y + p_h + 8))
                    # tile legend
                    legend = self.font_small.render("B=Brick S=Steel ~=Water F=Forest I=Ice", True, (160,160,160))
                    screen.blit(legend, (p_x - 20, p_y + p_h + 26))

                # selected big highlight label
                sel_label = pygame.font.Font(None, 26).render(f"> SELECTED: STAGE {selected+1} <", True, COLOR_YELLOW)
                screen.blit(sel_label, sel_label.get_rect(center=(SCREEN_WIDTH//2, back_y + 40)))

        # footer for publishing info + sound label
        footer = pygame.font.Font(None, 18).render("35 Original NES Maps + Authentic NES SFX (feichao93 pack) - Bricks/Water/Forest/Steel/Ice + Tank Move Engine + Explosions + Powerups", True, (100,100,120))
        screen.blit(footer, footer.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-30)))

        # Second footer with all 35 maps copyright + original
        footer2 = pygame.font.Font(None, 16).render("Stage 1: 18*basic 2*fast ... Stage 35: 4*power 6*fast 10*armor (700 enemies total) - Authentic Battle City 1985", True, (80,80,100))
        screen.blit(footer2, footer2.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT-14)))

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
