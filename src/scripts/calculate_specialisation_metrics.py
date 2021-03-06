'''
Calculates the specialisation metrics for genomes in the given results folder
'''

import numpy as np
import os
import pandas as pd

from fitness import FitnessCalculator
from agents.nn_agent_lean import NNAgent
from scipy.stats import multivariate_normal
from glob import glob

evolved_genomes_parameters_directory = "/Users/mostafa/Documents/Code/PhD/TS-Platform/results/2021_02_17_cma_for_diff_slopes_combined/experiments"
evolved_genomes_results_directory = "/Users/mostafa/Documents/Code/PhD/TS-Platform/results/2021_02_17_cma_for_diff_slopes_combined/results"
results_file = os.path.join(evolved_genomes_results_directory, "results_final.csv")

num_agents = 2
sliding_speed = 2

# Create data file
specialisation_file = f"specialisation_different_slopes_{sliding_speed}.csv"
f = open(specialisation_file, "w")
f.write(f"Model Name,Team Fitness,R_coop,R_coop_eff,R_spec,R_coop x P,R_coop_eff x P,R_spec x P,Model Directory\n")
#f.write("\n")



''''''
for generation in ["final"]:
    results_file = os.path.join(evolved_genomes_results_directory,f"results_{generation}.csv")

    # Load all evolved genomes into pandas dataframe
    evolved_data = pd.read_csv(results_file)

    # Get evolved data
    # For each genome
    for index, row in evolved_data.iterrows():
        ''''''

        # Check if it has team reward and 2 agents
        if row["reward_level"] == "team" and row["num_agents"] == num_agents and row["sliding_speed"] == sliding_speed:
            # Get genome from corresponding model file
            model_file = os.path.join(evolved_genomes_results_directory, row["model_name"])

            # Use this line if the evolutionary run also did seeding
            parameter_filename = os.path.join(evolved_genomes_parameters_directory, "cma_with_seeding_" + "_".join(row["model_name"].split("/")[-1].split("_")[1:-2]) + ".json")

            # Use this line if the evolutionary run did not use seeding
            #parameter_filename = os.path.join(evolved_genomes_parameters_directory, "_".join(row["model_name"].split("_")[:-2]) + ".json")

            fitness_calculator = FitnessCalculator(parameter_filename)

            full_genome = np.load(model_file)
            mid = int(len(full_genome) / 2)
            genome_part_1 = full_genome[0:mid]
            genome_part_2 = full_genome[mid:]
            agent_1 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(),
                              parameter_filename, genome_part_1)
            agent_2 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(),
                              parameter_filename, genome_part_2)
            results = fitness_calculator.calculate_fitness(agent_list=[agent_1, agent_2], render=False, time_delay=0,
                                                           measure_specialisation=True, logging=False, logfilename=None,
                                                           render_mode="human")

            fitness_matrix = results["fitness_matrix"]
            new_fitness = np.mean([fitness_matrix[0][episode] + fitness_matrix[1][episode] for episode in range(len(fitness_matrix[0]))])
            specialisation_measures = np.mean(np.array(results["specialisation_list"]), axis=0)

            f.write(",".join([row["model_name"]] + [str(new_fitness)] + [str(measure) for measure in specialisation_measures] + [evolved_genomes_results_directory]) + "\n")


        ''''''
        # Duplicate genome if it has an individual reward
        if row["reward_level"] == "individual" and row["num_agents"] == num_agents and row["sliding_speed"] == sliding_speed:
            # Get genome from corresponding model file
            model_file = os.path.join(evolved_genomes_results_directory, row["model_name"])

            # Use this line if the evolutionary run also did seeding
            parameter_filename = os.path.join(evolved_genomes_parameters_directory, "cma_with_seeding_" + "_".join(row["model_name"].split("/")[-1].split("_")[1:-2]) + ".json")

            # Use this line if the evolutionary run did not use seeding
            # parameter_filename = os.path.join(evolved_genomes_parameters_directory, "_".join(row["model_name"].split("_")[:-2]) + ".json")

            fitness_calculator = FitnessCalculator(parameter_filename)

            mean_array = np.load(model_file)
            variance = None

            name_substring = "_".join(str(param) for param in row["model_name"].split("/")[-1].split("_")[1:-2])
            regex_string = f'{evolved_genomes_results_directory}/cma_with_seeding_*{name_substring}*.log'
            log_files = glob(regex_string)

            if len(log_files) > 1 or len(log_files) < 1:
                raise RuntimeError("Inappropriate number of log files")

            log_file = log_files[0]
            #log_file = os.path.join(evolved_genomes_results_directory, "_".join(row["model_name"].split("_")[:-1]) + ".log")

            g = open(log_file, "r")
            log_data = g.read().strip().split("\n")
            g.close()

            # If last line starts with Best, get line before
            flag = True
            i = -1
            while flag:
                if log_data[i].startswith("Best"):
                    variance = float(log_data[i - 1].strip().split()[4]) / 100
                    flag = False
                else:
                    i -= 1

            seed = row["seed"]

            random_variable = multivariate_normal(mean=mean_array, cov=np.identity(len(mean_array)) * variance)
            team = random_variable.rvs(2, seed)

            agent_1 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(),
                              parameter_filename, team[0])
            agent_2 = NNAgent(fitness_calculator.get_observation_size(), fitness_calculator.get_action_size(),
                              parameter_filename, team[1])
            results = fitness_calculator.calculate_fitness(agent_list=[agent_1, agent_2], render=False, time_delay=0,
                                                           measure_specialisation=True, logging=False, logfilename=None,
                                                           render_mode="human")
            fitness_matrix = results["fitness_matrix"]
            new_fitness = np.mean([fitness_matrix[0][episode] + fitness_matrix[1][episode] for episode in range(len(fitness_matrix[0]))])
            specialisation_measures = np.mean(np.array(results["specialisation_list"]), axis=0)

            f.write(",".join([row["model_name"]] + [str(new_fitness)] + [str(measure) for measure in specialisation_measures] + [evolved_genomes_results_directory]) + "\n")


f.close()
