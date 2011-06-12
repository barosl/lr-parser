#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lr_parser import Parser

INITIAL_MEM_OFFSET = 99

class IntermCodeGenerator:
	mem_offset = INITIAL_MEM_OFFSET
	sym2mem = {}
	interm_code = None
	label_cnt = 0
	fds = {}

	def determ_inher_attrs(self, node):
		# do here

		for child in node['childs']:
			determ_inher_attr(child)

	def determ_synth_attrs(self, node):
		for child in node['childs']:
			determ_synth_attr(child)

		# do here

	def alloc_place(self, size):
		offset = self.mem_offset
		self.mem_offset -= size
		return offset

	def get_id_place(self, sym_idx, err=None):
		try: return self.sym2mem[sym_idx]
		except KeyError:
			self.sym2mem[sym_idx] = place = self.alloc_place(1)
			return place

	def get_tmp_place(self):
		return self.alloc_place(1)

	def get_new_label(self):
		new_label = self.label_cnt
		self.label_cnt += 1
		return new_label

	def determ_attrs(self, node):
		if not node['childs']: return

		params = {
			'node': node,
			'childs': node['childs'],

			'id_place': self.get_id_place,
			'tmp_place': self.get_tmp_place,
			'new_label': self.get_new_label,
		}

		for child in node['childs']:
			self.determ_attrs(child)

		eval(node['sem_rules'], params)

	def set_tree(self, tree):
		self.mem_offset = INITIAL_MEM_OFFSET
		self.sym2mem = {}
		self.interm_code = None
		self.label_cnt = 0
		self.fds = {}

		self.fds['input'] = self.get_id_place('input') # FIXME: should be number
		self.fds['output'] = self.get_id_place('output') # FIXME: should be number
		self.determ_attrs(tree)
		self.interm_code = tree['code']

	def get_inst(self, cmd, addr, place):
		if cmd == 'load':
			if place == self.fds['input']: return '%02d IN;' % addr
			else: return '%02d LDA %02d;' % (addr, place)
		else:
			if place == self.fds['output']: return '%02d OUT;' % addr
			else: return '%02d STA %02d;' % (addr, place)

	def get_lmc_code(self):
		res = []

		labels = {}
		jmps = []

		addr = 0
		for row in self.interm_code:
			cmd, args = row[0], row[1:]

			if cmd == 'assign':
				res.append('%02d LDA #%02d;' % (addr, args[1]))
				addr += 1
				res.append(self.get_inst('store', addr, args[0]))
				addr += 1

			elif cmd == 'copy':
				res.append(self.get_inst('load', addr, args[1]))
				addr += 1
				res.append(self.get_inst('store', addr, args[0]))
				addr += 1

			elif cmd == 'load':
				res.append(self.get_inst('load', addr, args[0]))
				addr += 1

			elif cmd == 'store':
				res.append(self.get_inst('store', addr, args[0]))
				addr += 1

			elif cmd == 'addt':
				res.append('%02d ADD %02d;' % (addr, args[0]))
				addr += 1

			elif cmd == 'subt':
				res.append('%02d SUB %02d;' % (addr, args[0]))
				addr += 1

			elif cmd == 'goto_if':
				res.append('%02d SKZ;' % addr)
				addr += 1
				res.append([addr, args[0]]) # jump
				jmps.append(len(res)-1)
				addr += 1

			elif cmd == 'goto':
				res.append([addr, args[0]]) # jump
				jmps.append(len(res)-1)
				addr += 1

			elif cmd == 'label':
				labels[args[0]] = addr

			elif cmd == 'input':
				res.append('%02d IN;' % addr)
				addr += 1

			elif cmd == 'output':
				res.append('%02d OUT;' % addr)
				addr += 1

		for idx in jmps:
			row = res[idx]
			res[idx] = '%02d JMP %02d;' % (row[0], labels[row[1]])

		res.append('%02d HLT;' % addr)
		addr += 1

		return '\n'.join(res)

def main():
	parser = Parser()
	parser.load_rules('rules/rules.txt.barosl')
	tree = parser.parse_file('input/sum.barosl')

	interm = IntermCodeGenerator()
	interm.set_tree(tree)

	for code in interm.interm_code:
		print code
	print '----'

	code = interm.get_lmc_code()

	print code
	print '----'

if __name__ == '__main__':
	main()
