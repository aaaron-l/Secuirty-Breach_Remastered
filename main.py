import asyncio
import pygame
from math import *
from random import *
from collections import *
import heapq

pygame.init()
pygame.display.set_caption("Security Breach")

# constants

WIDTH, HEIGHT = 1000, 1000
FPS = 60

GRID_SIZE = 25
CELL_SIZE = 107

MAP_WIDTH = GRID_SIZE * CELL_SIZE
MAP_HEIGHT = GRID_SIZE * CELL_SIZE

WALL_THICKNESS = 13

GOAL = (GRID_SIZE // 2, GRID_SIZE // 2)

EDGES = (
    [(x, 0) for x in range(GRID_SIZE)] +
    [(x, GRID_SIZE - 1) for x in range(GRID_SIZE)] +
    [(0, y) for y in range(1, GRID_SIZE - 1)] +
    [(GRID_SIZE - 1, y) for y in range(1, GRID_SIZE - 1)]
)

COLOR_BG = (22, 22, 29)

PLAYER_SPEED = 320
PLAYER_SIZE = 80
PLAYER_RADIUS = 24
ANIMATION_SPEED = 10

BASIC_SPEED = 150
HUNTER_SPEED = 210
AMBUSHER_SPEED = 195
INTERCEPTOR_SPEED = 200
BLOCKER_SPEED = 500

PLAYER_VISION = 220
ENEMY_VISION = 190

ELITE_WARNING_TIME = 3

screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

font = pygame.font.SysFont("arial", 36)
small_font = pygame.font.SysFont("arial", 24)
large_font = pygame.font.SysFont("arial", 72)


# images

FLOOR_IMAGE = pygame.image.load("background.png").convert()
FLOOR_IMAGE = pygame.transform.scale(FLOOR_IMAGE, (CELL_SIZE, CELL_SIZE))

DIAMOND_IMAGE = pygame.image.load("diamond.png").convert_alpha()
DIAMOND_IMAGE = pygame.transform.scale(
    DIAMOND_IMAGE, (CELL_SIZE, CELL_SIZE)
)

KEY_IMAGE = pygame.image.load("key.png").convert_alpha()
KEY_IMAGE = pygame.transform.scale(KEY_IMAGE, (24, 24))

DOOR_IMAGE = pygame.image.load("door.png").convert_alpha()
DOOR_IMAGE = pygame.transform.scale(
    DOOR_IMAGE, (CELL_SIZE, WALL_THICKNESS * 2)
)


# maze generation

class Cell:
    WALL_IMAGE = pygame.image.load("wall.png").convert_alpha()
    WALL_IMAGE = pygame.transform.scale(
        WALL_IMAGE, (CELL_SIZE, WALL_THICKNESS)
    )
    WALL_IMAGE_VERTICAL = pygame.transform.rotate(WALL_IMAGE, 90)

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.walls = [True, True, True, True]
        self.visited = False

    def draw(self, surface, camera_x=0, camera_y=0):
        x_pix = self.x * CELL_SIZE - camera_x
        y_pix = self.y * CELL_SIZE - camera_y

        if self.walls[0]:
            surface.blit(self.WALL_IMAGE, (x_pix, y_pix))

        if self.walls[1]:
            surface.blit(
                self.WALL_IMAGE_VERTICAL,
                (x_pix + CELL_SIZE - WALL_THICKNESS, y_pix)
            )

        if self.walls[2]:
            surface.blit(
                self.WALL_IMAGE,
                (x_pix, y_pix + CELL_SIZE - WALL_THICKNESS)
            )

        if self.walls[3]:
            surface.blit(self.WALL_IMAGE_VERTICAL, (x_pix, y_pix))


# code from classwork

def get_neighbors(cell, grid):
    neighbors = []

    for dx, dy in [(0, -1), (1, 0), (0, 1), (-1, 0)]:
        nx = cell.x + dx
        ny = cell.y + dy

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


# shared edge between each cell gets its individual dictionary key

def get_edge_key(cell_a, cell_b):
    return tuple(sorted((cell_a, cell_b)))


# removes 30% of walls that are not next to doors

def make_imperfect_maze(grid, door_edges):
    walls = []

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            cell = grid[y][x]

            if x < GRID_SIZE - 1 and cell.walls[1]:
                walls.append(((x, y), (x + 1, y)))

            if y < GRID_SIZE - 1 and cell.walls[2]:
                walls.append(((x, y), (x, y + 1)))

    safe_walls = []

    for a, b in walls:
        edge = get_edge_key(a, b)

        if edge in door_edges:
            continue

        adjacent_to_door = False

        for door_edge in door_edges:
            if a in door_edge or b in door_edge:
                adjacent_to_door = True
                break

        if not adjacent_to_door:
            safe_walls.append((a, b))

    remove_count = int(len(safe_walls) * 0.30)

    for a, b in sample(safe_walls, remove_count):
        x1, y1 = a
        x2, y2 = b

        if x1 == x2:
            grid[y1][x1].walls[2] = False
            grid[y2][x2].walls[0] = False
        else:
            grid[y1][x1].walls[1] = False
            grid[y2][x2].walls[3] = False


def generate_maze(start):
    grid = [
        [Cell(x, y) for x in range(GRID_SIZE)]
        for y in range(GRID_SIZE)
    ]

    # DFS

    stack = []
    current = grid[start[1]][start[0]]
    current.visited = True

    keys = []
    doors = []

    # markov transition for key-door generation

    state = "key"
    key_probability = 0
    door_probability = 0
    pending_keys = []

    while True:
        neighbors = get_neighbors(current, grid)

        if neighbors:
            next_cell = choice(neighbors)
            stack.append(current)
            remove_walls(current, next_cell)

            if state == "key":
                key_probability = min(100, key_probability + 3)

                if random() < key_probability / 100:
                    key = generate_key(current)
                    keys.append(key)
                    pending_keys.append(key)
                    state = "door"
                    door_probability = 0

            elif state == "door":
                key_probability = min(100, key_probability + .5)

                if random() < key_probability / 100:
                    key = generate_key(current)
                    keys.append(key)
                    pending_keys.append(key)
                    key_probability = 0

                door_probability = min(100, door_probability + 5)

                if random() < door_probability / 100:
                    door = create_door(
                        (current.x, current.y),
                        (next_cell.x, next_cell.y)
                    )

                    doors.append(door)

                    for key in pending_keys:
                        key.door = door

                    pending_keys.clear()
                    state = "key"
                    key_probability = 0
                    door_probability = 0

            next_cell.visited = True
            current = next_cell

        elif stack:
            current = stack.pop()

        else:
            break

    door_edges = {door.edge for door in doors}
    make_imperfect_maze(grid, door_edges)

    return grid, keys, doors


# keys and doors

def get_direction_edge(cell_x, cell_y, direction):
    if direction == "up":
        neighbor = (cell_x, cell_y - 1)
    elif direction == "right":
        neighbor = (cell_x + 1, cell_y)
    elif direction == "down":
        neighbor = (cell_x, cell_y + 1)
    else:
        neighbor = (cell_x - 1, cell_y)

    return get_edge_key((cell_x, cell_y), neighbor)


def get_cell(x, y):
    return int(x // CELL_SIZE), int(y // CELL_SIZE)


def cell_center(cell):
    return (
        cell[0] * CELL_SIZE + CELL_SIZE / 2,
        cell[1] * CELL_SIZE + CELL_SIZE / 2
    )


class Keys:
    def __init__(self, pos):
        self.pos = pygame.math.Vector2(pos)
        self.image = KEY_IMAGE
        self.door = None

    def draw(self, surface, camera_x=0, camera_y=0):
        rect = self.image.get_rect(
            center=(self.pos.x - camera_x, self.pos.y - camera_y)
        )
        surface.blit(self.image, rect)


class Doors:
    def __init__(self, pos, edge, vertical=False):
        self.pos = pygame.math.Vector2(pos)
        self.edge = edge
        self.locked = True
        self.image = DOOR_IMAGE

        if vertical:
            self.image = pygame.transform.rotate(self.image, 90)

    def draw(self, surface, camera_x=0, camera_y=0):
        if not self.locked:
            return

        rect = self.image.get_rect(
            center=(self.pos.x - camera_x, self.pos.y - camera_y)
        )
        surface.blit(self.image, rect)


def create_door(cell_a, cell_b):
    x, y = cell_a
    nx, ny = cell_b
    edge = get_edge_key(cell_a, cell_b)

    if nx > x:
        pos = ((x + 1) * CELL_SIZE, y * CELL_SIZE + CELL_SIZE / 2)
        vertical = True
    elif nx < x:
        pos = (x * CELL_SIZE, y * CELL_SIZE + CELL_SIZE / 2)
        vertical = True
    elif ny > y:
        pos = (x * CELL_SIZE + CELL_SIZE / 2, (y + 1) * CELL_SIZE)
        vertical = False
    else:
        pos = (x * CELL_SIZE + CELL_SIZE / 2, y * CELL_SIZE)
        vertical = False

    return Doors(pos, edge, vertical)


def generate_key(cell):
    pos = (
        cell.x * CELL_SIZE + CELL_SIZE / 2,
        cell.y * CELL_SIZE + CELL_SIZE / 2
    )
    return Keys(pos)


def collect_keys(player, keys):
    for key in keys[:]:
        distance = hypot(
            player.x - key.pos.x,
            player.y - key.pos.y
        )

        if distance <= player.radius + 12:
            keys.remove(key)

            if key.door is not None:
                key.door.locked = False


# pathfinding

def get_open_neighbors(cell, grid):
    x, y = cell
    result = []

    directions = [
        (0, -1, 0),
        (1, 0, 1),
        (0, 1, 2),
        (-1, 0, 3)
    ]

    for dx, dy, wall_index in directions:
        nx = x + dx
        ny = y + dy

        if 0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE:
            if not grid[y][x].walls[wall_index]:
                result.append((nx, ny))

    return result


def a_star(start, goal, grid):
    if start == goal:
        return [start]

    frontier = [(0, start)]
    came_from = {start: None}
    cost = {start: 0}

    while frontier:
        _, current = heapq.heappop(frontier)

        if current == goal:
            break

        for neighbor in get_open_neighbors(current, grid):
            new_cost = cost[current] + 1

            if neighbor not in cost or new_cost < cost[neighbor]:
                cost[neighbor] = new_cost

                priority = (
                    new_cost +
                    abs(goal[0] - neighbor[0]) +
                    abs(goal[1] - neighbor[1])
                )

                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current

    path = []
    current = goal

    while current is not None:
        path.append(current)
        current = came_from[current]

    return path[::-1]


def get_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


# player

class Entity:
    def __init__(self, x, y, speed, radius):
        self.x = x
        self.y = y
        self.speed = speed
        self.radius = radius


class Player(Entity):
    def __init__(self, x, y):
        px, py = cell_center((x, y))
        super().__init__(px, py, PLAYER_SPEED, PLAYER_RADIUS)

        self.direction = "down"

        self.animations = {
            "right": [],
            "up": [],
            "down": [],
            "left": []
        }

        for i in range(1, 4):
            image = pygame.image.load(f"right_{i}.png").convert_alpha()
            image = pygame.transform.scale(image, (PLAYER_SIZE, PLAYER_SIZE))
            self.animations["right"].append(image)
            self.animations["left"].append(
                pygame.transform.flip(image, True, False)
            )

        for i in range(1, 4):
            image = pygame.image.load(f"up_{i}.png").convert_alpha()
            image = pygame.transform.scale(image, (PLAYER_SIZE, PLAYER_SIZE))
            self.animations["up"].append(image)

        for i in range(1, 4):
            image = pygame.image.load(f"down_{i}.png").convert_alpha()
            image = pygame.transform.scale(image, (PLAYER_SIZE, PLAYER_SIZE))
            self.animations["down"].append(image)

        self.frame = 0
        self.animation_timer = 0

        self.history = deque(maxlen=64)
        self.history.append((x, y))

        self.intersection_history = deque(maxlen=30)

    def get_movement(self):
        keys = pygame.key.get_pressed()
        dx = 0
        dy = 0

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1

        if dx and dy:
            dx *= 1 / sqrt(2)
            dy *= 1 / sqrt(2)

        return dx, dy

    def can_move(self, x, y, direction, grid, doors, escape_mode, blockers):
        cell_x, cell_y = get_cell(self.x, self.y)

        if not (0 <= cell_x < GRID_SIZE and 0 <= cell_y < GRID_SIZE):
            return escape_mode

        cell = grid[cell_y][cell_x]

        if direction == "right":
            boundary = (cell_x + 1) * CELL_SIZE

            if x + self.radius > boundary - WALL_THICKNESS / 2:
                edge = get_direction_edge(cell_x, cell_y, direction)
                door = doors.get(edge)

                if cell.walls[1] or (door and door.locked):
                    return False

        elif direction == "left":
            boundary = cell_x * CELL_SIZE

            if x - self.radius < boundary + WALL_THICKNESS / 2:
                edge = get_direction_edge(cell_x, cell_y, direction)
                door = doors.get(edge)

                if cell.walls[3] or (door and door.locked):
                    return False

        elif direction == "down":
            boundary = (cell_y + 1) * CELL_SIZE

            if y + self.radius > boundary - WALL_THICKNESS / 2:
                edge = get_direction_edge(cell_x, cell_y, direction)
                door = doors.get(edge)

                if cell.walls[2] or (door and door.locked):
                    return False

        elif direction == "up":
            boundary = cell_y * CELL_SIZE

            if y - self.radius < boundary + WALL_THICKNESS / 2:
                edge = get_direction_edge(cell_x, cell_y, direction)
                door = doors.get(edge)

                if cell.walls[0] or (door and door.locked):
                    return False

        for blocker in blockers:
            if circle_rect_collision(x, y, self.radius, blocker.rect):
                return False

        return True

    def update(self, grid, dt, doors, escape_mode, blockers):
        dx, dy = self.get_movement()
        moving = dx != 0 or dy != 0

        if dx != 0:
            self.direction = "right" if dx > 0 else "left"
            movement = dx * self.speed * dt
            steps = max(1, ceil(abs(movement) / 2))
            step = movement / steps

            for _ in range(steps):
                if self.can_move(
                    self.x + step, self.y, self.direction,
                    grid, doors, escape_mode, blockers
                ):
                    self.x += step
                else:
                    break

        if dy != 0:
            self.direction = "down" if dy > 0 else "up"
            movement = dy * self.speed * dt
            steps = max(1, ceil(abs(movement) / 2))
            step = movement / steps

            for _ in range(steps):
                if self.can_move(
                    self.x, self.y + step, self.direction,
                    grid, doors, escape_mode, blockers
                ):
                    self.y += step
                else:
                    break

        new_cell = get_cell(self.x, self.y)

        if (
            0 <= new_cell[0] < GRID_SIZE and
            0 <= new_cell[1] < GRID_SIZE
        ):
            if self.history[-1] != new_cell:
                self.history.append(new_cell)

                if len(self.history) >= 3:
                    previous = self.history[-2]
                    incoming_cell = self.history[-3]

                    if len(get_open_neighbors(previous, grid)) >= 3:
                        incoming = (
                            previous[0] - incoming_cell[0],
                            previous[1] - incoming_cell[1]
                        )

                        outgoing = (
                            new_cell[0] - previous[0],
                            new_cell[1] - previous[1]
                        )

                        self.intersection_history.append(
                            (previous, incoming, outgoing)
                        )

        if moving:
            self.animation_timer += dt

            if self.animation_timer >= 1 / ANIMATION_SPEED:
                self.animation_timer = 0
                self.frame = (self.frame + 1) % 3
        else:
            self.frame = 0
            self.animation_timer = 0

    def draw(self, surface, camera_x, camera_y):
        image = self.animations[self.direction][self.frame]

        rect = image.get_rect(
            center=(self.x - camera_x, self.y - camera_y)
        )

        surface.blit(image, rect)


def circle_rect_collision(x, y, radius, rect):
    closest_x = max(rect.left, min(x, rect.right))
    closest_y = max(rect.top, min(y, rect.bottom))

    return hypot(x - closest_x, y - closest_y) < radius


# ai movement

class NPC(Entity):
    def __init__(self, cell, speed, radius, kind):
        x, y = cell_center(cell)
        super().__init__(x, y, speed, radius)

        self.cell = cell
        self.path = []
        self.path_index = 0
        self.kind = kind

        self.rect = pygame.Rect(
            0, 0, CELL_SIZE * 0.55, CELL_SIZE * 0.55
        )

        self.rect.center = (round(x), round(y))

        self.animations = {
            "right": [],
            "left": [],
            "up": [],
            "down": []
        }

        for i in range(1, 4):
            image = pygame.image.load(
                f"{kind}r{i}.png"
            ).convert_alpha()

            image = pygame.transform.scale(
                image, (PLAYER_SIZE, PLAYER_SIZE)
            )

            self.animations["right"].append(image)
            self.animations["left"].append(
                pygame.transform.flip(image, True, False)
            )

        for i in range(1, 4):
            image = pygame.image.load(
                f"{kind}u{i}.png"
            ).convert_alpha()

            image = pygame.transform.scale(
                image, (PLAYER_SIZE, PLAYER_SIZE)
            )

            self.animations["up"].append(image)

        for i in range(1, 4):
            image = pygame.image.load(
                f"{kind}d{i}.png"
            ).convert_alpha()

            image = pygame.transform.scale(
                image, (PLAYER_SIZE, PLAYER_SIZE)
            )

            self.animations["down"].append(image)

        self.direction = "down"
        self.frame = 0
        self.animation_timer = 0

        self.repath_timer = 0
        self.markov_timer = 0

        self.previous_cell = None

    def set_path(self, target, grid):
        start = get_cell(self.x, self.y)

        if not (0 <= start[0] < GRID_SIZE and 0 <= start[1] < GRID_SIZE):
            return

        path = a_star(start, target, grid)

        if path:
            self.path = path
            self.path_index = 1 if len(path) > 1 else 0

    def move(self, dt):
        if not self.path or self.path_index >= len(self.path):
            self.frame = 0
            self.animation_timer = 0
            return

        target_cell = self.path[self.path_index]
        target_x, target_y = cell_center(target_cell)

        dx = target_x - self.x
        dy = target_y - self.y

        if abs(dx) > abs(dy):
            self.direction = "right" if dx > 0 else "left"
        elif dy != 0:
            self.direction = "down" if dy > 0 else "up"

        distance = hypot(dx, dy)
        movement = self.speed * dt

        if distance <= movement:
            self.x = target_x
            self.y = target_y
            self.cell = target_cell
            self.path_index += 1

        elif distance > 0:
            self.x += dx / distance * movement
            self.y += dy / distance * movement

        self.rect.center = (round(self.x), round(self.y))

        self.animation_timer += dt

        if self.animation_timer >= 1 / ANIMATION_SPEED:
            self.animation_timer = 0
            self.frame = (self.frame + 1) % 3

    def draw(self, surface, camera_x, camera_y):
        image = self.animations[self.direction][self.frame]

        rect = image.get_rect(
            center=(self.x - camera_x, self.y - camera_y)
        )

        surface.blit(image, rect)

# basic npc uses modified dfs to explore the maze
def move_basic_npc(npc, grid, doors_by_edge, dt):
    if not npc.path or npc.path_index >= len(npc.path):
        current = get_cell(npc.x, npc.y)

        neighbors = get_open_neighbors(current, grid)

        # removes neighbors blocked by locked doors
        available = []

        for neighbor in neighbors:
            edge = get_edge_key(current, neighbor)
            door = doors_by_edge.get(edge)

            if door and door.locked:
                continue

            if neighbor != npc.previous_cell:
                available.append(neighbor)

        if available:
            target = choice(available)

        # backtracks when there are no other available cells
        elif npc.previous_cell is not None:
            target = npc.previous_cell

        else:
            return

        npc.previous_cell = current

        npc.path = [current, target]
        npc.path_index = 1

    npc.move(dt)


# spawns enemies at least 5 manhattan distance away from player

def choose_spawn_cells(player_cell, amount):
    candidates = []

    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            distance = abs(x - player_cell[0]) + abs(y - player_cell[1])

            if distance >= 5:
                candidates.append((x, y))

    shuffle(candidates)

    return candidates[:amount]


def create_basic_npc(player):
    player_cell = get_cell(player.x, player.y)
    spawn_cell = choose_spawn_cells(player_cell, 1)[0]

    return NPC(
        spawn_cell,
        BASIC_SPEED,
        22,
        "basic"
    )


def create_npcs(round_number, player, grid):
    spawn = get_cell(player.x, player.y)

    if round_number == 1:
        kinds = ["hunter"]
    elif round_number == 2:
        kinds = ["hunter", "ambusher"]
    elif round_number == 3:
        kinds = ["hunter", "ambusher", "interceptor"]
    elif round_number < 10:
        kinds = ["hunter", "ambusher", "interceptor", "blocker"]
    else:
        kinds = [
            "hunter", "ambusher", "interceptor",
            "blocker", "blocker", "blocker"
        ]

    spawn_cells = choose_spawn_cells(spawn, len(kinds))

    speeds = {
        "hunter": HUNTER_SPEED,
        "ambusher": AMBUSHER_SPEED,
        "interceptor": INTERCEPTOR_SPEED,
        "blocker": BLOCKER_SPEED
    }

    radii = {
        "hunter": 25,
        "ambusher": 23,
        "interceptor": 23,
        "blocker": 0
    }

    return [
        NPC(cell, speeds[kind], radii[kind], kind)
        for cell, kind in zip(spawn_cells, kinds)
    ]


# ambusher and interceptor targeting

def get_path_ahead(player, steps, grid, doors_by_edge):
    directions = {
        "up": (0, -1, 0),
        "right": (1, 0, 1),
        "down": (0, 1, 2),
        "left": (-1, 0, 3)
    }

    dx, dy, wall_index = directions[player.direction]
    current = get_cell(player.x, player.y)

    for _ in range(steps):
        x, y = current
        neighbor = (x + dx, y + dy)

        if not (0 <= neighbor[0] < GRID_SIZE and 0 <= neighbor[1] < GRID_SIZE):
            break

        if grid[y][x].walls[wall_index]:
            break

        edge = get_edge_key(current, neighbor)
        door = doors_by_edge.get(edge)

        if door and door.locked:
            break

        current = neighbor

    return current


# blocker markov model

def find_next_intersection(player_cell, heading, grid):
    current = player_cell
    previous = None

    while True:
        neighbors = get_open_neighbors(current, grid)

        if len(neighbors) >= 3:
            if previous is None:
                return current, heading

            incoming = (
                current[0] - previous[0],
                current[1] - previous[1]
            )

            return current, incoming

        forward = [
            neighbor for neighbor in neighbors
            if neighbor != previous
        ]

        if not forward:
            if previous is None:
                return None, None

            return None, None

        next_cell = max(
            forward,
            key=lambda cell: (
                (cell[0] - current[0]) * heading[0] +
                (cell[1] - current[1]) * heading[1]
            )
        )

        previous = current
        current = next_cell

def predict_intersection_exit(intersection, incoming, history, grid):
    local_choices = defaultdict(float)
    global_choices = defaultdict(float)

    for i, (recorded_intersection, recorded_incoming, outgoing) in enumerate(history):
        weight = i + 1

        global_choices[outgoing] += weight

        if (
            recorded_intersection == intersection and
            recorded_incoming == incoming
        ):
            local_choices[outgoing] += weight

    available = [
        (
            neighbor[0] - intersection[0],
            neighbor[1] - intersection[1]
        )
        for neighbor in get_open_neighbors(intersection, grid)
    ]

    choices = {
        direction: count
        for direction, count in local_choices.items()
        if direction in available
    }

    if not choices:
        choices = {
            direction: count
            for direction, count in global_choices.items()
            if direction in available
        }

    if choices:
        best_count = max(choices.values())

        best_directions = [
            direction
            for direction, count in choices.items()
            if count == best_count
        ]

        return choice(best_directions)

    if incoming in available:
        return incoming

    return choice(available) if available else None


def get_blocker_target(player, grid):
    player_cell = get_cell(player.x, player.y)

    directions = {
        "up": (0, -1),
        "right": (1, 0),
        "down": (0, 1),
        "left": (-1, 0)
    }

    heading = directions[player.direction]

    intersection, incoming = find_next_intersection(
        player_cell, heading, grid
    )

    if intersection is None:
        return get_path_ahead(player, 1, grid, {})

    outgoing = predict_intersection_exit(
        intersection,
        incoming,
        player.intersection_history,
        grid
    )

    if outgoing is None:
        return intersection

    return (
        intersection[0] + outgoing[0],
        intersection[1] + outgoing[1]
    )


# ai updates

def update_npcs(npcs, player, grid, doors_by_edge, dt):
    player_cell = get_cell(player.x, player.y)

    if not (
        0 <= player_cell[0] < GRID_SIZE and
        0 <= player_cell[1] < GRID_SIZE
    ):
        return

    for npc in npcs:
        # basic npc explores independently of the player
        if npc.kind == "basic":
            move_basic_npc(npc, grid, doors_by_edge, dt)
            continue

        npc.repath_timer += dt

        # blocker follows the predicted intersection exit

        if npc.kind == "blocker":
            npc.markov_timer += dt

            if npc.markov_timer >= 20 or npc.path_index >= len(npc.path):
                npc.markov_timer = 0

                target = get_blocker_target(player, grid)
                npc.set_path(target, grid)

        elif npc.kind == "hunter":
            if npc.repath_timer >= 1.0 or not npc.path:
                npc.repath_timer = 0
                npc.set_path(player_cell, grid)

        elif npc.kind == "ambusher":
            if npc.repath_timer >= 1.0 or not npc.path:
                npc.repath_timer = 0

                distance = get_distance(
                    get_cell(npc.x, npc.y),
                    player_cell
                )

                if distance <= 4:
                    target = player_cell
                else:
                    target = get_path_ahead(player, 4, grid, doors_by_edge)

                npc.set_path(target, grid)

        elif npc.kind == "interceptor":
            if npc.repath_timer >= 1.0 or not npc.path:
                npc.repath_timer = 0

                distance = get_distance(
                    get_cell(npc.x, npc.y),
                    player_cell
                )

                if distance <= 4:
                    target = player_cell
                else:
                    target = get_path_ahead(player, 4, grid, doors_by_edge)

                npc.set_path(target, grid)

        npc.move(dt)


def check_enemy_collision(player, npcs):
    for npc in npcs:
        if npc.kind == "blocker":
            continue

        distance = hypot(player.x - npc.x, player.y - npc.y)

        if distance <= player.radius + npc.radius:
            return True

    return False

# breaks open maze walls at the edge

def open_perimeter(grid):
    for x in range(GRID_SIZE):
        grid[0][x].walls[0] = False
        grid[GRID_SIZE - 1][x].walls[2] = False

    for y in range(GRID_SIZE):
        grid[y][0].walls[3] = False
        grid[y][GRID_SIZE - 1].walls[1] = False


# drawing

def draw_diamond(surface, camera_x=0, camera_y=0):
    rect = DIAMOND_IMAGE.get_rect(
        center=(
            GOAL[0] * CELL_SIZE + CELL_SIZE / 2 - camera_x,
            GOAL[1] * CELL_SIZE + CELL_SIZE / 2 - camera_y
        )
    )

    surface.blit(DIAMOND_IMAGE, rect)


def draw_map(surface, grid):
    for y in range(GRID_SIZE):
        for x in range(GRID_SIZE):
            surface.blit(
                FLOOR_IMAGE,
                (x * CELL_SIZE, y * CELL_SIZE)
            )

    for row in grid:
        for cell in row:
            cell.draw(surface)


def draw_items(surface, keys, doors, camera_x=0, camera_y=0):
    for key in keys:
        key.draw(surface, camera_x, camera_y)

    for door in doors:
        door.draw(surface, camera_x, camera_y)


def get_camera(player):
    camera_x = player.x - WIDTH // 2
    camera_y = player.y - HEIGHT // 2

    camera_x = max(0, min(camera_x, MAP_WIDTH - WIDTH))
    camera_y = max(0, min(camera_y, MAP_HEIGHT - HEIGHT))

    return camera_x, camera_y


def draw_darkness(surface, player, npcs, camera_x, camera_y):
    darkness = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA
    )

    darkness.fill((0, 0, 0, 250))

    player_position = (
        round(player.x - camera_x),
        round(player.y - camera_y)
    )

    pygame.draw.circle(
        darkness,
        (0, 0, 0, 0),
        player_position,
        PLAYER_VISION
    )

    for npc in npcs:
        enemy_position = (
            round(npc.x - camera_x),
            round(npc.y - camera_y)
        )

        pygame.draw.circle(
            darkness,
            (0, 0, 0, 0),
            enemy_position,
            ENEMY_VISION
        )

    surface.blit(darkness, (0, 0))


def draw_sonar_map(grid, keys, doors, player, npcs):
    surface = pygame.Surface((WIDTH, HEIGHT))
    surface.fill((0, 0, 0))

    cell_width = WIDTH / GRID_SIZE
    cell_height = HEIGHT / GRID_SIZE

    thickness = max(
        2,
        int(WALL_THICKNESS * WIDTH / MAP_WIDTH)
    )

    # highlights center square

    center = GRID_SIZE // 2

    pygame.draw.rect(
        surface, (0, 180, 0),
        (
            center * cell_width,
            center * cell_height,
            cell_width,
            cell_height
        )
    )

    for row in grid:
        for cell in row:
            x = cell.x * cell_width
            y = cell.y * cell_height

            if cell.walls[0]:
                pygame.draw.line(
                    surface, (125, 125, 135),
                    (x, y), (x + cell_width, y), thickness
                )

            if cell.walls[1]:
                pygame.draw.line(
                    surface, (125, 125, 135),
                    (x + cell_width, y),
                    (x + cell_width, y + cell_height), thickness
                )

            if cell.walls[2]:
                pygame.draw.line(
                    surface, (125, 125, 135),
                    (x, y + cell_height),
                    (x + cell_width, y + cell_height), thickness
                )

            if cell.walls[3]:
                pygame.draw.line(
                    surface, (125, 125, 135),
                    (x, y), (x, y + cell_height), thickness
                )

    # draws remaining keys

    for key in keys:
        x = key.pos.x / MAP_WIDTH * WIDTH
        y = key.pos.y / MAP_HEIGHT * HEIGHT

        pygame.draw.circle(
            surface, (255, 220, 40),
            (int(x), int(y)), 5
        )

    # draws locked doors

    for door in doors:
        if door.locked:
            x = door.pos.x / MAP_WIDTH * WIDTH
            y = door.pos.y / MAP_HEIGHT * HEIGHT

            pygame.draw.circle(
                surface, (160, 100, 45),
                (int(x), int(y)), 5
            )

    # draws current enemy positions

    for npc in npcs:
        x = npc.x / MAP_WIDTH * WIDTH
        y = npc.y / MAP_HEIGHT * HEIGHT

        color = (80, 220, 120) if npc.kind == "basic" else (255, 35, 35)

        pygame.draw.circle(
            surface, color,
            (int(x), int(y)), 7
        )

    # draws current player position

    px = player.x / MAP_WIDTH * WIDTH
    py = player.y / MAP_HEIGHT * HEIGHT

    pygame.draw.circle(
        surface, (40, 120, 255),
        (int(px), int(py)), 8
    )

    return surface


def draw_hud(surface, score, round_number):
    text = small_font.render(
        f"Round: {round_number}    Escapes: {score}",
        True, (255, 255, 255)
    )

    surface.blit(text, (20, 20))


def draw_end_screen(surface, won, score):
    surface.fill((8, 8, 13))

    if won:
        heading = large_font.render(
            "YOU ESCAPED", True, (70, 230, 130)
        )
        message = "The next maze is waiting."
        prompt = "Press SPACE for the next round"

    else:
        heading = large_font.render(
            "GAME OVER", True, (235, 55, 55)
        )
        message = "You were caught."
        prompt = "Press SPACE to start a new run"

    heading_rect = heading.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 - 120)
    )

    surface.blit(heading, heading_rect)

    score_text = font.render(
        f"Total escapes: {score}",
        True, (255, 255, 255)
    )

    score_rect = score_text.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 - 20)
    )

    surface.blit(score_text, score_rect)

    message_text = small_font.render(
        message, True, (190, 190, 200)
    )

    message_rect = message_text.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 + 55)
    )

    surface.blit(message_text, message_rect)

    prompt_text = small_font.render(
        prompt, True, (255, 255, 255)
    )

    prompt_rect = prompt_text.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 + 130)
    )

    surface.blit(prompt_text, prompt_rect)


def draw_elite_warning(surface, timer):
    surface.fill((0, 0, 0))

    warning = large_font.render(
        "THE ELITES ARE COMING",
        True, (230, 35, 35)
    )

    warning_rect = warning.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 - 20)
    )

    surface.blit(warning, warning_rect)

    subtitle = small_font.render(
        "Escape the facility!",
        True, (220, 220, 220)
    )

    subtitle_rect = subtitle.get_rect(
        center=(WIDTH // 2, HEIGHT // 2 + 55)
    )

    surface.blit(subtitle, subtitle_rect)


# round setup

def create_round(round_number):
    start = choice(EDGES)

    grid, keys, doors = generate_maze(start)

    player = Player(*start)

    # spawns the basic npc with the player
    npcs = [create_basic_npc(player) for _ in range(5)]

    world_surface = pygame.Surface(
        (MAP_WIDTH, MAP_HEIGHT)
    )

    draw_map(world_surface, grid)

    overview = draw_sonar_map(
        grid, keys, doors, player, npcs
    )

    return (
        grid, keys, doors, player, npcs,
        world_surface, overview
    )


# main game loop

async def main():
    score = 0
    round_number = 1

    (
        grid, keys, doors, player, npcs,
        world_surface, overview
    ) = create_round(round_number)

    doors_by_edge = {
        door.edge: door for door in doors
    }

    state = "preview"

    preview_start = pygame.time.get_ticks()
    preview_duration = 5000
    preview_return_state = "maze"

    warning_timer = 0

    diamond_collected = False

    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:

                # opens and closes the sonar map

                if event.key == pygame.K_q:
                    if state == "preview":
                        state = preview_return_state

                    elif state in ("maze", "escape"):
                        preview_return_state = state
                        state = "preview"
                        preview_start = pygame.time.get_ticks()

                        # updates the map with current positions and items

                        overview = draw_sonar_map(
                            grid, keys, doors, player, npcs
                        )

                # starts the next round or a new run

                if event.key == pygame.K_SPACE and state in ("win", "lose"):
                    if state == "lose":
                        score = 0
                        round_number = 1

                    (
                        grid, keys, doors, player, npcs,
                        world_surface, overview
                    ) = create_round(round_number)

                    doors_by_edge = {
                        door.edge: door for door in doors
                    }

                    state = "preview"
                    preview_start = pygame.time.get_ticks()
                    preview_return_state = "maze"

                    diamond_collected = False
        # preview

        if state == "preview":
            screen.blit(overview, (0, 0))

            if pygame.time.get_ticks() - preview_start >= preview_duration:
                state = preview_return_state

        # maze

        elif state == "maze":
            player.update(
                grid, dt, doors_by_edge, False, []
            )

            # basic npc keeps roaming before the diamond is collected
            update_npcs(npcs, player, grid, doors_by_edge, dt)

            collect_keys(player, keys)

            goal_x, goal_y = cell_center(GOAL)

            if hypot(
                player.x - goal_x,
                player.y - goal_y
            ) <= player.radius + 20:

                diamond_collected = True

                keys.clear()
                doors.clear()
                doors_by_edge.clear()

                open_perimeter(grid)

                # redraws the world with the open exits

                draw_map(world_surface, grid)

                # adds elites without removing the basic npc
                npcs.extend(
                    create_npcs(round_number, player, grid)
                )

                warning_timer = ELITE_WARNING_TIME
                state = "alert"

            camera_x, camera_y = get_camera(player)

            screen.blit(
                world_surface,
                (-camera_x, -camera_y)
            )

            draw_items(
                screen, keys, doors,
                camera_x, camera_y
            )

            if not diamond_collected:
                draw_diamond(
                    screen, camera_x, camera_y
                )

            # draws all current npcs
            for npc in npcs:
                npc.draw(screen, camera_x, camera_y)

            player.draw(
                screen, camera_x, camera_y
            )

            draw_darkness(
                screen, player, npcs,
                camera_x, camera_y
            )

            draw_hud(screen, score, round_number)

        # elite warning

        elif state == "alert":
            warning_timer -= dt

            camera_x, camera_y = get_camera(player)

            screen.blit(
                world_surface,
                (-camera_x, -camera_y)
            )

            for npc in npcs:
                npc.draw(
                    screen, camera_x, camera_y
                )

            player.draw(
                screen, camera_x, camera_y
            )

            draw_elite_warning(screen, warning_timer)

            if warning_timer <= 0:
                state = "escape"

        # escape

        elif state == "escape":
            blockers = [
                npc for npc in npcs
                if npc.kind == "blocker"
            ]

            player.update(
                grid, dt, doors_by_edge,
                True, blockers
            )

            update_npcs(npcs, player, grid, doors_by_edge, dt)

            if check_enemy_collision(player, npcs):
                state = "lose"

            if (
                player.x < 0 or
                player.y < 0 or
                player.x > MAP_WIDTH or
                player.y > MAP_HEIGHT
            ):
                score += 1
                round_number += 1
                state = "win"

            camera_x, camera_y = get_camera(player)

            screen.blit(
                world_surface,
                (-camera_x, -camera_y)
            )

            draw_items(
                screen, keys, doors,
                camera_x, camera_y
            )

            for npc in npcs:
                npc.draw(
                    screen, camera_x, camera_y
                )

            player.draw(
                screen, camera_x, camera_y
            )

            draw_darkness(
                screen, player, npcs,
                camera_x, camera_y
            )

            draw_hud(
                screen, score, round_number - 1
            )

        # win and lose screens

        elif state == "win":
            draw_end_screen(screen, True, score)

        elif state == "lose":
            draw_end_screen(screen, False, score)

        pygame.display.flip()

        await asyncio.sleep(0)

    pygame.quit()


asyncio.run(main())