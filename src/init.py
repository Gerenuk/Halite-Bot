# parameters for graph weighting
# ships contribute weights in the space they control (which is the
# ball of radius 1 or 2 around their position). sites controlled by
# multiple ships should get higher weights
# heuristic: going "through a site" usually takes two steps. if you
# to go "around the site" while staying 1 step away it takes 4 steps
# so the weight should be > 4/2 = 2
MY_WEIGHT = 1
MY_RADIUS = 1

# going "through 3 sites" usually takes 4 steps. if you want to go
# want "around the 3 sites" while staying 2 steps from the middle, it
# takes 8 steps so the weight should be > 8/4 = 2. but we want to be
# very scared of opponent ships so we set this to 4
OPP_WEIGHT = 4
OPP_RADIUS = 2

HUNT_WEIGHT = 4
HUNT_RADIUS = 3

# parameters for shipyard conversion
YARD_DIST = 5
YARD_RADIUS = 8
MIN_CELLS = 20
YARD_SCHEDULE = np.array([0, 10, 30, 40, 50])
FIFO_MODE = True

# how many steps are the "initial" and "final" phases of the game
STEPS_INITIAL = 50
STEPS_FINAL = 50

# parameters for spawning decisions
MAX_SHIPS = 70
MIN_SHIPS = 15
SPAWNING_RATIO = 0.33
SPAWNING_STEP = 150
SPAWNING_OFFSET = 5

# parameters for setting bounties and hunters
SHIPS_PER_BOUNTY = 5
HUNTING_MAX_RATIO = 0.33
YARD_HUNTING_START = 330
YARD_HUNTING_FINAL = 30
YARD_HUNTING_MIN_SHIPS = 10
YARD_HUNTING_RADIUS = 6
MIN_MINING_HALITE = 5

# rate options
STEPS_SPIKE = 15  # steps remaining before spike is added
SPIKE_PREMIUM = 0.8  # spike to deposit everything at the end
RISK_PREMIUM = 0.02  # gets added for each threat within RISK_RADIUS
RISK_RADIUS = 12
SPAWN_PREMIUM = 0.02  # deposit if we need halite to spawn
BASELINE_SHIP_RATE = 0.08  # tendency to visit more sites
BASELINE_YARD_RATE = 0  # tendency to go to yard / mine for less time

# intialize global strategy objects we keep throughout the episode
stats = Stats()
bounties = Bounties()
fifos = Fifos()
targets = Targets()
