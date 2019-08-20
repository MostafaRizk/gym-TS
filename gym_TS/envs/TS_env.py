"""
Code modified from OpenAI's Mountain Car example
"""

import gym
from gym import error, spaces, utils
from gym.utils import seeding

import math
import numpy as np

class TSEnv(gym.Env):
    metadata = {
      'render.modes': ['human', 'rgb_array'],
      'video.frames_per_second': 30
    }

    def __init__(self, goal_velocity = 0):
        '''
        Initialise position, speed, gravity and velocity. Also defines action space and observation space. Creates seed?
        :param goal_velocity:
        '''
        self.min_position = 0
        self.max_position = 10
        self.max_speed = 0.07
        self.goal_position = 8.5
        self.goal_velocity = goal_velocity
        self.offset = 5

        self.force=0.001
        self.gravity=0.0025

        self.slope_start = 2.5
        self.slope_end = 7.5
        self.slope_angle = 10

        self.low = np.array([self.min_position, -self.max_speed])
        self.high = np.array([self.max_position, self.max_speed])

        self.viewer = None

        #TODO: Modify to have relevant actions and observations
        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(self.low, self.high, dtype=np.float32)

        self.seed()

        #TODO: Initialise neural network

    def seed(self, seed=None):
        '''
        Creates random seed and returns it
        :param seed:
        :return:
        '''
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action):
        '''
        Logs state, adjusts velocity according to action taken, adjusts position according to velocity and records new state.
        :param action:
        :return: The new state, the reward and whether or not the goal has been achieved
        '''

        #Returns an error if the action is invalid
        assert self.action_space.contains(action), "%r (%s) invalid" % (action, type(action))

        position, velocity = self.state
        '''
        velocity += (action-1)*self.force + math.cos(3*position)*(-self.gravity)
        velocity = np.clip(velocity, -self.max_speed, self.max_speed)
        position += velocity
        position = np.clip(position, self.min_position, self.max_position)

        if (position==self.min_position and velocity<0):
            velocity = 0
        '''

        #TODO: Plug observations into NN

        done = bool(position >= self.goal_position and velocity >= self.goal_velocity)
        reward = -1.0

        self.state = (position, velocity)
        return np.array(self.state), reward, done, {}

    def reset(self):
        '''
        Sets a new random location between 0 and 1 and sets velocity to 0
        :return:
        '''
        #TODO: Redefine state to be (position, want_res, has_res, behav) ?
        self.state = np.array([self.np_random.uniform(low=0, high=1), 0])
        return np.array(self.state)

    def height_map(self, x):
        '''
        Maps an x coordinate on the track to the height of the track at that point
        :param x:
        :return:
        '''
        if x < self.slope_start:
            return self.slope_start * math.tan(math.radians(self.slope_angle))
        elif x < self.slope_end:
            return x * math.tan(math.radians(self.slope_angle))
        else:
            return self.slope_end * math.tan(math.radians(self.slope_angle))

    def _height(self, xs):
        '''
        Returns height according to the function representing the track
        :param xs:
        :return:
        '''
        if not isinstance(xs,np.ndarray):
            return self.height_map(xs)
        else:
            ys = np.copy(xs)
            for i in range(len(xs)):
                ys[i] = self.height_map(xs[i])
            return ys

    def render(self, mode='human'):
        '''
        Renders the environment and agent(s)
        :param mode:
        :return:
        '''
        screen_width = 600
        screen_height = 400

        world_width = self.max_position - self.min_position
        scale = screen_width/world_width
        carwidth=40
        carheight=20
        reswidth=20
        resheight=30


        if self.viewer is None:
            #Define the geometry of the track
            from gym.envs.classic_control import rendering
            self.viewer = rendering.Viewer(screen_width, screen_height)
            xs = np.linspace(self.min_position, self.max_position, 100)
            ys = self._height(xs)
            print(xs)
            print(ys)
            xys = list(zip((xs-self.min_position)*scale, ys*scale))

            self.track = rendering.make_polyline(xys)
            self.track.set_linewidth(4)
            self.viewer.add_geom(self.track)

            clearance = 10

            #Create car
            l,r,t,b = -carwidth/2, carwidth/2, carheight, 0
            car = rendering.FilledPolygon([(l,b), (l,t), (r,t), (r,b)])
            car.set_color(0, 0, 1)
            car.add_attr(rendering.Transform(translation=(0, clearance)))
            self.cartrans = rendering.Transform()
            car.add_attr(self.cartrans)
            self.viewer.add_geom(car)
            frontwheel = rendering.make_circle(carheight/2.5)
            frontwheel.set_color(.5, .5, .5)
            frontwheel.add_attr(rendering.Transform(translation=(carwidth/4,clearance)))
            frontwheel.add_attr(self.cartrans)
            self.viewer.add_geom(frontwheel)
            backwheel = rendering.make_circle(carheight/2.5)
            backwheel.add_attr(rendering.Transform(translation=(-carwidth/4,clearance)))
            backwheel.add_attr(self.cartrans)
            backwheel.set_color(.5, .5, .5)
            self.viewer.add_geom(backwheel)

            #Create resource
            l, r, t, b = (self.goal_position-self.min_position)*scale -reswidth / 2, (self.goal_position-self.min_position)*scale + reswidth / 2, self._height(self.goal_position)*scale + resheight, self._height(self.goal_position)*scale
            resource = rendering.FilledPolygon([(l, b), (l, t), (r, t), (r, b)])
            #TODO: Allow movement of resource
            #resource.add_attr(rendering.Transform(translation=(0, clearance)))
            #self.cartrans = rendering.Transform()
            #car.add_attr(self.cartrans)
            self.viewer.add_geom(resource)
            resource.set_color(0, 1, 0)


        #Set position of car
        pos = self.state[0]
        self.cartrans.set_translation((pos-self.min_position)*scale, self._height(pos)*scale)
        #self.cartrans.set_rotation(math.cos(3 * pos))

        return self.viewer.render(return_rgb_array = mode=='rgb_array')

    def get_keys_to_action(self):
        return {():1,(276,):0,(275,):2,(275,276):1} #control with left and right arrow keys

    def close(self):
        if self.viewer:
            self.viewer.close()
            self.viewer = None
