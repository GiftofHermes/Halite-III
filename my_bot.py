#!/usr/bin/env python3

# Import the Halite SDK, which will let you interact with the game.
import hlt
from hlt import constants
from hlt import constants  # halite constants
from hlt.positionals import Direction, Position  # helper for moving
import random
import logging
from random import shuffle


# List of points to observe relative to ship
def create_observe_list(vision):
    observe_list = []
    for y in range(vision*2+1):
        for x in range(vision*2+1):
            observe_list.append([x-vision,y-vision])
    return observe_list

observe_list = create_observe_list(7)

def observe(ship):
    observations = {}
    for point in observe_list:
        position = ship.position + Position(*point)
        position = game_map.normalize(position)
        observations[position.x,position.y] = game_map[position].halite_amount
        #logging.info(f'Position: {position} Halite: {observations[position.x,position.y]}')

        if observations[position.x,position.y] > promising_halite_amount:
            if (position not in promising_cells) and (position not in ship_destinations.values()):
                promising_cells.append(position)
        else:
            if position in promising_cells:
                promising_cells.remove(position)
    return observations


def list_to_direction(list):
    if list == [0,-1]:
        return Direction.North
    if list == [0,1]:
        return Direction.South
    if list == [1,0]:
        return Direction.East
    if list == [-1, 0]:
        return Direction.West
    if list == [0,0]:
        return Direction.Still


def navigate(ship, target):
    '''
        takes a ship and its target destination. (Position)
        return a direction.

        if it can move towards to direction it will.
        if it can't move and can stay still it will.
        if it can't move towards it and can't stay still it will randomly move to a safe location.
        if none of these is possible it will stay still and die.
    '''

    global position_choices
    unsafe_moves = game_map.get_unsafe_moves(ship.position,target)
    shuffle(unsafe_moves)
    move = None
    for unsafe_move in unsafe_moves:
        unsafe_position = [x + y for x, y in zip(unsafe_move, [ship.position.x, ship.position.y])]
        unsafe_position = game_map.normalize(Position(*unsafe_position))
        if unsafe_position not in position_choices:
            move = unsafe_move
            break

    if move == None:
        if ship.position not in position_choices:
            move = Direction.Still
        else:
            cardinals = Position.get_surrounding_cardinals(ship.position)
            for cardinal in cardinals:
                if cardinal not in position_choices:
                    x = cardinal.x - ship.position.x
                    y = cardinal.y - ship.position.y
                    move = list_to_direction([x,y])
                    break
    if move == None:
        logging.info(f'Ship {ship.id} will Die')
        move = Direction.Still

    return move

def choose_destination(ship):
    '''
    takes a ship and returns a destination
    '''
    destination = None
    moving_to_old_destination = False
    if len(promising_cells) != 0:
        min_value = 999
        for cell in promising_cells:
            distance = game_map.calculate_distance(ship.position, cell) + 1
            halite_amount = game_map[cell].halite_amount
            value = distance * distance / (halite_amount + 1)
            if value < min_value:
                destination = cell
                min_value = value
        if ship.id in ship_destinations:
            old_destination = ship_destinations[ship.id]
            distance = game_map.calculate_distance(ship.position, old_destination) + 1
            halite_amount = game_map[old_destination].halite_amount
            value = distance * distance / (halite_amount + 1)
            if value < min_value:
                destination = old_destination
                min_value = value
                moving_to_old_destination = True
        if moving_to_old_destination == False:
            promising_cells.remove(destination)
        return destination

    # if promising_cells is empty
    elif len(promising_cells) == 0:
        distance = game_map.calculate_distance(ship.position, me.shipyard.position)
        if distance < 3:
            move = Direction.invert(game_map.naive_navigate(ship, me.shipyard.position))
            if move == Direction.Still:
                move = random.choice(direction_order[:4])
        else:
            #logging.info('ENTERED HERE')
            shipyard_direction = game_map.naive_navigate(ship, me.shipyard.position)
            random.shuffle(direction_order)
            for direction in direction_order:
                if direction not in [shipyard_direction,Direction.Still]:
                    move = direction
        destination = ship.position + Position(*move)
        destination = game_map.normalize(destination)
        return destination

def generate_unmoving_ships():
    unmoving_ships = []
    for ship in me.get_ships():
        # ships that are unable to move
        if ship.halite_amount < game_map[ship.position].halite_amount / 10:
            unmoving_ships.append(ship.id)
        # ships that are collecting halite
        elif ship_states[ship.id] == 'collecting':
            unmoving_ships.append(ship.id)
    return unmoving_ships

def execute_move(ship,move):
    upcoming_position = ship.position + Position(*move)
    upcoming_position = game_map.normalize(upcoming_position)
    position_choices.append(upcoming_position)
    command_queue.append(ship.move(move))

def check_ship_will_deposit():
    for position in position_choices:
        if position == me.shipyard.position:
            return True
    return False

def suicide(ship):
    distance_to_dropoff = game_map.calculate_distance(ship.position,me.shipyard.position)
    if distance_to_dropoff < 2:
        unsafe_moves = game_map.get_unsafe_moves(ship.position,me.shipyard.position)
        shuffle(unsafe_moves)
        move = None
        for unsafe_move in unsafe_moves:
            unsafe_position = [x + y for x, y in zip(unsafe_move, [ship.position.x, ship.position.y])]
            unsafe_position = game_map.normalize(Position(*unsafe_position))
            move = unsafe_move
            break
        if move == None:
            move = Direction.Still
    else:
        move = navigate(ship, me.shipyard.position)
    return move


# Lasting variables
drop_percent = 0.7
# List of cells with high amount of halite
promising_cells = []
ship_states = {}
ship_destinations = {}
create_dropoff = 0
promising_halite_amount = 250
halite_percent = 15
game_state = 'start'

# This game object contains the initial game state.
game = hlt.Game()
# Respond with your name.
game.ready("GoH_learner")

while True:
    # Get the latest game state.
    game.update_frame()
    # You extract player metadata and the updated map metadata here for convenience.
    me = game.me
    game_map = game.game_map

    # A command queue holds all the commands you will run this turn.
    command_queue = []

    # specify the order we know this all to be
    direction_order = [Direction.North, Direction.South, Direction.East, Direction.West, Direction.Still]

    position_choices = []
    unable_to_move_ships = []
    collecting_ships= []
    dropping_ships = []
    searching_ships = []
    all_ships = []

    for ship in me.get_ships():
        all_ships.append(ship.id)
    for key in list(ship_destinations.keys()):
        if key not in all_ships:
            del ship_destinations[key]
    for key in list(ship_states.keys()):
        if key not in all_ships:
            del ship_states[key]

    # try constants.MAX_TURNS / 14 instead of 30
    if game.turn_number + constants.MAX_TURNS / 14 > constants.MAX_TURNS:
        turns_left = constants.MAX_TURNS - game.turn_number
        random_number = random.choice([3,4,5,6,7])
        for ship in me.get_ships():
            if ship_states[ship.id] != 'suicide':
                if game_map.calculate_distance(ship.position, me.shipyard.position) + random_number > turns_left:
                    ship_states[ship.id] = 'suicide'
                    if ship.id in ship_destinations:
                        del ship_destinations[ship.id]

    for ship in me.get_ships():
        #logging.info(f"Ship {ship.id} has {ship.halite_amount} halite.")
        observations = observe(ship)
        if ship.id not in ship_states:
            ship_states[ship.id] = 'searching'

    unmoving_ships = generate_unmoving_ships()

    for ship in me.get_ships():
        if ship.id in unmoving_ships:

            if ship_states[ship.id] == 'collecting':
                collecting_ships.append(ship.id)
                # if ship gets enough halite to turn back
                if ship.halite_amount > constants.MAX_HALITE * drop_percent:
                    ship_states[ship.id] = 'dropping'
                    del ship_destinations[ship.id]
                # if ship finishes collecting and still does not have enough halite to go back
                elif game_map[ship.position].halite_amount < constants.MAX_HALITE / halite_percent:
                    ship_states[ship.id] = 'searching'
                    del ship_destinations[ship.id]
            else:
                unable_to_move_ships.append(ship.id)

            move = Direction.Still
            execute_move(ship,move)

        # ship.id not in unmoving_ships
        else:
            if ship.id in ship_destinations:
                if ship.position == ship_destinations[ship.id]:
                    ship_states[ship.id] = 'collecting'
                    collecting_ships.append(ship.id)
                    unmoving_ships.append(ship.id)

                    move = Direction.Still
                    execute_move(ship,move)

    #logging.info(f'collecting_ships: \n {collecting_ships}')
    #logging.info(f'unable to move ships: \n {unable_to_move_ships}')

    for ship in me.get_ships():
        if ship.id not in unmoving_ships:
            if ship_states[ship.id] == 'dropping':
                if ship.position != me.shipyard.position:
                    dropping_ships.append(ship.id)
                    move = navigate(ship,me.shipyard.position)
                    execute_move(ship,move)
                else:
                    ship_states[ship.id] = 'searching'

            if ship_states[ship.id] == 'searching':
                #observations = observe(ship)
                searching_ships.append(ship.id)
                destination = choose_destination(ship)
                ship_destinations[ship.id] = destination
                #logging.info(f'Ship {ship.id} destination: {destination}')
                move = navigate(ship,destination)
                execute_move(ship,move)

            if ship_states[ship.id] == 'suicide':
                move = suicide(ship)
                execute_move(ship,move)

    #logging.info('State of all ships')
    #logging.info(f'Unable to move ships: \n {unable_to_move_ships}')
    #logging.info(f'Collecting ships: \n {collecting_ships}')
    #logging.info(f'Dropping ships: \n {dropping_ships}')
    #logging.info(f'Searching ships: \n {searching_ships}')
    logging.info(f'Promising cells:\n {promising_cells}')
    #logging.info(f'Ship destinations \n {ship_destinations}')
    #for ship in me.get_ships():
    #    logging.info(f'Ship {ship.id} state: {ship_states[ship.id]}')
    if game_state == 'start':
        if me.halite_amount >= 1000 and not game_map[me.shipyard].is_occupied and not check_ship_will_deposit():
            command_queue.append(me.shipyard.spawn())
            if game.turn_number > constants.MAX_TURNS / 2:
                game_state = 'middle'
                drop_percent = 0.9
                promising_halite_amount = 140
                halite_percent = 20
    elif game_state == 'middle':
        if game.turn_number + 13 > constants.MAX_TURNS:
            game_state = 'ending'
            logging.info('This is the end game')

    # Send your moves back to the game environment, ending this turn.
    game.end_turn(command_queue)
