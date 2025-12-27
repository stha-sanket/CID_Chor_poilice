import pygame
import sys
import random
import os

# --- Constants ---
WIDTH, HEIGHT = 1024, 576
SKY_BLUE = (135, 206, 235)
GROUND_COLOR = (34, 139, 34)
PLATFORM_COLOR = (139, 69, 19)
POLE_COLOR = (101, 67, 33)
FLAG_RED = (200, 0, 0)
FLAG_WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

GRAVITY = 1500.0  # px/s^2
PLAYER_SPEED = 300.0
ENEMY_SPEED = 210.0
JUMP_STRENGTH = -520.0
GROUND_Y = HEIGHT - 80
ASSETS_DIR = 'assets'

# --- Helper ---
def load_image(name, scale_height=None):
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname).convert_alpha()
    except pygame.error:
        print(f"Cannot load image: {name}")
        raise SystemExit(f"Missing {name} in assets/")
    if scale_height:
        ratio = scale_height / image.get_height()
        new_size = (int(image.get_width() * ratio), scale_height)
        image = pygame.transform.scale(image, new_size)
    return image, image.get_rect()

# --- Base Entity Class ---
class Entity:
    def __init__(self, game, image_file, world_x, world_y, scale_height=68):
        self.game = game
        self.base_image, self.rect = load_image(image_file, scale_height)
        self.image = self.base_image
        self.world_x = world_x
        self.world_y = world_y
        self.rect.topleft = (world_x, world_y)
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = False

    def handle_horizontal_collision(self):
        for plat in self.game.platforms:
            if self.rect.colliderect(plat):
                if self.vel_x > 0:
                    self.rect.right = plat.left
                    self.vel_x = 0.0
                elif self.vel_x < 0:
                    self.rect.left = plat.right
                    self.vel_x = 0.0
        self.world_x = self.rect.x

    def handle_vertical_collision(self):
        self.on_ground = False
        for plat in self.game.platforms:
            if self.rect.colliderect(plat):
                if self.vel_y > 0:
                    self.rect.bottom = plat.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif self.vel_y < 0:
                    self.rect.top = plat.bottom
                    self.vel_y = 0.0
        self.world_y = self.rect.y

    def update_physics(self, dt):
        # Horizontal movement
        dx = self.vel_x * dt
        self.world_x += dx
        self.rect.x = self.world_x
        self.handle_horizontal_collision()

        # Vertical movement
        dy = self.vel_y * dt
        self.world_y += dy
        self.rect.y = self.world_y
        self.handle_vertical_collision()

    def get_screen_pos(self, camera_x):
        return self.world_x - camera_x, self.world_y

# --- Player ---
class Player(Entity):
    def __init__(self, game):
        super().__init__(game, 'chor.png', 100.0, GROUND_Y - 68)
        self.direction = 1

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.vel_x = 0.0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.direction = -1

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH

        self.vel_y += GRAVITY * dt

        self.update_physics(dt)

        # Flip sprite
        if self.direction == -1:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

# --- Enemy ---
class Enemy(Entity):
    def __init__(self, game, world_x, world_y):
        img_file = random.choice(['police.png', 'police2.png'])
        super().__init__(game, img_file, world_x, world_y)
        self.direction = 1.0
        self.react_timer = 0.0

    def update(self, dt):
        player = self.game.player
        dist_x = player.world_x - self.world_x

        # Chase logic with slight delay/rand
        self.react_timer += dt
        if self.react_timer > 0.3 + random.uniform(-0.1, 0.1):  # React every ~0.3s
            if abs(dist_x) > 40:
                self.direction = 1.0 if dist_x > 0 else -1.0
            self.react_timer = 0.0

        self.vel_x = self.direction * ENEMY_SPEED

        # Jump logic - nerfed/probabilistic
        if self.on_ground:
            # Jump towards player if much higher
            if random.random() < 0.5 and player.world_y < self.world_y - 70 and abs(dist_x) < 160:
                self.vel_y = JUMP_STRENGTH * 0.82

            # Check ahead for gap/wall
            probe_dist = 55
            probe_x = self.world_x + self.direction * probe_dist
            probe_y_ground = self.world_y + self.rect.height
            probe_y_head = self.world_y + 25

            ground_hit = any(plat.collidepoint(probe_x, probe_y_ground) for plat in self.game.platforms)
            wall_hit = any(plat.collidepoint(probe_x, probe_y_head) for plat in self.game.platforms)

            if not ground_hit:
                if random.random() < 0.35:  # Low chance to jump gaps
                    self.vel_y = JUMP_STRENGTH * 0.78
            elif wall_hit:
                if random.random() < 0.6:  # Decent chance to jump walls
                    self.vel_y = JUMP_STRENGTH * 0.85

        self.vel_y += GRAVITY * dt
        self.update_physics(dt)

        # Flip
        if self.direction < 0:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

# --- Game ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chor Police Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 40)
        self.big_font = pygame.font.SysFont(None, 80)
        self.score = 0
        self.high_score = 0
        self.state = 'start'
        self.camera_x = 0

    def create_level(self):
        self.platforms = []
        # Ground
        for x in range(0, 3200, 100):
            self.platforms.append(pygame.Rect(x, GROUND_Y, 100, HEIGHT - GROUND_Y))

        # Platforms - more for strategy
        extra_platforms = [
            (550, GROUND_Y - 130, 280, 25),
            (950, GROUND_Y - 240, 220, 25),
            (1350, GROUND_Y - 170, 280, 25),
            (1750, GROUND_Y - 300, 320, 25),
            (2150, GROUND_Y - 130, 220, 25),
            (2500, GROUND_Y - 200, 180, 25),
            (2650, GROUND_Y - 350, 150, 25),  # High near end
        ]
        for pos in extra_platforms:
            self.platforms.append(pygame.Rect(pos))

        # Goal
        self.goal = pygame.Rect(3050, GROUND_Y - 220, 60, 220)
        self.flag_image = None
        try:
            self.flag_image, _ = load_image('flag.png', scale_height=180)
        except:
            pass  # Will draw custom flag

    def reset(self):
        self.create_level()
        self.player = Player(self)
        self.enemies = [
            Enemy(self, 780, GROUND_Y - 68),
            Enemy(self, 1420, GROUND_Y - 170 - 68),
            Enemy(self, 2120, GROUND_Y - 130 - 68),
        ]
        self.score = 0
        self.state = 'playing'
        self.camera_x = 0

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events(dt)
            if self.state == 'playing':
                self.update(dt)
            self.draw()
            pygame.display.flip()

    def handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if self.state == 'start':
                    self.reset()
                elif self.state in ['game_over', 'win'] and event.key == pygame.K_r:
                    self.reset()

    def update(self, dt):
        self.player.update(dt)
        for enemy in self.enemies[:]:
            enemy.update(dt)

            # Stomp enemy
            if (self.player.vel_y > 100 and  # Falling fast
                self.player.rect.colliderect(enemy.rect) and
                self.player.rect.bottom < enemy.rect.centery + 15):
                self.enemies.remove(enemy)
                self.player.vel_y = JUMP_STRENGTH * 0.65
                self.score += 100
                continue

            # Caught
            if self.player.rect.colliderect(enemy.rect):
                self.state = 'game_over'
                self.high_score = max(self.high_score, self.score)
                return

        # Win
        if self.player.rect.colliderect(self.goal):
            self.state = 'win'
            self.high_score = max(self.high_score, self.score)

        # Camera
        self.camera_x = max(0, self.player.world_x - WIDTH // 3)

    def draw(self):
        self.screen.fill(SKY_BLUE)

        if self.state == 'start':
            self.draw_start()
            return

        # World offset
        cam = self.camera_x

        # Platforms
        screen_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)
        for plat in self.platforms:
            draw_r = plat.move(-cam, 0)
            if draw_r.colliderect(screen_rect):
                color = GROUND_COLOR if plat.height > 50 else PLATFORM_COLOR
                pygame.draw.rect(self.screen, color, draw_r)
                pygame.draw.rect(self.screen, BLACK, draw_r, 2)

        # Goal/Flag
        goal_r = self.goal.move(-cam, 0)
        if self.flag_image:
            self.screen.blit(self.flag_image, goal_r.topleft)
        else:
            # Custom flag
            pole_rect = pygame.Rect(goal_r.centerx - 4, goal_r.top, 8, goal_r.height)
            pygame.draw.rect(self.screen, POLE_COLOR, pole_rect)
            flag_rect = pygame.Rect(goal_r.centerx, goal_r.top + 30, 50, 90)
            pygame.draw.rect(self.screen, FLAG_RED, flag_rect)
            pygame.draw.polygon(self.screen, FLAG_WHITE, [flag_rect.topright, (flag_rect.right + 25, flag_rect.centery), flag_rect.bottomright])

        # Enemies
        for e in self.enemies:
            sx, sy = e.get_screen_pos(cam)
            self.screen.blit(e.image, (sx, sy))

        # Player
        px, py = self.player.get_screen_pos(cam)
        self.screen.blit(self.player.image, (px, py))

        # UI
        score_t = self.font.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(score_t, (20, 20))

        # Overlays
        if self.state == 'game_over':
            self.draw_overlay("CAUGHT BY POLICE!", RED, f"Score: {self.score}  High: {self.high_score}")
        elif self.state == 'win':
            self.draw_overlay("YOU ESCAPED!", (0, 255, 0), f"Final Score: {self.score}  High: {self.high_score}")

    def draw_start(self):
        title = self.big_font.render("Chor Police Adventure", True, BLACK)
        prompt = self.font.render("Press any key to start your escape!", True, BLACK)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 ))

    def draw_overlay(self, msg, color, score_msg):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        msg_t = self.big_font.render(msg, True, color)
        score_t = self.font.render(score_msg, True, WHITE)
        restart_t = self.font.render("Press R to play again", True, WHITE)
        self.screen.blit(msg_t, (WIDTH//2 - msg_t.get_width()//2, HEIGHT//2 - 80))
        self.screen.blit(score_t, (WIDTH//2 - score_t.get_width()//2, HEIGHT//2 ))
        self.screen.blit(restart_t, (WIDTH//2 - restart_t.get_width()//2, HEIGHT//2 + 80))

if __name__ == '__main__':
    Game().run()