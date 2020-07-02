import json
from fitness import FitnessCalculator
from agents.nn_agent import NNAgent


class Learner:
    def __init__(self, calculator):
        assert isinstance(calculator, FitnessCalculator), "Did not pass a fitness calculator object"

        self.parameter_filename = calculator.get_parameter_filename()
        self.parameter_dictionary = calculator.get_parameter_dictionary()

        self.fitness_calculator = calculator
        self.population_size = self.parameter_dictionary['algorithm']['agent_population_size']
        self.team_type = self.parameter_dictionary['general']['team_type']
        self.reward_level = self.parameter_dictionary['general']['reward_level']
        self.genome_length = self.get_genome_length()
        self.Agent = None

        if self.parameter_dictionary['general']['agent_type'] == "nn":
            self.Agent = NNAgent

    def learn(self):
        pass

    # Helpers ---------------------------------------------------------------------------------------------------------

    def get_genome_length(self):
        """
        Get the length of the typical genome that will be used in learning

        @param parameter_filename: Name of the file containing the experiment parameters
        @return: Integer representing the genome length
        """
        if self.parameter_dictionary['general']['agent_type'] == "nn":

            # Get the number of weights in a neural network-based agent
            num_weights = NNAgent(self.fitness_calculator.get_observation_size(),
                                  self.fitness_calculator.get_action_size(), self.parameter_filename).get_num_weights()

            # Genomes for heterogeneous teams rewarded at the team level are twice as long because two agent genomes
            # must be concatenated into a larger one
            if self.parameter_dictionary['general']['team_type'] == "heterogeneous" and \
                    self.parameter_dictionary['general']['reward_level'] == "team":
                return num_weights * 2
            else:
                return num_weights

    def convert_genomes_to_agents(self, genome_population):
        """
        Convert list of genomes into list of agents that use those genomes, according to team type and reward level
        specified in the parameters

        @param genome_population: List of genomes
        @return: List of Agent objects that can be used in the environment
        """
        agent_population = []

        # In homogeneous teams, each genome is used for two identical agents
        if self.team_type == "homogeneous":
            for genome in genome_population:
                agent_1 = self.Agent(self.fitness_calculator.get_observation_size(),
                                     self.fitness_calculator.get_action_size(), self.parameter_filename, genome)
                agent_2 = self.Agent(self.fitness_calculator.get_observation_size(),
                                     self.fitness_calculator.get_action_size(), self.parameter_filename, genome)
                agent_population += [agent_1, agent_2]

        elif self.team_type == "heterogeneous":
            # In heterogeneous teams rewarded at the team level, each genome is two concatenated agents
            if self.reward_level == "team":
                for genome in genome_population:
                    mid = int(len(genome) / 2)
                    genome_part_1 = genome[0:mid]
                    genome_part_2 = genome[mid:]
                    agent_1 = self.Agent(self.fitness_calculator.get_observation_size(),
                                         self.fitness_calculator.get_action_size(), self.parameter_filename,
                                         genome_part_1)
                    agent_2 = self.Agent(self.fitness_calculator.get_observation_size(),
                                         self.fitness_calculator.get_action_size(), self.parameter_filename,
                                         genome_part_2)
                    agent_population += [agent_1, agent_2]

            # In heterogeneous teams rewarded at the individual level, each genome is a unique agent
            elif self.reward_level == "individual":
                for genome in genome_population:
                    agent_1 = self.Agent(self.fitness_calculator.get_observation_size(),
                                         self.fitness_calculator.get_action_size(), self.parameter_filename, genome)
                    agent_population += [agent_1]

        return agent_population

    def get_genome_fitnesses_from_agent_fitnesses(self, agent_fitnesses):
        """
        Given a list of fitnesses of pairs of agents, returns the fitnesses of the genomes they came from, based on the
        configuration of team type and reward level

        @param agent_fitnesses: A list of fitness values for each agent in the agent population
        @return: A list of fitness values for each genome that the agents came from
        """
        genome_fitnesses = []

        if self.reward_level == "team":
            for i in range(0, len(agent_fitnesses)-1, 2):
                genome_fitness = agent_fitnesses[i] + agent_fitnesses[i+1]
                genome_fitnesses += [genome_fitness]

            return genome_fitnesses

        elif self.reward_level == "individual" and self.team_type == "heterogneous":
            return agent_fitnesses

        else:
            raise RuntimeError('Homogeneous-Individual configuration not fully supported yet')


    def generate_model_name(self, fitness):
        pass

    @staticmethod
    def get_core_params_in_model_name(parameter_dictionary):
        """
        Given a parameter dictionary, returns a list of the important parameter values that are not specific to the
        algorithm being used (e.g. environment params, seed, agent type etc).

        @param parameter_dictionary: Dictionary of parameters
        @return: List of parameter values
        """
        parameters_in_name = []
        # Get general params
        parameters_in_name += [parameter_dictionary['general']['algorithm_selected']]
        parameters_in_name += [parameter_dictionary['general']['team_type']]
        parameters_in_name += [parameter_dictionary['general']['reward_level']]
        parameters_in_name += [parameter_dictionary['general']['agent_type']]
        parameters_in_name += [parameter_dictionary['general']['seed']]

        # Get environment params
        parameters_in_name += [parameter_dictionary['environment']['num_agents']]
        parameters_in_name += [parameter_dictionary['environment']['num_resources']]
        parameters_in_name += [parameter_dictionary['environment']['sensor_range']]
        parameters_in_name += [parameter_dictionary['environment']['sliding_speed']]
        parameters_in_name += [parameter_dictionary['environment']['arena_length']]
        parameters_in_name += [parameter_dictionary['environment']['arena_width']]
        parameters_in_name += [parameter_dictionary['environment']['cache_start']]
        parameters_in_name += [parameter_dictionary['environment']['slope_start']]
        parameters_in_name += [parameter_dictionary['environment']['source_start']]
        parameters_in_name += [parameter_dictionary['environment']['base_cost']]
        parameters_in_name += [parameter_dictionary['environment']['upward_cost_factor']]
        parameters_in_name += [parameter_dictionary['environment']['downward_cost_factor']]
        parameters_in_name += [parameter_dictionary['environment']['carry_factor']]
        parameters_in_name += [parameter_dictionary['environment']['resource_reward']]
        parameters_in_name += [parameter_dictionary['environment']['simulation_length']]
        parameters_in_name += [parameter_dictionary['environment']['num_simulation_runs']]

        # Get agent params for relevant agent type
        agent_type = parameter_dictionary['general']['agent_type']

        if agent_type == 'nn':
            parameters_in_name += [parameter_dictionary['agent']['nn']['hidden_layers']]
            parameters_in_name += [parameter_dictionary['agent']['nn']['activation_function']]

        return parameters_in_name

    @staticmethod
    def get_additional_params_in_model_name(parameter_dictionary):
        pass
