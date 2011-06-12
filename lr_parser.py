#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from lexer import Lexer

class ParserError:
	def __init__(self, msg): self.msg = msg
	def __str__(self): return self.msg

class Item:
	def __init__(self, st, syms, idx):
		if syms == ['']: syms = []

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
	rules = None
	st_sym = ' '
	firsts_cache = {}
	states = {}
	lr_table = {}

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

		for line in open(fpath):
			words = re.findall('\\S+', line)
			if len(words) <= 1 or words[1] != '=>':
				raise ParserError, '\'=>\' not exists in rule'
			label, syms = words[0], words[2:]

			if not syms: syms.append('')

			if not_yet:
				not_yet = False
				rules[self.st_sym] = [[label]]

			if label not in rules: rules[label] = []
			rules[label].append(syms)

		self.rules = rules
		self.firsts_cache = {}

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

				if sym in state.childs: raise ParserError, 'duplicate entry in GOTO graph'
				state.childs[sym] = new_state

		return states

	def create_table(self):
		follows = self.calc_follows()
		self.states = self.get_cano_coll()
		lr_table = dict((x, {}) for x in self.states)

		for state in self.states:
			for item in state.items:
				for sym in item.syms:
					if sym in self.rules: continue

				if item.ended():
					if item.st == self.st_sym:
						sym = '$'

						if sym in lr_table[state]:
							raise ParserError, 'duplicate entry in LR table'

						lr_table[state][sym] = ['a']
					else:
						for sym in follows[item.st]:
							if sym in lr_table[state]:
								raise ParserError, 'duplicate entry in LR table'

							lr_table[state][sym] = ['r', item]

				else:
					sym = item.get_cur_sym()
					if sym in self.rules:
						if sym in self.rules and sym in state.childs:
							new_val = ['g', state.childs[sym]]

							if lr_table[state].get(sym, new_val) != new_val:
								raise ParserError, 'duplicate entry in LR table'

							lr_table[state][sym] = new_val
					else:
						if sym in state.childs:
							if sym in lr_table[state]:
								raise ParserError, 'duplicate entry in LR table'

							lr_table[state][sym] = ['s', state.childs[sym]]

		self.lr_table = lr_table

	def load_rules(self, fpath):
		self.read_rules(fpath)
		self.create_table()

	def parse_syms(self, syms):
		if not self.rules:
			raise ParserError, 'rules not loaded'

		que = ['$']+list(reversed(syms))
		stack = [self.states[0]]
		tree_stack = []
		tree = None

		while True:
			if not que: raise ParserError, 'input queue empty'
			sym = que[-1]
			if not stack: raise ParserError, 'stack underflow'
			state = stack[-1]

			try: info = self.lr_table[state][sym]
			except KeyError: raise ParserError, 'input not acceptable: %s' % sym

			if info[0] == 's':
				stack.append(sym)
				tree_stack.append({'name': sym, 'childs': []})
				stack.append(info[1])
				que.pop()

			elif info[0] == 'r':
				cnt = len(info[1].syms)*2
				if len(stack) < cnt: raise ParserError, 'stack underflow'

				childs = []
				if cnt:
					stack[-cnt:] = []

					childs = tree_stack[-cnt/2:]
					tree_stack[-cnt/2:] = []

				stack.append(info[1].st)
				tree_stack.append({'name': info[1].st, 'childs': childs})
				info2 = self.lr_table[stack[-2]][stack[-1]]
				if info2[0] != 'g': raise ParserError, 'invalid LR table entry detected'
				stack.append(info2[1])

			elif info[0] == 'a':
				tree = tree_stack.pop()
				if len(stack) != 3 or len(que) != 1 or len(tree_stack) != 0:
					raise ParserError, 'invalid parser state'
				break

			else:
				raise ParserError, 'invalid LR table entry detected'

		return tree

	def parse_with_lexer(self, lexer):
		syms = []

		while True:
			tok = lexer.get_next_tok()
			if tok['type'] == 'eof': break

			if tok['type'] == 'kw': sym = tok['str']
			elif tok['type'] == 'rop': sym = 'relop'
			elif tok['type'] == 'lop': sym = tok['str']
			else: sym = tok['type']

			syms.append(sym)

		return self.parse_syms(syms)

	def parse_text(self, text):
		lexer = Lexer()
		lexer.parse_text(text)
		return self.parse_with_lexer(lexer)

	def parse_file(self, fpath):
		lexer = Lexer()
		lexer.parse_file(fpath)
		return self.parse_with_lexer(lexer)

def main():
	parser = Parser()
	parser.load_rules('rules/rules.txt')
	tree = parser.parse_syms(['id', '=', 'num', ';', 'id', '=', 'num', ';'])
	print tree
	tree = parser.parse_text('a=123; b=456;')
	print tree
	tree = parser.parse_file('input/a.c')
	print tree

if __name__ == '__main__':
	main()
