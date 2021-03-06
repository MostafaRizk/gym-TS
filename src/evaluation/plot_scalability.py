import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import argparse

from scipy import stats
from operator import add

setups = ["Centralised", "Decentralised", "One-pop", "Homogeneous"]
spec_metric_index = 2 # R_spec
#spec_metric_index = 5 # R_spec_P


def from_string(arr_str):
    """
    Convert string to a 2D array
    @param arr_str:
    @return:
    """
    arr_str = arr_str[1:-1]
    a = []
    list_to_parse = arr_str.strip('').split("]")[:-1]

    for el in list_to_parse:
        new_el = el.replace("[","")
        new_el = [float(item) for item in new_el.split()]
        a += [new_el]

    return a


def plot_scalability(path_to_results, path_to_graph, plot_type, max_agents, violin=False, y_height=15000, showing="fitness"):
    # Prepare data lists
    x = [i for i in range(2, max_agents+2, 2)]
    y_centralised = []
    y_decentralised = []
    y_onepop = []
    y_homogeneous = []

    yerr_centralised = []
    yerr_decentralised = []
    yerr_onepop = []
    yerr_homogeneous = []

    # Read data from results file
    data = pd.read_csv(path_to_results)

    results = {}

    for setup in setups:
        for team_size in range(2, max_agents + 2, 2):
            key = f"{setup}-{team_size}"
            results[key] = {}

    for index, row in data.iterrows():
        learning_type = row["learning_type"].capitalize()
        team_type = row["team_type"].capitalize()
        reward_level = row["reward_level"].capitalize()
        num_agents = row["num_agents"]
        seed = row["seed"]

        if learning_type == "Centralised" and reward_level == "Individual":
            key = f"One-pop-{num_agents}"
        elif team_type == "Homogeneous":
            key = f"{team_type}-{num_agents}"
        else:
            key = f"{learning_type}-{num_agents}"

        if seed not in results[key]:
            results[key][seed] = None

        results[key][seed] = {"fitness": from_string(row["fitness"]),
                              "specialisation": from_string(row["specialisation"])}

    scores = {}

    for setup in setups:
        for team_size in range(2, max_agents + 2, 2):
            key = f"{setup}-{team_size}"
            scores[key] = []

    for num_agents in range(2, max_agents+2, 2):
        for setup in setups:
            key = f"{setup}-{num_agents}"

            for seed in results[key]:
                if showing == "fitness":
                    team_fitness_list = [0] * len(results[key][seed]["fitness"][0])

                    for j in range(num_agents):
                        team_fitness_list = list(map(add, team_fitness_list, results[key][seed]["fitness"][j]))

                    scores[key] += [np.mean(team_fitness_list)/num_agents]

                elif showing == "specialisation":
                    specialisation_each_episode = [episode[spec_metric_index] for episode in results[key][seed]["specialisation"]]
                    specialisation = np.mean(specialisation_each_episode)
                    scores[key] += [specialisation]

            if setup == "Centralised":
                y = y_centralised
                yerr = yerr_centralised

            elif setup == "Decentralised":
                y = y_decentralised
                yerr = yerr_decentralised

            elif setup == "One-pop":
                y = y_onepop
                yerr = yerr_onepop

            elif setup == "Homogeneous":
                y = y_homogeneous
                yerr = yerr_homogeneous

            if plot_type == "mean":
                y += [np.mean(scores[key])]
                yerr += [np.std(scores[key])]
            elif plot_type == "best":
                y += [np.max(scores[key])]
                yerr += [stats.sem(scores[key])]
            elif plot_type == "median":
                y += [np.median(scores[key])]
                yerr += [stats.sem(scores[key])]
            elif plot_type == "no_variance":
                y += [np.mean(scores[key])]
            elif plot_type == "error":
                y += [np.mean(scores[key])]
                yerr += [stats.sem(scores[key])]

    for key in results:
        print(f"{key}: {len(results[key])}")

    # Plot
    ''''''
    if not violin:
        fig1, ax1 = plt.subplots(figsize=(12, 8))
        ax1.set_title(f'Scalability of Evolved {showing.capitalize()} with Number of Agents', fontsize=20)
        if showing == "fitness":
            ax1.set_ylim(0, y_height)
            ax1.set_ylabel('Fitness per agent', fontsize=18)
        elif showing == "specialisation":
            ax1.set_ylim(0, 1.1)
            ax1.set_ylabel('Team Specialisation', fontsize=18)
        ax1.set_xticks([x for x in range(2, max_agents+2, 2)])
        ax1.set_xlabel('Number of Agents', fontsize=18)

        for tick in ax1.xaxis.get_major_ticks():
            tick.label.set_fontsize(16)

        for tick in ax1.yaxis.get_major_ticks():
            tick.label.set_fontsize(16)

        if plot_type == "mean" or plot_type == "error":
            plt.errorbar(x, y_centralised, yerr_centralised, fmt='r-', label="Centralised")
            plt.errorbar(x, y_decentralised, yerr_decentralised, fmt='b-', label="Decentralised")
            plt.errorbar(x, y_onepop, yerr_onepop, fmt='g-', label="One-pop")
            plt.errorbar(x, y_homogeneous, yerr_homogeneous, fmt='k-', label="Homogeneous")

        elif plot_type == "best" or plot_type == "median":
            plt.plot(x, y_centralised, 'ro-', label=f"Centralised ({plot_type})")
            plt.plot(x, y_decentralised, 'bo-', label=f"Decentralised ({plot_type})")
            plt.plot(x, y_onepop, 'go-', label=f"One-pop ({plot_type})")
            plt.plot(x, y_homogeneous, 'ko-', label=f"Homogeneous ({plot_type})")

        else:
            plt.plot(x, y_centralised, 'ro-', label="Centralised")
            plt.plot(x, y_decentralised, 'bo-', label="Decentralised")
            plt.plot(x, y_onepop, 'go-', label="One-pop")
            plt.plot(x, y_homogeneous, 'ko-', label="Homogeneous")

        plt.legend(loc='upper right', fontsize=16)
        plt.savefig(path_to_graph)

    else:
        def set_axis_style(ax, labels):
            ax.get_xaxis().set_tick_params(direction='out')
            ax.xaxis.set_ticks_position('bottom')
            ax.set_xticks(np.arange(1, len(labels) + 1))
            ax.set_xticklabels(labels, fontsize=12)
            ax.set_xlim(0.25, len(labels) + 0.75)
            for tick in ax.yaxis.get_major_ticks():
                tick.label.set_fontsize(12)

        #fig = plt.figure(figsize=(19, 9))
        fig, axs = plt.subplots(1, 4, sharey=True, figsize=(19,9))
        num_cols = 3

        for col,ax in enumerate(axs):

            if showing == "fitness":
                ax.set_ylim(-2000, y_height)
                ax.set_ylabel("Fitness per Agent")
            elif showing == "specialisation":
                ax.set_ylim(-0.2, 1.2)
                ax.set_ylabel("Team Specialisation")

            num_agents = (col+1) * 2
            parts = ax.violinplot([scores[f"{setup}-{num_agents}"] for setup in setups])

            for id,pc in enumerate(parts['bodies']):
                if setups[id] == "Centralised":
                    pc.set_color('red')
                elif setups[id] == "Decentralised":
                    pc.set_color('blue')
                elif setups[id] == "One-pop":
                    pc.set_color('green')
                elif setups[id] == "Homogeneous":
                    pc.set_color('black')

            for pc in ('cbars', 'cmins', 'cmaxes'):
                parts[pc].set_color('black')

            set_axis_style(ax, setups)
            ax.set_title(f"{num_agents} Agents")

        plt.suptitle(f"{showing.capitalize()} Distribution")
        plt.savefig(path_to_graph)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot scalability')
    parser.add_argument('--results_path', action="store")
    parser.add_argument('--graph_path', action="store")
    parser.add_argument('--plot_type', action="store")
    parser.add_argument('--max_agents', action="store")
    parser.add_argument('--violin', action="store")
    parser.add_argument('--y_height', action="store")
    parser.add_argument('--showing', action="store")

    results_path = parser.parse_args().results_path
    graph_path = parser.parse_args().graph_path
    plot_type = parser.parse_args().plot_type
    max_agents = int(parser.parse_args().max_agents)
    violin = parser.parse_args().violin

    if not violin or violin != "True":
        violin = False
    else:
        violin = True

    y_height = parser.parse_args().y_height

    if y_height:
        y_height = int(y_height)

    showing = parser.parse_args().showing

    plot_scalability(results_path, graph_path, plot_type, max_agents, violin, y_height, showing)