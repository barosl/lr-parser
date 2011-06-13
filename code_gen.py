#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lr_parser import Parser
import os
import sys
import re

class CodeGenError:
	def __init__(self, msg): self.msg = msg
	def __str__(self): return self.msg

class IntermCodeGen:
	mem_offset = 0
	sym2mem = {}
	code = None
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
		self.mem_offset += size
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
		self.mem_offset = 0
		self.sym2mem = {}
		self.code = None
		self.label_cnt = 0
		self.fds = {}

		self.fds['input'] = self.get_id_place('input') # FIXME: should be number
		self.fds['output'] = self.get_id_place('output') # FIXME: should be number
		self.determ_attrs(tree)
		self.code = tree['code']

		i = 0
		while i < len(self.code):
			code = self.code[i]
			cmd, args = code[0], code[1:]

			res = []

			if cmd == 'assign':
				if args[0] == self.fds['output']:
					place = self.get_tmp_place()
					res = [['assign', place, args[1]], ['load', place], ['output']]

			elif cmd == 'copy':
				res = [
					['input'] if args[1] == self.fds['input'] else ['load', args[1]],
					['output'] if args[0] == self.fds['output'] else ['store', args[0]],
				]

			elif cmd == 'load':
				if args[0] == self.fds['input']: res = [['input']]

			elif cmd == 'store':
				if args[0] == self.fds['output']: res = [['output']]

			if res:
				self.code[i:i+1] = res
				i += len(res)
			else: i += 1

class NativeCodeGen:
	def __init__(self, interm):
		self.interm = interm

class LmcCodeGen(NativeCodeGen):
	MEM_OFFSET = 99

	def get_code(self):
		res = []

		labels = {}
		jmps = []

		addr = 0
		for code in self.interm.code:
			cmd, args = code[0], code[1:]

			if cmd == 'assign':
				res.append('%02d LDA #%02d;' % (addr, args[1]))
				addr += 1
				res.append('%02d STA %02d;' % (addr, self.MEM_OFFSET - args[0]))
				addr += 1

			elif cmd == 'load':
				res.append('%02d LDA %02d;' % (addr, self.MEM_OFFSET - args[0]))
				addr += 1

			elif cmd == 'store':
				res.append('%02d STA %02d;' % (addr, self.MEM_OFFSET - args[0]))
				addr += 1

			elif cmd == 'add':
				res.append('%02d ADD %02d;' % (addr, self.MEM_OFFSET - args[0]))
				addr += 1

			elif cmd == 'sub':
				res.append('%02d SUB %02d;' % (addr, self.MEM_OFFSET - args[0]))
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

			else:
				raise CodeGenError, 'unknown instruction: %s' % cmd

		for idx in jmps:
			code = res[idx]
			res[idx] = '%02d JMP %02d;' % (code[0], labels[code[1]])

		res.append('%02d HLT;' % addr)
		addr += 1

		res.append('')
		return '\n'.join(res)

class NasmCodeGen(NativeCodeGen):
	def get_code(self):
		res = []

		res.append('\textern printf, scanf')

		res.append('')
		res.append('\tsection .data')
		res.append('fmt_out: db \'%d\', 10, 0')
		res.append('fmt_in: db \'%d\', 0')
		for place in xrange(self.interm.mem_offset):
			res.append('var_%d: dd 0' % place)
		res.append('buf_int: dd 0')

		res.append('')
		res.append('\tsection .text')
		res.append('')

		res.append('\tglobal main')
		res.append('main:')

		res.append('\tpush ebp')
		res.append('\tmov ebp, esp')

		for code in self.interm.code:
			cmd, args = code[0], code[1:]

			if cmd == 'assign':
				res.append('\tmov dword [var_%d], %d' % (args[0], args[1]))

			elif cmd == 'copy':
				res.append('\tmov dword edx, [var_%d]' % args[1])
				res.append('\tmov dword [var_%d], edx' % args[0])

			elif cmd == 'load':
				res.append('\tmov dword eax, [var_%d]' % args[0])

			elif cmd == 'store':
				res.append('\tmov dword [var_%d], eax' % args[0])

			elif cmd == 'add':
				res.append('\tmov edx, [var_%d]' % args[0])
				res.append('\tadd eax, edx')

			elif cmd == 'sub':
				res.append('\tmov edx, [var_%d]' % args[0])
				res.append('\tsub eax, edx')

			elif cmd == 'mul':
				res.append('\tmov ebx, eax')
				res.append('\tmov eax, [var_%d]' % args[0])
				res.append('\timul ebx')

			elif cmd == 'div':
				res.append('\tcdq')
				res.append('\tidiv dword [var_%d]' % args[0])

			elif cmd == 'mod':
				res.append('\tcdq')
				res.append('\tidiv dword [var_%d]' % args[0])
				res.append('\tmov eax, edx')

			elif cmd == 'goto_if':
				res.append('\tcmp eax, 0')
				res.append('\tjnz label_%s' % args[0])

			elif cmd == 'goto':
				res.append('\tjmp label_%s' % args[0])

			elif cmd == 'label':
				res.append('label_%d:' % args[0])

			elif cmd == 'input':
				res.append('\tpush buf_int')
				res.append('\tpush fmt_in')
				res.append('\tcall scanf')
				res.append('\tadd esp, 4*2')
				res.append('\tmov eax, [buf_int]')

			elif cmd == 'output':
				res.append('\tpush eax')
				res.append('\tpush fmt_out')
				res.append('\tcall printf')
				res.append('\tadd esp, 4*2')

			else:
				raise CodeGenError, 'unknown instruction: %s' % cmd

		res.append('\tmov esp, ebp')
		res.append('\tpop ebp')

		res.append('\tmov eax, 0')
		res.append('\tret')

		res.append('')
		return '\n'.join(res)

class HtmlCodeGen(NativeCodeGen):
	def get_code(self):
		res = []

		res.append('<!DOCTYPE html>')
		res.append('<html><head><title>LR Parsing Results</title></head><body><script type="text/javascript">')

		label_used = False

		for code in self.interm.code:
			cmd, args = code[0], code[1:]

			if cmd == 'assign':
				res.append('var_%d = %d;' % (args[0], args[1]))

			elif cmd == 'copy':
				res.append('var_%d = var_%d;' % (args[0], args[1]))

			elif cmd == 'load':
				res.append('acc = var_%d;' % args[0])

			elif cmd == 'store':
				res.append('var_%d = acc;' % args[0])

			elif cmd == 'add':
				res.append('acc += var_%d;' % args[0])

			elif cmd == 'sub':
				res.append('acc -= var_%d;' % args[0])

			elif cmd == 'mul':
				res.append('acc *= var_%d;' % args[0])

			elif cmd == 'div':
				res.append('acc /= var_%d;' % args[0])

			elif cmd == 'mod':
				res.append('acc %%= var_%d;' % args[0])

			elif cmd == 'goto_if':
				res.append('if (acc) { label_%d(); return; }' % args[0])

			elif cmd == 'goto':
				res.append('label_%d(); return;' % args[0])

			elif cmd == 'label':
				res.append('label_%d();' % args[0]);
				if label_used: res.append('}')
				else: label_used = True
				res.append('function label_%d() {' % args[0])

			elif cmd == 'input':
				res.append('acc = parseInt(prompt(\'Input a number:\'));');

			elif cmd == 'output':
				res.append('document.write(acc); document.write(\'<br />\\n\');');

			else:
				raise CodeGenError, 'unknown instruction: %s' % cmd

		if label_used: res.append('}')

		res.append('</script></body></html>')

		res.append('')
		return '\n'.join(res)

def main():
	parser = Parser()
	parser.load_rules('rules/rules.txt.barosl')
	tree = parser.parse_file('input/sum.barosl')

	interm = IntermCodeGen()
	interm.set_tree(tree)

	for code in interm.code: print code
	print '----'

	code_gens = [LmcCodeGen, NasmCodeGen, HtmlCodeGen]
	code_gen = code_gens[1]

	code = code_gen(interm).get_code()

	print code.rstrip()
	print '----'

	if code_gen == NasmCodeGen:
		out_fpath = 'a.out'
		obj_fpath = 'a.o'

		asm_fpath = 'a.as'
		lst_fpath = 'a.lst'

		if sys.platform == 'win32': code = re.sub('\\b(main|printf|scanf)\\b', '_\\1', code)

		open(asm_fpath, 'w').write(code)

		try:
			if sys.platform == 'win32':
				out_fpath = 'a.exe'
				obj_fpath = 'a.obj'

				lib_dirs = [
					'%ProgramFiles%\\Microsoft Visual Studio 9.0\\VC\\lib', '%ProgramFiles%\\Microsoft SDKs\\Windows\\v7.0A\\Lib'
					'%ProgramFiles(x86)%\\Microsoft Visual Studio 9.0\\VC\\lib', '%ProgramFiles(x86)%\\Microsoft SDKs\\Windows\\v7.0A\\Lib'
				]

				if os.system('nasm -fwin32 -l%s -o%s %s' % (lst_fpath, obj_fpath, asm_fpath)): raise CodeGenError, 'failed to execte nasm'
				if os.system('link /out:%s %s %s libcmt.lib /subsystem:console' % (out_fpath, ' '.join('/libpath:"%s"' % x for x in lib_dirs), obj_fpath)): raise CodeGenError, 'failed to execte gcc'
			else:
				if os.system('nasm -felf32 -l%s -o%s %s' % (lst_fpath, obj_fpath, asm_fpath)): raise CodeGenError, 'failed to execte nasm'
				if os.system('gcc -m32 -o%s %s' % (out_fpath, obj_fpath)): raise CodeGenError, 'failed to execte gcc'

		finally:
			try: os.unlink(obj_fpath)
			except OSError: pass
			try: os.unlink(lst_fpath)
			except OSError: pass

	elif code_gen == HtmlCodeGen:
		open('output.html', 'w').write(code)

if __name__ == '__main__':
	main()
