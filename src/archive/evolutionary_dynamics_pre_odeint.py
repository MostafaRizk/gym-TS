def get_final_distribution(parameter_file, payoff):
    """
    Get distribution of strategies after a certain amount of time passes
    @param parameter_file: Path to json file
    @param payoff: Payoff matrix for all pairs of strategies
    @return: List containing distribution of strategies at each time step
    """

    parameter_dictionary = json.loads(open(parameter_file).read())

    # Distribution of strategies over time (assumes everyone is a novice to begin with)
    x = {"Novice": [parameter_dictionary["initial_distribution"]["Novice"]],
         "Generalist": [parameter_dictionary["initial_distribution"]["Generalist"]],
         "Dropper": [parameter_dictionary["initial_distribution"]["Dropper"]],
         "Collector": [parameter_dictionary["initial_distribution"]["Collector"]]}

    # Average fitness of each strategy based on their proportions in the population
    novice_fitness = [sum([x[strategy][0]*payoff["Novice"][strategy] for strategy in x])]
    generalist_fitness = [sum([x[strategy][0]*payoff["Generalist"][strategy] for strategy in x])]
    dropper_fitness = [sum([x[strategy][0]*payoff["Dropper"][strategy] for strategy in x])]
    collector_fitness = [sum([x[strategy][0]*payoff["Collector"][strategy] for strategy in x])]

    # Average fitness of population
    average_fitness = x["Novice"][0]*novice_fitness[0] + x["Generalist"][0]*generalist_fitness[0] + \
                      x["Dropper"][0]*dropper_fitness[0] + x["Collector"][0]*collector_fitness[0]

    total_time = parameter_dictionary["total_time"]
    dt = parameter_dictionary["dt"]

    novice_fitness[0] *= dt
    generalist_fitness[0] *= dt
    dropper_fitness[0] *= dt
    collector_fitness[0] *= dt

    for t in range(total_time):
        # Calculate fitness of each strategy and average fitness
        f_novice = sum([x[strategy][t]*payoff["Novice"][strategy] for strategy in x])
        f_generalist = sum([x[strategy][t]*payoff["Generalist"][strategy] for strategy in x])
        f_dropper = sum([x[strategy][t]*payoff["Dropper"][strategy] for strategy in x])
        f_collector = sum([x[strategy][t]*payoff["Collector"][strategy] for strategy in x])
        f_avg = x["Novice"][t]*f_novice + x["Generalist"][t]*f_generalist + x["Dropper"][t]*f_dropper + x["Collector"][t]*f_collector

        # Append to vectors
        novice_fitness += [f_novice * dt]
        generalist_fitness += [f_generalist * dt]
        dropper_fitness += [f_dropper * dt]
        collector_fitness += [f_collector * dt]

        # Differential equations to update proportions
        x["Novice"] += [x["Novice"][t] + (x["Novice"][t] * (f_novice - f_avg))*dt]
        x["Generalist"] += [x["Generalist"][t] + (x["Generalist"][t] * (f_generalist - f_avg)) * dt]
        x["Dropper"] += [x["Dropper"][t] + (x["Dropper"][t] * (f_dropper - f_avg)) * dt]
        x["Collector"] += [x["Collector"][t] + (x["Collector"][t] * (f_collector - f_avg)) * dt]

    return x


def plot_results(x, parameter_file):

    # Make plots
    plt.plot(x["Novice"], label='Novice')
    plt.plot(x["Generalist"], label='Generalist')
    plt.plot(x["Dropper"], label='Dropper')
    plt.plot(x["Collector"], label='Collector')
    plt.grid()
    plt.ylim(-0.1, 1.1)
    plt.title("Distribution of Strategies Over Time")
    plt.ylabel("Proportion of population")
    plt.xlabel("Time")
    plt.legend(loc='best')

    path = "/".join([el for el in parameter_file.split("/")[:-1]]) + "/analysis"
    filename = parameter_file.split("/")[-1].strip(".json") + ".png"

    plt.savefig(os.path.join(path, filename))
