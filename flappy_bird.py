import pygame
import random
import sys
import math
import json
import os
from datetime import datetime

# Initialize Pygame
pygame.init()

# Constants
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600
GRAVITY = 0.25
FLAP_STRENGTH = -7
PIPE_SPEED = 3
PIPE_GAP = 150
PIPE_FREQUENCY = 1500  # milliseconds
BIRD_COLLISION_MARGIN = 0.42  # Percentage of the bird's size to use for collision
BASE_COLLISION_MARGIN = 1  # Percentage of the bird's size to use for base collision
TIP_COLLISION_MARGIN = 0.6   # Percentage of the bird's size to use for tip collision
PIPE_WIDTH = 80  # Width of the pipes in game (adjusted for better proportions)
CLOUD_SPEED = 1  # Base speed of cloud movement
CLOUD_SCALE = 0.15  # Scale factor for cloud image (1024x1024 -> ~153x153)
CLOUD_VELOCITY_FACTOR = 0.3  # How much the bird's velocity affects cloud speed
DEBUG_MODE = True  # Toggle debug visualization
HIGHSCORE_FILE = "highscore.json"  # File to store high score

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
SKY_BLUE = (135, 206, 235)  # A nice light blue for the background

# Set up the game window
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption('Flappy Bird')
clock = pygame.time.Clock()

# Load and scale bird image
bird_img = pygame.image.load('bird.png')
bird_size = 20  # Adjust this value based on your image size
bird_img = pygame.transform.scale(bird_img, (bird_size * 2, bird_size * 2))

# Load and scale pipe image
pipe_base_img = pygame.image.load('Pipe_Base.png')
pipe_tip_img = pygame.image.load('Pipe_Tip.png')

# Define standard heights for base and tip sections
PIPE_BASE_HEIGHT = 80  # Standard height for one base section
PIPE_TIP_HEIGHT = 40   # Standard height for the tip section
PIPE_BASE_WIDTH = PIPE_WIDTH -16

# Scale the pipe images to match our game dimensions exactly
pipe_base_img = pygame.transform.scale(pipe_base_img, (PIPE_BASE_WIDTH, PIPE_BASE_HEIGHT))
pipe_tip_img = pygame.transform.scale(pipe_tip_img, (PIPE_WIDTH, PIPE_TIP_HEIGHT))
pipe_base_img_flipped = pygame.transform.flip(pipe_base_img, False, True)
pipe_tip_img_flipped = pygame.transform.flip(pipe_tip_img, False, True)

# Load and scale cloud image
cloud_img = pygame.image.load('cloud.png')
cloud_width = int(cloud_img.get_width() * CLOUD_SCALE)
cloud_height = int(cloud_img.get_height() * CLOUD_SCALE)
cloud_img = pygame.transform.scale(cloud_img, (cloud_width, cloud_height))

# Bird properties
bird_x = WINDOW_WIDTH // 3
bird_y = WINDOW_HEIGHT // 2
bird_velocity = 0

# Pipe properties
pipes = []
last_pipe = pygame.time.get_ticks()

# Cloud properties
class Cloud:
    def __init__(self):
        self.x = WINDOW_WIDTH
        self.y = random.randint(0, WINDOW_HEIGHT // 2)  # Only in upper half
        self.base_speed = CLOUD_SPEED * random.uniform(0.5, 1.5)  # Varied base speeds
    
    def update(self, bird_velocity):
        # Add bird's velocity to cloud speed (opposite direction)
        current_speed = self.base_speed + (abs(bird_velocity) * CLOUD_VELOCITY_FACTOR)
        self.x -= current_speed 
        return self.x > -cloud_width  # Return True if cloud is still on screen

clouds = [Cloud() for _ in range(3)]  # Start with 3 clouds

# Game state
score = 0
game_active = False  # Start with game inactive
game_started = False  # New state to track if game has ever started
debug_mode = True  # Toggle debug visualization
attempts = 0  # Track number of attempts
font = pygame.font.Font(None, 36)
small_font = pygame.font.Font(None, 24)  # Smaller font for additional info

def load_highscore():
    """Load high score from file"""
    try:
        if os.path.exists(HIGHSCORE_FILE):
            with open(HIGHSCORE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('score', 0)
    except:
        return 0
    return 0

def save_highscore(new_score):
    """Save high score to file"""
    try:
        data = {'score': new_score}
        with open(HIGHSCORE_FILE, 'w') as f:
            json.dump(data, f)
    except:
        pass  # Silently fail if we can't save the score

# Initialize high score
high_score = load_highscore()

def create_pipe():
    """Create a new pipe with random height"""
    gap_y = random.randint(100, WINDOW_HEIGHT - 100)
    top_height = gap_y - PIPE_GAP // 2
    bottom_height = WINDOW_HEIGHT - (gap_y + PIPE_GAP // 2)
    
    # Create pipe objects with their heights
    top_pipe = {
        'rect': pygame.Rect(WINDOW_WIDTH, 0, PIPE_WIDTH, top_height),
        'height': top_height
    }
    bottom_pipe = {
        'rect': pygame.Rect(WINDOW_WIDTH, gap_y + PIPE_GAP // 2, 
                          PIPE_WIDTH, bottom_height),
        'height': bottom_height
    }
    return {'top': top_pipe, 'bottom': bottom_pipe}

def draw_bird():
    """Draw the bird using the loaded image"""
    # Calculate bird rotation based on velocity
    rotation = -bird_velocity * 2  # Adjust multiplier to change rotation sensitivity
    rotated_bird = pygame.transform.rotate(bird_img, rotation)
    
    # Get the rect of the rotated bird for proper positioning
    bird_rect = rotated_bird.get_rect(center=(bird_x, int(bird_y)))
    screen.blit(rotated_bird, bird_rect)
    return bird_rect  # Return the rect for collision detection

def get_collision_circle(bird_rect):
    """Create a collision circle based on the BIRD_COLLISION_MARGIN"""
    # Calculate the radius of the collision circle
    radius = min(bird_rect.width, bird_rect.height) * BIRD_COLLISION_MARGIN / 2
    
    # Get the center of the bird
    center_x = bird_rect.centerx
    center_y = bird_rect.centery
    
    return (center_x, center_y, radius)

def draw_repeating_pipe(pipe, is_top):
    """Draw a pipe with repeating base texture and tip"""
    base_img = pipe_base_img if not is_top else pipe_base_img_flipped
    tip_img = pipe_tip_img if not is_top else pipe_tip_img_flipped
    
    # Calculate how many complete base sections we need
    remaining_height = pipe['height'] - PIPE_TIP_HEIGHT
    num_repeats = math.ceil(remaining_height / PIPE_BASE_HEIGHT)
    
    # Calculate x offset to center the base image
    base_x_offset = (PIPE_WIDTH - PIPE_BASE_WIDTH) // 2  # 5 pixels on each side
    
    if is_top:
        # Draw the base sections from bottom up
        for i in range(num_repeats):
            y_pos = pipe['rect'].bottom - PIPE_TIP_HEIGHT - ((i + 1) * PIPE_BASE_HEIGHT)
            if y_pos + PIPE_BASE_HEIGHT > 0 and y_pos < WINDOW_HEIGHT:
                screen.blit(base_img, (pipe['rect'].x + base_x_offset, y_pos))
        
        # Draw tip at the bottom of the top pipe
        tip_y = pipe['rect'].bottom - PIPE_TIP_HEIGHT
    else:
        # Draw the base sections from top down
        for i in range(num_repeats):
            y_pos = pipe['rect'].y + PIPE_TIP_HEIGHT + (i * PIPE_BASE_HEIGHT)
            if y_pos + PIPE_BASE_HEIGHT > 0 and y_pos < WINDOW_HEIGHT:
                screen.blit(base_img, (pipe['rect'].x + base_x_offset, y_pos))
        
        # Draw tip at the top of the bottom pipe
        tip_y = pipe['rect'].y
    
    # Draw the tip
    if tip_y + PIPE_TIP_HEIGHT > 0 and tip_y < WINDOW_HEIGHT:
        screen.blit(tip_img, (pipe['rect'].x, tip_y))

def draw_pipes():
    """Draw all pipes"""
    for pipe in pipes:
        # Draw top pipe with repeating texture
        draw_repeating_pipe(pipe['top'], True)
        # Draw bottom pipe with repeating texture
        draw_repeating_pipe(pipe['bottom'], False)
        
        # Draw debug colliders if debug mode is on
        if debug_mode:
            # Draw collision rectangles in red
            pygame.draw.rect(screen, RED, pipe['top']['rect'], 1)
            pygame.draw.rect(screen, RED, pipe['bottom']['rect'], 1)

def check_collision(bird_rect):
    """Check if bird collides with pipes or boundaries"""
    # Get the collision circle
    center_x, center_y, radius = get_collision_circle(bird_rect)
    
    # Optional: Draw the collision circle for debugging
    if debug_mode:
        pygame.draw.circle(screen, RED, (center_x, center_y), radius, 1)
    
    # Check collision with pipes
    for pipe in pipes:
        # Check collision with top pipe
        if (center_x + radius > pipe['top']['rect'].left and 
            center_x - radius < pipe['top']['rect'].right and
            center_y - radius < pipe['top']['rect'].bottom):
            return True
        
        # Check collision with bottom pipe
        if (center_x + radius > pipe['bottom']['rect'].left and 
            center_x - radius < pipe['bottom']['rect'].right and
            center_y + radius > pipe['bottom']['rect'].top):
            return True
    
    # Check collision with boundaries
    if center_y - radius <= 0 or center_y + radius >= WINDOW_HEIGHT:
        return True
    
    return False

def reset_game():
    """Reset game state"""
    global bird_y, bird_velocity, pipes, score, game_active, game_started
    bird_y = WINDOW_HEIGHT // 2
    bird_velocity = 0
    pipes = []
    score = 0
    game_active = True
    game_started = True

def update_score():
    """Update the score and high score"""
    global score, high_score
    score += 1
    if score > high_score:
        high_score = score
        save_highscore(high_score)

def draw_score_info(x, y, is_game_over=False):
    """Draw score information at the specified position"""
    score_text = font.render(f'Score: {score}', True, BLACK)
    high_score_text = font.render(f'High Score: {high_score}', True, BLACK)
    
    if is_game_over:
        # Center align for game over screen
        score_rect = score_text.get_rect(centerx=x, centery=y)
        high_score_rect = high_score_text.get_rect(centerx=x, centery=y + 40)
    else:
        # Left align for in-game display
        score_rect = score_text.get_rect(topleft=(x, y))
        high_score_rect = high_score_text.get_rect(topleft=(x, y + 30))
    
    screen.blit(score_text, score_rect)
    screen.blit(high_score_text, high_score_rect)

def draw_transparent_box(x, y, width, height, alpha=178):  # 178 is ~70% of 255
    """Draw a semi-transparent white box"""
    # Create a surface for the box
    box_surface = pygame.Surface((width, height))
    box_surface.fill(WHITE)
    # Set the alpha value (transparency)
    box_surface.set_alpha(alpha)
    # Get the rect for positioning
    box_rect = box_surface.get_rect(center=(x, y))
    # Draw the box
    screen.blit(box_surface, box_rect)
    return box_rect

def draw_start_screen():
    """Draw the start screen with transparent box"""
    # Calculate the size needed for the box
    box_width = 400
    box_height = 200
    box_x = WINDOW_WIDTH // 2
    box_y = WINDOW_HEIGHT // 2
    
    # Draw the transparent box
    draw_transparent_box(box_x, box_y, box_width, box_height)
    
    # Calculate vertical spacing
    line_height = 40
    start_y = box_y - (line_height * 2)  # Start 2 lines up from center
    
    # Draw the text
    title_text = font.render('Flappy Bird', True, BLACK)
    start_text = font.render('Press SPACE to start', True, BLACK)
    escape_text = font.render('Press ESC to quit', True, BLACK)
    score_text = font.render(f'Score: {score}', True, BLACK)
    high_score_text = font.render(f'High Score: {high_score}', True, BLACK)
    
    # Position all text elements with consistent spacing
    texts = [
        (title_text, start_y),
        (start_text, start_y + line_height),
        (escape_text, start_y + line_height * 2),
        (score_text, start_y + line_height * 3),
        (high_score_text, start_y + line_height * 4)
    ]
    
    # Draw main text elements
    for text, y_pos in texts:
        text_rect = text.get_rect(center=(box_x, y_pos))
        screen.blit(text, text_rect)

def draw_game_over_screen():
    """Draw the game over screen with transparent box"""
    # Calculate the size needed for the box
    box_width = 400
    box_height = 250
    box_x = WINDOW_WIDTH // 2
    box_y = WINDOW_HEIGHT // 2
    
    # Draw the transparent box
    draw_transparent_box(box_x, box_y, box_width, box_height)
    
    # Calculate vertical spacing
    line_height = 40
    start_y = box_y - (line_height * 2)  # Start 2 lines up from center
    
    # Draw the text
    game_over_text = font.render('Game Over!', True, BLACK)
    restart_text = font.render('Press SPACE to restart', True, BLACK)
    escape_text = font.render('Press ESC to quit', True, BLACK)
    score_text = font.render(f'Score: {score}', True, BLACK)
    high_score_text = font.render(f'High Score: {high_score}', True, BLACK)
    
    # Position all text elements with consistent spacing
    texts = [
        (game_over_text, start_y),
        (restart_text, start_y + line_height),
        (escape_text, start_y + line_height * 2),
        (score_text, start_y + line_height * 3),
        (high_score_text, start_y + line_height * 4)
    ]
    
    # Draw main text elements
    for text, y_pos in texts:
        text_rect = text.get_rect(center=(box_x, y_pos))
        screen.blit(text, text_rect)

# Game loop
while True:
    current_time = pygame.time.get_ticks()
    
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == pygame.K_d:
                debug_mode = not debug_mode
            if event.key == pygame.K_SPACE:
                if not game_started:
                    reset_game()
                elif game_active:
                    bird_velocity = FLAP_STRENGTH
                else:
                    reset_game()

    # Update clouds
    if not game_active:
        clouds = [cloud for cloud in clouds if cloud.update(PIPE_SPEED)]
    else:
        clouds = [cloud for cloud in clouds if cloud.update(PIPE_SPEED * 3)]
    while len(clouds) < 3:  # Maintain 3 clouds
        clouds.append(Cloud())

    if game_active:
        # Update bird position
        bird_velocity += GRAVITY
        bird_y += bird_velocity

        # Create new pipes
        if current_time - last_pipe > PIPE_FREQUENCY:
            pipes.append(create_pipe())
            last_pipe = current_time

        # Update pipes
        for pipe in pipes[:]:
            pipe['top']['rect'].x -= PIPE_SPEED
            pipe['bottom']['rect'].x -= PIPE_SPEED
            
            # Remove pipes that are off screen and update score
            if pipe['top']['rect'].right < 0:
                pipes.remove(pipe)
                update_score()

    # Draw everything
    screen.fill(SKY_BLUE)  # Fill with sky blue background
    
    # Draw clouds
    for cloud in clouds:
        screen.blit(cloud_img, (cloud.x, cloud.y))
    
    if not game_started:
        draw_start_screen()
    else:
        bird_rect = draw_bird()  # Get the bird's rect from drawing
        draw_pipes()
        
        # Check for collisions using the bird's actual rect
        if game_active and check_collision(bird_rect):
            game_active = False
        
        # Draw scores during gameplay
        draw_score_info(10, 10)
        
        # Draw game over message
        if not game_active:
            draw_game_over_screen()

    pygame.display.update()
    clock.tick(60) 