import socket
import math
import time
import threading

import pygame
from pygame.image import load
import pygame.gfxdraw

from configs import get_game_root
from poetry import get_all_poets, find_poet

pygame.init()

FLAGS = pygame.VIDEORESIZE
RESOLUTION = [1600, 900]

y_gravity = -9.81
x_gravity = 0
grid_scale = RESOLUTION[1] / 4
time_scale = 1000
WALLS = ["WALL", "HOLE", "WALL", "WALL"]
EFFICIENCY = .2
MIN_FORCE = .1
WALL_WEIGHT = 500
BALL_ACCEL = 10
JUMP_VEL = 4

WIN_ARC = .5

BUFFER_SIZE = 32
BUFFER_PART = 8

SLEEP_TIME = .01

clock = pygame.time.Clock()

send_time = -1000
recv_time = -1000
send_int = -553
recv_int = -553

PING_UPDATE = 500
PING_FACTOR = 10
PING_SIZE = 50
ping_time = 0

SEND_LOCK = threading.Lock()

enemy_wins = 0
my_wins = 0

PLAYER_SIZE = 20

LEFT_COLOR = (125, 125, 125)
RIGHT_COLOR = (255, 255, 255)

GROUND_FACTOR = 1.25


def get_millis():
    return time.time() * 1000


def is_number(num):
    """Checks if num is a number"""
    try:
        float(num)
    except ValueError:
        return False
    return True


def get_int(prompt="", choices=None):
    """Calls get_input and ensures response is an int"""
    if not isinstance(choices, type(None)):
        for choice in choices:
            if not is_number(choice):
                raise Exception("Given choice is not an int")
    answer = get_input(prompt, choices)
    if is_number(answer):
        return int(answer)
    else:
        return get_int(prompt, choices)


def check_input(check, prompt="", choices=None):
    """Calls get_input and checks if answer is check (lowercase)

    :param check: returns whether given answer is check. Returns answer if None
    """

    answer = get_input(prompt, choices)
    return answer == check.lower()


def get_input(prompt="", choices=None):
    """Waits for user to give answer from choices

    :param choices: List of choices to verify answer against
    :param prompt: Prompt to pass to input
    :rtype: String (lowercase)
    """
    while True:
        answer = input(prompt).lower()
        if not isinstance(choices, type(None)):
            lowered_choices = list(x.lower() for x in choices)
            if answer in lowered_choices:
                return answer
            elif len(answer) > 0:
                i = len(answer) - 1
                while i >= 0:
                    matches = []
                    for choice in lowered_choices:
                        if choice.startswith(answer[:i + 1]):
                            matches.append(choice)
                    if len(matches) == 1:
                        return matches[0]
                    elif len(matches) == 0:
                        break
                    # Multiple matches
                    i -= 1
        else:
            return answer


def elastic_bounce(m1, v1, m2, v2, eff):
    """Returns the final vel of 1 after an elastic bounce"""
    force = (((m1 - m2) / (m1 + m2)) * v1) + (
            ((2 * m2) / (m1 + m2)) * v2)
    if abs(force) <= MIN_FORCE:
        return 0
    return force * EFFICIENCY * eff


def angle_of_points(point1, point2):
    return math.atan2(point2[0] - point1[0], point2[1] - point1[1])


def angled_point(point, angle, dist):
    x = point[0] + math.sin(angle) * dist
    y = point[1] + math.cos(angle) * dist
    return [x, y]


def get_dist(point1, point2):
    return math.sqrt(
        (point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)


def PointsInCircum(r, n=100):
    """Found here: https://stackoverflow.com/a/8488079/7587147"""
    return [
        (math.cos(2 * math.pi / n * x) * r, math.sin(2 * math.pi / n * x) * r)
        for x in range(0, n + 1)]


class Player(threading.Thread):
    def __init__(self, _connection=None, _poet=None):
        super().__init__()
        self.connection = _connection
        self.poet = _poet
        self.pos = None
        self.radius = None
        self.vel = None
        self.color = LEFT_COLOR
        self.local = None
        self.path = get_game_root() + self.poet.lower() + ".jpg"
        self.era = find_poet(self.poet)[0]
        self.atts = find_poet(self.poet)[1]
        self.jumps = 1
        self.jump_start = 2
        self.air_move = False
        self.mass = 10 // self.atts["bounce"]

        if self.era == "Romantic":
            self.era_color = (255, 50, 50)
        elif self.era == "Victorian":
            self.era_color = (50, 50, 50)
        else:
            self.era_color = (50, 125, 50)

    def run(self):
        global quit_running, send_time, recv_time, recv_int, send_int, enemy_wins
        while not quit_running:
            time.sleep(SLEEP_TIME)
            if not self.local:
                try:
                    data = self.connection.recv(BUFFER_SIZE)
                except ConnectionResetError:
                    print("Server has closed")
                    break

                if not data:
                    print("Lost connection")
                    break
                if data.decode().startswith("WIN"):
                    enemy_wins += 1
                    reset()
                else:
                    data = unformat_data(data.decode())
                    if not isinstance(data, type(None)):
                        self.pos = data[0:2]
                        self.vel = data[2:4]
                recv_int = get_millis() * PING_FACTOR - recv_time
                recv_time = get_millis() * PING_FACTOR
            else:  # TODO: Only send remote input. Calc all on local
                data_string = format_data(*self.pos, *self.vel)
                SEND_LOCK.acquire()
                try:
                    remote_player.connection.sendall(data_string.encode())
                except ConnectionResetError:
                    print("Player left")
                    quit_running = True
                    raise SystemExit
                SEND_LOCK.release()
                send_int = get_millis() * PING_FACTOR - send_time
                send_time = get_millis() * PING_FACTOR

    def reset(self, host=True, local=False):
        """Resets player position"""
        global grid_scale
        self.local = local
        grid_scale = RESOLUTION[1] / 4
        width = display.get_width()
        height = display.get_height()
        self.vel = [0, 0]
        self.radius = width // PLAYER_SIZE
        if not host:
            self.pos = [self.radius * 2, height - self.radius * 2]
        else:
            self.color = RIGHT_COLOR
            self.pos = [width - self.radius * 2, height - self.radius * 2]

    def render(self):
        if self.on_ground(True):
            self.jumps = self.jump_start
            self.air_move = False
        pygame.draw.circle(display, self.color, list(int(x) for x in self.pos),
                           self.radius)
        image = load(self.path)
        image = pygame.transform.scale(image,
                                       [int(self.radius*1.3), int(self.radius*1.3)])
        if self.vel[0] < 0:
            image = pygame.transform.flip(image, True, False)

        # TODO: Use texture or picture with border?
        display.blit(image, [*list(x - self.radius//1.5 for x in self.pos)])
        pygame.draw.circle(display, self.color, list(int(x) for x in self.pos),
                           int(self.radius), int(self.radius // 3))
        pygame.draw.circle(display, self.color,
                           list(int(x + 1) for x in self.pos),
                           int(self.radius), int(self.radius // 3))
        pygame.draw.circle(display, self.color,
                           list(int(x - 1) for x in self.pos),
                           int(self.radius), int(self.radius // 3))
        pygame.draw.circle(display, self.era_color,
                           list(int(x) for x in self.pos),
                           int(self.radius), int(self.radius // 8))
        pygame.draw.circle(display, self.era_color,
                           list(int(x - 1) for x in self.pos),
                           int(self.radius), int(self.radius // 8))
        pygame.draw.circle(display, self.era_color,
                           list(int(x + 1) for x in self.pos),
                           int(self.radius), int(self.radius // 8))
        # points = []
        # for point in PointsInCircum(self.radius, 300):  # TODO: optimise vertexes
        #     points.append([self.pos[0] + point[0], self.pos[1] + point[1]])
        # pygame.gfxdraw.textured_polygon(display, points, image, int(self.pos[0] + self.radius*.75), int(self.pos[1] + self.radius*.75))  # TODO: Why jumpy?

    def tick(self, secs, balls):
        for i in range(0, 2):
            if i == 1:
                self.vel[1] -= y_gravity * secs
            else:
                self.vel[0] -= x_gravity * secs
            self.pos[i] += (self.vel[i] * secs) * grid_scale
        self.check_pos(balls)

    def check_pos(self, balls):

        # Check Walls

        i = 0
        for wall in WALLS:
            new_pos = None
            new_vel = None
            opposite_pos = None
            if i == 0 or i == 3:
                # RIGHT or BOTTOM
                if self.pos[i % 2] + self.radius >= RESOLUTION[i % 2]:
                    new_pos = RESOLUTION[i % 2] - (self.radius + 1)
                    opposite_pos = (self.radius + 1)
                    if i == 3:
                        eff = self.atts["elastic"]
                    else:
                        eff = 1
                    new_vel = elastic_bounce(self.mass,
                                             self.vel[i % 2],
                                             WALL_WEIGHT, 0, eff)
            else:
                # TOP OR LEFT
                if self.pos[i % 2] - self.radius <= 0:
                    new_pos = (self.radius + 1)
                    opposite_pos = RESOLUTION[i % 2] - (self.radius + 1)
                    new_vel = elastic_bounce(self.mass,
                                             self.vel[i % 2],
                                             WALL_WEIGHT, 0, 1)

            if not isinstance(new_pos, type(None)):
                if wall == "WALL":
                    self.pos[i % 2] = new_pos
                    self.vel[i % 2] = new_vel
                elif wall == "LOOP":
                    self.pos[i % 2] = opposite_pos
                elif wall == "HOLE":
                    pass
                else:
                    balls.remove(self)
            i += 1

    def collide(self, _ball, _collisions):
        if _ball != self and not ([self, _ball] in _collisions
                                  or [_ball, self] in _collisions):
            dist = math.sqrt((_ball.pos[0] - self.pos[0]) ** 2 + (
                    _ball.pos[1] - self.pos[1]) ** 2)
            if dist <= self.radius + _ball.radius:
                selftempx = self.vel[0]
                selftempy = self.vel[1]
                self.vel[0] = elastic_bounce(self.mass, self.vel[0],
                                             _ball.mass, _ball.vel[0], 1)
                self.vel[1] = elastic_bounce(self.mass, self.vel[1],
                                             _ball.mass, _ball.vel[1], 1)
                _ball.vel[0] = elastic_bounce(_ball.mass, _ball.vel[0],
                                              self.mass, selftempx, 1)
                _ball.vel[1] = elastic_bounce(_ball.mass, _ball.vel[1],
                                              self.mass, selftempy, 1)

                angle1 = angle_of_points(self.pos, _ball.pos)
                angle2 = angle_of_points(_ball.pos, self.pos)

                if self.local:
                    if -WIN_ARC < angle1 < WIN_ARC:
                        # Jumped on opponent's head
                        return "WIN"
                    elif -WIN_ARC < angle2 < WIN_ARC and LOCAL_GAME:
                        # Jumped on my head
                        return "LOST"

                n_dist2 = dist * (
                        self.radius / (self.radius + _ball.radius))

                center = angled_point(self.pos, angle1, n_dist2)
                if get_dist(self.pos, center) <= self.radius:
                    self.pos = angled_point(center, angle2, self.radius + 1)
                if get_dist(_ball.pos, center) <= _ball.radius:
                    _ball.pos = angled_point(center, angle1, _ball.radius + 1)
            _collisions.append([self, _ball])
        return _collisions

    def on_wall(self):
        if self.on_ground(True):
            return True
        elif -self.radius <= self.pos[1] <= self.radius * get_att(self, "ground factor", GROUND_FACTOR):
            return True
        elif self.pos[0] >= display.get_width() - self.radius * get_att(self, "ground factor", GROUND_FACTOR):
            return not self.pos[1] <= -self.radius  # Walls not above ceiling
        elif self.pos[0] <= self.radius * GROUND_FACTOR:
            return not self.pos[1] <= -self.radius
        return False

    def on_ground(self, touching=False, moved=True):
        on_ground = self.pos[1] >= display.get_height() - self.radius * get_att(self, "ground factor", GROUND_FACTOR)
        if touching:
            return on_ground
        if self.era == "Romantic":
            return on_ground
        elif self.era == "Victorian":
            if not moved and self.air_move:
                return True
            if self.jumps > 0:
                self.air_move = True
                self.jumps -= 1
                return True
            self.air_move = False
            return False
        else:
            return self.on_wall()


def reset():
    local_player.reset(hosting, True)
    remote_player.reset(not hosting, False)


def format_data(*data):
    string = ""
    for obj in data:
        if isinstance(obj, int) or isinstance(obj, float):
            string += f'{obj:.{BUFFER_PART}f}'[:BUFFER_PART]
        else:
            if len(obj) > BUFFER_PART:
                string += obj[:BUFFER_PART]
            else:
                string += obj.ljust(BUFFER_PART, "~")
    return string


def unformat_data(data):
    if len(data) < BUFFER_SIZE:
        return None  # Not all data received
    data_list = []
    while len(data) >= BUFFER_PART:
        part = data[:BUFFER_PART]
        if not is_number(part):
            data_list.append(part.rstrip("~"))
        else:
            data_list.append(float(part))
        if len(data) > BUFFER_PART:
            data = data[BUFFER_PART:]
        else:
            break
    return data_list


def choose_poet(player=1):
    poet = "list"
    while poet == "list":
        poet = get_input(
            "Player " + str(player) + ", Choose a poet. ['List'] for options: ",
            get_all_poets() + ["List"])
        if poet == "list":
            print(get_all_poets())
    print(poet.title())
    return poet


def get_att(player, att, default=None):
    if att in player.atts:
        return player.atts[att]
    return default


LOCAL_GAME = check_input("Yes", "Run local game? ", ["Yes", "No"])

local_player = Player(_poet=choose_poet())
remote_player = None
hosting = False

if not LOCAL_GAME:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_port = get_int("Enter the port: ")
    server_host = socket.gethostbyname(socket.gethostname())
    if not check_input("Yes", "Use system IP: " + server_host + ":" + str(
            server_port) + "? ", ["Yes", "No"]):
        server_host = get_input("Enter the IP: ")
    if check_input("Host", "Host or Join? ", ["Host", "Join"]):
        # HOST
        hosting = True
        print("Hosting")
        try:
            server_sock.bind((server_host, server_port))
        except OSError:
            raise Exception("Server already running.")
            # See comment below

        server_sock.listen()
        connection, address = server_sock.accept()
        print("Player connected from " + str(address) + ".")
        try:
            data = connection.recv(BUFFER_SIZE)
        except ConnectionResetError:
            raise Exception("Server has closed")

        poet = data.decode().strip().title()
        remote_player = Player(connection, poet)

        data_string = local_player.poet.ljust(BUFFER_SIZE, " ")
        SEND_LOCK.acquire()
        try:
            connection.sendall(data_string.encode())
        except ConnectionResetError:
            print("Player left")
            quit_running = True
            raise SystemExit
        SEND_LOCK.release()

    else:
        # Join
        print("Joining")
        try:
            server_sock.connect((server_host, server_port))
        except OSError:
            raise Exception("Could not connect")
            # Look, my users won't know what a OSError is anyways
        data_string = local_player.poet.ljust(BUFFER_SIZE, " ")
        SEND_LOCK.acquire()
        try:
            server_sock.sendall(data_string.encode())
        except ConnectionResetError:
            print("Player left")
            quit_running = True
            raise SystemExit
        SEND_LOCK.release()

        try:
            data = server_sock.recv(BUFFER_SIZE)
        except ConnectionResetError:
            raise Exception("Server has closed")

        poet = data.decode().strip().title()

        remote_player = Player(server_sock, poet)
else:
    remote_player = Player(_poet=choose_poet())

display = pygame.display.set_mode(RESOLUTION, FLAGS)

quit_running = False

reset()
if not LOCAL_GAME:
    remote_player.start()
    local_player.start()
balls = [local_player, remote_player]
secs = 0
sim_time = get_millis()

key_downs = set()

while not quit_running:
    key_presses = set()
    for event in pygame.event.get():
        if event.type == pygame.VIDEORESIZE:
            display = pygame.display.set_mode(event.dict["size"], FLAGS)
            RESOLUTION = event.dict["size"]
            reset()
        elif event.type == pygame.QUIT:
            quit_running = True
            break
        elif event.type == pygame.KEYDOWN:
            key = event.dict["key"]
            if key == pygame.K_ESCAPE:
                quit_running = True
                break
            else:
                if key not in key_downs:
                    key_presses.add(key)
                key_downs.add(key)
        elif event.type == pygame.KEYUP:
            key_downs.remove(event.dict["key"])

    if pygame.K_a in key_downs:
        if local_player.on_ground(
                moved=pygame.K_a in key_presses) or local_player.era != "Victorian":
            local_player.vel[0] -= BALL_ACCEL * secs * get_att(local_player, "accel", 1)
    if pygame.K_d in key_downs:
        if local_player.on_ground(
                moved=pygame.K_d in key_presses) or local_player.era != "Victorian":
            local_player.vel[0] += BALL_ACCEL * secs * get_att(local_player, "accel", 1)
    if pygame.K_w in key_presses or pygame.K_SPACE in key_presses or (
            local_player.era != "Victorian" and (
            pygame.K_w in key_downs or pygame.K_SPACE in key_downs)):
        if local_player.on_ground(moved=True):
            local_player.vel[1] -= JUMP_VEL * get_att(local_player, "jump vel", 1)

    if LOCAL_GAME:
        if pygame.K_LEFT in key_downs:
            if remote_player.on_ground(
                    moved=pygame.K_LEFT in key_presses) or remote_player.era != "Victorian":
                remote_player.vel[0] -= BALL_ACCEL * secs * get_att(remote_player, "accel", 1)
        if pygame.K_RIGHT in key_downs:
            if remote_player.on_ground(
                    moved=pygame.K_RIGHT in key_presses) or remote_player.era != "Victorian":
                remote_player.vel[0] += BALL_ACCEL * secs * get_att(remote_player, "accel", 1)
        if pygame.K_UP in key_presses or (
                remote_player.era != "Victorian" and pygame.K_UP in key_downs):
            if remote_player.on_ground(moved=True):
                remote_player.vel[1] -= JUMP_VEL * get_att(remote_player, "jump vel", 1)

    new_sim_time = get_millis()
    secs = (new_sim_time - sim_time) / time_scale
    sim_time = new_sim_time

    collisions = []
    win = False
    i = 0
    while not win:
        j = 0
        while not win:
            collisions = balls[i].collide(balls[j], collisions)
            if collisions == "WIN":
                my_wins += 1
                win = True
                break
            elif collisions == "LOST":
                # Only can occur in local game
                enemy_wins += 1
                win = True
                break
            if balls[i].tick(secs, balls):
                i -= 1
            balls[i].render()
            j += 1
            if j >= len(balls):
                break
        i += 1
        if i >= len(balls):
            break

    if win:
        reset()
        if not LOCAL_GAME:
            SEND_LOCK.acquire()
            try:
                remote_player.connection.sendall(
                    "WIN".ljust(BUFFER_SIZE, " ").encode())
            except ConnectionResetError:
                print("Player left")
                quit_running = True
                raise SystemExit
            SEND_LOCK.release()
    font = pygame.font.SysFont("monospace", PING_SIZE//2)
    if not LOCAL_GAME:
        if get_millis() - ping_time >= PING_UPDATE:
            pings = str(int(send_int)).rjust(5) + " | " + str(
                int(recv_int)).rjust(5)
            ping_time = get_millis()
        label = font.render(pings, 1, (255, 255, 255))
        width, height = font.size(pings)
        display.blit(label, (int(display.get_width() - width), height))
    font = pygame.font.SysFont("monospace", PING_SIZE)
    score = str(my_wins).strip(" ")
    label = font.render(score, 1, LEFT_COLOR)
    width1, height = font.size(score)
    display.blit(label, (0, height))
    score = " " + str(enemy_wins).strip(" ")
    label = font.render(score, 1, RIGHT_COLOR)
    width2, height = font.size(score)
    display.blit(label, (width1, height))

    pygame.display.flip()
    display.fill((0, 0, 0))
    # time.sleep(SLEEP_TIME)

# TODO: Add local play
