'''
Deep Q-learning Agent
Taken from example at https://keon.io/deep-q-learning/
'''
import numpy as np
import random
from time import time

from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Reshape
from keras.optimizers import Adam
from keras.callbacks import TensorBoard

# import warnings
# warnings.filterwarnings('ignore',category=FutureWarning)


class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.tensorboard = TensorBoard(log_dir="./gym_TS/logs/DQN_{}".format(time()))

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Dense(50, input_dim=self.state_size, activation='relu'))
        # model.add(Dense(24, activation='relu'))
        # model.add(Reshape((1, 24)))
        # model.add(LSTM(64, return_sequences=False, dropout=0.1, recurrent_dropout=0.1))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss='mse', optimizer=Adam(lr=self.learning_rate))

        return model

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return random.randrange(self.action_size)
        act_values = self.model.predict(state)

        return np.argmax(act_values[0])  # returns action

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)

        for state, action, reward, next_state, done in minibatch:
            target = reward

            if not done:
              target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

            target_f = self.model.predict(state)
            target_f[0][action] = target
            # self.model.fit(state, target_f, epochs=1, verbose=0, callbacks=[self.tensorboard])
            self.model.fit(state, target_f, epochs=1, verbose=0)

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def save(self, filename):
        self.model.save(filename)
