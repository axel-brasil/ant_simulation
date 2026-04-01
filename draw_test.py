#!/bin/python

import pygame
from pygame.locals import *

RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (127, 127, 127)

pygame.init()
screen = pygame.display.set_mode((640, 440))

start = (0, 0)
size = (0, 0)

drawing = False
rect_list = []
running = True

while running:
    for event in pygame.event.get():
        print(event)
        if event.type == QUIT:
            running = False
        elif event.type == MOUSEBUTTONDOWN:
            start = event.pos
            size = 0, 0
            drawing = True
        elif event.type == MOUSEMOTION and drawing:
            end = event.pos
            size = abs(end[0]-start[0]), abs(end[1]-start[1])
        elif event.type == MOUSEBUTTONUP:
            end = event.pos
            size = abs(end[0]-start[0]), abs(end[1]-start[1])
            rect = pygame.Rect(start, size)
            rect_list.append(rect)
            drawing = False

    screen.fill(GRAY)

    # Draw rect size while drawing
    pygame.draw.rect(screen, BLUE, (start, size), 1)

    for rect in rect_list:
        pygame.draw.rect(screen, RED, rect, 3)
    pygame.display.update()

pygame.quit()
