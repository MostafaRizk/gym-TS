"""
Implements an environment to study cooperative agent behaviour inspired by Ferrante et al. 2015
https://journals.plos.org/ploscompbiol/article?id=10.1371/journal.pcbi.1004273

The environment consists of an arena with a slope and flat areas at the top and bottom. At the top, there is a 'source'
that contains resources. At the bottom there is a 'nest' containing agents and a 'cache' separating the nest and slope.
The agents' task is to retrieve as many resources as possible in the alotted time from the source and transport them to
the nest. Agents receive a reward for successfully depositing resources at the nest but pay a cost for moving (similar
to a battery), with the cost increasing if they are traveling up the slope and/or carrying a resource and decreasing if
they are traveling down the slope. The environment is a 2D grid-world with a discrete action-space.
"""
import json
import numpy as np
import copy

# Put this import in a try/except because otherwise, the cluster throws an error
try:
    from helpers import rendering

except:
    pass


class SlopeEnv:
    # Primary functions -----------------------------------------------------------------------------------------------
    def __init__(self, parameter_filename=None):
        """
        Initialises constants and variables for agents, resources and environment
        :param
        """
        if parameter_filename is None:
            raise RuntimeError("No parameter file specified for the environment")

        parameter_dictionary = json.loads(open(parameter_filename).read())

        try:
            self.observation_version = parameter_dictionary['environment']['observation_version']
        except KeyError:
            self.observation_version = "complex"

        # Environment dimensions
        self.arena_constraints = {"x_min": 0, "x_max": parameter_dictionary['environment']['arena_width'], "y_min": 0,
                                  "y_max": parameter_dictionary['environment']['arena_length']}
        self.nest_size = parameter_dictionary['environment']['cache_start']
        self.cache_size = parameter_dictionary['environment']['slope_start'] - parameter_dictionary['environment'][
            'cache_start']
        self.slope_size = parameter_dictionary['environment']['source_start'] - parameter_dictionary['environment'][
            'slope_start']
        self.source_size = parameter_dictionary['environment']['arena_length'] - parameter_dictionary['environment'][
            'source_start']
        self.nest_start = self.arena_constraints["y_min"]
        self.cache_start = parameter_dictionary['environment']['cache_start']
        self.slope_start = parameter_dictionary['environment']['slope_start']
        self.source_start = parameter_dictionary['environment']['source_start']
        self.num_arena_tiles = self.arena_constraints["x_max"] * self.arena_constraints["y_max"]
        self.sliding_speed = parameter_dictionary['environment']['sliding_speed']

        # agent constants
        self.agent_width = 0.8
        self.sensor_range = parameter_dictionary['environment']['sensor_range']

        # Resource constants
        self.resource_width = 0.6
        self.base_cost = parameter_dictionary['environment']['base_cost']
        self.reward_for_resource = parameter_dictionary['environment']['resource_reward']
        self.upward_cost_factor = parameter_dictionary['environment']['upward_cost_factor']
        self.downward_cost_factor = parameter_dictionary['environment']['downward_cost_factor']
        self.carry_factor = parameter_dictionary['environment']['carry_factor']

        # Other constants and variables
        self.num_agents = parameter_dictionary['environment']['num_agents']
        self.default_num_resources = parameter_dictionary['environment']['num_resources']
        self.current_num_resources = self.default_num_resources
        self.latest_resource_id = self.default_num_resources - 1
        self.dumping_position = (-10, -10)

        # Rendering constants
        self.scale = 50  # Scale for rendering
        self.nest_colour = [0.25, 0.25, 0.25]
        self.cache_colour = [0.5, 0.5, 0.5]
        self.slope_colour = [0.5, 0.25, 0.25]
        self.source_colour = [0.25, 0.5, 0.5]
        self.agent_colour = [0, 0, 0.25]
        self.resource_colour = [0, 0.25, 0]

        # Rendering variables
        self.viewer = None
        self.agent_transforms = None
        self.resource_transforms = None

        try:
            self.agent_transforms = [rendering.Transform() for i in range(self.num_agents)]
            self.resource_transforms = [rendering.Transform() for i in range(self.default_num_resources)]

        except:
            pass

        self.agent_positions = [None] * self.num_agents
        self.resource_positions = [None] * self.default_num_resources
        self.resource_carried_by = [[]] * self.default_num_resources

        # Step variables
        self.behaviour_map = [self.forward_step, self.backward_step, self.left_step, self.right_step]
        self.action_name = ["FORWARD", "BACKWARD", "LEFT", "RIGHT", "PICKUP", "DROP"]
        self.has_resource = [None for i in range(self.num_agents)]

        self.seed_value = parameter_dictionary['general']['seed']
        self.np_random = np.random.RandomState(self.seed_value)

        # Observation space (additional details explained in self.get_agent_observations())

        # Range=1 -> 9 tiles. Range=2 -> 25 tiles. Agent at the center.
        self.tiles_in_sensing_range = (2 * self.sensor_range + 1) ** 2

        if self.observation_version == "simple":
            # 1 bit for each tile in range + 4 bits for location + 1 bit for object detection + 1 bit for object possession
            self.observation_space_size = self.tiles_in_sensing_range + 4 + 1 + 1
        else:
            # Tiles in sensing range are onehotencoded + 4 bits for location + 1 bit for object possession
            self.observation_space_size = self.tiles_in_sensing_range * 4 + 4 + 1

        # Action space
        # 0- Forward, 1- Backward, 2- Left, 3- Right, 4- Pick up, 5- Drop
        self.action_space_size = 6

    def step(self, agent_actions):
        """
        Updates the environment according to agents' actions

        :param agent_actions A list of integers representing the action each agent is taking

        :return A 4-tuple containing: a list containing each agent's observation, the reward at this time step,
        a boolean indicating if the simulation is done, any additional information
        """

        # Returns an error if the number of actions is incorrect
        assert len(agent_actions) == self.num_agents, "Incorrect number of actions"

        # Returns an error if any action is invalid
        for action in agent_actions:
            # assert self.action_space.contains(action), "%r (%s) invalid" % (action, type(action))
            assert action in range(self.action_space_size), "%r (%s) invalid" % (action, type(action))

        done = False

        rewards = [0.0, 0.0]

        # The agents act
        old_agent_positions = copy.deepcopy(self.agent_positions)

        for i in range(len(agent_actions)):
            cost_multiplier = 1
            team_id = i % 2

            # If agent is carrying something, multiply the cost of moving
            if self.has_resource[i] is not None:
                cost_multiplier = self.carry_factor

            if agent_actions[i] < 4:
                self.behaviour_map[agent_actions[i]](i)

                # More costly for agent to move up the slope than down
                if self.get_area_from_position(self.agent_positions[i]) == "SLOPE":
                    if self.action_name[agent_actions[i]] == "FORWARD":
                        rewards[team_id] -= self.upward_cost_factor * self.base_cost * cost_multiplier

                    elif self.action_name[agent_actions[i]] == "BACKWARD":
                        rewards[team_id] -= self.base_cost * self.downward_cost_factor * cost_multiplier

                    else:
                        rewards[team_id] -= self.base_cost * cost_multiplier

                # Negative reward for moving when not on slope. Same as having a battery
                else:
                    rewards[team_id] -= self.base_cost * cost_multiplier

            # Negative reward for dropping/picking up but is not affected by resource weight
            else:
                rewards[team_id] -= self.base_cost

        # The agents' old positions are wiped out
        for position in old_agent_positions:
            # self.state[position[1]][position[0]] = 0
            self.agent_map[position[1]][position[0]] = 0

        # The resources' old positions are wiped out
        for position in self.resource_positions:
            if position != self.dumping_position:
                # self.state[position[1] + self.arena_constraints["y_max"]][position[0]] = 0
                self.resource_map[position[1]][position[0]] = 0

        agent_collision_positions = copy.deepcopy(self.agent_positions)

        # The agents' new positions are updated
        for i in range(len(self.agent_positions)):
            for j in range(len(self.agent_positions)):
                # If the agent's new position is the same as another agent's new position, it stays where it was
                if (self.agent_positions[i] == self.agent_positions[j] or self.agent_positions[i] ==
                    old_agent_positions[j]) and i != j:
                    # If agent i is colliding with agent j's new position, it keeps its old position
                    # If agent i is colliding with agent j's old position, it keeps its old position (this is in case
                    # agent j changes its mind and decides to stay where it is to avoid a collision with a third agent)
                    # But do not update agent i's position in self.agent_positions so that agent j has the chance to
                    # update its position too. Otherwise, agent i will back off but agent j will continue and agents
                    # with higher indices will have an advantage
                    agent_collision_positions[i] = old_agent_positions[i]

            # If agent i's new position is the same as resource j and it is carrying a resource and that resource
            # is not resource j, then stay at the previous position
            # i.e agents should only collide with resources to pick them up and they can only hold one resource at a
            # time
            for j in range(len(self.resource_positions)):
                if self.agent_positions[i] == self.resource_positions[j]:
                    if self.has_resource[i] is not None and self.has_resource[i] != j:
                        agent_collision_positions[i] = old_agent_positions[i]

            # self.state[agent_collision_positions[i][1]][agent_collision_positions[i][0]] = i + 1
            self.agent_map[agent_collision_positions[i][1]][agent_collision_positions[i][0]] = i + 1

        self.agent_positions = agent_collision_positions

        for i in range(len(self.resource_positions)):
            for j in range(len(old_agent_positions)):
                # Ensure that a resource that was at the same location as a agent in the last time step moves with the agent
                # (i.e. the agent holds onto the resource). Also ensure that agent picks it up (unless it was just dropped)
                if self.resource_positions[i] == old_agent_positions[j]:
                    # If an agent currently has a resource and is doing a drop action, drop the resource
                    # If an agent currently has a resource and is NOT doing a drop action, hold onto it
                    if self.has_resource[j] == i:
                        if self.action_name[agent_actions[j]] == "DROP":
                            self.drop_resource(j)
                        else:
                            self.pickup_or_hold_resource(j, i)

                # Ensure that a resource that is at the same location as a agent now gets picked up if the agent is
                # doing a pickup action
                if self.resource_positions[i] == self.agent_positions[j]:
                    if self.has_resource[j] is None:
                        if self.action_name[agent_actions[j]] == "PICKUP":
                            self.pickup_or_hold_resource(j, i)

            # If a resource is on the slope and not in the possession of a agent, it slides
            if self.resource_positions[i] != self.dumping_position and \
                    self.get_area_from_position(self.resource_positions[i]) == "SLOPE" and \
                    i not in self.has_resource:
                self.slide_resource(i)

        # If a agent has returned a resource to the nest the resource is deleted and the agent is rewarded
        for i in range(self.num_agents):
            if self.get_area_from_position(self.agent_positions[i]) == "NEST" and \
                    self.has_resource[i] is None and \
                    self.agent_positions[i] in self.resource_positions:
                # Find the resource with the same position as the current agent and get that resource's id
                resource_id = self.resource_positions.index(self.agent_positions[i])

                # Reward all agents if a resource is retrieved
                rewards[0] += self.reward_for_resource
                rewards[1] += self.reward_for_resource

                self.delete_resource(resource_id)

        num_resources_at_source = 0

        # Spawn a new resource any time the number of resources at the source decreases below the default threshold
        for position in self.resource_positions:
            try:
                if self.get_area_from_position(position) == "SOURCE":
                    num_resources_at_source += 1
            except ValueError:
                pass

            # If there are more resources at the source than the default, there's no need to continue counting
            if num_resources_at_source >= self.default_num_resources:
                break

        resource_deficit = self.default_num_resources - num_resources_at_source

        if resource_deficit > 0:
            for i in range(resource_deficit):
                self.spawn_resource()

        # Update the state with the new resource positions
        for i in range(len(self.resource_positions)):
            if self.resource_positions[i] != self.dumping_position:
                self.resource_map[self.resource_positions[i][1]][self.resource_positions[i][0]] = i + 1

        self.state = np.concatenate((self.agent_map, self.resource_map), axis=0)  # Fully observable environment
        observations = self.get_agent_observations()

        return observations, rewards

    def reset(self):
        """
        """

        # Make sure agents and resources will all fit in the environment
        assert self.num_agents <= self.arena_constraints[
            "x_max"] * self.nest_size, "Not enough room in the nest for all agents"
        assert self.default_num_resources <= self.arena_constraints[
            "x_max"] * self.source_size, "Not enough room in the source for all resources"

        try:
            self.viewer.close()
        except:
            pass

        self.viewer = None

        self.resource_positions = [None for i in range(self.default_num_resources)]

        self.resource_carried_by = [[] for i in range(self.default_num_resources)]

        try:
            self.resource_transforms = [rendering.Transform() for i in range(self.default_num_resources)]
        except:
            pass

        self.latest_resource_id = self.default_num_resources - 1

        # Creates empty state
        self.agent_map = self.generate_arena()  # Empty agent map

        self.resource_map = self.generate_arena()  # Empty resource map

        # Places all agents
        for i in range(self.num_agents):
            agent_placed = False
            while not agent_placed:
                x, y = self.generate_agent_position()
                if self.agent_map[y][x] == 0:
                    self.agent_map[y][x] = i + 1
                    self.agent_positions[i] = (x, y)
                    agent_placed = True

        # Places all resources
        for i in range(self.default_num_resources):
            resource_placed = False
            while not resource_placed:
                x, y = self.generate_resource_position()
                if self.resource_map[y][x] == 0:
                    self.resource_map[y][x] = i + 1
                    self.resource_positions[i] = (x, y)
                    resource_placed = True
        '''
        # Places straight line of resources
        for i in range(self.default_num_resources):
            x, y = i, self.arena_constraints["y_max"]-1
            self.resource_map[y][x] = i + 1
            self.resource_positions[i] = (x,y)
        '''

        # NOTE: To change this, must also change the observation space in __init__
        self.state = np.concatenate((self.agent_map, self.resource_map), axis=0)

        # Reset variables that were changed during runtime
        self.has_resource = [None for i in range(self.num_agents)]
        self.current_num_resources = self.default_num_resources

        # return np.array(self.state)
        return self.get_agent_observations()

    # Initialisers ----------------------------------------------------------------------------------------------------
    def generate_arena(self):
        """
        Generates 2D matrix representing an empty arena i.e. each tile contains a 0
        :return:
        """

        return [[0 for i in range(self.arena_constraints["x_max"])] for j in range(self.arena_constraints["y_max"])]

    def generate_agent_position(self):
        """
        Generates and returns valid coordinates for a single agent
        :return: x and y coordinates of the agent
        """
        x = self.np_random.randint(low=self.arena_constraints["x_min"], high=self.arena_constraints["x_max"])
        y = self.np_random.randint(low=self.nest_start, high=self.nest_start + self.nest_size)
        return x, y

    def generate_resource_position(self):
        """
        Generates and returns valid coordinates for a single resource
        :return: x and y coordinates of the resource
        """
        x = self.np_random.randint(low=self.arena_constraints["x_min"], high=self.arena_constraints["x_max"])
        y = self.np_random.randint(low=self.source_start, high=self.arena_constraints["y_max"])
        return x, y

    def get_agent_observations(self):
        if self.observation_version == "simple":
            return self.get_observations_simple()
        elif self.observation_version == "complex":
            return self.get_observations_complex()

    def get_observations_simple(self):
        observations = []
        readable_observations = []

        for j in range(len(self.agent_positions)):
            position = self.agent_positions[j]
            observation = [0] * self.observation_space_size
            readable_observation = []

            # If a tile in the agent's sensing range is:
            # An agent, wall or object-            observation[k] = 1, otherwise 0
            current_x = position[0] - self.sensor_range
            current_y = position[1] + self.sensor_range
            row_progress = 0

            resource_in_range = False

            for k in range(self.tiles_in_sensing_range):
                # If coordinate is out of bounds then it is a wall
                if self.arena_constraints["x_max"] <= current_x or current_x < 0 or self.arena_constraints["y_max"] <= current_y or current_y < 0:
                    observation[k] = 1  # Wall
                    readable_observation += ["Object (wall)"]
                # If coordinate contains a agent and the agent is not this agent
                elif self.agent_map[current_y][current_x] != 0 and (
                        current_x != position[0] or current_y != position[1]):
                    observation[k] = 1  # Another agent
                    readable_observation += ["Object (agent)"]
                # If coordinate is a resource
                elif self.resource_map[current_y][current_x] != 0 and self.has_resource[j] != self.resource_map[current_y][current_x] - 1:
                    observation[k] = 1  # A resource
                    readable_observation += ["Object (resource)"]
                    resource_in_range = True
                else:
                    observation[k] = 0  # Blank space
                    readable_observation += ["Blank"]

                row_progress += 1

                if row_progress >= self.sensor_range * 2 + 1:
                    row_progress = 0
                    current_x = position[0] - self.sensor_range
                    current_y -= 1
                else:
                    current_x += 1

            area = self.get_area_from_position(position)
            obs_index = self.tiles_in_sensing_range

            # If the area the agent is located in is
            # The nest-     observation[9] = 1, otherwise 0
            # The cache-    observation[10] = 1, otherwise 0
            # The slope-    observation[11] = 1, otherwise 0
            # The source-   observation[12] = 1, otherwise 0
            if area == "NEST":
                observation[obs_index] = 1
            elif area == "CACHE":
                observation[obs_index + 1] = 1
            elif area == "SLOPE":
                observation[obs_index + 2] = 1
            else:
                observation[obs_index + 3] = 1

            readable_observation += [area]

            # If a resource is
            # In range-   observation[13] = 1, otherwise 0
            if resource_in_range:
                observation[obs_index + 4] = 1
                readable_observation = ["In range"]
            else:
                readable_observation = ["Not in range"]


            # If the agent
            # Has a resource-   observation[14] = 1, otherwise 0
            if self.has_resource[j] is not None:
                observation[obs_index + 5] = 1
                readable_observation += ["Has"]
            else:
                readable_observation += ["Doesn't have"]

            observations += [np.array(observation)]
            readable_observations += [readable_observation]

        return observations



    def get_observations_complex(self):
        """
        Generate a list containing each agent's observation. Each agent observes:
        1. A radius of self.sensor_range around itself. If sensor range is 0, it only checks the tile it is currently
        on. A onehotencoded bit-vector is added to the observation denoting whether the agent detects a blank space,
        another agent (not possible if it's the tile directly underneath), a resource or a wall (also not possible).
        If the radius is greater than 0, then the agent is at the center of a square (side=3 if radius=1,
        side=5 if radius=2 etc). The same readings are added starting from the top left tile and going row by row
        until the bottom right tile.
        2. Where the agent is (Nest, Cache, Slope, Source) also encoded as a bit-vector
        3. Whether or not the agent is carrying a resource (encoded as a single bit)
        :return:
         """

        observations = []
        readable_observations = []

        for j in range(len(self.agent_positions)):
            position = self.agent_positions[j]
            observation = [0] * self.observation_space_size
            readable_observation = []

            # If a tile in the agent's sensing range is:
            # Blank-            observation[k + 0] = 1, otherwise 0
            # Another agent-    observation[k + 1] = 1, otherwise 0
            # A resource-       observation[k + 2] = 1, otherwise 0
            # A wall-           observation[k + 3] = 1, otherwise 0
            # Each tile is represented by 4 indices instead of 1(for purposes of onehotencoding)
            current_x = position[0] - self.sensor_range
            current_y = position[1] + self.sensor_range
            row_progress = 0

            for k in range(self.tiles_in_sensing_range):
                # If coordinate is out of bounds then it is a wall
                if self.arena_constraints["x_max"] <= current_x or current_x < 0 or self.arena_constraints[
                    "y_max"] <= current_y or current_y < 0:
                    observation[4 * k + 3] = 1  # Wall
                    readable_observation += ["Wall"]
                # If coordinate contains a agent and the agent is not this agent
                elif self.agent_map[current_y][current_x] != 0 and (
                        current_x != position[0] or current_y != position[1]):
                    observation[4 * k + 1] = 1  # Another agent
                    readable_observation += ["agent"]
                # If coordinate is a resource
                elif self.resource_map[current_y][current_x] != 0 and self.has_resource[j] != \
                        self.resource_map[current_y][current_x] - 1:
                    observation[4 * k + 2] = 1  # A resource
                    readable_observation += ["Resource"]
                else:
                    observation[4 * k + 0] = 1  # Blank space
                    readable_observation += ["Blank"]

                row_progress += 1

                if row_progress >= self.sensor_range * 2 + 1:
                    row_progress = 0
                    current_x = position[0] - self.sensor_range
                    current_y -= 1
                else:
                    current_x += 1

            area = self.get_area_from_position(position)
            obs_index = self.tiles_in_sensing_range * 4

            # If the area the agent is located in is
            # The nest-     observation[4] = 1, otherwise 0
            # The cache-    observation[5] = 1, otherwise 0
            # The slope-    observation[6] = 1, otherwise 0
            # The source-   observation[7] = 1, otherwise 0
            if area == "NEST":
                observation[obs_index] = 1
            elif area == "CACHE":
                observation[obs_index + 1] = 1
            elif area == "SLOPE":
                observation[obs_index + 2] = 1
            else:
                observation[obs_index + 3] = 1

            readable_observation += [area]

            # If the agent
            # Has a resource-   observation[8] = 1, otherwise 0
            if self.has_resource[j] is not None:
                observation[obs_index + 4] = 1
                readable_observation += ["Has"]
            else:
                readable_observation += ["Doesn't have"]

            observations += [np.array(observation)]
            readable_observations += [readable_observation]

        return observations

    # Simple getters --------------------------------------------------------------------------------------------------
    def get_num_agents(self):
        """
        Returns number of agents
        :return: Integer representing number of agents
        """
        return self.num_agents

    def get_default_num_resources(self):
        """
        Returns default number of resources
        :return: Integer representing number of resources
        """
        return self.default_num_resources

    def get_observation_size(self):
        return self.observation_space_size

    def get_action_size(self):
        return self.action_space_size

    # Helpers ---------------------------------------------------------------------------------------------------------
    def get_area_from_position(self, position):
        """
        Gets the area of the environment corresponding to a position i.e. NEST, SOURCE etc
        :param position:
        :return: A string representing the area's name in uppercase
        """

        x = position[0]
        y = position[1]

        if x < self.arena_constraints["x_min"] or x > self.arena_constraints["x_max"]:
            raise ValueError("x position is not valid")

        if self.nest_start <= y < self.cache_start:
            return "NEST"
        elif self.cache_start <= y < self.slope_start:
            return "CACHE"
        elif self.slope_start <= y < self.source_start:
            return "SLOPE"
        elif self.source_start <= y < self.arena_constraints["y_max"]:
            return "SOURCE"
        else:
            raise ValueError("y position is not valid")

    def source_is_full(self):
        """
        Determines if the source area has a resource at every grid position and is thus "full"
        :return: True if full, False otherwise
        """
        for y in range(int(self.source_size)):
            for x in range(self.arena_constraints["x_max"]):
                if self.resource_map[int(self.source_start) + y][x] == 0 and (
                x, int(self.source_start) + y) not in self.resource_positions:
                    return False

        return True

    # Actions ---------------------------------------------------------------------------------------------------------
    def forward_step(self, agent_id):
        """
        agent with id agent_id moves one step forward i.e. up in the y direction
        :param agent_id: Index of the agent in self.agent_positions
        :return:
        """
        self.agent_positions[agent_id] = (
            self.agent_positions[agent_id][0],
            np.clip(self.agent_positions[agent_id][1] + 1, self.arena_constraints["y_min"],
                    self.arena_constraints["y_max"] - 1))

    def backward_step(self, agent_id):
        """
        agent with id agent_id moves one step back i.e. down in the y direction
        :param agent_id: Index of the agent in self.agent_positions
        :return:
        """
        self.agent_positions[agent_id] = (
            self.agent_positions[agent_id][0],
            np.clip(self.agent_positions[agent_id][1] - 1, self.arena_constraints["y_min"],
                    self.arena_constraints["y_max"] - 1))

    def left_step(self, agent_id):
        """
        agent with id agent_id moves one step to the left
        :param agent_id: Index of the agent in self.agent_positions
        :return:
        """
        self.agent_positions[agent_id] = (
            np.clip(self.agent_positions[agent_id][0] - 1, self.arena_constraints["x_min"],
                    self.arena_constraints["x_max"] - 1),
            self.agent_positions[agent_id][1])

    def right_step(self, agent_id):
        """
        agent with id agent_id moves one step to the right
        :param agent_id: Index of the agent in self.agent_positions
        :return:
        """
        self.agent_positions[agent_id] = (
            np.clip(self.agent_positions[agent_id][0] + 1, self.arena_constraints["x_min"],
                    self.arena_constraints["x_max"] - 1),
            self.agent_positions[agent_id][1])

    def pickup_or_hold_resource(self, agent_id, resource_id):
        """
        Lets a agent pick up or hold a resource. I.e. the position of the resource is updated to match that of the
        agent that has picked it up or is holding it. Ensures that the agent is marked as having that resource.
        :param agent_id: Index of the agent in self.agent_positions
        :param resource_id: Index of the resource in self.resource_positions
        :return:
        """
        self.resource_positions[resource_id] = self.agent_positions[agent_id]
        self.has_resource[agent_id] = resource_id

    def drop_resource(self, agent_id):
        """
        Lets a agent drop a resource. I.e. Ensures that the agent is marked as no longer having that resource.
        :param agent_id: Index of the agent in self.agent_positions
        :return:
        """
        resource_id = self.has_resource[agent_id]

        if agent_id not in self.resource_carried_by[resource_id]:
            self.resource_carried_by[resource_id] += [agent_id]

        self.has_resource[agent_id] = None

    # Envioronment dynamics -------------------------------------------------------------------------------------------
    def slide_resource(self, resource_id):
        """
        Lets a resource slide. I.e. the position moves towards the nest
        :param resource_id:
        :return:
        """

        new_x = self.resource_positions[resource_id][0]
        new_y = max(self.resource_positions[resource_id][1] - self.sliding_speed,
                    self.cache_start)

        self.resource_positions[resource_id] = (new_x, new_y)

    def spawn_resource(self):
        """
        Spawn a new resource in the source area if it is possible to do so
        :return: x,y coordinate of new resource if successful. None otherwise
        """
        # Places all resources
        resource_placed = False

        # If there is no space to spawn new resources, don't spawn
        if self.source_is_full():
            return None

        while not resource_placed:
            x, y = self.generate_resource_position()
            if self.resource_map[y][x] == 0 and (x, y) not in self.resource_positions:
                self.resource_map[y][x] = self.latest_resource_id + 1
                self.latest_resource_id += 1
                self.resource_positions += [(x, y)]
                try:
                    self.resource_transforms += [rendering.Transform()]
                except:
                    pass
                self.resource_carried_by += [[]]
                resource_placed = True
                self.current_num_resources += 1
                try:
                    self.add_resource_to_rendering(self.latest_resource_id)
                except:
                    pass
                return x, y

    def delete_resource(self, resource_id):
        """
        Sends a resource to the dumping position and decrements the resource count
        :param resource_id:
        :return:
        """
        self.resource_positions[resource_id] = self.dumping_position
        self.current_num_resources -= 1

    # Specialisation Metrics ------------------------------------------------------------------------------------------
    def calculate_ferrante_specialisation(self):
        """
        Calculates task specialisation according to Ferrante et al's measure i.e:
        Of all the retrieved resources, what proportion were carried by multiple agents
        :return: Float denoting degree of specialisation
        """
        resources_retrieved_by_many = 0
        total_resources_retrieved = 0

        for i in range(len(self.resource_positions)):
            if self.resource_positions[i] == self.dumping_position:
                total_resources_retrieved += 1

                if len(self.resource_carried_by[i]) > 1:
                    resources_retrieved_by_many += 1

        if total_resources_retrieved != 0:
            return resources_retrieved_by_many / total_resources_retrieved
        else:
            return 0.0

    # Rendering Functions ---------------------------------------------------------------------------------------------
    def draw_arena_segment(self, top, bottom, rgb_tuple):
        """
        Helper function that creates the geometry for a segment of the arena. Intended to be used by the viewer

        :param top:
        :param bottom:
        :param rgb_tuple:
        :return: A FilledPolygon object that can be added to the viewer using add_geom
        """

        l, r, t, b = self.arena_constraints["x_min"] * self.scale, \
                     self.arena_constraints["x_max"] * self.scale, \
                     top * self.scale, \
                     bottom * self.scale
        arena_segment = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])
        arena_segment.add_attr(
            rendering.Transform(
                translation=(
                    0, 0)))
        arena_transform = rendering.Transform()
        arena_segment.add_attr(arena_transform)
        arena_segment.set_color(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])
        return arena_segment

    def draw_grid(self):
        """
        Helper function that creates the geometry of gridlines to be used by the viewer

        :return: List of grid lines (PolyLine objects) each to be added to the viewer as a geometry object with add_geom
        """

        grid_lines = []

        # Draw vertical lines
        verticals_list = np.linspace(self.arena_constraints["x_min"] * self.scale,
                                     self.arena_constraints["x_max"] * self.scale, self.arena_constraints["x_max"] + 1)

        for tick in verticals_list:
            xs = np.array([tick for i in range(self.arena_constraints["y_max"] + 1)])
            ys = np.linspace(self.arena_constraints["y_min"] * self.scale,
                             self.arena_constraints["y_max"] * self.scale, self.arena_constraints["y_max"] + 1)
            xys = list(zip(xs, ys))

            line = rendering.make_polyline(xys)
            grid_lines += [line]

        # Draw horizontal lines
        horizontals_list = np.linspace(self.arena_constraints["y_min"] * self.scale,
                                       self.arena_constraints["y_max"] * self.scale,
                                       self.arena_constraints["y_max"] + 1)

        for tick in horizontals_list:
            xs = np.linspace(self.arena_constraints["x_min"] * self.scale,
                             self.arena_constraints["x_max"] * self.scale, self.arena_constraints["x_max"] + 1)
            ys = np.array([tick for i in range(self.arena_constraints["x_max"] + 1)])
            xys = list(zip(xs, ys))

            line = rendering.make_polyline(xys)
            grid_lines += [line]

        return grid_lines

    def render(self, mode='human'):
        """
        Renders the environment, placing all agents and resources in appropriate positions
        :param mode:
        :return:
        """

        screen_width = self.arena_constraints["x_max"] * self.scale
        screen_height = self.arena_constraints["y_max"] * self.scale

        if self.viewer is None:
            self.viewer = rendering.Viewer(screen_width, screen_height)

            # Draw nest
            nest = self.draw_arena_segment(self.nest_size, self.nest_start, self.nest_colour)
            self.viewer.add_geom(nest)

            # Draw cache
            cache = self.draw_arena_segment(self.cache_start + self.cache_size,
                                            self.cache_start, self.cache_colour)
            self.viewer.add_geom(cache)

            # Draw slope
            slope = self.draw_arena_segment(self.slope_start + self.slope_size,
                                            self.slope_start, self.slope_colour)
            self.viewer.add_geom(slope)

            # Draw source
            source = self.draw_arena_segment(self.source_start + self.source_size,
                                             self.source_start, self.source_colour)
            self.viewer.add_geom(source)

            # Draw grid
            grid_lines = self.draw_grid()
            for line in grid_lines:
                self.viewer.add_geom(line)

            # Draw agent(s)
            for i in range(self.num_agents):
                agent = rendering.make_circle(self.agent_width / 2 * self.scale)
                agent.set_color(self.agent_colour[0], self.agent_colour[1], self.agent_colour[2])
                agent.add_attr(
                    rendering.Transform(
                        translation=(
                            0,
                            0)))
                agent.add_attr(self.agent_transforms[i])
                self.viewer.add_geom(agent)

            # Draw resource(s)
            for i in range(self.default_num_resources):
                resource = rendering.make_circle(self.resource_width / 2 * self.scale)
                resource.set_color(self.resource_colour[0], self.resource_colour[1], self.resource_colour[2])
                resource.add_attr(
                    rendering.Transform(
                        translation=(
                            0,
                            0)))
                resource.add_attr(self.resource_transforms[i])
                self.viewer.add_geom(resource)

        # Set position of agent(s)
        for i in range(self.num_agents):
            self.agent_transforms[i].set_translation(
                (self.agent_positions[i][0] - self.arena_constraints["x_min"] + 0.5) * self.scale,
                (self.agent_positions[i][1] - self.arena_constraints["y_min"] + 0.5) * self.scale)

        # Set position of resource(s)
        for i in range(len(self.resource_positions)):
            self.resource_transforms[i].set_translation(
                (self.resource_positions[i][0] - self.arena_constraints["x_min"] + 0.5) * self.scale,
                (self.resource_positions[i][1] - self.arena_constraints["y_min"] + 0.5) * self.scale)

        return self.viewer.render(return_rgb_array=mode == 'rgb_array')

    def add_resource_to_rendering(self, resource_id):
        resource = rendering.make_circle(self.resource_width / 2 * self.scale)
        resource.set_color(self.resource_colour[0], self.resource_colour[1], self.resource_colour[2])
        resource.add_attr(
            rendering.Transform(
                translation=(
                    0,
                    0)))
        resource.add_attr(self.resource_transforms[resource_id])
        if self.viewer is not None:
            self.viewer.add_geom(resource)

    def close(self):
        if self.viewer:
            self.viewer.close()
            self.viewer = None
