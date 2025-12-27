import pygame
import sys
import random
import os

# --- Constants ---
WIDTH, HEIGHT = 1024, 576
SKY_BLUE = (135, 206, 235)
GROUND_COLOR = (34, 139, 34)
PLATFORM_COLOR = (139, 69, 19)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)

GRAVITY = 0.8
PLAYER_SPEED = 5
JUMP_STRENGTH = -15
GROUND_Y = HEIGHT - 80
ASSETS_DIR = 'assets'

# --- Helper ---
def load_image(name, scale_height=None):
    fullname = os.path.join(ASSETS_DIR, name)
    try:
        image = pygame.image.load(fullname).convert_alpha()
    except pygame.error:
        print(f"Cannot load image: {name}")
        raise SystemExit
    if scale_height:
        ratio = scale_height / image.get_height()
        new_size = (int(image.get_width() * ratio), scale_height)
        image = pygame.transform.scale(image, new_size)
    return image, image.get_rect()

# --- Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self, game):
        super().__init__()
        self.game = game
        self.base_image, self.rect = load_image('chor.png', scale_height=70)
        self.image = self.base_image
        self.world_x = 100.0
        self.world_y = GROUND_Y - self.rect.height
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.direction = 1

    def update(self, dt):
        keys = pygame.key.get_pressed()
        self.vel_x = 0
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel_x = PLAYER_SPEED
            self.direction = 1
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel_x = -PLAYER_SPEED
            self.direction = -1

        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = JUMP_STRENGTH

        self.vel_y += GRAVITY

        # Move horizontally
        self.world_x += self.vel_x
        self.check_collision(dx=self.vel_x, dy=0)

        # Move vertically
        self.world_y += self.vel_y
        self.on_ground = False
        self.check_collision(dx=0, dy=self.vel_y)

        # Flip sprite
        if self.direction == -1:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

        self.rect.topleft = (self.world_x, self.world_y)

    def check_collision(self, dx, dy):
        temp_rect = self.rect.move(dx, dy)
        for plat in self.game.platforms:
            if temp_rect.colliderect(plat):
                if dy > 0:  # Falling
                    self.world_y = plat.top - self.rect.height
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:  # Hitting head
                    self.vel_y = 0
                if dx > 0:
                    self.world_x = plat.left - self.rect.width
                elif dx < 0:
                    self.world_x = plat.right

class Enemy(pygame.sprite.Sprite):
    def __init__(self, game, x, y):
        super().__init__()
        img = random.choice(['police.png', 'police2.png'])
        self.base_image, self.rect = load_image(img, scale_height=70)
        self.image = self.base_image
        self.game = game
        self.world_x = x
        self.world_y = y
        self.vel_x = 0
        self.vel_y = 0
        self.on_ground = False
        self.direction = -1

    def update(self, dt):
        player = self.game.player
        dist_x = player.world_x - self.world_x

        # Chase player
        if abs(dist_x) > 20:
            self.direction = 1 if dist_x > 0 else -1
            self.vel_x = self.direction * 3.5

        # Jump if needed
        if self.on_ground:
            # Jump to reach player if higher
            if player.world_y < self.world_y - 40 and abs(dist_x) < 250:
                self.vel_y = JUMP_STRENGTH * 0.9
            # Jump over gaps / walls
            probe_x = self.world_x + self.direction * 50
            on_edge = True
            for plat in self.game.platforms:
                if plat.collidepoint(probe_x, self.world_y + self.rect.height + 5):
                    on_edge = False
                    break
            if on_edge:
                self.vel_y = JUMP_STRENGTH * 0.85

        self.vel_y += GRAVITY

        # Horizontal move
        self.world_x += self.vel_x
        self.check_collision(dx=self.vel_x, dy=0)

        # Vertical move
        self.world_y += self.vel_y
        self.on_ground = False
        self.check_collision(dx=0, dy=self.vel_y)

        # Flip
        if self.direction == -1:
            self.image = pygame.transform.flip(self.base_image, True, False)
        else:
            self.image = self.base_image

        self.rect.topleft = (self.world_x, self.world_y)

    def check_collision(self, dx, dy):
        temp_rect = self.rect.move(dx, dy)
        for plat in self.game.platforms:
            if temp_rect.colliderect(plat):
                if dy > 0:
                    self.world_y = plat.top - self.rect.height
                    self.vel_y = 0
                    self.on_ground = True
                elif dy < 0:
                    self.vel_y = 0
                if dx != 0:
                    self.vel_x = -self.vel_x * 0.5  # Bounce a bit on wall

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

    def create_level(self):
        self.platforms = []
        # Ground
        for x in range(0, 3000, 100):
            self.platforms.append(pygame.Rect(x, GROUND_Y, 100, HEIGHT - GROUND_Y))

        # Floating platforms
        extra = [
            (600, GROUND_Y - 120, 300, 20),
            (1000, GROUND_Y - 220, 200, 20),
            (1400, GROUND_Y - 150, 250, 20),
            (1800, GROUND_Y - 280, 300, 20),
            (2300, GROUND_Y - 100, 200, 20),
        ]
        for p in extra:
            self.platforms.append(pygame.Rect(p))

        # Goal flag
        self.goal = pygame.Rect(2800, GROUND_Y - 200, 60, 200)
        self.flag_image, _ = load_image('flag.png', scale_height=200)

    def reset(self):
        self.create_level()
        self.player = Player(self)
        self.enemies = [
            Enemy(self, 800, GROUND_Y - 70),
            Enemy(self, 1500, GROUND_Y - 220 - 70),
            Enemy(self, 2200, GROUND_Y - 70),
        ]
        self.score = 0
        self.state = 'playing'

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if self.state == 'start':
                        self.reset()
                    elif self.state in ['game_over', 'win'] and event.key == pygame.K_r:
                        self.reset()

            if self.state == 'playing':
                self.player.update(dt)
                for e in self.enemies[:]:
                    e.update(dt)
                    # Player stomps enemy
                    if self.player.vel_y > 0 and self.player.rect.bottom < e.rect.centery:
                        if self.player.rect.colliderect(e.rect):
                            self.enemies.remove(e)
                            self.player.vel_y = JUMP_STRENGTH * 0.6
                            self.score += 100
                            continue
                    # Enemy catches player
                    if self.player.rect.colliderect(e.rect):
                        self.state = 'game_over'

                # Reach goal
                if self.player.rect.colliderect(self.goal):
                    self.state = 'win'
                    self.high_score = max(self.high_score, self.score)

                # Camera follow
                camera_x = max(0, self.player.world_x - WIDTH // 3)

            self.draw(camera_x if self.state == 'playing' else 0)
            pygame.display.flip()

    def draw(self, camera_x):
        self.screen.fill(SKY_BLUE)

        if self.state == 'start':
            title = self.big_font.render("Chor Police Adventure", True, BLACK)
            prompt = self.font.render("Press any key to steal... I mean start!", True, BLACK)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 100))
            self.screen.blit(prompt, (WIDTH//2 - prompt.get_width()//2, HEIGHT//2 + 20))
            return

        # Draw platforms
        for plat in self.platforms:
            draw_rect = plat.move(-camera_x, 0)
            if draw_rect.colliderect(self.screen.get_rect()):
                pygame.draw.rect(self.screen, PLATFORM_COLOR if plat.height < 100 else GROUND_COLOR, draw_rect)

        # Draw goal
        goal_screen = self.goal.move(-camera_x, 0)
        self.screen.blit(self.flag_image, goal_screen.topleft)

        # Draw enemies
        for e in self.enemies:
            screen_x = e.world_x - camera_x
            self.screen.blit(e.image, (screen_x, e.world_y))

        # Draw player
        screen_x = self.player.world_x - camera_x
        self.screen.blit(self.player.image, (screen_x, self.player.world_y))

        # UI
        score_text = self.font.render(f"Score: {self.score}", True, BLACK)
        self.screen.blit(score_text, (10, 10))

        # End screens
        if self.state == 'game_over':
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            text = self.big_font.render("CAUGHT BY POLICE!", True, RED)
            score_line = self.font.render(f"Score: {self.score}   High: {self.high_score}", True, WHITE)
            restart = self.font.render("Press R to try escaping again", True, WHITE)
            self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 100))
            self.screen.blit(score_line, (WIDTH//2 - score_line.get_width()//2, HEIGHT//2))
            self.screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 80))

        elif self.state == 'win':
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(180)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))
            text = self.big_font.render("YOU ESCAPED!", True, (0, 200, 0))
            score_line = self.font.render(f"Final Score: {self.score}   High: {self.high_score}", True, WHITE)
            restart = self.font.render("Press R to play again", True, WHITE)
            self.screen.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//2 - 100))
            self.screen.blit(score_line, (WIDTH//2 - score_line.get_width()//2, HEIGHT//2))
            self.screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2 + 80))

if __name__ == '__main__':
    Game().run()