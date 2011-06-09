#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Lexer:
	stack = []
	fp = None

	def __init__(self):
		self.init_tables()

	def init_tables(self):
		self.syms = []
		self.kws = [
			'if', 'else', 'while', 'do', 'for', 'typedef', 'struct', 'int', 'char', 'float',
			'double', 'void', 'return', 'static', 'enum', 'continue', 'break', 'unsigned', 'sizeof', 'goto',
			'short', 'const', 'extern', 'case', 'long', 'switch', 'default', 'union',
		]

	def get_sym_idx(self, name):
		for i, sym in enumerate(self.syms):
			if sym['name'] == name: return i

		self.syms.append({'name': name})
		return len(self.syms)-1

	def get_kw_idx(self, name):
		return self.kws.index(name)

	def parse_file(self, fpath):
		self.init_tables()

		self.stack = []
		self.fp = open(fpath)

	def parse_text(self, text):
		self.init_tables()

		self.stack = list(reversed(text))
		self.fp = None

	def getc(self):
		return self.stack.pop() if self.stack else self.fp.read(1) if self.fp else ''

	def ungetc(self, ch):
		self.stack.append(ch)

	def get_next_tok(self):
		state = 0
		buf = []

		tok = {}

		while True:
			ch = self.getc()
			ch_ord = ord(ch) if ch else 0
			buf.append(ch)
			buf_str = ''.join(buf)

			if state == 0: # Neutral state
				buf = [ch]

				if ch == ' ' or ch == '\t' or ch == '\n' or ch == '\r':
					pass # Nothing done here

				elif (ch_ord >= ord('a') and ch_ord <= ord('z')) or (ch_ord >= ord('A') and ch_ord <= ord('Z')) or ch == '_':
					state = 1

				elif ch == '/':
					state = 2

				elif ch == '#':
					state = 3; # Preprocessor indicator: Delegates the process to '//' state

				elif ch == '"':
					state = 6

				elif ch == '(':
					tok['type'] = '('
					return tok

				elif ch == ')':
					tok['type'] = ')'
					return tok

				elif ch == '{':
					tok['type'] = '{'
					return tok

				elif ch == '}':
					tok['type'] = '}'
					return tok

				elif ch == '[':
					tok['type'] = '['
					return tok

				elif ch == ']':
					tok['type'] = ']'
					return tok

				elif ch == '*':
					state = 25

				elif ch == '=':
					state = 12

				elif ch_ord >= ord('0') and ch_ord <= ord('9'):
					num_int = int(ch)
					num_frac = 0.0
					num_frac_unit = 1.0
					num_exp = 0
					num_exp_sign = 1

					state = 7

				elif ch == ';':
					tok['type'] = ';'
					return tok

				elif ch == ',':
					tok['type'] = ','
					return tok

				elif ch == '\'':
					state = 13

				elif ch == '+':
					state = 16

				elif ch == '!':
					state = 17

				elif ch == '-':
					state = 18

				elif ch == '&':
					state = 19

				elif ch == '|':
					state = 20

				elif ch == '<':
					state = 21

				elif ch == '>':
					state = 22

				elif ch == '?':
					tok['type'] = '?'
					return tok

				elif ch == ':':
					tok['type'] = ':'
					return tok

				elif ch == '.':
					tok['type'] = '.'
					return tok

				elif ch == '%':
					state = 23

				elif ch == '^':
					state = 24

				elif ch == '':
					tok['type'] = 'eof'
					return tok

				else:
					return None

			elif state == 1: # Identifier token
				if (ch_ord >= ord('a') and ch_ord <= ord('z')) or (ch_ord >= ord('A') and ch_ord <= ord('Z')) or ch == '_' or (ch_ord >= ord('0') and ch_ord <= ord('9')):
					pass
				else:
					self.ungetc(buf.pop())
					buf_str = ''.join(buf)

					try: idx = self.get_kw_idx(buf_str)
					except ValueError:
						idx = self.get_sym_idx(buf_str)

						tok['type'] = 'id'
						tok['num'] = idx
						tok['str'] = buf_str
						return tok
					else:
						tok['type'] = 'kw'
						tok['num'] = idx
						tok['str'] = buf_str
						return tok

			elif state == 2: # Starts with '/'
				if ch == '/':
					tok['num'] = '/'

					state = 3
				elif ch == '*':
					tok['num'] = '/'
					tok['num'] = '*'

					state = 4
				elif ch == '=':
					tok['type'] = '/='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '/'
					return tok

			elif state == 3: # Starts with '//'
				if ch == '\n' or ch == '\r':
					state = 0
				elif ch == '':
					tok['type'] = 'eof'
					return tok

				tok['num'] = ch

			elif state == 4: # Starts with '/*'
				if ch == '*': state = 5
				elif ch == '':
					tok['type'] = 'eof'
					return tok

				tok['num'] = ch

			elif state == 5: # Ends with '*'
				if ch == '/':
					tok['num'] = ch

					state = 0
				else:
					self.ungetc(buf.pop())

					state = 4

			elif state == 6: # String tok
				if ch == '"':
					buf_str = buf_str[1:-1]
					tok['type'] = 'str'
					return tok

			elif state == 7: # Numeric token: Integer part
				if ch_ord >= ord('0') and ch_ord <= ord('9'):
					num_int = num_int*10 + int(ch)
				elif ch == '.':
					state = 8
				elif ch == 'e' or ch == 'E':
					state = 9
				else:
					self.ungetc(buf.pop())

					state = 11

			elif state == 8: # Numeric token: Fraction part
				if ch_ord >= ord('0') and ch_ord <= ord('9'):
					num_frac_unit /= 10
					num_frac += num_frac_unit*int(ch)
				elif ch == 'e' or ch == 'E':
					state = 9
				else:
					self.ungetc(buf.pop())

					state = 11

			elif state == 9: # Numeric token: Exponent part
				if ch == '+' or ch == '-':
					num_exp_sign = -1 if ch == '-' else 1

					state = 10
				elif ch_ord >= ord('0') and ch_ord <= ('9'):
					self.ungetc(buf.pop())

					state = 10
				else:
					self.ungetc(buf.pop())

					state = 11

			elif state == 10: # Numeric token: Exponent part after sign
				if ch_ord >= ord('0') and ch_ord <= ord('9'):
					num_exp = num_exp*10 + int(ch)
				else:
					self.ungetc(buf.pop())

					state = 11

			elif state == 11: # Numeric token: Synthesize the parts
				self.ungetc(buf.pop())

				tok['type'] = 'num'
				if num_frac or num_exp:
					tok['num'] = 1
					tok['str'] = (num_int + num_frac)*pow(10.0, num_exp*num_exp_sign)
				else:
					tok['num'] = 0
					tok['str'] = num_int
				return tok

			elif state == 12: # Starts with '='
				if ch == '=':
					tok['type'] = 'rop'
					tok['str'] = '=='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '='
					return tok

			elif state == 13: # Starts with '\''
				if ch == '\'': return 2
				elif ch == '\\': state = 14
				else:
					buf = [ch]
					state = 15

			elif state == 14: # Starts with '\'\\'
				if ch == 'a': buf = ['\a']
				elif ch == 'b': buf = ['\b']
				elif ch == 'n': buf = ['\n']
				elif ch == 'r': buf = ['\r']
				elif ch == '0': buf = ['\0']
				else: buf = [ch]
				state = 15

			elif state == 15: # Ends with '\''
				if ch != '\'': return 2
				tok['type'] = 'ch'
				tok['num'] = buf_str
				return tok

			elif state == 16: # Starts with '+'
				if ch == '+':
					tok['type'] = '++'
					return tok
				elif ch == '=':
					tok['type'] = '+='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '+'
					return tok

			elif state == 17: # Starts with '!'
				if ch == '=':
					tok['type'] = 'rop'
					tok['str'] = '!='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = 'lop'
					tok['str'] = '!'
					return tok

			elif state == 18: # Starts with '-'
				if ch == '-':
					tok['type'] = '--'
					return tok
				elif ch == '=':
					tok['type'] = '-='
					return tok
				elif ch == '>':
					tok['type'] = '->'
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '-'
					return tok

			elif state == 19: # Starts with '&'
				if ch == '&':
					tok['type'] = 'lop'
					tok['str'] = '&&'
					return tok
				elif ch == '=':
					tok['type'] = '&='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '&'
					return tok

			elif state == 20: # Starts with '|'
				if ch == '|':
					tok['type'] = 'lop'
					tok['str'] = '||'
					return tok
				elif ch == '=':
					tok['type'] = '|='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '|'
					return tok

			elif state == 21: # Starts with '<'
				if ch == '=':
					tok['type'] = 'rop'
					tok['str'] = '<='
					return tok
				elif ch == '<':
					state = 26
				else:
					self.ungetc(buf.pop())

					tok['type'] = 'rop'
					tok['str'] = '<'
					return tok

			elif state == 22: # Starts with '>'
				if ch == '=':
					tok['type'] = 'rop'
					tok['str'] = '>='
					return tok
				elif ch == '>':
					state = 27
				else:
					self.ungetc(buf.pop())

					tok['type'] = 'rop'
					tok['str'] = '>'
					return tok

			elif state == 23: # Starts with '%'
				if ch == '=':
					tok['type'] = '%='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '%'
					return tok

			elif state == 24: # Starts with '^'
				if ch == '=':
					tok['type'] = '^='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '^'
					return tok

			elif state == 25: # Starts with '*'
				if ch == '=':
					tok['type'] = '*='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '*'
					return tok

			elif state == 26: # Starts with '<<'
				if ch == '=':
					tok['type'] = '<<='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '<<'
					return tok

			elif state == 27: # Starts with '>>'
				if ch == '=':
					tok['type'] = '>>='
					return tok
				else:
					self.ungetc(buf.pop())

					tok['type'] = '>>'
					return tok
