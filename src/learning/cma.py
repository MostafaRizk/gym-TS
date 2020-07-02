from learning.learner_parent import Learner

class CMALearner(Learner):
    def learn(self):
        pass












def cma_es(fitness_calculator, seed_value, sigma, model_name, results_file_name, team_type, selection_level, num_generations, num_teams):
    pop_size = num_teams

    if team_type == "heterogeneous" and selection_level == "individual":
        pop_size = num_teams * 2

    options = {'seed': seed_value, 'maxiter': num_generations, 'popsize': pop_size, 'tolx': 1e-3, 'tolfunhist': 2e2} #, 'ftarget': 'inf'}

    model_params = model_name.split("_")

    simulation_length = model_params[3]
    num_trials = model_params[5]
    random_seed = model_params[6]
    num_robots = model_params[7]
    num_resources = model_params[8]
    sensor_range = model_params[9]
    slope_angle = model_params[10]
    arena_length = model_params[11]
    arena_width = model_params[12]
    cache_start = model_params[13]
    slope_start = model_params[14]
    source_start = model_params[15]
    upward_cost_factor = model_params[16]
    downward_cost_factor = model_params[17]
    carry_factor = model_params[18]
    resource_reward_factor = model_params[19]

    seed_file = f"bootstrap_{team_type}_{selection_level}_{simulation_length}_{num_trials}_{random_seed}_{num_robots}_{num_resources}_{sensor_range}_{slope_angle}_{arena_length}_{arena_width}_{cache_start}_{slope_start}_{source_start}_{upward_cost_factor}_{downward_cost_factor}_{carry_factor}_{resource_reward_factor}.npy"
    seed_genome = None
    # f"CMA_{team_type}_{simulation_length}_{num_generations}_{num_trials}_{random_seed}_{num_robots}_{num_resources}_{sensor_range}_{slope_angle}_{arena_length}_{arena_width}_{cache_start}_{slope_start}_{source_start}_{upward_cost_factor}_{downward_cost_factor}_{carry_factor}_{resource_reward_factor}_{sigma}_{population}"

    try:
        seed_genome = np.load(seed_file)
    except:
        raise RuntimeError("No bootstrap model matches this experiment's parameters")

    seed_fitness = None #fitness_calculator.calculate_fitness(team_type, selection_level, individual_1, individual_2, render=False)

    es = cma.CMAEvolutionStrategy(seed_genome, sigma, options)

    log_file_name = model_name + ".log"

    # Send output to log file
    old_stdout = sys.stdout
    log_file = open(log_file_name, "a")
    sys.stdout = log_file

    while not es.stop():
        population = es.ask()

        if team_type == "homogeneous" and selection_level == "individual":
            new_population = []
            for ind in population:
                new_population += [ind, ind]
            population = new_population

        fitnesses = fitness_calculator.calculate_fitness_of_population(population, team_type, selection_level)
        es.tell(population, [-f for f in fitnesses])
        iteration_number = es.result.iterations

        if iteration_number == 0:
            seed_fitness = -es.result[1]

        if iteration_number % LOG_EVERY == 0:
            # Log results to results file
            results = model_name.replace("_", ",")
            results += f",{log_file_name}, {seed_fitness}, {-es.result[1]}\n"
            intermediate_results_file_name = f"results_{iteration_number}.csv"

            if not os.path.exists(intermediate_results_file_name):
                results_file = open(intermediate_results_file_name, 'a')
                results_file.write("Algorithm Name, Team Type, Selection Level, Simulation Length, Num Generations, Num Trials, "
                                   "Random Seed, Num Robots, Num Resources, Sensor Range, Slope Angle, Arena Length, "
                                   "Arena Width, Cache Start, Slope Start, Source Start, Sigma, Population, Log File, "
                                   "Seed Fitness, Evolved Fitness\n")
            else:
                results_file = open(intermediate_results_file_name, 'a')

            results_file.write(results)
            results_file.close()

            # Log genome
            # Split the genome and save both halves separately for heterogeneous setup
            if team_type == "heterogeneous" and selection_level == "team":
                best_individual_1 = TinyAgent(fitness_calculator.get_observation_size(),
                                              fitness_calculator.get_action_size(),
                                              seed=seed_value)
                best_individual_2 = TinyAgent(fitness_calculator.get_observation_size(),
                                              fitness_calculator.get_action_size(),
                                              seed=seed_value)

                # Split genome
                mid = int(len(es.result[0]) / 2)
                best_individual_1.load_weights(es.result[0][0:mid])
                best_individual_2.load_weights(es.result[0][mid:])

                best_individual_1.save_model(model_name + "_controller1_" + str(iteration_number) + "_")
                best_individual_2.save_model(model_name + "_controller2_" + str(iteration_number) + "_")

            else:
                best_individual = TinyAgent(fitness_calculator.get_observation_size(),
                                            fitness_calculator.get_action_size(),
                                            seed=seed_value)
                best_individual.load_weights(es.result[0])
                best_individual.save_model(model_name + "_" + str(iteration_number))

        es.disp()

    print(f"Best score is {-es.result[1]}")

    ''''''
    sys.stdout = old_stdout
    log_file.close()

    # Append results to results file. Create file if it doesn't exist
    results = model_name.replace("_", ",")
    results += f",{log_file_name}, {seed_fitness}, {-es.result[1]}\n"
    results_file = open(results_file_name, 'a')
    results_file.write(results)
    results_file.close()

    return es.result[0]