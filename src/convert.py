import numpy as np

from settings import (YARD_SCHEDULE, YARD_MAX_STEP, YARD_RADIUS,
                      YARD_DIST, OPP_YARD_DIST, MIN_CELLS)


def convert(state, actions, protection_memory):
    # protect yards if any opponent ship gets within distance 2
    inds = np.ix_(state.opp_ship_pos, state.my_yard_pos)
    dist = np.amin(state.dist[inds], axis=0, initial=state.map_size)
    threatened = state.my_yard_pos[dist <= 2]
    protection_memory = np.union1d(protection_memory, threatened)

    # stop protecting yards if an opponent yard is too close
    inds = np.ix_(state.opp_yard_pos, state.my_yard_pos)
    dist = np.amin(state.dist[inds], axis=0, initial=state.map_size)
    working_yards = state.my_yard_pos[dist > 3]
    protection_memory = np.intersect1d(protection_memory, working_yards)

    # if we don't have any yards, we try to convert the ship
    # with the most cargo immediately
    if len(state.my_yards) == 0:
        ship = max(actions.ships, key=lambda ship: state.my_ships[ship][1])

        if legal(ship, state):
            actions.decided[ship] = "CONVERT"
            state.update(ship, "CONVERT")
            actions.ships.remove(ship)

        return protection_memory

    # otherwise, we convert a ship if we have too few yards for our ships
    # and it is not too late in the game, provided we have ships
    num_ships = state.my_ship_pos.size
    yards_wanted = sum([x <= num_ships for x in YARD_SCHEDULE])
    should_convert = (working_yards.size < yards_wanted)
    should_convert = should_convert and (state.step < YARD_MAX_STEP)
    should_convert = should_convert and (len(actions.ships) > 0)

    if not should_convert:
        return protection_memory

    # if we should convert, we choose the ship with the highest score
    # convert the ship with maximum score if this is legal and
    # the score is non-zero
    ship = max(actions.ships, key=lambda ship: score(ship, state))

    if legal(ship, state) and (score(ship, state) > 0):
        actions.decided[ship] = "CONVERT"
        state.update(ship, "CONVERT")
        actions.ships.remove(ship)

    return protection_memory


# the score of each ship is the number of halite cells within YARD_RADIUS
# the score defaults to 0 if there is another yard within YARD_DIST or
# if there are less than MIN_CELLS halite cells nearby
def score(ship, state):
    # compute distance to nearest yards and ships
    pos = state.my_ships[ship][0]
    my_yard_dist = np.amin(state.dist[state.my_yard_pos, pos],
                           initial=state.map_size)
    opp_yard_dist = np.amin(state.dist[state.opp_yard_pos, pos],
                            initial=state.map_size)
    opp_ship_dist = np.amin(state.dist[state.opp_ship_pos, pos],
                            initial=state.map_size)

    # count number of halite cells within YARD_RADIUS
    hood = (state.dist[pos, :] <= YARD_RADIUS)
    cells = np.sum(hood & (state.halite_map > 0))

    # score is number of halite cells unless there are too few
    # or we are too close to an opponent ship/yard
    eligible = (my_yard_dist >= YARD_DIST)
    eligible = eligible and (opp_yard_dist >= OPP_YARD_DIST)
    eligible = eligible and (opp_ship_dist >= 2)
    eligible = eligible and (cells >= MIN_CELLS)

    return cells if eligible else 0


# returns True if CONVERT is a legal action for ship - need to have enough
# halite and not be on another yard. if you only have one ship, you can
# only convert if you still have enough halite to spawn a ship afterwards
def legal(ship, state):
    pos, hal = state.my_ships[ship]
    minhal = state.convert_cost - hal
    if len(state.my_ships) == 1:
        minhal += state.spawn_cost
    return (state.my_halite >= minhal) and (pos not in state.my_yard_pos)
