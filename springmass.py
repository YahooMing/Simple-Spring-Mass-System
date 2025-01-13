import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np

# Stałe fizyczne
GRAVITY = np.array([0, -9.8, 0], dtype=float)  # Gravity in Y scale
TIME_STEP = 0.016  # 60 FPS
DRAG = 0.98  # suppression 1
SPRING_CONSTANT = 50.0
DAMPING = 0.98  # suppresion 2

# Resolutio
WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080

# Obiekty fizyczne
class Mass:
    def __init__(self, position, movable=True):
        self.position = np.array(position, dtype=float)
        self.prev_position = np.array(position, dtype=float)
        self.force = np.zeros(3, dtype=float)
        self.movable = movable

    def update(self):
        if self.movable:
            # Verlet
            temp = np.copy(self.position)
            self.position = (2 * self.position - self.prev_position) * DRAG + self.force * TIME_STEP**2
            self.prev_position = temp
            self.force = np.zeros(3, dtype=float)  # zeroing force

class Spring:
    def __init__(self, mass1, mass2, rest_length):
        self.mass1 = mass1
        self.mass2 = mass2
        self.rest_length = rest_length

    def apply_force(self):
        delta = self.mass2.position - self.mass1.position
        distance = np.linalg.norm(delta)
        if distance > 0:
            force = SPRING_CONSTANT * (distance - self.rest_length) * delta / distance
            relative_velocity = (self.mass2.position - self.mass2.prev_position) - \
                                (self.mass1.position - self.mass1.prev_position)
            damping_force = DAMPING * relative_velocity * delta / distance

            self.mass1.force += force + damping_force
            self.mass2.force -= force + damping_force

# Pygame and OpenGL init
def init_screen():
    pygame.init()
    display = (WINDOW_WIDTH, WINDOW_HEIGHT)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    gluPerspective(45, (display[0] / display[1]), 0.1, 100.0)
    glTranslatef(0.0, 0.0, -20)

# mass render
def render_mass(mass, size=0.5):
    x, y, z = mass.position
    half_size = size / 2

    vertices = [
        [x - half_size, y - half_size, z - half_size],
        [x + half_size, y - half_size, z - half_size],
        [x + half_size, y + half_size, z - half_size],
        [x - half_size, y + half_size, z - half_size],
        [x - half_size, y - half_size, z + half_size],
        [x + half_size, y - half_size, z + half_size],
        [x + half_size, y + half_size, z + half_size],
        [x - half_size, y + half_size, z + half_size],
    ]

    edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]

    glBegin(GL_LINES)
    glColor3f(1, 0, 0)
    for edge in edges:
        for vertex in edge:
            glVertex3fv(vertices[vertex])
    glEnd()

# spring render
def render_spring(spring):
    glBegin(GL_LINES)
    glColor3f(0, 1, 0)
    glVertex3fv(spring.mass1.position)
    glVertex3fv(spring.mass2.position)
    glEnd()

# mouse
def get_mouse_world_position(mouse_x, mouse_y):
    world_x = (mouse_x / WINDOW_WIDTH) * 20 - 10  # [-10, 10]
    world_y = -(mouse_y / WINDOW_HEIGHT) * 20 + 10  # [10, -10]
    return np.array([world_x, world_y, 0])

# Renderowanie tekstu
def render_text(text, position, font_size=24, color=(255, 255, 255)):
    font = pygame.font.SysFont("Arial", font_size)
    text_surface = font.render(text, True, color, (0, 0, 0, 0))  # Przezroczyste tło
    text_data = pygame.image.tostring(text_surface, "RGBA", True)
    glWindowPos2d(*position)
    glDrawPixels(text_surface.get_width(), text_surface.get_height(), GL_RGBA, GL_UNSIGNED_BYTE, text_data)

# Główna pętla
def main():
    init_screen()

    masses = [
        Mass([0, 5, 0], movable=False),
        Mass([0, 0, 0]),  # the middle one
        Mass([-5, -5, 0], movable=False),
        Mass([5, -5, 0], movable=False)
    ]

    springs = [
        Spring(masses[0], masses[1], 5),
        Spring(masses[1], masses[2], 7),
        Spring(masses[1], masses[3], 7)
    ]

    dragging = None
    wind_active = False
    wind_force = np.array([0, 0, 0], dtype=float)
    camera_angle = [0, 0]

    while True:
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                return
            elif event.type == MOUSEBUTTONDOWN:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                mouse_pos = get_mouse_world_position(mouse_x, mouse_y)
                for mass in masses:
                    if np.linalg.norm(mass.position - mouse_pos) < 1.0:
                        dragging = mass
                        break
            elif event.type == MOUSEBUTTONUP:
                dragging = None
            elif event.type == KEYDOWN:
                if event.key == K_w:  # On and off the wind
                    wind_active = not wind_active
                elif event.key == K_1:
                    camera_angle = [0, 0]
                elif event.key == K_2:
                    camera_angle = [30, 0]
                elif event.key == K_3:
                    camera_angle = [-30, 0]
                elif event.key == K_4:
                    camera_angle = [0, 30]

        if dragging:
            mouse_x, mouse_y = pygame.mouse.get_pos()
            dragging.position = get_mouse_world_position(mouse_x, mouse_y)

        if wind_active:
            wind_force = np.random.uniform(-100, 100, size=3)
        else:
            wind_force = np.zeros(3)

        for spring in springs:
            spring.apply_force()

        for mass in masses:
            mass.force += GRAVITY
            if wind_active and mass is masses[1]:
                mass.force += wind_force
            mass.update()

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluPerspective(45, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 100.0)
        glTranslatef(0.0, 0.0, -20)
        glRotatef(camera_angle[0], 1, 0, 0)
        glRotatef(camera_angle[1], 0, 1, 0)

        for spring in springs:
            render_spring(spring)
        for mass in masses:
            render_mass(mass)

        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WINDOW_WIDTH, WINDOW_HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        status_text = "Wind: ON" if wind_active else "Wind: OFF"
        render_text(status_text, position=(10, 10), color=(255,0,0))

        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

        pygame.display.flip()
        pygame.time.wait(int(TIME_STEP * 1000))


if __name__ == "__main__":
    main()
