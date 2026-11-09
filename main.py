import pygame
from math import *
from random import *

pygame.init()
pygame.display.set_caption("Security Breach ")

WIDTH, HEIGHT = 800, 800
FPS = 60
GRID_SIZE = 25
CELL_SIZE = WIDTH // GRID_SIZE

START = (GRID_SIZE // 2, GRID_SIZE // 2)
GOAL = (GRID_SIZE - 1, GRID_SIZE - 1)

COLOR_BG = (22, 22, 29)
COLOR_WALL = (145, 150, 163)
COLOR_START = (39, 174, 96)
COLOR_GOAL = (192, 57, 43)
COLOR_CURRENT = (241, 196, 15)

screen = pygame.display.set_mode()
clock = pygame.time.Clock()

class Cell: 
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.walls = [True, True, True, True]
        self.visited = False

    def draw(self, surface):
        x_pix = self.x * CELL_SIZE
        y_pix = self.y * CELL_SIZE

        if self.walls[0]:
            pygame.draw.line(surface, COLOR_WALL, (x_pix, y_pix), (x_pix + CELL_SIZE, y_pix), 2)

        if self.walls[1]:
            pygame.draw.line(surface, COLOR_WALL, (x_pix + CELL_SIZE, y_pix), (x_pix + CELL_SIZE, y_pix + CELL_SIZE), 2)

        if self.walls[2]:
            pygame.draw.line(surface, COLOR_WALL, (x_pix + CELL_SIZE, y_pix + CELL_SIZE), (x_pix, y_pix + CELL_SIZE), 2)

        if self.walls[3]:
            pygame.draw.line(surface, COLOR_WALL, (x_pix, y_pix + CELL_SIZE), (x_pix, y_pix), 2)

def get_neighbors(cell, grid):
    neighbors = []
    directions = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    for dx, dy in directions:
        nx, ny = cell.x + dx, cell.y + dy

        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            neighbor = grid[ny][nx]

            if not neighbor.visited:
                neighbors.append(neighbor)

    return neighbors

def remove_walls(current, next_cell):
    dx = current.x - next_cell.x
    dy = current.y - next_cell.y

    if dx == -1:
        current.walls[1] = False
        next_cell.walls[3] = False
    elif dx == 1:
        current.walls[3] = False
        next_cell.walls[1] = False

    if dy == -1:
        current.walls[2] = False
        next_cell.walls[0] = False
    elif dy == 1:
        current.walls[0] = False
        next_cell.walls[2] = False

def reset_generation_state():
    grid = [
        [Cell(x, y) for x in range(GRID_SIZE)]
        for y in range(GRID_SIZE)
    ]

    stack = []
    current = grid[0][0]
    current.visited = True

    return grid, stack, current, True


def make_imperfect_maze(grid):
    walls = []

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            cell = grid[y][x]

            if x < GRID_SIZE - 1 and cell.walls[1]:
                walls.append((cell, grid[y][x + 1]))

            if y < GRID_SIZE - 1 and cell.walls[2]:
                walls.append((cell, grid[y + 1][x]))

    amount = round(len(walls) * 0.30)

    for current, next_cell in sample(walls, amount):
        remove_walls(current, next_cell)

def main():
    grid, stack, current, generating = reset_generation_state()

    running = True

    while running:
        screen.fill(COLOR_BG)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if generating:
            neighbors = get_neighbors(current, grid)

            if neighbors:
                next_cell = choice(neighbors)
                stack.append(current)
                remove_walls(current, next_cell)
                next_cell.visited = True
                current = next_cell

            elif stack:
                current = stack.pop()

            else:
                make_imperfect_maze(grid)
                generating = False
        
        for row in grid:
            for cell in row:
                cell.draw(screen)

        if generating:
            pygame.draw.rect(
                screen,
                COLOR_CURRENT,
                (current.x * CELL_SIZE + 3,
                 current.y * CELL_SIZE + 3,
                 CELL_SIZE - 6, CELL_SIZE - 6)
            )

        
        pygame.draw.rect(
            screen,
            COLOR_START,
            (START[0] * CELL_SIZE + 4,
             START[1] * CELL_SIZE + 4,
             CELL_SIZE - 8, CELL_SIZE - 8)
        )

        pygame.draw.rect(
            screen,
            COLOR_GOAL,
            (GOAL[0] * CELL_SIZE + 4,
             GOAL[1] * CELL_SIZE + 4,
             CELL_SIZE - 8, CELL_SIZE - 8)
        )

        pygame.display.flip()
        clock.tick(120 if generating else FPS)

    pygame.quit()


main()
