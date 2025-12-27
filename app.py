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
ENEMY_SPEED = 299.0
JUMP_STRENGTH = -650.0
GROUND_Y = HEIGHT - 80
ASSETS_DIR = 'assets'

# --- Helper ---
def load_image(name, scale_height=None):
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname).convert_alpha()
    except pygame.error:
        print(f"Cannot load image: {name} - using placeholder")
        # Create simple colored rect as placeholder
        surf = pygame.Surface((40, scale_height or 68))
        surf.fill(RED if 'police' in name else (255, 165, 0))
        image = surf
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
        self.world_x = float(world_x)
        self.world_y = float(world_y)
        self.rect.topleft = (self.world_x, self.world_y)
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
        # Horizontal
        dx = self.vel_x * dt
        self.world_x += dx
        self.rect.x = self.world_x
        self.handle_horizontal_collision()

        # Vertical
        dy = self.vel_y * dt
        self.world_y += dy
        self.rect.y = self.world_y
        self.handle_vertical_collision()

    def get_screen_pos(self, camera_x):
        return self.world_x - camera_x, self.world_y

# --- Player (NO STOMPING) ---
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

# --- Enemy (UNSTOMPABLE - Pure chase) ---
class Enemy(Entity):
    def __init__(self, game, world_x, world_y):
        img_file = random.choice(['police.png', 'police2.png'])
        super().__init__(game, img_file, world_x, world_y)
        self.direction = 1.0
        self.react_timer = 0.0
        self.last_player_x = 0.0

    def update(self, dt):
        player = self.game.player
        dist_x = player.world_x - self.world_x

        # Slower reaction time
        self.react_timer += dt
        if self.react_timer > 0.4 + random.uniform(-0.1, 0.15):
            if abs(dist_x) > 50:
                self.direction = 1.0 if dist_x > 0 else -1.0
            self.react_timer = 0.0

        self.vel_x = self.direction * ENEMY_SPEED

        # Jump logic - nerfed
        if self.on_ground:
            # Rarely jump toward player
            if (random.random() < 0.3 and 
                player.world_y < self.world_y - 60 and 
                abs(dist_x) < 140):
                self.vel_y = JUMP_STRENGTH * 0.8

            # Check for gaps/walls
            probe_dist = 60
            probe_x = self.world_x + self.direction * probe_dist
            probe_y_ground = self.world_y + self.rect.height
            probe_y_head = self.world_y + 30

            ground_exists = any(plat.collidepoint(probe_x, probe_y_ground) 
                              for plat in self.game.platforms)
            wall_exists = any(plat.collidepoint(probe_x, probe_y_head) 
                            for plat in self.game.platforms)

            if not ground_exists and random.random() < 0.4:
                self.vel_y = JUMP_STRENGTH * 0.75
            elif wall_exists and random.random() < 0.5:
                self.vel_y = JUMP_STRENGTH * 0.82

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
        pygame.display.set_caption("Chor Police Adventure - NO STOMPING!")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 40)
        self.big_font = pygame.font.SysFont(None, 80)
        self.score = 0
        self.high_score = 0
        self.state = 'start'
        self.camera_x = 0

    def create_level(self):
        self.platforms = []
        # Ground (longer level)
        for x in range(0, 3400, 100):
            self.platforms.append(pygame.Rect(x, GROUND_Y, 100, HEIGHT - GROUND_Y))

        # Strategic platforms
        extra_platforms = [
            (550, GROUND_Y - 130, 280, 25),
            (950, GROUND_Y - 240, 220, 25),
            (1350, GROUND_Y - 170, 280, 25),
            (1750, GROUND_Y - 300, 320, 25),
            (2150, GROUND_Y - 130, 220, 25),
            (2500, GROUND_Y - 200, 180, 25),
            (2800, GROUND_Y - 350, 150, 25),  # High jump near end
            (3100, GROUND_Y - 100, 200, 25),  # Final platform
        ]
        for pos in extra_platforms:
            self.platforms.append(pygame.Rect(pos))

        # Goal flag
        self.goal = pygame.Rect(3250, GROUND_Y - 220, 70, 220)

    def reset(self):
        self.create_level()
        self.player = Player(self)
        self.enemies = [
            Enemy(self, 780, GROUND_Y - 68),
            Enemy(self, 1480, GROUND_Y - 170 - 68),
            Enemy(self, 2180, GROUND_Y - 130 - 68),
        ]
        self.score = 0
        self.state = 'playing'
        self.camera_x = 0

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            
            if self.state == 'playing':
                self.update(dt)
            
            self.draw()
            pygame.display.flip()

    def handle_events(self):
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
            
            # NO STOMPING - Just collision = caught
            if self.player.rect.colliderect(enemy.rect):
                self.state = 'game_over'
                self.high_score = max(self.high_score, self.score)
                return

        # Win condition
        if self.player.rect.colliderect(self.goal):
            self.state = 'win'
            self.high_score = max(self.high_score, self.score)

        # Camera follows player (but not too fast)
        target_cam = max(0, self.player.world_x - WIDTH // 3)
        self.camera_x += (target_cam - self.camera_x) * 0.1

        # Score increases with distance
        self.score = int(self.player.world_x / 10)

    def draw(self):
        self.screen.fill(SKY_BLUE)

        if self.state == 'start':
            self.draw_start()
            return

        cam = self.camera_x
        screen_rect = pygame.Rect(0, 0, WIDTH, HEIGHT)

        # Platforms
        for plat in self.platforms:
            draw_r = plat.move(-cam, 0)
            if draw_r.colliderect(screen_rect):
                color = GROUND_COLOR if plat.height > 50 else PLATFORM_COLOR
                pygame.draw.rect(self.screen, color, draw_r)
                pygame.draw.rect(self.screen, BLACK, draw_r, 2)

        # Goal Flag (auto-drawn)
        goal_r = self.goal.move(-cam, 0)
        if goal_r.colliderect(screen_rect):
            # Pole
            pole_rect = pygame.Rect(goal_r.centerx - 5, goal_r.top, 10, goal_r.height)
            pygame.draw.rect(self.screen, POLE_COLOR, pole_rect)
            # Flag
            flag_rect = pygame.Rect(goal_r.centerx + 5, goal_r.top + 40, 55, 100)
            pygame.draw.rect(self.screen, FLAG_RED, flag_rect)
            pygame.draw.polygon(self.screen, FLAG_WHITE, 
                              [(flag_rect.right, flag_rect.centery-10), 
                               (flag_rect.right + 30, flag_rect.centery), 
                               (flag_rect.right, flag_rect.centery+10)])

        # Enemies
        for e in self.enemies:
            sx, sy = e.get_screen_pos(cam)
            if 0 <= sx <= WIDTH:
                self.screen.blit(e.image, (sx, sy))

        # Player
        px, py = self.player.get_screen_pos(cam)
        self.screen.blit(self.player.image, (px, py))

        # UI
        score_t = self.font.render(f"Score: {self.score} | Goal: 3250", True, BLACK)
        self.screen.blit(score_t, (20, 20))
        dist_t = self.font.render(f"Distance: {int(self.player.world_x)}", True, BLACK)
        self.screen.blit(dist_t, (20, 60))

        # Game Over/Win overlays
        if self.state == 'game_over':
            self.draw_overlay("CAUGHT BY POLICE!", RED, f"Score: {self.score}  High: {self.high_score}")
        elif self.state == 'win':
            self.draw_overlay("YOU ESCAPED! 🏆", (0, 255, 0), f"Final: {self.score}  High: {self.high_score}")

    def draw_start(self):
        title = self.big_font.render("Chor Police Adventure", True, BLACK)
        subtitle = self.font.render("NO STOMPING - Pure Chase!", True, RED)
        prompt = self.font.render("WASD/Space to run & jump | Reach the flag!", True, BLACK)
        self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
        self.screen.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//2 - 60))
        self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 + 20))

    def draw_overlay(self, msg, color, score_msg):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(200)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        
        msg_t = self.big_font.render(msg, True, color)
        score_t = self.font.render(score_msg, True, WHITE)
        restart_t = self.font.render("Press R to try again, chor!", True, WHITE)
        
        self.screen.blit(msg_t, (WIDTH//2 - msg_t.get_width()//2, HEIGHT//2 - 80))
        self.screen.blit(score_t, (WIDTH//2 - score_t.get_width()//2, HEIGHT//2 ))
        self.screen.blit(restart_t, (WIDTH//2 - restart_t.get_width()//2, HEIGHT//2 + 80))

if __name__ == '__main__':
    Game().run()