"""
Repurposes and modifies code from https://github.com/declanoller/rwg-benchmark/ to conduct benchmarking on sampled
genomes
"""

import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime
import json


class BenchmarkPlotter:
    def __init__(self, env_name):
        self.env_name = env_name
        self.run_dir = ""
        self.dt_str = datetime.now().strftime('%d-%m-%Y_%H-%M-%S')

        #### Plot params
        self.plot_pt_alpha = 0.2
        self.plot_label_params = {
            'fontsize': 18
        }
        self.plot_tick_params = {
            'fontsize': 13
        }
        self.plot_title_params = {
            'fontsize': 18
        }

    def plot_scores(self, sample_dict, **kwargs):

        '''
        For plotting results. Pass it a dict of the form
        returned by sample().

        Plots several versions of the same data (only mean, in the order they're
        run, mean, but ordered by increasing value, and then the mean and the scores
        for each trial).
        '''

        ###################### In time order

        plt.close('all')
        plt.plot(sample_dict['all_scores'], color='dodgerblue', label='All mean scores')

        plt.xlabel('Sample', **self.plot_label_params)
        plt.ylabel('Sample mean score', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_score_mean_timeseries_{}.png'.format(self.env_name, self.dt_str)))

        ###################### In mean order

        all_scores = sample_dict['all_scores']
        all_scores = sorted(all_scores)

        plt.close('all')
        plt.plot(all_scores, color='mediumseagreen')

        plt.xlabel('Sorted by sample mean score', **self.plot_label_params)
        plt.ylabel('Sample mean score', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_score_mean_ordered_{}.png'.format(self.env_name, self.dt_str)))

        ###################### In mean order, with all trials

        all_trials = sample_dict['all_trials']
        all_trials = sorted(all_trials, key=lambda x: np.mean(x))

        all_trials_mean = np.mean(all_trials, axis=1)

        # For coloring by all episode scores
        all_trials_indexed = [[[i, y] for y in x] for i, x in enumerate(all_trials)]
        all_trials_indexed = np.array(all_trials_indexed).reshape((-1, 2))

        perc_cutoff = 99.9
        perc_cutoff_val = np.percentile(all_trials_indexed[:, 1], perc_cutoff)

        all_trials_below = np.array([x for x in all_trials_indexed if x[1] < perc_cutoff_val])
        all_trials_above = np.array([x for x in all_trials_indexed if x[1] >= perc_cutoff_val])

        plt.close('all')
        plt.plot(*all_trials_below.transpose(), 'o', color='tomato', alpha=self.plot_pt_alpha, markersize=3)
        plt.plot(*all_trials_above.transpose(), 'o', color='mediumseagreen', alpha=self.plot_pt_alpha, markersize=3)
        plt.plot(all_trials_mean, color='black')

        plt.xlabel('Sorted by $R_a(n)$', **self.plot_label_params)
        plt.ylabel('$S_{a,n,e}$ and $M_{a,n}$', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_score_trials_ordered_{}.png'.format(self.env_name, self.dt_str)))

    def plot_all_trial_stats(self, sample_dict, **kwargs):

        '''
        Plots the variance, min, and max of the scores for the N_episodes of
        each episode, as a function of the mean score for that episode.

        '''

        N_samples = len(sample_dict['all_trials'])
        N_episodes = len(sample_dict['all_trials'][0])

        ####################### Episode score variance
        plt.close('all')

        sigma = np.std(sample_dict['all_trials'], axis=1)

        plt.plot(sample_dict['all_scores'], sigma, 'o', color='mediumorchid', alpha=self.plot_pt_alpha)

        plt.xlabel('$M_a(n)$', **self.plot_label_params)
        plt.ylabel('$V_{a,n}$', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.tight_layout()
        fname = os.path.join(self.run_dir, '{}_variance_meanscore_{}.png'.format(self.env_name, self.dt_str))
        plt.savefig(fname)

        ####################### Min sample score
        plt.close('all')

        trial_min = np.min(sample_dict['all_trials'], axis=1)

        plt.plot(sample_dict['all_scores'], trial_min, 'o', color='dodgerblue', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('Min of sample scores', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        plt.title(f'{self.env_name} environment,\n min score of N_episodes = {N_episodes}', **self.plot_title_params)
        plt.tight_layout()
        fname = os.path.join(self.run_dir, '{}_min_score_{}.png'.format(self.env_name, self.dt_str))
        plt.savefig(fname)

        ####################### Max episode score
        plt.close('all')

        trial_max = np.max(sample_dict['all_trials'], axis=1)

        plt.plot(sample_dict['all_scores'], trial_max, 'o', color='dodgerblue', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('Max of sample scores', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        plt.title(f'{self.env_name} environment,\n max score of N_episodes = {N_episodes}', **self.plot_title_params)
        plt.tight_layout()
        fname = os.path.join(self.run_dir, '{}_max_score_{}.png'.format(self.env_name, self.dt_str))
        plt.savefig(fname)

        ####################### Min and max episode score
        plt.close('all')

        trial_min = np.min(sample_dict['all_trials'], axis=1)
        trial_max = np.max(sample_dict['all_trials'], axis=1)

        plt.plot(sample_dict['all_scores'], trial_min, 'o', color='mediumturquoise', alpha=self.plot_pt_alpha)
        plt.plot(sample_dict['all_scores'], trial_max, 'o', color='plum', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('Min and max of sample scores', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        plt.title(f'{self.env_name} environment, min (turquoise) and \nmax (purple) score of N_episodes = {N_episodes}',
                  **self.plot_title_params)
        plt.tight_layout()
        fname = os.path.join(self.run_dir, '{}_min_max_score_{}.png'.format(self.env_name, self.dt_str))
        plt.savefig(fname)

    def plot_sample_histogram(self, dist, dist_label, fname, **kwargs):

        '''
        For plotting the distribution of various benchmarking stats for self.env_name.
        Plots a vertical dashed line at the mean.

        kwarg plot_log = True also plots one with a log y axis, which is often
        better because the number of best solutions are very small.
        '''

        fname = os.path.join(self.run_dir, fname)

        plt.close('all')
        # mu = np.mean(dist)
        # sd = np.std(dist)

        if kwargs.get('N_bins', None) is None:
            plt.hist(dist, color='dodgerblue', edgecolor='gray')
        else:
            plt.hist(dist, color='dodgerblue', edgecolor='gray', bins=kwargs.get('N_bins', None))

        # plt.axvline(mu, linestyle='dashed', color='tomato', linewidth=2)
        # plt.xlabel(dist_label, **self.plot_label_params)

        plt.xlabel('$M_{a,n}$', **self.plot_label_params)
        plt.ylabel('Counts', **self.plot_label_params)
        # plt.ylabel('$S_{t,n,r}$ and $M_{t,n}$', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.title(f'{dist_label} distribution for {self.env_name}\n$\mu = {mu:.1f}$, $\sigma = {sd:.1f}$', **self.plot_title_params)
        # plt.title(f'{dist_label} distribution \nfor {self.env_name}', **self.plot_title_params)
        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.savefig(fname)

        if kwargs.get('plot_log', False):
            if kwargs.get('N_bins', None) is None:
                plt.hist(dist, color='dodgerblue', edgecolor='gray', log=True)
            else:
                plt.hist(dist, color='dodgerblue', edgecolor='gray', bins=kwargs.get('N_bins', None), log=True)

            # plt.axvline(mu, linestyle='dashed', color='tomato', linewidth=2)
            # plt.xlabel(dist_label, **self.plot_label_params)
            plt.xlabel('$M_{a,n}$', **self.plot_label_params)
            plt.ylabel('log(Counts)', **self.plot_label_params)

            plt.xticks(**self.plot_tick_params)
            plt.yticks(**self.plot_tick_params)

            # plt.title(f'{dist_label} distribution for {self.env_name}\n$\mu = {mu:.1f}$, $\sigma = {sd:.1f}$', **self.plot_title_params)
            # plt.title(f'{dist_label} distribution \nfor {self.env_name}', **self.plot_title_params)
            plt.title(f'{self.env_name} environment', **self.plot_title_params)
            plt.tight_layout()
            plt.savefig(fname.replace('dist', 'log_dist'))

    def plot_weight_stats(self, sample_dict, **kwargs):

        '''
        For plotting episode mean scores and the corresponding L1 or L2 sums
        of the weight matrix that produced those scores.

        '''

        L0_weights = sample_dict['L0_weights']
        L1_weights = sample_dict['L1_weights']
        L2_weights = sample_dict['L2_weights']
        all_scores = sample_dict['all_scores']

        ###################### L0
        plt.close('all')
        plt.plot(all_scores, L0_weights, 'o', color='forestgreen', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('L0/N_weights', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment,\n L0 sum of weights', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_L0_vs_meanscore_{}.png'.format(self.env_name, self.dt_str)))

        ###################### L1
        plt.close('all')
        plt.plot(all_scores, L1_weights, 'o', color='forestgreen', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('L1/N_weights', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment,\n L1 sum of weights', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_L1_vs_meanscore_{}.png'.format(self.env_name, self.dt_str)))

        ######################## L2
        plt.close('all')
        plt.plot(all_scores, L2_weights, 'o', color='forestgreen', alpha=self.plot_pt_alpha)

        plt.xlabel('Sample mean score', **self.plot_label_params)
        plt.ylabel('L2/N_weights', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        # plt.legend()
        plt.title(f'{self.env_name} environment,\n L2 sum of weights', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_L2_vs_meanscore_{}.png'.format(self.env_name, self.dt_str)))

    def plot_score_percentiles(self, sample_dict, **kwargs):

        ###################### In mean order, with all trials

        all_trials = sample_dict['all_trials']
        all_trials_mean = np.mean(all_trials, axis=1)

        percs = np.linspace(0, 100.0, 20)
        perc_values = np.percentile(all_trials_mean, percs)

        percs_10 = np.arange(10, 100, 5).tolist() + [96, 97, 98, 99]
        perc_10_values = np.percentile(all_trials_mean, percs_10)

        plt.close('all')
        # plt.plot(all_trials, 'o', color='tomato', alpha=self.plot_pt_alpha)
        plt.figure(figsize=(10, 6))
        ax = plt.gca()
        for perc, val in zip(percs_10, perc_10_values):
            ax.axvline(perc, linestyle='dashed', color='gray', linewidth=0.5, label=f'perc {perc} = {val:.1f}')
            ax.axhline(val, linestyle='dashed', color='gray', linewidth=0.5)

        plt.plot(percs, perc_values, color='mediumseagreen')

        plt.xlabel('Percentile', **self.plot_label_params)
        plt.ylabel('Percentile value', **self.plot_label_params)

        plt.xticks(**self.plot_tick_params)
        plt.yticks(**self.plot_tick_params)

        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.title(f'{self.env_name} environment', **self.plot_title_params)
        plt.tight_layout()
        plt.savefig(os.path.join(self.run_dir, '{}_percentiles_{}.png'.format(self.env_name, self.dt_str)))

    def save_sample_dict(self, sample_dict):
        '''
        For saving the results of the run in a .json file, for later analysis.
        '''

        # Maybe not necessary, but to be careful to not modify the original
        sample_dict_copy = sample_dict.copy()
        if 'best_weights' in sample_dict_copy.keys():
            sample_dict_copy.pop('best_weights')

        fname = os.path.join(self.run_dir, 'sample_stats.json')
        # Save distributions to file

        with open(fname, 'w+') as f:
            json.dump(sample_dict_copy, f, indent=4)

    def save_all_sample_stats(self, sample_dict, **kwargs):
        '''
        For saving all the stats and plots for the sampling, just a collector
        function.

        '''

        self.save_sample_dict(sample_dict)
        if kwargs.get('save_plots', True):
            self.plot_scores(sample_dict)
            self.plot_all_trial_stats(sample_dict)
            self.plot_sample_histogram(sample_dict['all_scores'], 'Mean sample score',
                                       f'{self.env_name}_all_scores_dist_{self.dt_str}.png', plot_log=True, **kwargs)
            self.plot_weight_stats(sample_dict)
            self.plot_score_percentiles(sample_dict)