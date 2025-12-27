import pygame
import sys
import random
import time
import os

# --- Constants ---
WIDTH, HEIGHT = 1024, 576
SKY_BLUE = (135, 206, 235)
GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
BRICK_LINE = (101, 67, 33)
BLUE = (0, 100, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

GRAVITY = 0.7
PLAYER_MAX_SPEED = 6.0
JUMP_STRENGTH = -16
GROUND_Y = HEIGHT - 80

ASSETS_DIR = 'assets'

# --- Helper Functions ---
def load_image(name, scale=1):
    """Loads an image, scales it, and handles transparency."""
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error as message:
        print('Cannot load image:', name)
        raise SystemExit(message)
    image = image.convert_alpha()
    size = image.get_size()
    scaled_size = (int(size[0] * scale), int(size[1] * scale))
    image = pygame.transform.scale(image, scaled_size)
    return image, image.get_rect()

# --- Game Classes ---

class Player:
    def __init__(self, game):
        self.game = game
        self.image, self.rect = load_image('chor.png', scale=1.5)
        self.base_image = self.image
        self.world_x = 200.0
        self.world_y = GROUND_Y - self.rect.height
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.direction = 1 # 1 for right, -1 for left
        self.invincible = False
        self.invincible_end_time = 0.0

    def move(self, dx, dy):
        self.rect.x += dx
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dx > 0: self.rect.right = solid.left
                elif dx < 0: self.rect.left = solid.right
                self.vel_x = 0.0
        
        self.rect.y += dy
        self.on_ground = False
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dy > 0:
                    self.rect.bottom = solid.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = solid.bottom
                    self.vel_y = 0.0
        
        self.world_x = self.rect.x
        self.world_y = self.rect.y

    def update(self, dt):
        keys = pygame.key.get_pressed()
        accel = 50.0 * dt

        # --- Movement ---
        target_vel_x = 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            target_vel_x = PLAYER_MAX_SPEED
            self.direction = 1
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            target_vel_x = -PLAYER_MAX_SPEED
            self.direction = -1
        
        # Smooth acceleration/deceleration
        self.vel_x += (target_vel_x - self.vel_x) * 0.3

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH
            self.on_ground = False

        self.vel_y += GRAVITY * dt * 60

        # --- Position & Collision Update ---
        self.rect.topleft = (self.world_x, self.world_y)
        self.move(self.vel_x * dt * 60, self.vel_y * dt * 60)

        # --- Collisions with items/enemies ---
        self.check_collisions()

        # --- Power-up Timer ---
        if self.invincible and time.time() > self.invincible_end_time:
            self.invincible = False
            
        # --- Flip Image ---
        if self.direction == -1:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

    def check_collisions(self):
        # Enemies
        for enemy in self.game.enemies[:]:
            if self.rect.colliderect(enemy.rect):
                if self.invincible:
                    self.game.enemies.remove(enemy)
                    self.game.score += 100
                    continue
                if self.vel_y > 1 and self.rect.bottom < enemy.rect.centery + 10:
                    self.game.enemies.remove(enemy)
                    self.game.score += 50
                    self.vel_y = JUMP_STRENGTH * 0.6
                else: 
                    self.game.state = 'game_over'

    def get_screen_pos(self, camera_x):
        return int(self.world_x - camera_x), int(self.world_y)

class Enemy:
    def __init__(self, game, world_x, world_y):
        self.game = game
        img_choice = random.choice(['police.png', 'police2.png'])
        self.image, self.rect = load_image(img_choice, scale=1.5)
        self.base_image = self.image
        
        self.world_x = world_x
        self.world_y = world_y
        self.rect.topleft = (world_x, world_y)
        
        self.vel_x = 0.0
        self.vel_y = 0.0
        self.on_ground = True
        self.direction = -1

    def move(self, dx, dy):
        self.rect.x += dx
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dx > 0: self.rect.right = solid.left
                elif dx < 0: self.rect.left = solid.right
                self.vel_x = 0.0
        
        self.rect.y += dy
        self.on_ground = False
        for solid in self.game.platforms:
            if self.rect.colliderect(solid):
                if dy > 0:
                    self.rect.bottom = solid.top
                    self.vel_y = 0.0
                    self.on_ground = True
                elif dy < 0:
                    self.rect.top = solid.bottom
                    self.vel_y = 0.0
        
        self.world_x = self.rect.x
        self.world_y = self.rect.y

    def update(self, dt):
        # --- AI Logic ---
        player = self.game.player
        
        # Horizontal chase
        dist_x = player.world_x - self.world_x
        if dist_x > 5:
            self.vel_x += 0.5
            self.direction = 1
        elif dist_x < -5:
            self.vel_x -= 0.5
            self.direction = -1
        
        self.vel_x = max(-4, min(self.vel_x, 4)) # Clamp speed
        self.vel_x *= 0.95 # Friction

        # Jumping AI
        if self.on_ground:
            # 1. Jump if player is above
            if player.world_y < self.world_y - 50 and abs(dist_x) < 200:
                self.vel_y = JUMP_STRENGTH * 0.8
            # 2. Jump if a wall is in the way
            else:
                probe_x = self.rect.centerx + (self.direction * 40)
                for plat in self.game.platforms:
                    if plat.collidepoint(probe_x, self.rect.centery):
                        self.vel_y = JUMP_STRENGTH * 0.9
                        break

        # --- Physics and Movement ---
        self.vel_y += GRAVITY * dt * 60
        self.rect.topleft = (self.world_x, self.world_y)
        self.move(self.vel_x * dt * 60, self.vel_y * dt * 60)
        
        # --- Flip Image ---
        if self.direction == -1:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

    def get_screen_pos(self, camera_x):
        return int(self.world_x - camera_x), int(self.world_y)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chor Police Adventure")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 36)
        self.large_font = pygame.font.SysFont(None, 72)
        self.running = True
        self.state = 'start_screen'
        self.high_score = 0
        self.camera_x = 0

    def create_level(self):
        self.platforms = []
        # Ground floor
        for i in range(0, 2000, 100):
            self.platforms.append(pygame.Rect(i, GROUND_Y, 100, 100))
        
        # Some platforms
        level_layout = [
            (500, GROUND_Y - 100, 200, 20),
            (800, GROUND_Y - 200, 150, 20),
            (1100, GROUND_Y - 150, 100, 20),
            (1400, GROUND_Y - 250, 200, 150),
            (1600, GROUND_Y - 100, 100, 20),
        ]
        for plat in level_layout:
            self.platforms.append(pygame.Rect(plat))

    def reset(self):
        self.create_level()
        self.player = Player(self)
        self.enemies = [
            Enemy(self, 800, GROUND_Y - 40),
            Enemy(self, 1450, GROUND_Y - 250 - 40)
        ]
        self.score = 0
        self.state = 'playing'

    def run(self):
        while self.running:
            self.dt = self.clock.tick(60) / 1000.0
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if self.state == 'start_screen':
                    self.reset()
                elif self.state == 'game_over' and event.key == pygame.K_r:
                    self.reset()

    def update(self):
        if self.state != 'playing':
            return
        self.player.update(self.dt)
        for enemy in self.enemies:
            enemy.update(self.dt)
        self.camera_x = self.player.world_x - WIDTH // 3

    def draw(self):
        self.screen.fill(SKY_BLUE)
        if self.state == 'start_screen':
            self.draw_start_screen()
        else: # Draw game world for both 'playing' and 'game_over'
            self.draw_game()
            if self.state == 'game_over':
                self.draw_game_over_screen()
        pygame.display.flip()

    def draw_game(self):
        # Platforms
        for plat in self.platforms:
            sx = plat.x - self.camera_x
            pygame.draw.rect(self.screen, BROWN, (sx, plat.y, plat.width, plat.height))

        # Enemies
        for enemy in self.enemies:
            sx, sy = enemy.get_screen_pos(self.camera_x)
            self.screen.blit(enemy.image, (sx, sy))

        # Player
        px, py = self.player.get_screen_pos(self.camera_x)
        self.screen.blit(self.player.image, (px, py))

        # UI
        ui_text = self.font.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(ui_text, (10, 10))

    def draw_start_screen(self):
        title = self.large_font.render("Chor Police Adventure", True, BLACK)
        prompt = self.font.render("Press any key to start", True, BLACK)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2, HEIGHT // 2 + 20))

    def draw_game_over_screen(self):
        self.high_score = max(self.high_score, self.score)
        over_text = self.large_font.render("CAUGHT! GAME OVER", True, RED)
        final_score = self.font.render(f"Final Score: {self.score}  High: {self.high_score}", True, BLACK)
        restart_text = self.font.render("Press R to Restart", True, BLACK)
        self.screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 100))
        self.screen.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, HEIGHT // 2 - 20))
        self.screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 60))

# --- Main Execution ---
if __name__ == '__main__':
    game = Game()
    game.run()