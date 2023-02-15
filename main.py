#!/bin/python

import pygame
import random
# Costants
width = 800
height = 800
population_number = 800
start_point = [400, 400] # X, Y

# Variables
ants = []
barriers = []
foods = []
anthills = []
anthill_pheromone_trace = []
food_pheromone_trace = []

pygame.init()
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption('Ant Simulation GUI')
clock = pygame.time.Clock()


class ant_class():
    def __init__(self, position_x, position_y, start_direction, food_found):
        self.position_x      = position_x 
        self.position_y      = position_y
        self.start_direction = start_direction
        self.food_found     = food_found

class barrier():
    def __init__(self, start, end, rect, size):
        self.start = start
        self.end   = end
        self.rect  = rect
        self.size  = size
    def Draw(self, screen):
        pygame.draw.rect(screen, (150,255,150), self.rect)

class food():
    def __init__(self, start, rect, size):
        self.start = start
        self.rect  = rect
        self.size  = size
    def Draw(self, screen):
        pygame.draw.rect(screen, (255,255,150), self.rect)

class anthill_pheromone():
    def __init__(self, start, rect, size, time):
        self.start = start
        self.rect  = rect
        self.size  = size
        self.time  = time
    def Draw(self, screen):
        pygame.draw.rect(screen, (20,0,0), self.rect)

class food_pheromone():
    def __init__(self, start, rect, size, time):
        self.start = start
        self.rect  = rect
        self.size  = size
        self.time  = time
    def Draw(self, screen):
        pygame.draw.rect(screen, (100,100,0), self.rect)


class anthill():
    def __init__(self, start, rect, size):
        self.start = start
        self.rect  = rect
        self.size  = size
    def Draw(self, screen):
        pygame.draw.rect(screen, (255,0,0), self.rect)
    def Spawn(self):
        pass

def barrier_creation(event):
    global drawing 
    global start
    drawing = False
 
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 1:
            start = event.pos # X, Y of start point of the rect
            drawing = True
            print(start)
    elif event.type == pygame.MOUSEBUTTONUP:
        if event.button == 1:
            end = event.pos   # X, Y of end point of the rect
            size = end[0]-start[0], end[1]-start[1] # Calculate the size
            rect = pygame.Rect(start, size)
            block = barrier(start, end, rect, size)
            barriers.append(block)
            #print(start, size)
            print(barriers)
            drawing = False

def food_creation(event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 3:
            size = 10, 10
            start = event.pos # X, Y of start point of the rect
            rect = pygame.Rect(start, size)
            food_bit = food(start, rect, 20) 
            foods.append(food_bit) 

def anthill_creation(event):
    if event.type == pygame.MOUSEBUTTONDOWN:
        if event.button == 2:
            size = 10, 10
            start = event.pos # X, Y of start point of the rect
            rect = pygame.Rect(start, size)
            anthill_c = anthill(start, rect, 20) 
            anthills.append(anthill_c) 
            ant_creation(population_number) 

def ant_creation(population_number):
    global ants
    for _ in range(population_number):
        #                   position_x          position_y                          start direction               food
        ant = ant_class(anthills[0].start[0], anthills[0].start[1], [random.randint(-2,2), random.randint(-2,2)], False) 
        ants.append(ant) 

def anthill_pheromone_creation():
    size = 2, 2
    for ant in ants:
        if ant.food_found == False:
            start = [ant.position_x, ant.position_y]
            rect = pygame.Rect(start, size)
            anthill_pheromone_bit = anthill_pheromone(start, rect, 2, 0) 
            anthill_pheromone_trace.append(anthill_pheromone_bit) 

def food_pheromone_creation():
    size = 2, 2
    for ant in ants:
        if ant.food_found == True:
            start = [ant.position_x, ant.position_y]
            rect = pygame.Rect(start, size)
            food_pheromone_bit = food_pheromone(start, rect, 2, 0) 
            food_pheromone_trace.append(food_pheromone_bit) 

def ants_movement():
    global ants
    for ant in ants:
        if ant.food_found == False or ant.food_found == True:
            ant.position_x += random.choice([random.randint(-2,2), ant.start_direction[0]])
            ant.position_y += random.choice([random.randint(-2,2), ant.start_direction[1]])
        #elif ant.food_found == True: # FIX
        #    for food in food_pheromone_trace:
        #        if (ant.position_x in range(food.start[0]-2, food.start[0]) and 
        #            ant.position_y in range(food.start[1], food.start[1] + food.size)): # Check left side
        #                ant.start_direction = [random.randint(-2,0), random.randint(-2,2)] 

        #        if (ant.position_y in range(food.start[1]-2, food.start[1]) and 
        #            ant.position_x in range(food.start[0], food.start[0] + food.size)): # Check upper side
        #                ant.start_direction = [random.randint(-2,2), random.randint(-2,0)] 

        #        if (ant.position_x in range(food.start[0]+food.size, food.start[0]+food.size+2) and 
        #            ant.position_y in range(food.start[1], food.start[1] + food.size)): # Check right side
        #                ant.start_direction = [random.randint(0,2), random.randint(-2,2)] 

        #        if (ant.position_y in range(food.start[1]+food.size, food.start[1]+food.size+2) and 
        #            ant.position_x in range(food.start[0], food.start[0] + food.size)): # Check down side
        #                ant.start_direction = [random.randint(-2,2), random.randint(0,2)] 

def ants_collision():
    for ant in ants:
        if ant.position_x > width-2 or ant.position_y > height-2:
            ant.start_direction = [random.randint(-2,0), random.randint(-2,0)] 
        if ant.position_x < 2 or ant.position_y < 2:
            ant.start_direction = [random.randint(0,2), random.randint(0,2)] 
        for barrier in barriers:
            # barrier.start[0] = barrier x position 
            # barrier.start[1] = barrier y position 
            # barrier.size[0]  = barrier length in x axys
            # barrier.size[1]  = barrier length in y axys
            
            if (ant.position_x in range(barrier.start[0]-4, barrier.start[0]) and 
                ant.position_y in range(barrier.start[1], barrier.start[1] + barrier.size[1])): # Check left side
                    ant.start_direction = [random.randint(-2,0), random.randint(-2,2)] 

            if (ant.position_y in range(barrier.start[1]-4, barrier.start[1]) and 
                ant.position_x in range(barrier.start[0], barrier.start[0] + barrier.size[0])): # Check upper side
                    ant.start_direction = [random.randint(-2,2), random.randint(-2,0)] 

            if (ant.position_x in range(barrier.start[0]+barrier.size[0], barrier.start[0]+barrier.size[0]+4) and 
                ant.position_y in range(barrier.start[1], barrier.start[1] + barrier.size[1])): # Check right side
                    ant.start_direction = [random.randint(0,2), random.randint(-2,2)] 

            if (ant.position_y in range(barrier.start[1]+barrier.size[1], barrier.start[1]+barrier.size[1]+4) and 
                ant.position_x in range(barrier.start[0], barrier.start[0] + barrier.size[0])): # Check down side
                    ant.start_direction = [random.randint(-2,2), random.randint(0,2)] 
                        
        for food in foods:
            if (ant.position_x in range(food.start[0]-4, food.start[0]) and 
                ant.position_y in range(food.start[1], food.start[1] + food.size)): # Check left side
                    ant.start_direction = [random.randint(-2,0), random.randint(-2,2)] 
                    ant.food_found = True

            if (ant.position_y in range(food.start[1]-4, food.start[1]) and 
                ant.position_x in range(food.start[0], food.start[0] + food.size)): # Check upper side
                    ant.start_direction = [random.randint(-2,2), random.randint(-2,0)] 
                    ant.food_found = True

            if (ant.position_x in range(food.start[0]+food.size, food.start[0]+food.size+4) and 
                ant.position_y in range(food.start[1], food.start[1] + food.size)): # Check right side
                    ant.start_direction = [random.randint(0,2), random.randint(-2,2)] 
                    ant.food_found = True

            if (ant.position_y in range(food.start[1]+food.size, food.start[1]+food.size+4) and 
                ant.position_x in range(food.start[0], food.start[0] + food.size)): # Check down side
                    ant.start_direction = [random.randint(-2,2), random.randint(0,2)] 
                    ant.food_found = True

def start_window():
    done = False
    #start = (0,0)
    #size = (0,0)

    while not done:
        screen.fill((0,40,0))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
            barrier_creation(event)
            food_creation(event)
            if len(anthills) < 1:
                anthill_creation(event)
            
        for ant in ants:
            #print(ant.food_found)
            pygame.draw.rect(screen, 'red', pygame.Rect(ant.position_x, ant.position_y, 2, 2)) 
        for _ in barriers:
            bar = _.Draw(screen)
        for _ in foods:
            bar = _.Draw(screen)
        for _ in anthills:
            bar = _.Draw(screen)
        for _ in anthill_pheromone_trace:
            bar = _.Draw(screen) 
            _.time += 1
        for _ in food_pheromone_trace:
            bar = _.Draw(screen) 
            _.time += 1

        anthill_pheromone_creation()
        food_pheromone_creation()

        pygame.display.flip()
        ants_movement()
        ants_collision()
        clock.tick(60)

        #for _ in ants:
        #    print(_.food_found)
        #print('_'*20)

if '__main__' == __name__:
    #ant_creation(population_number, start_point)
    start_window()

# END FILE
