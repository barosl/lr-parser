#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from lexer import Lexer

class ParseError:
	def __init__(self, msg): self.msg = msg
	def __str__(self): return self.msg

class Rule:
	def __init__(self, syms, sem_rules=None):
		self.syms = syms
		self.set_sem_rules(sem_rules)

	def set_sem_rules(self, sem_rules):
		self.sem_rules = compile(sem_rules, '<string>', 'exec') if sem_rules else None

	def __iter__(self): return iter(self.syms)
	def __len__(self): return len(self.syms)
	def __getitem__(self, key): return self.syms[key]

class Item:
	def __init__(self, st, syms, idx):
		if syms and syms[0] == '': syms.syms = []

		self.st = st
		self.syms = syms
		self.idx = idx

	def __repr__(self):
		output = self.st+' => '

		for i, sym in enumerate(self.syms):
			if i == self.idx: output += '.'
			if not sym: sym = '[e]'
			output += sym+' '

		if self.idx == len(self.syms): output += '.'

		return '('+output.rstrip()+')'

	def ended(self):
		return self.idx == len(self.syms)

	def get_cur_sym(self):
		return self.syms[self.idx]

class State:
	def __init__(self, no, items):
		self.no = no
		self.items = items
		self.childs = {}

	def __repr__(self):
		return '(#%d: %s)' % (self.no, repr(self.items))

class Parser:
	st_sym = ' '

	rules = None
	firsts_cache = {}
	lr_table = {}
	state_0 = None

	def get_firsts(self, syms):
		res = self.firsts_cache.get(tuple(syms), [])
		if res: return res

		if len(syms) == 1:
			sym = syms[0]
			if sym not in self.rules:
				res = [sym]
			else:
				res = set()
				for cur_syms in self.rules[sym]:
					res.update(self.get_firsts(cur_syms))
				res = list(res)
		else:
			found = False

			for sym in syms:
				cur_firsts = self.get_firsts([sym])

				for first in cur_firsts:
					if first == '': found = True
					else: res.append(first)

				if not found: break

			if found: res.append('')

		self.firsts_cache[tuple(syms)] = res
		return res

	def calc_follows(self):
		follows = {}
		for non_term in self.rules: follows[non_term] = set()

		follows[self.st_sym].update('$')
		prev_size = 1

		while True:
			for non_term in self.rules:
				for syms in self.rules[non_term]:
					for i, sym in enumerate(syms):
						if sym not in self.rules: continue

						cur_firsts = None
						if i != len(syms)-1:
							cur_firsts = self.get_firsts(syms[i+1:])
							follows[sym].update(x for x in cur_firsts if x != '')

						if i == len(syms)-1 or '' in cur_firsts:
							follows[sym].update(follows[non_term])

			cur_size = sum(len(x) for x in follows.itervalues())
			if prev_size == cur_size: break
			prev_size = cur_size

		return follows

	def get_closure(self, items):
		que = list(items)
		res = []

		visit = {}

		while que:
			item = que.pop()
			res.append(item)

			if item.ended(): continue
			sym = item.get_cur_sym()
			if sym in visit: continue
			visit[sym] = True

			if sym in self.rules:
				for syms in self.rules[sym]:
					que.append(Item(sym, syms, 0))

		return res

	def get_goto(self, items, sym):
		return self.get_closure(Item(x.st, x.syms, x.idx+1) for x in items if not x.ended() and x.get_cur_sym() == sym)

	def read_rules(self, fpath):
		rules = {}
		not_yet = True

		pythonic = False
		sem_rules = ''
		is_first = True
		cur_syms = None

		for line in open(fpath):
			if is_first:
				is_first = False
				if line.startswith('#'):
					pythonic = True
					continue

			if line.startswith('#'):
				if not pythonic: continue
				else:
					if cur_syms:
						cur_syms.set_sem_rules(sem_rules)
						cur_syms = None
					sem_rules = ''
				line = line[1:]
			elif pythonic:
				sem_rules += line
				continue

			words = re.findall('\\S+', line)
			if not words: continue
			if len(words) <= 1 or words[1] != '=>':
				raise ParseError, '\'=>\' not exists in rule'
			label, syms = words[0], words[2:]

			if not syms: syms.append('')

			if not_yet:
				not_yet = False
				rules[self.st_sym] = [[label]]

			if label not in rules: rules[label] = []

			cur_syms = Rule(syms)
			rules[label].append(cur_syms)

		if not_yet:
			raise ParseError, 'empty grammar'

		if pythonic and cur_syms:
			cur_syms.set_sem_rules(sem_rules)
			cur_syms = None

		self.rules = rules
		self.firsts_cache = {}
		self.lr_table = {}
		self.state_0 = None

	def get_cano_coll(self):
		states = []
		repr2state = {}

		items = self.get_closure([Item(self.st_sym, self.rules[self.st_sym][0], 0)])
		state = State(len(states), items)
		states.append(state)

		items_repr = repr(items)
		repr2state[items_repr] = state

		que = [state]
		while que:
			state = que.pop()

			for sym in set(x.get_cur_sym() for x in state.items if not x.ended()):
				new_items = self.get_goto(state.items, sym)
				new_items_repr = repr(new_items)

				new_state = repr2state.get(new_items_repr, None)
				if not new_state:
					new_state = State(len(states), new_items)
					states.append(new_state)
					repr2state[new_items_repr] = new_state

					que.append(new_state)

				if sym in state.childs: raise ParseError, 'duplicate entry in GOTO graph'
				state.childs[sym] = new_state

		return states

	def create_table(self):
		follows = self.calc_follows()
		states = self.get_cano_coll()
		lr_table = dict((x, {}) for x in states)

		for state in states:
			for item in state.items:
				if item.ended():
					if item.st == self.st_sym:
						sym = '$'

						if sym in lr_table[state]:
							raise ParseError, 'duplicate entry in LR table'

						lr_table[state][sym] = ['a']
					else:
						for sym in follows[item.st]:
							if sym in lr_table[state]:
								raise ParseError, 'duplicate entry in LR table'

							lr_table[state][sym] = ['r', item]

				else:
					sym = item.get_cur_sym()
					if sym in state.childs:
						if sym in self.rules: new_val = ['g', state.childs[sym]]
						else: new_val = ['s', state.childs[sym]]

						# Some redundant checks were done here; if the same state and sym are given,
						# state.childs[sym] must always be the same.
						if lr_table[state].get(sym, new_val)[0] != new_val[0]:
							raise ParseError, 'duplicate entry in LR table'

						lr_table[state][sym] = new_val

		self.lr_table = lr_table
		self.state_0 = states[0]

	def load_rules(self, fpath):
		self.read_rules(fpath)
		self.create_table()

	def parse_toks(self, toks):
		if not self.rules:
			raise ParseError, 'rules not loaded'

		que = [{'type': '$', 'buf': '$'}]+list(reversed(toks))
		stack = [self.state_0]
		tree_stack = []
		tree = None

		while True:
			if not que: raise ParseError, 'input queue empty'
			tok = que[-1]
			if not stack: raise ParseError, 'stack underflow'
			state = stack[-1]

			try: info = self.lr_table[state][tok['type']]
			except KeyError: raise ParseError, 'input not acceptable: %s (%s)' % (tok['buf'], tok['type'])

			if info[0] == 's':
				stack.append(tok)
				tree_stack.append(dict(tok, childs=[]))
				stack.append(info[1])
				que.pop()

			elif info[0] == 'r':
				cnt = len(info[1].syms)*2
				if len(stack) < cnt: raise ParseError, 'stack underflow'

				childs = []
				if cnt:
					stack[-cnt:] = []

					childs = tree_stack[-cnt/2:]
					tree_stack[-cnt/2:] = []

				stack.append(info[1].st)
				tree_stack.append({'name': info[1].st, 'childs': childs, 'sem_rules': info[1].syms.sem_rules})
				info2 = self.lr_table[stack[-2]][stack[-1]]
				if info2[0] != 'g': raise ParseError, 'invalid LR table entry detected'
				stack.append(info2[1])

			elif info[0] == 'a':
				tree = tree_stack.pop()
				if len(stack) != 3 or len(que) != 1 or len(tree_stack) != 0:
					raise ParseError, 'invalid parser state'
				break

			else:
				raise ParseError, 'invalid LR table entry detected'

		return tree

	def parse_with_lexer(self, lexer):
		toks = []

		while True:
			tok = lexer.get_next_tok()
			if tok['type'] == 'eof': break

			toks.append(tok)

		return self.parse_toks(toks)

	def parse_text(self, text):
		lexer = Lexer()
		lexer.parse_text(text)
		return self.parse_with_lexer(lexer)

	def parse_file(self, fpath):
		lexer = Lexer()
		try: lexer.parse_file(fpath)
		except IOError: raise ParseError, 'file not accessible'
		return self.parse_with_lexer(lexer)

def main():
	parser = Parser()
	parser.load_rules('rules/rules.txt.prof')
	tree = parser.parse_toks([{'type': x} for x in ['id', '=', 'num', ';', 'id', '=', 'num', ';']])
	print tree
	tree = parser.parse_text('a=123; b=456;')
	print tree
	tree = parser.parse_file('input/a.c')
	print tree

if __name__ == '__main__':
	main()
