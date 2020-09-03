import argparse
import json

from agents.hardcoded.collector import HardcodedCollectorAgent
from agents.hardcoded.dropper import HardcodedDropperAgent
from agents.hardcoded.generalist import HardcodedGeneralistAgent
from agents.hardcoded.lazy_generalist import HardcodedLazyGeneralistAgent
from fitness import FitnessCalculator
from learning.cma import CMALearner
from learning.rwg import RWGLearner
import numpy as np
from agents.nn_agent_lean import NNAgent
import pandas as pd

model_name = "rwg_heterogeneous_team_nn_slope_1_2_4_1_4_8_4_1_3_7_1_3.0_0.2_2_1000_500_5_rnn_True_0_0_linear_20000_normal_0_1_22071.879999999997.npy"
parameter_filename = "rnn_bias_0HL.json"
fitness_calculator = FitnessCalculator(parameter_filename)

csv_file = "sorted_rwg.csv"
f = open(csv_file, "r")
genomes = f.read().strip().split("\n")
f.close()

npy_genome = NNAgent.load_model_from_file(model_name)
npy_mid = int(len(npy_genome) / 2)
genome_part_1_npy = npy_genome[0:npy_mid]
genome_part_2_npy = npy_genome[npy_mid:]

full_genome = np.array([float(weight) for weight in genomes[0].split(",")[0:-6]])
mid = int(len(full_genome) / 2)
genome_part_1 = full_genome[0:mid]
genome_part_2 = full_genome[mid:]
agent_1 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(), parameter_filename, genome_part_1)
agent_2 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(), parameter_filename, genome_part_2)
results = fitness_calculator.calculate_fitness(agent_1, agent_2, render=True, time_delay=0.1)