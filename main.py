import socket
import math
import time
import threading

import pygame

LOCAL_TEST = False  # Set True to skip socket connection
FLAGS = pygame.VIDEORESIZE
RESOLUTION = [1280, 768]

y_gravity = -9.81
x_gravity = 0
grid_scale = RESOLUTION[1] / 4
time_scale = 1000
WALLS = ["LOOP", "WALL", "LOOP", "WALL"]
EFFICIENCY = .5
MIN_FORCE = .5
WALL_WEIGHT = 500
BALL_ACCEL = 10
JUMP_VEL = 9

BUFFER_SIZE = 40


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


def elastic_bounce(m1, v1, m2, v2):
    """Returns the final vel of 1 after an elastic bounce"""
    force = (((m1 - m2) / (m1 + m2)) * v1) + (
        ((2 * m2) / (m1 + m2)) * v2)
    if abs(force) <= MIN_FORCE:
        return 0
    return force * EFFICIENCY


def angle_of_points(point1, point2):
    return math.atan2(point2[0] - point1[0], point2[1] - point1[1])


def angled_point(point, angle, dist):
    x = point[0] + math.sin(angle) * dist
    y = point[1] + math.cos(angle) * dist
    return [x, y]


def get_dist(point1, point2):
    return math.sqrt(
        (point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)


class Player(threading.Thread):
    def __init__(self, _connection=None):
        super().__init__()
        self.connection = _connection
        self.pos = None
        self.radius = None
        self.vel = None
        self.mass = 10
        self.color = (255, 255, 255)
        self.border = (125, 125, 125)
        self.local = None

    def run(self):
        while True:
            time.sleep(.1)
            if not self.local:
                try:
                    data = self.connection.recv(BUFFER_SIZE)
                except ConnectionResetError:
                    print("Server has closed")
                    break

                if not data:
                    print("Lost connection")
                    break
                data = unformat_data(data.decode())
                self.pos = data[0:2]
                self.vel = data[2:4]
            else:
                data_string = format_data(*self.pos, *self.vel)
                remote_player.connection.sendall(data_string.encode())

    def reset(self, host=True, local=False):
        """Resets player position"""
        global grid_scale
        self.local = local
        grid_scale = RESOLUTION[1] / 4
        width = display.get_width()
        height = display.get_height()
        self.vel = [0, 0]
        self.radius = width // 32
        if host:
            self.pos = [self.radius * 2, height - self.radius * 2]
            self.color = (255, 0, 0)
        else:
            self.pos = [width - self.radius * 2, height - self.radius * 2]
        if local:
            self.border = (0, 255, 0)

    def render(self):
        pygame.draw.circle(display, self.border, list(int(x) for x in self.pos), int(self.radius*1.25))
        pygame.draw.circle(display, self.color, list(int(x) for x in self.pos), self.radius)

    def tick(self, secs, balls):
        for i in range(0, 2):
            if i == 1:
                self.vel[i] -= y_gravity * secs
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
                    new_vel = elastic_bounce(self.mass,
                                             self.vel[i % 2],
                                             WALL_WEIGHT, 0)
            else:
                # TOP OR LEFT
                if self.pos[i % 2] - self.radius <= 0:
                    new_pos = (self.radius + 1)
                    opposite_pos = RESOLUTION[i % 2] - (self.radius + 1)
                    new_vel = elastic_bounce(self.mass,
                                             self.vel[i % 2],
                                             WALL_WEIGHT, 0)

            if not isinstance(new_pos, type(None)):
                if wall == "WALL":
                    self.pos[i % 2] = new_pos
                    self.vel[i % 2] = new_vel
                elif wall == "LOOP":
                    self.pos[i % 2] = opposite_pos
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
                                             _ball.mass, _ball.vel[0])
                self.vel[1] = elastic_bounce(self.mass, self.vel[1],
                                             _ball.mass, _ball.vel[1])
                _ball.vel[0] = elastic_bounce(_ball.mass, _ball.vel[0],
                                              self.mass, selftempx)
                _ball.vel[1] = elastic_bounce(_ball.mass, _ball.vel[1],
                                              self.mass, selftempy)

                angle1 = angle_of_points(self.pos, _ball.pos)
                angle2 = angle_of_points(_ball.pos, self.pos)
                n_dist2 = dist * (
                    self.radius / (self.radius + _ball.radius))

                center = angled_point(self.pos, angle1, n_dist2)
                if get_dist(self.pos, center) <= self.radius:
                    self.pos = angled_point(center, angle2, self.radius + 1)
                if get_dist(_ball.pos, center) <= _ball.radius:
                    _ball.pos = angled_point(center, angle1, _ball.radius + 1)
            _collisions.append([self, _ball])
        return _collisions

    def on_ground(self):
        return self.pos[1] >= display.get_height() - self.radius * 1.5


def format_data(*data):
    string = ""
    for obj in data:
        if isinstance(obj, int) or isinstance(obj, float):
            string += f'{obj:.10f}'[:10]
        else:
            if len(obj) > 10:
                string += obj[:10]
            else:
                string += obj.ljust(10, "~")
    return string


def unformat_data(data):
    data_list = []
    while len(data) >= 10:
        part = data[:10]
        if not is_number(part):
            data_list.append(part.rstrip("~"))
        else:
            data_list.append(float(part))
        if len(data) > 10:
            data = data[10:]
        else:
            break
    return data_list


local_player = Player()
remote_player = None
hosting = False

if not LOCAL_TEST:
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_port = get_int("Enter the port: ")

    if check_input("Host", "Host or Join? ", ["Host", "Join"]):
        # HOST
        hosting = True
        server_host = socket.gethostbyname(socket.gethostname())
        if not check_input("Yes", "Host on " + server_host + ":" + str(
                server_port) + "? ", ["Yes", "No"]):
            # Do not host on machine port for some reason
            server_host = get_input("Enter the IP: ")
        try:
            server_sock.bind((server_host, server_port))
        except OSError:
            raise Exception("Server already running.")
            # See comment below

        server_sock.listen()
        connection, address = server_sock.accept()
        print("Player connected from " + str(address) + ".")
        remote_player = Player(connection)
    else:
        # Join
        # server_host = get_input("Enter the IP: ")
        server_host = socket.gethostbyname(socket.gethostname())  # TODO: Enter IP Manually: replace this with ^ line
        try:
            server_sock.connect((server_host, server_port))
        except OSError:
            raise Exception("Could not connect")
            # Look, my users won't know what a OSError is anyways
        remote_player = Player(server_sock)
else:
    remote_player = Player()

display = pygame.display.set_mode(RESOLUTION, FLAGS)

local_player.reset(hosting, True)
remote_player.reset(not hosting, False)
remote_player.start()
local_player.start()
balls = [local_player, remote_player]
secs = 0
sim_time = get_millis()

ball_dir = "STOP"

quit_running = False
while not quit_running:
    if ball_dir == "STOPPING":
        ball_dir = "STOP"
    elif ball_dir == "LEFTING":
        ball_dir = "LEFT"
    elif ball_dir == "RIGHTING":
        ball_dir = "RIGHT"
    elif ball_dir == "UPPING":
        ball_dir = "UP"
    for event in pygame.event.get():
        if event.type == pygame.VIDEORESIZE:
            display = pygame.display.set_mode(event.dict["size"], FLAGS)
            RESOLUTION = event.dict["size"]
        elif event.type == pygame.QUIT:
            quit_running = True
            break
        elif event.type == pygame.KEYDOWN:
            if event.dict["key"] == pygame.K_ESCAPE:
                quit_running = True
                break
            elif event.dict["key"] == pygame.K_LEFT:
                ball_dir = "LEFTING"
            elif event.dict["key"] == pygame.K_SPACE \
                    or event.dict["key"] == pygame.K_UP:
                if local_player.on_ground():
                    ball_dir = "UPPING"
            elif event.dict["key"] == pygame.K_RIGHT:
                ball_dir = "RIGHTING"
        elif event.type == pygame.KEYUP:
            if event.dict["key"] == pygame.K_LEFT:
                if ball_dir == "LEFT":
                    ball_dir = "STOPPING"
            elif event.dict["key"] == pygame.K_RIGHT:
                if ball_dir == "RIGHT":
                    ball_dir = "STOPPING"
            elif event.dict["key"] == pygame.K_UP \
                    or event.dict["key"] == pygame.K_SPACE:
                if ball_dir == "UP":
                    ball_dir = "STOPPING"

    if ball_dir == "LEFT":
        local_player.vel[0] -= BALL_ACCEL * secs
    if ball_dir == "RIGHT":
        local_player.vel[0] += BALL_ACCEL * secs
    if ball_dir == "UPPING":
        local_player.vel[1] += JUMP_VEL

    new_sim_time = get_millis()
    secs = (new_sim_time - sim_time) / time_scale
    sim_time = new_sim_time

    collisions = []
    i = 0
    while True:
        j = 0
        while True:
            collisions = balls[i].collide(balls[j], collisions)
            if balls[i].tick(secs, balls):
                i -= 1
            balls[i].render()
            j += 1
            if j >= len(balls):
                break
        i += 1
        if i >= len(balls):
            break

    pygame.display.flip()
    display.fill((0, 0, 0))
