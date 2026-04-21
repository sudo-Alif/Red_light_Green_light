from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math
import random
import time
import sys

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
ARENA_BASE_LENGTH = 1600
ARENA_LENGTH      = 2200
ARENA_WIDTH       = 2000
ARENA_HEIGHT      = 375

fovY     = 90          # was 120 – less fisheye distortion
WINDOW_W = 1800
WINDOW_H = 900

CAMERA_HEIGHT_MIN = -350
CAMERA_HEIGHT_MAX =  350

# ─────────────────────────────────────────────
#  PLAYER
# ─────────────────────────────────────────────
player_x     = -ARENA_BASE_LENGTH / 2 - 50
player_y     = 0
player_z     = 90
player_angle = 270

camera_mode          = 0
camera_rot_y         = 270
camera_height_offset = 0
cheat_mode           = False

# ─────────────────────────────────────────────
#  DOLL / GUNMEN
# ─────────────────────────────────────────────
doll_x      = ARENA_BASE_LENGTH / 2
doll_y      = 50
doll_z      = 200
doll_angle  = 270
doll_height = 500

gunman1_x = doll_x + 150
gunman1_y = doll_y - 200
gunman1_z = 90
gunman1_angle = 450

gunman2_x = doll_x + 150
gunman2_y = doll_y + 200
gunman2_z = 90
gunman2_angle = 450

# ─────────────────────────────────────────────
#  GAME STATE
# ─────────────────────────────────────────────
game_state  = "Running"
light_state = "GREEN"
light_timer = 0.0
light_switch_time = 0.0

countdown_timer      = 5.0
countdown_start_time = 0.0
game_started         = False

game_timer      = 60.0
game_start_time = 0.0

player_status    = "Alive"
player_dead      = False
player_visible   = True
player_prev_x    = player_x
player_prev_y    = player_y
movement_threshold = 5
player_last_pos_x  = player_x
player_last_pos_y  = player_y
red_ref_x = None
red_ref_y = None

bullets         = []
BULLET_SPEED    = 2000.0
BULLET_SIZE     = 9.0

targets_shot_at = set()

coins                    = []
player_invisible         = False
player_invisible_end_time = 0

is_sprinting  = False
shift_pressed = False

# ─────────── KEY STATE  (fixed: press/release, not toggle) ───────────
key_w = False
key_s = False
key_a = False
key_d = False

last_update_time = time.time()

move_speed   = 130
sprint_speed = 220

MIN_PLAYER_DISTANCE = 100
game_over           = False

# ─────────────────────────────────────────────
#  LIGHTING HELPERS
# ─────────────────────────────────────────────
def set_material_color(r, g, b, shininess=20):
    """Set color + material properties for lit rendering."""
    glColor3f(r, g, b)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT,   [r*0.4, g*0.4, b*0.4, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE,   [r,     g,     b,     1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR,  [0.4,   0.4,   0.4,   1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, shininess)

def setup_lighting():
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_LIGHT1)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, 1)
    glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [0.25, 0.25, 0.28, 1.0])

    # Main overhead light
    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 1.0, 0.0])   # directional, from above
    glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 0.97, 0.90, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [0.6, 0.6,  0.6,  1.0])

    # Fill light from the finish-line side (warm)
    glLightfv(GL_LIGHT1, GL_POSITION, [1.0, 0.0, 0.3, 0.0])
    glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0.35, 0.15, 0.10, 1.0])
    glLightfv(GL_LIGHT1, GL_SPECULAR, [0.0, 0.0, 0.0, 1.0])

# ─────────────────────────────────────────────
#  NPC CLASS
# ─────────────────────────────────────────────
def is_position_valid(x, y, exclude_npcs=None, exclude_player=False):
    if exclude_npcs is None:
        exclude_npcs = []
    if not exclude_player:
        if math.sqrt((x - player_x)**2 + (y - player_y)**2) < MIN_PLAYER_DISTANCE:
            return False
    for npc in npcs:
        if npc in exclude_npcs:
            continue
        if math.sqrt((x - npc.x)**2 + (y - npc.y)**2) < MIN_PLAYER_DISTANCE:
            return False
    return True

class NPC:
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z
        self.angle = 270

        self.height_type = random.choice(['tall', 'short', 'normal'])
        self.speed_type   = random.choice(['fast', 'slow', 'normal'])
        self.width_type   = random.choice(['fat', 'thin', 'normal'])

        if self.speed_type == 'fast':
            self.base_speed = random.uniform(120, 175)
        elif self.speed_type == 'slow':
            self.base_speed = random.uniform(55, 95)
        else:
            self.base_speed = random.uniform(85, 130)

        self.speed              = self.base_speed
        self.speed_noise_target = self.base_speed

        self.scale_z = {'tall': 2.0, 'short': 1.0, 'normal': 1.5}[self.height_type]

        if self.width_type == 'fat':
            self.scale_x, self.scale_y = 1.5, 0.8
        elif self.width_type == 'thin':
            self.scale_x, self.scale_y = 0.7, 0.3
        else:
            self.scale_x, self.scale_y = 1.0, 0.5

        self.is_moving   = True
        self.move_timer  = random.uniform(2, 6)

        self.stumble_timer  = 0.0
        self.stumble_chance = random.uniform(0.001, 0.008)

        self.direction_change_timer = random.uniform(4, 12)
        self.hesitation_timer       = 0.0
        self.is_hesitating          = False
        self.panic_timer            = 0.0
        self.is_panicking           = False
        self.panic_chance           = 0.001

        self.strategic_mode        = random.choice([True, False])
        self.red_light_awareness   = random.uniform(0.7, 0.95)
        self.green_light_urgency   = random.uniform(1.2, 1.8)
        self.moves_during_red_light = random.choice([True, False])

        self.forward_bias             = random.uniform(0.7, 0.9)
        self.lateral_drift            = random.uniform(0.1, 0.3)
        self.base_forward_angle       = 270
        self.angle_correction_strength = random.uniform(0.3, 0.7)

        self.prev_x = x
        self.prev_y = y
        self.invisible          = False
        self.invisible_end_time = 0

        # Unique tint for body
        self.body_r = random.uniform(0.3, 0.9)
        self.body_g = random.uniform(0.3, 0.9)
        self.body_b = random.uniform(0.3, 0.9)

npcs = []

for i in range(9):
    while True:
        sx = -ARENA_BASE_LENGTH / 2 - 50 + random.randint(-100, 100)
        sy = random.randint(int(-ARENA_WIDTH/4), int(ARENA_WIDTH/4))
        if math.sqrt((sx - player_x)**2 + (sy - player_y)**2) >= MIN_PLAYER_DISTANCE:
            break
    npcs.append(NPC(sx, sy, 90))

for _ in range(15):
    coins.append((
        random.uniform(-ARENA_BASE_LENGTH/2 + 100, ARENA_BASE_LENGTH/2 - 100),
        random.uniform(-ARENA_WIDTH/2  + 100, ARENA_WIDTH/2  - 100),
        30
    ))

# ─────────────────────────────────────────────
#  RESET
# ─────────────────────────────────────────────
def reset_game():
    global player_x, player_y, player_z, player_angle, camera_rot_y, camera_height_offset, camera_mode
    global game_state, light_state, light_timer, light_switch_time
    global countdown_timer, countdown_start_time, game_started, game_timer, game_start_time
    global player_prev_x, player_prev_y, player_status, player_dead
    global player_last_pos_x, player_last_pos_y
    global bullets, player_invisible, player_invisible_end_time, is_sprinting
    global doll_angle, coins, targets_shot_at, npcs
    global player_visible, red_ref_x, red_ref_y, game_over
    global key_w, key_s, key_a, key_d

    player_x, player_y, player_z = -ARENA_BASE_LENGTH / 2 - 50, 0, 90
    player_angle       = 270
    camera_rot_y       = 270
    camera_height_offset = 0
    camera_mode        = 0

    game_state  = "Running"
    light_state = "GREEN"
    light_timer = 0.0
    light_switch_time = 0.0
    countdown_timer      = 5.0
    countdown_start_time = time.time()
    game_started    = False
    game_timer      = 60.0
    game_start_time = 0.0

    player_prev_x     = player_x
    player_prev_y     = player_y
    player_status     = "Alive"
    player_dead       = False
    player_visible    = True
    player_last_pos_x = player_x
    player_last_pos_y = player_y
    red_ref_x = red_ref_y = None
    game_over = False

    bullets = []
    targets_shot_at.clear()
    player_invisible          = False
    player_invisible_end_time = 0
    is_sprinting  = False
    doll_angle    = 180.0
    key_w = key_s = key_a = key_d = False

    coins = []
    for _ in range(15):
        coins.append((
            random.uniform(-ARENA_BASE_LENGTH/2 + 100, ARENA_BASE_LENGTH/2 - 100),
            random.uniform(-ARENA_WIDTH/2  + 100, ARENA_WIDTH/2  - 100),
            30
        ))

    npcs = []
    for _ in range(9):
        while True:
            sx = -ARENA_BASE_LENGTH / 2 - 50 + random.randint(-100, 100)
            sy = random.randint(int(-ARENA_WIDTH/4), int(ARENA_WIDTH/4))
            if math.sqrt((sx - player_x)**2 + (sy - player_y)**2) >= MIN_PLAYER_DISTANCE:
                break
        npcs.append(NPC(sx, sy, 90))

# ─────────────────────────────────────────────
#  DRAW ARENA
# ─────────────────────────────────────────────
def draw_checkerboard_floor():
    """Draw a two-tone checkerboard floor with proper normals."""
    cell_size   = 100
    half_l = ARENA_LENGTH // 2
    half_w = ARENA_WIDTH  // 2
    cols = ARENA_LENGTH // cell_size
    rows = ARENA_WIDTH  // cell_size

    glNormal3f(0, 0, 1)
    for ci in range(cols):
        for ri in range(rows):
            x0 = -half_l + ci * cell_size
            y0 = -half_w + ri * cell_size
            x1, y1 = x0 + cell_size, y0 + cell_size
            if (ci + ri) % 2 == 0:
                set_material_color(0.78, 0.68, 0.52)
            else:
                set_material_color(0.68, 0.58, 0.44)
            glBegin(GL_QUADS)
            glVertex3f(x0, y0, 0)
            glVertex3f(x1, y0, 0)
            glVertex3f(x1, y1, 0)
            glVertex3f(x0, y1, 0)
            glEnd()

def draw_lane_lines():
    """Dashed lines along the arena to guide players."""
    glNormal3f(0, 0, 1)
    set_material_color(0.9, 0.9, 0.7)
    lane_y_positions = [-600, -300, 0, 300, 600]
    seg_len  = 120
    seg_gap  = 60
    seg_w    = 6
    x = -ARENA_BASE_LENGTH // 2
    while x < ARENA_BASE_LENGTH // 2:
        x_end = min(x + seg_len, ARENA_BASE_LENGTH // 2)
        for lane_y in lane_y_positions:
            glBegin(GL_QUADS)
            glVertex3f(x,     lane_y - seg_w/2, 0.5)
            glVertex3f(x_end, lane_y - seg_w/2, 0.5)
            glVertex3f(x_end, lane_y + seg_w/2, 0.5)
            glVertex3f(x,     lane_y + seg_w/2, 0.5)
            glEnd()
        x += seg_len + seg_gap

def draw_start_finish_lines():
    half_w    = ARENA_WIDTH / 2
    thickness = 8.0
    start_x   = -ARENA_BASE_LENGTH / 2
    finish_x  =  ARENA_BASE_LENGTH / 2

    glNormal3f(0, 0, 1)
    # White start line
    set_material_color(1, 1, 1)
    glBegin(GL_QUADS)
    glVertex3f(start_x,             -half_w, 1)
    glVertex3f(start_x + thickness, -half_w, 1)
    glVertex3f(start_x + thickness,  half_w, 1)
    glVertex3f(start_x,              half_w, 1)
    glEnd()
    # Red finish line
    set_material_color(1, 0.1, 0.1)
    glBegin(GL_QUADS)
    glVertex3f(finish_x - thickness, -half_w, 1)
    glVertex3f(finish_x,             -half_w, 1)
    glVertex3f(finish_x,              half_w, 1)
    glVertex3f(finish_x - thickness,  half_w, 1)
    glEnd()

def draw_arena_walls():
    hl = ARENA_LENGTH / 2
    hw = ARENA_WIDTH  / 2

    # Right wall  (x = +hl), normal points inward (-x)
    set_material_color(0.76, 0.70, 0.58)
    glNormal3f(-1, 0, 0)
    glBegin(GL_QUADS)
    glVertex3f( hl, -hw, 0);  glVertex3f( hl,  hw, 0)
    glVertex3f( hl,  hw, ARENA_HEIGHT);  glVertex3f( hl, -hw, ARENA_HEIGHT)
    glEnd()

    # Left wall (x = -hl), normal (+x)
    glNormal3f(1, 0, 0)
    glBegin(GL_QUADS)
    glVertex3f(-hl,  hw, 0);  glVertex3f(-hl, -hw, 0)
    glVertex3f(-hl, -hw, ARENA_HEIGHT);  glVertex3f(-hl,  hw, ARENA_HEIGHT)
    glEnd()

    # Far wall (y = +hw), normal (-y)
    set_material_color(0.70, 0.65, 0.54)
    glNormal3f(0, -1, 0)
    glBegin(GL_QUADS)
    glVertex3f(-hl,  hw, 0);  glVertex3f( hl,  hw, 0)
    glVertex3f( hl,  hw, ARENA_HEIGHT);  glVertex3f(-hl,  hw, ARENA_HEIGHT)
    glEnd()

    # Near wall (y = -hw), normal (+y)
    glNormal3f(0, 1, 0)
    glBegin(GL_QUADS)
    glVertex3f( hl, -hw, 0);  glVertex3f(-hl, -hw, 0)
    glVertex3f(-hl, -hw, ARENA_HEIGHT);  glVertex3f( hl, -hw, ARENA_HEIGHT)
    glEnd()

def draw_arena_ceiling():
    glNormal3f(0, 0, -1)
    set_material_color(0.88, 0.86, 0.80)
    glBegin(GL_QUADS)
    glVertex3f(-ARENA_LENGTH/2, -ARENA_WIDTH/2, ARENA_HEIGHT)
    glVertex3f( ARENA_LENGTH/2, -ARENA_WIDTH/2, ARENA_HEIGHT)
    glVertex3f( ARENA_LENGTH/2,  ARENA_WIDTH/2, ARENA_HEIGHT)
    glVertex3f(-ARENA_LENGTH/2,  ARENA_WIDTH/2, ARENA_HEIGHT)
    glEnd()

def draw_arena():
    draw_checkerboard_floor()
    draw_lane_lines()
    draw_start_finish_lines()
    draw_arena_walls()
    draw_arena_ceiling()

# ─────────────────────────────────────────────
#  DRAW PLAYER
# ─────────────────────────────────────────────
def draw_player():
    if not player_visible or player_invisible:
        return

    glPushMatrix()
    glTranslatef(player_x, player_y, player_z)

    if game_over:
        glRotatef(180, 1, 0, 0)
        glTranslatef(0, 0, 30)
        body_color = (0.45, 0.45, 0.45)
        skin_color = (0.75, 0.75, 0.75)
        leg_color  = (0.35, 0.35, 0.35)
    else:
        glRotatef(player_angle, 0, 0, 1)
        body_color = (0.10, 0.55, 0.25)   # green tracksuit
        skin_color = (0.95, 0.78, 0.60)
        leg_color  = (0.08, 0.08, 0.55)

    if camera_mode == 0:
        set_material_color(*body_color)
        glPushMatrix(); glScalef(1, 0.5, 1.5); glutSolidCube(60); glPopMatrix()

        glPushMatrix(); glTranslatef(0, 0, 70)
        set_material_color(0.12, 0.12, 0.12)
        q = gluNewQuadric(); gluSphere(q, 30, 20, 20)
        glPopMatrix()

        set_material_color(*leg_color)
        glPushMatrix(); glTranslatef(-15, 0, -45); glRotatef(180, 1, 0, 0)
        q3 = gluNewQuadric(); gluCylinder(q3, 12, 8, 40, 12, 4); glPopMatrix()

        glPushMatrix(); glTranslatef(15, 0, -45); glRotatef(170, 1, 0, 0)
        q4 = gluNewQuadric(); gluCylinder(q4, 12, 8, 40, 12, 4); glPopMatrix()

    set_material_color(*skin_color)
    glPushMatrix(); glTranslatef(-40, 0, 40); glRotatef(200, 1, 0, 0)
    q5 = gluNewQuadric(); gluCylinder(q5, 8, 5, 40, 10, 4); glPopMatrix()

    glPushMatrix(); glTranslatef(40, 0, 40); glRotatef(200, 1, 0, 0)
    q6 = gluNewQuadric(); gluCylinder(q6, 8, 5, 40, 10, 4); glPopMatrix()

    glPopMatrix()

# ─────────────────────────────────────────────
#  DRAW COIN
# ─────────────────────────────────────────────
def draw_coin(x, y, z):
    glPushMatrix()
    glTranslatef(x, y, z)
    # rotation_angle = (time.time() * 90) % 360
    # glRotatef(rotation_angle, 0, 0, 1)

    set_material_color(1.0, 0.82, 0.0, shininess=60)
    q = gluNewQuadric()
    gluSphere(q, 22, 18, 18)

    # Shiny ring
    set_material_color(1.0, 1.0, 0.5, shininess=90)
    glPushMatrix()
    glRotatef(90, 1, 0, 0)
    gluDisk(q, 18, 25, 20, 2)
    glPopMatrix()

    glPopMatrix()

# ─────────────────────────────────────────────
#  DRAW NPC
# ─────────────────────────────────────────────
def draw_npc(npc):
    if npc.invisible:
        if time.time() > npc.invisible_end_time:
            npc.invisible = False
        else:
            return

    glPushMatrix()
    glTranslatef(npc.x, npc.y, npc.z)
    glRotatef(player_angle, 0, 0, 1)

    # Body color based on speed type
    if npc.speed_type == 'fast':
        body_r, body_g, body_b = 0.85, 0.40, 0.05
    elif npc.speed_type == 'slow':
        body_r, body_g, body_b = 0.20, 0.30, 0.80
    else:
        body_r, body_g, body_b = 0.40, 0.55, 0.10

    set_material_color(body_r, body_g, body_b)
    glPushMatrix(); glScalef(npc.scale_x, npc.scale_y, npc.scale_z); glutSolidCube(60); glPopMatrix()

    # Head
    glPushMatrix(); glTranslatef(0, 0, 70)
    head_colors = {'fat': (0.55, 0.22, 0.22), 'thin': (0.22, 0.45, 0.22), 'normal': (0.15, 0.15, 0.15)}
    set_material_color(*head_colors[npc.width_type])
    q = gluNewQuadric()
    head_size = {'fat': 35, 'thin': 24, 'normal': 29}[npc.width_type]
    gluSphere(q, head_size, 18, 18)
    glPopMatrix()

    # Legs
    leg_colors = {'tall': (0.85, 0.75, 0.0), 'short': (0.75, 0.05, 0.75), 'normal': (0.05, 0.05, 0.65)}
    set_material_color(*leg_colors[npc.height_type])
    leg_len = {'tall': 55, 'short': 30, 'normal': 40}[npc.height_type]

    glPushMatrix(); glTranslatef(-15, 0, -45); glRotatef(180, 1, 0, 0)
    q3 = gluNewQuadric(); gluCylinder(q3, 12, 8, leg_len, 12, 4); glPopMatrix()

    glPushMatrix(); glTranslatef(15, 0, -45); glRotatef(180, 1, 0, 0)
    q4 = gluNewQuadric(); gluCylinder(q4, 12, 8, leg_len, 12, 4); glPopMatrix()

    # Arms
    set_material_color(0.95, 0.80, 0.62)
    glPushMatrix(); glTranslatef(-40, 0, 40); glRotatef(200, 1, 0, 0)
    q5 = gluNewQuadric(); gluCylinder(q5, 8, 5, 40, 10, 4); glPopMatrix()

    glPushMatrix(); glTranslatef(40, 0, 40); glRotatef(200, 1, 0, 0)
    q6 = gluNewQuadric(); gluCylinder(q6, 8, 5, 40, 10, 4); glPopMatrix()

    glPopMatrix()

# ─────────────────────────────────────────────
#  DRAW DOLL
# ─────────────────────────────────────────────
def draw_doll():
    glPushMatrix()
    glTranslatef(doll_x, doll_y, doll_z)
    glRotatef(doll_angle, 0, 0, 1)
    glScalef(2, 2, 2)

    set_material_color(0.90, 0.10, 0.15)
    glPushMatrix(); glScalef(1, 0.5, 1.5); glutSolidCube(60); glPopMatrix()

    glPushMatrix(); glTranslatef(0, 0, 70)
    set_material_color(0.08, 0.08, 0.08)
    q = gluNewQuadric(); gluSphere(q, 30, 20, 20)
    glPopMatrix()

    set_material_color(0.05, 0.05, 0.60)
    for tx, ry in [(-15, 180), (15, 170)]:
        glPushMatrix(); glTranslatef(tx, 0, -45); glRotatef(ry, 1, 0, 0)
        q3 = gluNewQuadric(); gluCylinder(q3, 12, 8, 40, 12, 4); glPopMatrix()

    set_material_color(0.95, 0.80, 0.62)
    for tx, ry in [(-40, 100), (40, 100)]:
        glPushMatrix(); glTranslatef(tx, 0, 40); glRotatef(ry, 1, 0, 0)
        q5 = gluNewQuadric(); gluCylinder(q5, 8, 5, 40, 10, 4); glPopMatrix()

    glPopMatrix()

# ─────────────────────────────────────────────
#  DRAW GUNMAN
# ─────────────────────────────────────────────
def draw_gunman(x, y, z, angle):
    glPushMatrix()
    glTranslatef(x, y, z)
    glRotatef(angle, 0, 0, 1)

    set_material_color(0.55, 0.55, 0.10)
    glPushMatrix(); glScalef(1, 0.5, 1.5); glutSolidCube(60); glPopMatrix()

    glPushMatrix(); glTranslatef(0, 0, 70)
    set_material_color(0.08, 0.08, 0.08)
    q = gluNewQuadric(); gluSphere(q, 30, 20, 20)
    glPopMatrix()

    set_material_color(0.05, 0.05, 0.60)
    for tx, ry in [(-15, 180), (15, 180)]:
        glPushMatrix(); glTranslatef(tx, 0, -45); glRotatef(ry, 1, 0, 0)
        q3 = gluNewQuadric(); gluCylinder(q3, 12, 8, 40, 12, 4); glPopMatrix()

    set_material_color(0.95, 0.80, 0.62)
    for tx, ry in [(-40, -90), (40, -90)]:
        glPushMatrix(); glTranslatef(tx, 0, 40); glRotatef(ry, 1, 0, 0)
        q5 = gluNewQuadric(); gluCylinder(q5, 8, 5, 40, 10, 4); glPopMatrix()

    # Gun barrel
    set_material_color(0.25, 0.25, 0.25, shininess=50)
    glPushMatrix(); glTranslatef(0, 30, 40); glRotatef(-90, 1, 0, 0)
    q2 = gluNewQuadric(); gluCylinder(q2, 7, 3, 70, 16, 4); glPopMatrix()

    glPopMatrix()

# ─────────────────────────────────────────────
#  CAMERA
# ─────────────────────────────────────────────
def setupCamera():
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    aspect = WINDOW_W / float(WINDOW_H) if WINDOW_H else 1
    gluPerspective(fovY, aspect, 0.1, 2000)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    if camera_mode == 0:
        radius = 220
        cam_x = player_x + radius * math.sin(math.radians(camera_rot_y))
        cam_y = player_y + radius * math.cos(math.radians(camera_rot_y))
        cam_z = player_z + 160 + camera_height_offset

        cam_x = max(-ARENA_LENGTH/2 + 50, min(ARENA_LENGTH/2 - 50, cam_x))
        cam_y = max(-ARENA_WIDTH/2  + 50, min(ARENA_WIDTH/2  - 50, cam_y))
        cam_z = max(50, min(ARENA_HEIGHT - 50, cam_z))

        gluLookAt(cam_x, cam_y, cam_z, player_x, player_y, player_z, 0, 0, 1)
    else:
        eye_height = 70
        cam_x = player_x
        cam_y = player_y
        cam_z = max(player_z + 5, player_z + eye_height + camera_height_offset)
        cam_z = max(10, min(ARENA_HEIGHT - 10, cam_z))

        facing_dx = math.sin(math.radians(-player_angle))
        facing_dy = math.cos(math.radians(-player_angle))
        gluLookAt(cam_x, cam_y, cam_z,
                  cam_x + facing_dx * 100, cam_y + facing_dy * 100, cam_z,
                  0, 0, 1)

    # Reposition lights every frame so they stay world-fixed
    glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 1.0, 0.0])
    glLightfv(GL_LIGHT1, GL_POSITION, [1.0, 0.0, 0.3, 0.0])

# ─────────────────────────────────────────────
#  INPUT  (FIXED: proper press/release)
# ─────────────────────────────────────────────
def activate_cheat_mode():
    global cheat_mode, camera_mode
    cheat_mode = not cheat_mode
    if not cheat_mode:
        camera_mode = 0
    print("Cheat mode", "ON" if cheat_mode else "OFF")

def keyboardListener(key, x, y):
    global key_w, key_s, key_a, key_d, camera_mode, shift_pressed

    if key == b'r':
        reset_game()
    elif key == b'w':
        key_w = True
    elif key == b's':
        key_s = True
    elif key == b'a':
        key_a = True
    elif key == b'd':
        key_d = True
    elif key == b'c':
        activate_cheat_mode()
    elif key == b'v':
        camera_mode = 1 - camera_mode
        print("First-person" if camera_mode == 1 else "Third-person")

def keyboardUpListener(key, x, y):
    
    global key_w, key_s, key_a, key_d
    if key == b'w':
        key_w = False
    elif key == b's':
        key_s = False
    elif key == b'a':
        key_a = False
    elif key == b'd':
        key_d = False

def specialKeyListener(key, x, y):
    global camera_rot_y, camera_height_offset, player_angle, camera_mode

    if key == GLUT_KEY_LEFT:
        camera_rot_y -= 5 if camera_mode == 0 else 0
        if camera_mode == 1: player_angle += 5
    elif key == GLUT_KEY_RIGHT:
        camera_rot_y += 5 if camera_mode == 0 else 0
        if camera_mode == 1: player_angle -= 5
    elif key == GLUT_KEY_UP:
        camera_height_offset = min(CAMERA_HEIGHT_MAX, camera_height_offset + 18)
    elif key == GLUT_KEY_DOWN:
        camera_height_offset = max(CAMERA_HEIGHT_MIN, camera_height_offset - 18)
    glutPostRedisplay()

def mouseListener(button, state, x, y):
    global camera_mode
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN:
        camera_mode = 1 - camera_mode
        print("First-person" if camera_mode == 1 else "Third-person")

# ─────────────────────────────────────────────
#  MOVEMENT
# ─────────────────────────────────────────────
def update_player_movement(delta_time):
    global player_x, player_y, player_angle, game_started

    if cheat_mode and light_state == "RED" and game_started:
        return

    current_speed = move_speed
    movement_angle = camera_rot_y if camera_mode == 0 else player_angle

    rad = math.radians(-movement_angle)
    fx, fy = math.sin(rad), math.cos(rad)
    rx, ry = math.cos(rad), -math.sin(rad)

    vx = vy = 0.0

    if cheat_mode and light_state == "GREEN" and game_started:
        vx += fx; vy += fy

    if key_w: vx += fx; vy += fy
    if key_s: vx -= fx; vy -= fy
    if key_d: vx += rx; vy += ry
    if key_a: vx -= rx; vy -= ry

    if vx != 0.0 or vy != 0.0:
        mag = math.sqrt(vx*vx + vy*vy)
        nx = player_x + (vx / mag) * current_speed * delta_time
        ny = player_y + (vy / mag) * current_speed * delta_time

        white_start_line = -ARENA_BASE_LENGTH / 2
        if not game_started and nx > white_start_line:
            nx = white_start_line

        if -ARENA_LENGTH/2 + 30 < nx < ARENA_LENGTH/2 - 30 and is_position_valid(nx, player_y, exclude_player=True):
            player_x = nx
        if -ARENA_WIDTH/2  + 30 < ny < ARENA_WIDTH/2  - 30 and is_position_valid(player_x, ny, exclude_player=True):
            player_y = ny

# ─────────────────────────────────────────────
#  NPC MOVEMENT
# ─────────────────────────────────────────────
def update_npc_movement(delta_time):
    for npc in npcs:
        if game_started:
            if light_state == "GREEN":
                npc.is_moving  = True
                npc.move_timer = random.uniform(3, 8)
            elif light_state == "RED":
                if npc.moves_during_red_light:
                    npc.is_moving  = True
                    npc.move_timer = random.uniform(2, 5)
                elif random.random() < npc.red_light_awareness:
                    npc.is_moving  = False
                    npc.move_timer = random.uniform(0.1, 0.5)

        npc.move_timer -= delta_time
        if npc.move_timer <= 0:
            if not npc.is_moving:
                npc.is_moving  = True
                npc.move_timer = random.uniform(2, 6)
            else:
                if random.random() < 0.2:
                    npc.is_moving  = False
                    npc.move_timer = random.uniform(0.2, 1.0)
                else:
                    npc.move_timer = random.uniform(2, 6)

        npc.direction_change_timer -= delta_time
        if npc.direction_change_timer <= 0:
            angle_diff = npc.angle - npc.base_forward_angle
            while angle_diff >  180: angle_diff -= 360
            while angle_diff < -180: angle_diff += 360
            cf = npc.angle_correction_strength * (2 if abs(angle_diff) > 45 else 1)
            npc.angle += -angle_diff * cf + random.uniform(-15, 15) * npc.lateral_drift
            npc.angle  = max(npc.base_forward_angle - 60,
                             min(npc.base_forward_angle + 60, npc.angle))
            npc.direction_change_timer = random.uniform(1, 3)

        if not npc.is_hesitating and random.random() < 0.003:
            npc.is_hesitating  = True
            npc.hesitation_timer = random.uniform(0.1, 0.5)
        if npc.is_hesitating:
            npc.hesitation_timer -= delta_time
            if npc.hesitation_timer <= 0:
                npc.is_hesitating = False

        if not npc.is_panicking and random.random() < npc.panic_chance * 0.5:
            npc.is_panicking = True
            npc.panic_timer  = random.uniform(0.3, 1.0)
        if npc.is_panicking:
            npc.panic_timer -= delta_time
            if npc.panic_timer <= 0:
                npc.is_panicking = False
            else:
                npc.angle += random.uniform(-10, 10)

        if npc.stumble_timer <= 0 and random.random() < npc.stumble_chance * 0.5:
            npc.stumble_timer = random.uniform(0.05, 0.3)
        if npc.stumble_timer > 0:
            npc.stumble_timer -= delta_time

        speed_mod = 1.0
        if game_started and light_state == "GREEN":
            speed_mod *= npc.green_light_urgency
        ad = abs(npc.angle - npc.base_forward_angle)
        speed_mod *= 1.0 + npc.forward_bias * (1.0 - ad / 90.0)
        if npc.is_hesitating: speed_mod *= 0.7
        if npc.is_panicking:  speed_mod *= 1.3

        npc.speed_noise_target = npc.base_speed * speed_mod * (1 + random.uniform(-0.05, 0.05))
        npc.speed += (npc.speed_noise_target - npc.speed) * min(1.0, 5.0 * delta_time)

        if npc.is_moving:
            eff_speed = npc.speed * (0.6 if npc.stumble_timer > 0 else 1.0)
            fwd  = eff_speed * npc.forward_bias
            lat  = eff_speed * (1.0 - npc.forward_bias)
            dx = (fwd * math.sin(math.radians(-npc.base_forward_angle))
                + lat * math.sin(math.radians(-npc.angle))) * delta_time
            dy = (fwd * math.cos(math.radians(-npc.base_forward_angle))
                + lat * math.cos(math.radians(-npc.angle))) * delta_time
            nx, ny = npc.x + dx, npc.y + dy
            if not game_started and nx > -ARENA_BASE_LENGTH / 2:
                nx = -ARENA_BASE_LENGTH / 2
            if -ARENA_LENGTH/2+30 < nx < ARENA_LENGTH/2-30 and is_position_valid(nx, npc.y, exclude_npcs=[npc]):
                npc.x = nx
            if -ARENA_WIDTH/2 +30 < ny < ARENA_WIDTH/2 -30 and is_position_valid(npc.x, ny, exclude_npcs=[npc]):
                npc.y = ny

# ─────────────────────────────────────────────
#  BULLETS
# ─────────────────────────────────────────────
def fire_targeted_bullets(target_x, target_y, target_z):
    red_speed = BULLET_SPEED * 5.0
    for gx, gy, gz in [(gunman1_x, gunman1_y, gunman1_z),
                       (gunman2_x, gunman2_y, gunman2_z)]:
        dx, dy, dz = target_x - gx, target_y - gy, target_z - gz
        dist = math.sqrt(dx**2 + dy**2 + dz**2)
        if dist > 0:
            dx /= dist; dy /= dist; dz /= dist
            off = 60
            bullets.append({
                'x': gx + dx*off, 'y': gy + dy*off, 'z': gz + dz*off,
                'dx': dx*red_speed, 'dy': dy*red_speed, 'dz': dz*red_speed,
                'lifetime': 5.0
            })

def update_bullets(delta_time):
    for b in bullets[:]:
        b['x'] += b['dx'] * delta_time
        b['y'] += b['dy'] * delta_time
        b['z'] += b['dz'] * delta_time
        b['lifetime'] -= delta_time
        if b['lifetime'] <= 0:
            bullets.remove(b)

def point_segment_dist(px, py, pz, bx, by, bz, nx, ny, nz):
    abx, aby, abz = nx - bx, ny - by, nz - bz
    apx, apy, apz = px - bx, py - by, pz - bz
    c1 = apx*abx + apy*aby + apz*abz
    if c1 <= 0:
        return math.sqrt(apx**2 + apy**2 + apz**2)
    c2 = abx**2 + aby**2 + abz**2
    if c2 <= c1:
        return math.sqrt((px-nx)**2 + (py-ny)**2 + (pz-nz)**2)
    b_val = c1 / c2
    proj_x = bx + b_val * abx
    proj_y = by + b_val * aby
    proj_z = bz + b_val * abz
    return math.sqrt((px-proj_x)**2 + (py-proj_y)**2 + (pz-proj_z)**2)

def check_bullet_collision(delta_time):
    global player_dead, player_status, game_state, game_over, player_visible
    for b in bullets[:]:
        hit = False
        nx = b['x'] + b['dx']*delta_time
        ny = b['y'] + b['dy']*delta_time
        nz = b['z'] + b['dz']*delta_time
        if not player_invisible and not player_dead:
            if point_segment_dist(player_x, player_y, player_z, b['x'], b['y'], b['z'], nx, ny, nz) < 40:
                hit = True
                player_dead    = True
                player_status  = "Dead"
                game_state     = "Dead"
                game_over      = True
                player_visible = False
        if hit:
            if b in bullets:
                bullets.remove(b)
            continue
            
        for npc in npcs[:]:
            if not npc.invisible:
                if point_segment_dist(npc.x, npc.y, npc.z, b['x'], b['y'], b['z'], nx, ny, nz) < 40:
                    if b in bullets:
                        bullets.remove(b)
                    npcs.remove(npc)
                    break

# ─────────────────────────────────────────────
#  COINS / COLLISIONS
# ─────────────────────────────────────────────
def check_coin_collection():
    global player_invisible, player_invisible_end_time
    current_time = time.time()
    for coin in coins[:]:
        cx, cy, cz = coin
        if math.sqrt((player_x-cx)**2 + (player_y-cy)**2 + (player_z-cz)**2) < 80:
            player_invisible          = True
            player_invisible_end_time = current_time + 4
            print("Player invisible for 4 s")
            coins.remove(coin)
            coins.append((
                random.uniform(-ARENA_BASE_LENGTH/2+100, ARENA_BASE_LENGTH/2-100),
                random.uniform(-ARENA_WIDTH/2 +100, ARENA_WIDTH/2 -100),
                30
            ))
            break
        else:
            for npc in npcs:
                if math.sqrt((npc.x-cx)**2 + (npc.y-cy)**2 + (npc.z-cz)**2) < 80:
                    npc.invisible          = True
                    npc.invisible_end_time = current_time + 4
                    coins.remove(coin)
                    coins.append((
                        random.uniform(-ARENA_BASE_LENGTH/2+100, ARENA_BASE_LENGTH/2-100),
                        random.uniform(-ARENA_WIDTH/2 +100, ARENA_WIDTH/2 -100),
                        30
                    ))
                    break

def check_player_npc_collision():
    global player_invisible, player_invisible_end_time
    current_time = time.time()
    for npc in npcs:
        if math.sqrt((player_x-npc.x)**2 + (player_y-npc.y)**2 + (player_z-npc.z)**2) < 80:
            player_invisible          = True
            player_invisible_end_time = current_time + 4
            npc.invisible          = True
            npc.invisible_end_time = current_time + 4
            break

# ─────────────────────────────────────────────
#  GAME STATE UPDATE
# ─────────────────────────────────────────────
def update_game_state():
    global game_state, light_state, light_timer, light_switch_time
    global countdown_timer, countdown_start_time, game_started, game_timer, game_start_time
    global player_status, player_prev_x, player_prev_y, player_dead
    global player_invisible, player_invisible_end_time
    global last_update_time, doll_angle, red_ref_x, red_ref_y
    global player_visible, targets_shot_at, game_over

    current_time  = time.time()
    delta_time    = current_time - last_update_time
    last_update_time = current_time

    check_bullet_collision(delta_time)
    update_bullets(delta_time)

    if game_state in ("Dead", "Win"):
        return

    update_player_movement(delta_time)

    for npc in npcs:
        npc.prev_x, npc.prev_y = npc.x, npc.y
    update_npc_movement(delta_time)

    if not game_started:
        if countdown_start_time == 0:
            countdown_start_time = current_time
        countdown_timer = max(0, 5.0 - (current_time - countdown_start_time))
        if countdown_timer <= 0:
            game_started    = True
            game_start_time = current_time
            light_switch_time = current_time
            light_timer = random.uniform(3, 8)
        return

    game_timer = max(0, 60.0 - (current_time - game_start_time))

    light_timer -= delta_time
    if light_timer <= 0:
        if light_state == "GREEN":
            light_state = "RED"
            doll_angle += 180
            red_ref_x, red_ref_y = player_x, player_y
            for npc in npcs:
                npc.red_ref_x, npc.red_ref_y = npc.x, npc.y
            targets_shot_at.clear()
        else:
            light_state = "GREEN"
        light_switch_time = current_time
        light_timer = random.uniform(3, 8)

    # ── Invisibility expiry: reset ref so player is re-detectable ──
    if player_invisible and current_time > player_invisible_end_time:
        player_invisible = False
        if light_state == "RED":
            red_ref_x = player_x
            red_ref_y = player_y
            targets_shot_at.discard("player")

    # ── RED LIGHT VIOLATION → INSTANT DEATH ──
    # Runs BEFORE the finish-line check so moving during red light
    # while near the finish still kills — no bullet travel race condition.
    if light_state == "RED" and game_started:
        if not player_invisible and not cheat_mode:
            if red_ref_x is None:
                red_ref_x, red_ref_y = player_x, player_y
            dist_moved = math.sqrt((player_x - red_ref_x)**2 + (player_y - red_ref_y)**2)
            if dist_moved > movement_threshold and "player" not in targets_shot_at:
                fire_targeted_bullets(player_x, player_y, player_z)
                targets_shot_at.add("player")

        for npc in npcs[:]:
            if not npc.invisible and hasattr(npc, 'red_ref_x'):
                d = math.sqrt((npc.x - npc.red_ref_x)**2 + (npc.y - npc.red_ref_y)**2)
                nid = id(npc)
                if d > movement_threshold and nid not in targets_shot_at:
                    fire_targeted_bullets(npc.x, npc.y, npc.z)
                    targets_shot_at.add(nid)

    # ── Win: only reached if player survived the red-light check ──
    finish_x = ARENA_BASE_LENGTH / 2
    if player_x >= finish_x and player_status == "Alive":
        player_status = "Win"
        game_state    = "Win"
        return

    for npc in npcs[:]:
        if npc.x >= finish_x:
            npcs.remove(npc)

    player_prev_x, player_prev_y = player_x, player_y

    if game_timer <= 0 and player_status == "Alive":
        player_status = "Dead"
        player_dead   = True
        game_state    = "Dead"
        game_over     = True

# ─────────────────────────────────────────────
#  HUD
# ─────────────────────────────────────────────
def draw_text(x, y, text, r=1.0, g=1.0, b=1.0):
    glColor3f(r, g, b)
    glWindowPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(GLUT_BITMAP_HELVETICA_18, ord(ch))

def draw_text_big(x, y, text, font=GLUT_BITMAP_TIMES_ROMAN_24, r=1, g=1, b=1):
    glColor3f(r, g, b)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WINDOW_W, 0, WINDOW_H)
    glMatrixMode(GL_MODELVIEW);  glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW)

def draw_hud():
    glDisable(GL_LIGHTING)   # HUD is flat — lighting off

    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    glOrtho(0, WINDOW_W, 0, WINDOW_H, -1, 1)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()

    # ── Status (top-left) ──────────────────────────────
    status_r, status_g, status_b = (0.0, 1.0, 0.3) if player_status == "Alive" else (1.0, 0.2, 0.2)
    draw_text(14, WINDOW_H - 30,  f"Status: {player_status}", status_r, status_g, status_b)

    if game_started:
        dist = max(0, ARENA_BASE_LENGTH/2 - player_x)
        draw_text(14, WINDOW_H - 56,  f"Distance: {int(dist)}")
        draw_text(14, WINDOW_H - 82,  f"NPCs left: {len(npcs)}")

    # Coin info
    coin_y = WINDOW_H - 108
    if player_invisible:
        remaining = max(0, player_invisible_end_time - time.time())
        draw_text(14, coin_y, f"Invisible: {remaining:.1f}s", 0.0, 1.0, 1.0)
        coin_y -= 26
    inv_npcs = sum(1 for n in npcs if n.invisible)
    if inv_npcs > 0:
        draw_text(14, coin_y, f"Invisible NPCs: {inv_npcs}", 0.0, 1.0, 1.0)
        coin_y -= 26
    draw_text(14, coin_y, f"Coins: {len(coins)}", 1.0, 0.84, 0.0)

    # ── Controls legend (bottom-left) ──────────────────
    controls = ["WASD – Move", "Arrow – Camera", "V – View", "C – Cheat", "R – Restart"]
    for i, txt in enumerate(controls):
        draw_text(14, 14 + i*22, txt, 0.7, 0.7, 0.7)

    # ── Centre: countdown or timer ──────────────────────
    if not game_started:
        msg = f"Starts in {int(countdown_timer) + 1}"
        draw_text_big(WINDOW_W/2 - len(msg)*7, WINDOW_H - 50, msg, r=1, g=1, b=0)

        instrs = [
            "Run during GREEN light  —  freeze during RED light.",
            "Moving during red light  =  the gunmen shoot you.",
            "Cross the red finish line within 60 s to win.",
            "Gold coins grant 4 s of invisibility.",
            "V toggles 1st/3rd person",
        ]

        # Dark panel behind instructions for readability
        panel_x1 = WINDOW_W/2 - 360
        panel_x2 = WINDOW_W/2 + 360
        panel_y1 = WINDOW_H - 310
        panel_y2 = WINDOW_H - 145
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 0.0, 0.0, 0.65)
        glBegin(GL_QUADS)
        glVertex2f(panel_x1, panel_y1); glVertex2f(panel_x2, panel_y1)
        glVertex2f(panel_x2, panel_y2); glVertex2f(panel_x1, panel_y2)
        glEnd()
        glDisable(GL_BLEND)

        for i, line in enumerate(instrs):
            draw_text(WINDOW_W/2 - 340, WINDOW_H - 180 - i*28, line, 1.0, 1.0, 0.85)
    else:
        timer_text = f"{int(game_timer)}"
        clr = (1, 0.2, 0.2) if game_timer <= 10 else (1, 1, 1)
        draw_text_big(WINDOW_W/2 - len(timer_text)*9, WINDOW_H - 48, timer_text, r=clr[0], g=clr[1], b=clr[2])

        # Light indicator circle
        cx, cy, cr = WINDOW_W/2, WINDOW_H - 95, 16
        if light_state == "GREEN":
            glColor3f(0.0, 1.0, 0.1)
        else:
            glColor3f(1.0, 0.1, 0.1)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(cx, cy)
        for i in range(33):
            a = i * 2 * math.pi / 32
            glVertex2f(cx + cr*math.cos(a), cy + cr*math.sin(a))
        glEnd()

        if light_state == "GREEN":
            lbl = "GREEN LIGHT" + (" [AUTO-MOVE]" if cheat_mode else "")
            draw_text(WINDOW_W/2 - len(lbl)*4.5, WINDOW_H - 80, lbl, 0.0, 1.0, 0.2)
        else:
            lbl = "RED LIGHT" + (" [AUTO-STOP]" if cheat_mode else "")
            draw_text(WINDOW_W/2 - len(lbl)*4.5, WINDOW_H - 80, lbl, 1.0, 0.1, 0.1)

    # ── Game over overlays ──────────────────────────────
    if game_state == "Dead":
        draw_text_big(WINDOW_W/2 - 180, WINDOW_H/2 + 30, "YOU LOST!", r=1, g=0.1, b=0.1)
        draw_text_big(WINDOW_W/2 - 180, WINDOW_H/2 - 20, "Press R to Restart", r=1, g=1, b=1)
    elif game_state == "Win":
        draw_text_big(WINDOW_W/2 - 200, WINDOW_H/2 + 30, "YOU WON!", r=0.1, g=1, b=0.2)
        draw_text_big(WINDOW_W/2 - 200, WINDOW_H/2 - 20, "Press R to Restart", r=1, g=1, b=1)

    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW);  glPopMatrix()

    glEnable(GL_LIGHTING)    # restore lighting for 3-D objects

# ─────────────────────────────────────────────
#  DEPTH-SORTED DRAW  (fixed: store refs not indices)
# ─────────────────────────────────────────────
def calc_dist(x, y, z):
    if camera_mode == 0:
        radius = 220
        cx = player_x + radius * math.sin(math.radians(camera_rot_y))
        cy = player_y + radius * math.cos(math.radians(camera_rot_y))
        cz = player_z + 160 + camera_height_offset
    else:
        cx, cy, cz = player_x, player_y, player_z + 70 + camera_height_offset
    return math.sqrt((x-cx)**2 + (y-cy)**2 + (z-cz)**2)

def draw_objects_by_depth():
    objects = []

    objects.append(('arena',   None,   float('inf')))

    if player_visible and not player_invisible:
        objects.append(('player', None,   calc_dist(player_x, player_y, player_z)))

    for npc in npcs:
        if not npc.invisible:
            objects.append(('npc',  npc,  calc_dist(npc.x, npc.y, npc.z)))

    objects.append(('doll',    None,   calc_dist(doll_x,    doll_y,    doll_z)))
    objects.append(('gunman1', None,   calc_dist(gunman1_x, gunman1_y, gunman1_z)))
    objects.append(('gunman2', None,   calc_dist(gunman2_x, gunman2_y, gunman2_z)))

    for coin in coins:
        objects.append(('coin', coin, calc_dist(coin[0], coin[1], coin[2])))

    for b in bullets:
        objects.append(('bullet', b, calc_dist(b['x'], b['y'], b['z'])))

    objects.sort(key=lambda o: o[2], reverse=True)

    for kind, ref, _ in objects:
        if   kind == 'arena':   draw_arena()
        elif kind == 'player':  draw_player()
        elif kind == 'npc':     draw_npc(ref)
        elif kind == 'doll':    draw_doll()
        elif kind == 'gunman1': draw_gunman(gunman1_x, gunman1_y, gunman1_z, gunman1_angle)
        elif kind == 'gunman2': draw_gunman(gunman2_x, gunman2_y, gunman2_z, gunman2_angle)
        elif kind == 'coin':    draw_coin(ref[0], ref[1], ref[2])
        elif kind == 'bullet':
            glPushMatrix()
            glTranslatef(ref['x'], ref['y'], ref['z'])
            set_material_color(1.0, 0.15, 0.0, shininess=80)
            glutSolidSphere(BULLET_SIZE, 12, 12)
            # Bright core
            set_material_color(1.0, 0.8, 0.2, shininess=100)
            glutSolidSphere(BULLET_SIZE * 0.5, 8, 8)
            glPopMatrix()

# ─────────────────────────────────────────────
#  MAIN DISPLAY CALLBACK
# ─────────────────────────────────────────────
def reshapeListener(w, h):
    global WINDOW_W, WINDOW_H
    WINDOW_W = w
    WINDOW_H = max(h, 1)   # avoid divide-by-zero
    glViewport(0, 0, WINDOW_W, WINDOW_H)

def showScreen():
    update_game_state()
    check_coin_collection()
    check_player_npc_collision()

    glClearColor(0.55, 0.52, 0.46, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_W, WINDOW_H)
    setupCamera()

    draw_objects_by_depth()
    draw_hud()
    glutSwapBuffers()

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_W, WINDOW_H)
    glutInitWindowPosition(50, 50)
    glutCreateWindow(b"Red Light Green Light")

    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glShadeModel(GL_SMOOTH)
    setup_lighting()

    glutDisplayFunc(showScreen)
    glutIdleFunc(showScreen)
    glutReshapeFunc(reshapeListener)
    glutKeyboardFunc(keyboardListener)
    glutKeyboardUpFunc(keyboardUpListener)   # ← was missing entirely
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    glutMainLoop()

if __name__ == "__main__":
    main()