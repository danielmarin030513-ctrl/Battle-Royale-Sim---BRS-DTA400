import pygame
import random
import math

pygame.init()

width = 800
height = 600

screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("Battle Royale Simulator")

clock = pygame.time.Clock()

nummber_o_players = 30
player_radius = 8
speed = 2
players = []

for i in range(nummber_o_players):
    x = random.randint(player_radius, width - player_radius)
    y = random.randint(player_radius, height - player_radius)
    
    angle = random.uniform(0,2 * math.pi)
    
    players.append({
        "x": x,
        "y": y,
        "angle": angle,
        "hp": 100
    })

running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
    screen.fill((40, 80, 40))
    
    for player in players:
        
        player["x"] += math.cos(player["angle"]) * speed
        player["y"] += math.sin(player["angle"]) * speed
        
        if player["x"] <= player_radius or player["x"] >= width -player_radius:
            player["angle"] = math.pi - player["angle"]
            player["x"] = max(player_radius, min(width - player_radius, player["x"]))
            
        if player["y"] <= player_radius or player["y"] >= height - player_radius:
            player["angle"] = -player["angle"]
            player["y"] = max(player_radius, min(height - player_radius, player["y"]))
            
        pygame.draw.circle(
            screen,
            (255, 50, 50),
            (int(player["x"]), int(player["y"])),
            player_radius
        )
    
    pygame.display.flip()
    clock.tick(60)
    
pygame.quit()