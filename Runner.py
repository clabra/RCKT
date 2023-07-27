from copy import deepcopy
import torch
import random
import time
from utils import *
import numpy as np
from collections import defaultdict
import os


class Runner(object):

	@staticmethod
	def parse_args(parser):
		parser.add_argument('--save', type = int, default = 0,
			help = 'Save or not.')
		parser.add_argument('--seed', type = int, default = 0,
			help = 'Initial random seed.')
		parser.add_argument('--k_exps', type = int, default = 5,
			help = '# of the K-fold experiments')
		parser.add_argument('--split_ratio', type = float, default = 0.9,
			help = 'Split ratio.')
		parser.add_argument('--n_exps', type = int, default = 5,
			help = '# of the experiments')
		parser.add_argument('--exp', type = int, default = 0,
			help = '# of the experiments')
		parser.add_argument('--exp_range', type = str, default = 'None',
			help = '# of the experiments')

	def __init__(self, args):
		self.args = args
	
	def run_an_exp(self, model_class, train_set, test_set, order):

		train_set = deepcopy(train_set)
		test_set = deepcopy(test_set)

		pivot = int(len(train_set)*self.args.split_ratio)
		train_set, valid_set = train_set[:pivot], train_set[pivot:]

		train_set = model_class.preprocess(train_set, 'train')
		valid_set = model_class.preprocess(valid_set, 'valid')
		test_set = model_class.preprocess(test_set, 'test')

		model = model_class(self.args).to(self.args.device)
		model, valid_eval_dict = model.fit(train_set, valid_set, order)
		test_eval_dict = model.test(test_set)
		return valid_eval_dict, test_eval_dict
		
	def run(self, model_class, data):
		
		if self.args.save or self.args.save_model:
			if model_class.__name__ not in os.listdir('log/'):
				os.system('mkdir log/' + model_class.__name__)


		reset_seed(0)
		random.shuffle(data)

		data_chunks = list()
		step = len(data)//self.args.k_exps
		for i in range(self.args.k_exps):
			data_chunks.append(data[i*step:(i + 1)*step])

		total_valid_dict = defaultdict(list)
		total_test_dict = defaultdict(list)

		for i in range(min(self.args.k_exps, self.args.n_exps)):

			if eval(self.args.exp_range) != None:
				if not i + 1 in eval(self.args.exp_range):
					continue

			if self.args.exp != 0:
				if i != self.args.exp - 1:
					continue

			train_set = list()
			test_set = list()

			for j, chunk in enumerate(data_chunks):
				if i == j:
					test_set.extend(chunk)
				else:
					train_set.extend(chunk)

			reset_seed(self.args.seed + i)
			valid_eval_dict, test_eval_dict = self.run_an_exp(model_class, train_set, test_set, i)
			for key in valid_eval_dict:
				total_valid_dict[key].append(valid_eval_dict[key])
				total_test_dict[key].append(test_eval_dict[key])
		
		print('Test result of K experiments.')
		for key in total_test_dict:
			print(key + ':')
			for result in total_test_dict[key]:
				print('{:.4f}'.format(result))


		for key in total_valid_dict:
			total_valid_dict[key] = np.mean(total_valid_dict[key])
			total_test_dict[key] = np.mean(total_test_dict[key])

		print()
		print('Average results:')
		print('valid:\t', performance_str(total_valid_dict))
		print('test:\t', performance_str(total_test_dict))
		
		if self.args.save:
			t = time.time()
			t = time.localtime(t)
			t = time.strftime("%Y-%m-%d %H:%M:%S", t)
			file_path = 'log/' + model_class.__name__ + '/'
			file_path += t + '.info'
			check_point = {'args': self.args, 'valid': valid_eval_dict, 'test': test_eval_dict}
			if self.args.save: torch.save(check_point, file_path)

		return total_valid_dict, total_test_dict