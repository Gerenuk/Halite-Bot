class State:
    def __init__(self, obs, config):
        self.config = config  # remove eventually

        # game configuration
        self.map_size = config.size
        self.total_steps = config.episodeSteps
        self.step = obs.step
        self.halite_map = np.array(obs.halite)

        # my halite, yards, and ships
        my_id = obs.player
        self.my_halite, self.my_yards, self.my_ships = obs.players[my_id]

        # set joint and individual data for oppenents
        self._set_opp_data(obs)

        # list of positions with ships that have already moved this turn
        self.moved_this_turn = np.array([])

        # several functions want a vector of all sites so we only generate
        # this once and keep it
        size = self.map_size
        nsites = size ** 2
        self.sites = np.arange(nsites)

        # lookup tables for the effect of moves
        # north[x] is the position north of x, etc
        self.north = (self.sites - size) % nsites
        self.south = (self.sites + size) % nsites
        self.east = size * (self.sites // size) \
            + ((self.sites % size) + 1) % size
        self.west = size * (self.sites // size) \
            + ((self.sites % size) - 1) % size

        # dist[x,y] stores the l1-distance between x and y on the torus
        cols = self.sites % self.map_size
        rows = self.sites // self.map_size
        coldist = cols - cols[:, np.newaxis]
        rowdist = rows - rows[:, np.newaxis]
        coldist = np.fmin(np.abs(coldist), self.map_size - np.abs(coldist))
        rowdist = np.fmin(np.abs(rowdist), self.map_size - np.abs(rowdist))
        self.dist = coldist + rowdist

        # sets a number of numpy arrays deriving from self.my_ships, etc
        self._set_derived()

        # compute clusters used for shipyard conversion
        self._make_clusters()

        return

    # # remove eventually
    # def colrow(self, pos):
    #     return pos % self.map_size, pos // self.map_size

    def _set_opp_data(self, obs):
        # figure out my id / opponent id
        my_id = obs.player
        opp_ids = list(range(0, len(obs.players)))
        opp_ids.remove(my_id)

        # joint opponent ships and yards
        self.opp_ships = {}
        self.opp_yards = {}
        for opp in opp_ids:
            self.opp_yards.update(obs.players[opp][1])
            self.opp_ships.update(obs.players[opp][2])

        # list of lists. for each opponent has halite, yard positions, ship
        # positions, ship halite as numpy arrays
        self.opp_data = []
        for opp in opp_ids:
            halite, yards, ships = obs.players[opp]
            yard_pos = np.array(list(yards.values())).astype(int)
            if len(ships) > 0:
                poshal = np.array(list(ships.values()))
                ship_pos, ship_hal = np.split(poshal, 2, axis=1)
                ship_pos = np.ravel(ship_pos).astype(int)
                ship_hal = np.ravel(ship_hal).astype(int)
            else:
                ship_pos = np.array([]).astype(int)
                ship_hal = np.array([]).astype(int)

            self.opp_data.append([halite, yard_pos, ship_pos, ship_hal])

        return

    # several function need all ship positions as numpy arrays
    # these arrays need to be set by init() and also updated by update()
    # do this by calling _set_derived()
    def _set_derived(self):
        self.my_yard_pos = np.array(list(self.my_yards.values())).astype(int)
        self.opp_yard_pos = np.array(list(self.opp_yards.values())).astype(int)

        if len(self.my_ships) != 0:
            poshal = np.array(list(self.my_ships.values()))
            self.my_ship_pos, self.my_ship_hal = np.split(poshal, 2, axis=1)
            self.my_ship_pos = np.ravel(self.my_ship_pos).astype(int)
            self.my_ship_hal = np.ravel(self.my_ship_hal).astype(int)
        else:
            self.my_ship_pos = np.array([]).astype(int)
            self.my_ship_hal = np.array([]).astype(int)

        if len(self.opp_ships) != 0:
            poshal = np.array(list(self.opp_ships.values()))
            self.opp_ship_pos, self.opp_ship_hal = np.split(poshal, 2, axis=1)
            self.opp_ship_pos = np.ravel(self.opp_ship_pos).astype(int)
            self.opp_ship_hal = np.ravel(self.opp_ship_hal).astype(int)
        else:
            self.opp_ship_pos = np.array([]).astype(int)
            self.opp_ship_hal = np.array([]).astype(int)

        return

    def _make_clusters(self):
        # array of all sites we are currently occupying
        self.cluster_pos = np.append(self.my_ship_pos, self.my_yard_pos)
        self.cluster_pos = np.unique(self.cluster_pos)

        # if there are not enough sites to cluster, set them all as outliers
        if self.cluster_pos.size <= MIN_CLUSTER_SIZE:
            self.cluster_labels = - np.ones_like(self.cluster_pos)
            return

        # create a graph for clustering - see explanation in make_weights()
        my_weight, opp_weight = GRAPH_MY_WEIGHT, GRAPH_OPP_WEIGHT

        weights = np.ones(self.map_size ** 2)

        weights += my_weight * \
            np.sum(self.dist[self.my_ship_pos, :] <= 1, axis=0)

        if self.opp_ship_pos.size != 0:
            weights += opp_weight * \
                np.sum(self.dist[self.opp_ship_pos, :] <= 2, axis=0)

        if self.opp_yard_pos.size != 0:
            weights[self.opp_yard_pos] += opp_weight

        # unlike make_weights() we DON'T want to remove any weights on
        # the yards for this part
        # weights[state.my_yard_pos] = 0

        graph = make_graph_csr(self, weights)

        # compute graph distances to all cluster sites
        self.cluster_dists = dijkstra(graph, indices=self.cluster_pos)
        dist_matrix = self.cluster_dists[:, self.cluster_pos]

        # run the OPTICS clustering algorithm
        model = OPTICS(min_samples=MIN_SAMPLES,
                       min_cluster_size=MIN_CLUSTER_SIZE,
                       metric="precomputed")

        # ignore outlier warnings from OPTICS
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.cluster_labels = model.fit_predict(dist_matrix)

        return

    def get_cluster(self, pos):
        if pos not in self.cluster_pos:
            return np.array([]).astype(int)

        ind = np.flatnonzero(self.cluster_pos == pos)
        label = self.cluster_labels[ind]

        if label == -1:  # outliers - return only the position
            return np.array([pos])
        else:
            cluster_inds = np.flatnonzero(self.cluster_labels == label)
            return self.cluster_pos[cluster_inds]

    def newpos(self, pos, action):
        if (action is None) or (action == "CONVERT"):
            return pos
        elif action == "NORTH":
            return self.north[pos]
        elif action == "SOUTH":
            return self.south[pos]
        elif action == "EAST":
            return self.east[pos]
        elif action == "WEST":
            return self.west[pos]

    def update(self, actor, action):
        # first check if actor is yard and act accordingly
        if (actor in self.my_yards) and (action is None):
            return

        if action == "SPAWN":
            # generate a unique id string
            newid = f"spawn[{str(actor)}]-{str(uuid4())}"

            # create a new ship at yard position
            pos = self.my_yards[actor]
            self.my_ships[newid] = [pos, 0]

            # the result is a ship here that cannot move this turn
            self.moved_this_turn = np.append(self.moved_this_turn, pos)

            # subtract spawn cost from available halite
            self.my_halite -= int(self.config.spawnCost)

            # update internal variables that derive from my_ships, my_yards
            self._set_derived()
            return

        # if execution gets here, we know actor is a ship
        pos, hal = self.my_ships[actor]

        if action == "CONVERT":
            # generate a unique id string
            newid = f"convert[{str(actor)}]-{str(uuid4())}"

            # create a new yard at ship position and remove ship
            self.my_yards[newid] = pos
            del self.my_ships[actor]

            # remove conversion cost from available halite but don't add any
            # net gains - its not available until next turn
            self.my_halite += int(min(hal - self.config.convertCost, 0))
            self.halite_map[pos] = 0

            # update internal variables that derive from my_ships, my_yards
            self._set_derived()
            return

        # if execution gets here, the actor stays a ship
        # first update the halite
        # if the ship stays put, it can collect halite
        if action is None:
            collect = np.floor(self.halite_map[pos] * self.config.collectRate)
            nhal = int(hal + collect)
            self.halite_map[pos] -= collect

        # otherwise the move may cost halite
        else:
            nhal = int(hal * (1 - self.config.moveCost))

        # now update the position, and write the new values into my_ships
        npos = self.newpos(pos, action)
        self.my_ships[actor] = [npos, nhal]

        # add position to list of ships that can no longer move this turn
        self.moved_this_turn = np.append(self.moved_this_turn, npos)

        # update internal variables that derive from my_ships, my_yards
        self._set_derived()
        return


#############################




    def legal_actions(self, actor):
        if actor in self.my_yards:
            actions = [None, "SPAWN"]
            # need to have enough halite to spawn
            if self.my_halite < self.config.spawnCost:
                actions.remove("SPAWN")

        if actor in self.my_ships:
            actions = [None, "CONVERT", "NORTH", "SOUTH", "EAST", "WEST"]
            pos, hal = self.my_ships[actor]

            # need to have enough halite. if you only have one ship, you
            # can only convert if you still have enough halite afterwards
            # to spawn a new ship
            minhal = self.config.convertCost - hal
            if len(self.my_ships) == 1:
                minhal += self.config.spawnCost

            # can't convert if you don't have enough halite or are in a yard
            if self.my_halite < minhal or pos in self.my_yard_pos:
                actions.remove("CONVERT")

        return actions

    def self_collision(self, actor, action):
        if actor in self.my_yards:
            # shipyards only give collisions if we spawn a ship after moving
            # a ship there previously
            pos = self.my_yards[actor]
            coll = action == "SPAWN" and pos in self.moved_this_turn

        if actor in self.my_ships:
            pos, hal = self.my_ships[actor]

            # cannot convert onto another shiyard
            if action == "CONVERT":
                coll = pos in self.my_yard_pos
            # otherwise get the new position of the ship and check if
            # it runs into a ship that can no longer move
            else:
                npos = self.newpos(pos, action)
                coll = npos in self.moved_this_turn

        return coll

    def opp_collision(self, ship, action, strict=True):
        # return True if a collision is possible in the next step if ship
        # performs action
        pos, hal = self.my_ships[ship]
        npos = self.newpos(pos, action)

        # check whether we run into a yard
        coll = npos in self.opp_yard_pos

        # find those ships that have less halite than we do
        if strict:
            less_hal = self.opp_ship_pos[self.opp_ship_hal <= hal]
        else:
            less_hal = self.opp_ship_pos[self.opp_ship_hal < hal]

        if less_hal.size != 0:
            # list of sites where ships in less_hal could end up after one turn
            hood = np.flatnonzero(np.amin(self.dist[less_hal, :], axis=0) <= 1)

            # regard our own shipyards as safe havens - this is not necessarily
            # the case but many opponents will not want to run into the yard
            # this will cost them their ship too
            hood = np.setdiff1d(hood, self.my_yard_pos)

            coll = coll or npos in hood

        return coll