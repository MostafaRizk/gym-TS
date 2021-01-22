import numpy as np
import os
import pandas as pd

from fitness import FitnessCalculator
from agents.nn_agent_lean import NNAgent

evolved_genomes_parameters_directory = "/Users/mostafa/Documents/Code/PhD/TS-Platform/results/2020_11_24_magic_plot_combined_new_seed/experiments"
evolved_genomes_results_directory = "/Users/mostafa/Documents/Code/PhD/TS-Platform/results/2020_11_24_magic_plot_combined_new_seed/results"
results_file = os.path.join(evolved_genomes_results_directory,"results_final.csv")

# Load all genomes into pandas dataframe
evolved_data = pd.read_csv(results_file)
specialisation_file = os.path.join(evolved_genomes_results_directory,"specialisation_final.csv")
f = open(specialisation_file, "w")
f.write(f"Model Name,R_coop,R_coop_eff,R_spec,R_coop x P,R_coop_eff x P,R_spec x P\n")

# Get evolved data
# For each genome
for index, row in evolved_data.iterrows():
    # Check if it has team reward and 2 agents
    if row["reward_level"] == "team" and row["num_agents"] == 2:
        # Get genome from corresponding model file
        model_file = os.path.join(evolved_genomes_results_directory, row["model_name"])

        parameter_filename = os.path.join(evolved_genomes_parameters_directory, "_".join(row["model_name"].split("_")[:-2]) + ".json")
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
        specialisation_measures = np.mean(np.array(results["specialisation_list"]), axis=0)
        f.write(",".join([row["model_name"]] + [str(measure) for measure in specialisation_measures]) + "\n")
        break

    '''
    # Duplicate genome if it has an individual reward
    if row["reward_level"] == "individual" and row["num_agents"] == 2:
        # Get genome from corresponding model file
        model_file = os.path.join(evolved_genomes_results_directory, row["model_name"])
        genome = np.load(model_file)
    '''

f.close()