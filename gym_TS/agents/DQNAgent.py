'''
Deep Q-learning Agent
Taken from example at https://keon.io/deep-q-learning/
'''
import numpy as np
import random
from time import time
import copy

from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Reshape
from keras.optimizers import Adam
from keras.callbacks import TensorBoard
from keras import backend as K
from keras.losses import mean_squared_error
from keras.models import load_model

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
        self.epsilon_decay = 0.99999995
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.weights_loaded = False
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

    def load_model(self, model_path):
        #self.model.load_weights(weight_path)
        self.model = load_model(model_path)
        self.weights_loaded = True

    def remember(self, state, action, reward, next_state, done):
        self.memory.append((state, action, reward, next_state, done))

    def act(self, state):
        if not self.weights_loaded:
            if np.random.rand() <= self.epsilon:
                return random.randrange(self.action_size)
            act_values = self.model.predict(state)

            return np.argmax(act_values[0])  # returns action

        else:
            act_values = self.model.predict(state)
            return np.argmax(act_values[0])

    def replay(self, batch_size):
        minibatch = []
        try:
            minibatch = random.sample(self.memory, batch_size)
        except ValueError:
            minibatch = copy.deepcopy(self.memory)

        y_predicted = np.zeros([batch_size, self.action_size])
        y_true = np.zeros([batch_size, self.action_size])
        h = 0

        for state, action, reward, next_state, done in minibatch:
            old_qs = self.model.predict(state)  # Q values for state

            target = reward

            if not done:
                target = reward + self.gamma * np.amax(self.model.predict(next_state)[0])

            target_f = self.model.predict(state)
            target_f[0][action] = target  # q_values = [ blah, blah, target, blah]
            # self.model.fit(state, target_f, epochs=1, verbose=0, callbacks=[self.tensorboard])
            self.model.fit(state, target_f, epochs=1, verbose=0)

            y_predicted[h] = np.array(old_qs)
            y_true[h] = np.array(target_f)
            h += 1

        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # print("y_predicted: " + str(y_predicted))
        # print("y_true: " + str(y_true))
        y_predicted = K.variable(y_predicted)
        y_true = K.variable(y_true)
        loss = np.mean(K.eval(mean_squared_error(y_predicted,  y_true)))
        # print("Loss: " + str(loss))
        return loss

    def save(self, filename):
        self.model.save(filename)

    def generate_q_table(self, possible_states):
        for state in possible_states:
            print(str(state) + ": " + str(self.model.predict(state)))

