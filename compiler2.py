#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
from parser2 import Parser, ParseError
from code_gen import IntermCodeGen, LmcCodeGen, NasmCodeGen, HtmlCodeGen, CodeGenError
import os
import argparse
import re

class CompileError:
	def __init__(self, msg): self.msg = msg
	def __str__(self): return self.msg

class Compiler:
	parser = None
	code_gen = None

	def __init__(self):
		self.set_target('native')

	def set_rule_file(self, fpath):
		parser = Parser()
		parser.load_rules(fpath)

		self.parser = parser

	def set_target(self, target):
		self.code_gen = {'lmc': LmcCodeGen, 'native': NasmCodeGen, 'html': HtmlCodeGen}[target]

	def build(self, fpath):
		if not self.parser: raise CompileError, 'parser not initialized'
		if not self.code_gen: raise CompileError, 'target not selected'

		try: tree = self.parser.parse_file(fpath)
		except ParseError, e: raise CompileError, 'parse error: %s' % str(e)
		try:
			interm = IntermCodeGen(tree)
			code = self.code_gen(interm).get_code()
		except CodeGenError, e: raise CompileError, 'code generation error: %s' % str(e)

		base_fpath = fpath[:fpath.rindex('.')]

		if self.code_gen == LmcCodeGen:
			out_fpath = base_fpath + '.lmc'
			open(out_fpath, 'w').write(code)

		elif self.code_gen == NasmCodeGen:
			out_fpath = base_fpath + ('.exe' if sys.platform == 'win32' else '')
			obj_fpath = base_fpath + ('.obj' if sys.platform == 'win32' else '.o')

			asm_fpath = base_fpath + '.as'
			lst_fpath = base_fpath + '.lst'

			if sys.platform == 'win32': code = re.sub('\\b(main|printf|scanf)\\b', '_\\1', code)

			open(asm_fpath, 'w').write(code)

			try:
				if sys.platform == 'win32':
					lib_dirs = [
						'%ProgramFiles%\\Microsoft Visual Studio 9.0\\VC\\lib', '%ProgramFiles%\\Microsoft SDKs\\Windows\\v7.0A\\Lib'
						'%ProgramFiles(x86)%\\Microsoft Visual Studio 9.0\\VC\\lib', '%ProgramFiles(x86)%\\Microsoft SDKs\\Windows\\v7.0A\\Lib'
					]

					if os.system('nasm -fwin32 -l%s -o%s %s' % (lst_fpath, obj_fpath, asm_fpath)): raise CompileError, 'failed to execte nasm'
					if os.system('link /out:%s %s %s libcmt.lib /subsystem:console' % (out_fpath, ' '.join('/libpath:"%s"' % x for x in lib_dirs), obj_fpath)): raise CompileError, 'failed to execte gcc'
				else:
					if os.system('nasm -felf32 -l%s -o%s %s' % (lst_fpath, obj_fpath, asm_fpath)): raise CompileError, 'failed to execte nasm'
					if os.system('gcc -m32 -o%s %s' % (out_fpath, obj_fpath)): raise CompileError, 'failed to execte gcc'

			finally:
				try: os.unlink(obj_fpath)
				except OSError: pass
				try: os.unlink(lst_fpath)
				except OSError: pass

		elif self.code_gen == HtmlCodeGen:
			out_fpath = base_fpath + '.html'
			open(out_fpath, 'w').write(code)

def main():
	arg_parser = argparse.ArgumentParser(description='Compile some files.')
	arg_parser.add_argument('files', metavar='File', type=str, nargs='+', help='source files to build')
	arg_parser.add_argument('-t', '--target', dest='target', help='determine target system to be used')
	arg_parser.add_argument('-g', dest='grammar', default=os.path.dirname(__file__)+'/rules/rules.txt.barosl', help='choose grammar file for parsing')
	args = arg_parser.parse_args()

	compiler = Compiler()
	compiler.set_rule_file(args.grammar)

	if args.target:
		try: compiler.set_target(args.target)
		except KeyError: raise CompileError, 'unrecognizable target system'

	for fpath in args.files:
		compiler.build(fpath)

if __name__ == '__main__':
	main()
