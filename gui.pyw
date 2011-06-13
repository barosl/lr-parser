#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lr_parser import Parser, ParseError
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from code_gen import IntermCodeGen, CodeGenError, LmcCodeGen, NasmCodeGen, HtmlCodeGen
from compiler import Compiler, CompileError

NODE_W = 50
NODE_H = 50
NODE_SPACING = 10

def reorder_tree(tree):
	que = [[1, tree]]
	levels = {}

	while que:
		level, node = que[0]
		del que[0]

		if level not in levels: levels[level] = []
		levels[level].append(node)

		for child in node['childs']:
			que.append([level+1, child])

	return levels

def draw_tree(tree):
	levels = reorder_tree(tree)

	boxes = []
	lines = []

	y = NODE_SPACING
	for level, nodes in levels.iteritems():
		x = -((NODE_W+NODE_SPACING)*len(nodes) - NODE_SPACING)/2

		for node in nodes:
			is_term = 'type' in node
			name = node['buf'] if is_term else node['name']
			color = (255, 0, 0) if is_term else (0, 0, 255)

			box = {'name': name, 'x': x, 'y': y, 'w': NODE_W, 'h': NODE_H, 'color': color}
			node['box'] = box
			boxes.append(box)

			x += NODE_W+NODE_SPACING

		y += NODE_H+NODE_SPACING

	for level, nodes in levels.iteritems():
		for node in nodes:
			box_from = node['box']
			for child in node['childs']:
				box_to = child['box']
				lines.append({
					'po_from': [box_from['x']+box_from['w']/2, box_from['y']+box_from['h']/2],
					'po_to': [box_to['x']+box_to['w']/2, box_to['y']+box_to['h']/2],
				})

	max_y = y

	min_x = max_x = 0
	if boxes:
		min_x = max_x = boxes[0]['x']

		for box in boxes:
			if min_x > box['x']:
				min_x = box['x']

			if max_x < box['x']:
				max_x = box['x']

		min_x -= NODE_SPACING

		for box in boxes: box['x'] -= min_x
		for line in lines:
			line['po_from'][0] -= min_x
			line['po_to'][0] -= min_x
		max_x -= min_x

		max_x += NODE_W+NODE_SPACING

	return boxes, lines, max_x, max_y

class Canvas(QWidget):
	boxes = []
	lines = []

	def __init__(self):
		super(Canvas, self).__init__()

		self.resize(0, 0)

	def paintEvent(self, ev):
		pa = QPainter(self)

		pa.setFont(QFont(None, 15))

		for box in self.boxes:
			pa.setPen(QColor(0, 0, 0))
			pa.drawRect(box['x'], box['y'], box['w'], box['h'])
			pa.setPen(QColor(*box['color']))
			pa.drawText(box['x'], box['y'], box['w'], box['h'], Qt.AlignCenter, box['name'])

		for line in self.lines:
			pa.setPen(QColor(0, 0, 255))
			pa.drawLine(line['po_from'][0], line['po_from'][1], line['po_to'][0], line['po_to'][1])

class MainWnd(QWidget):
	compiler = None
	interm = None
	code = None
	fpath = ''

	area = None
	tree_area, tree_canvas = None, None
	interm_area = None
	code_area = None
	target_g = None

	def __init__(self):
		super(MainWnd, self).__init__()

		self.setWindowTitle(u'LR 구문 분석자')

		lt = QVBoxLayout(self)

		butts = QHBoxLayout()

		open_g = QPushButton(u'열기(&O)')
		open_g.clicked.connect(self.on_open)
		butts.addWidget(open_g)

		build_g = QPushButton(u'빌드(&B)')
		build_g.clicked.connect(self.on_build)
		butts.addWidget(build_g)

		about_g = QPushButton(u'정보(&A)')
		about_g.clicked.connect(lambda: QMessageBox.information(self, None, u'Copyright (C) 2011 by 랜덤여신 <http://barosl.com/>'))
		butts.addWidget(about_g)

		self.target_g = QComboBox()
		self.target_g.addItem(u'리틀 맨 컴퓨터', u'lmc')
		self.target_g.addItem(u'네이티브', u'native')
		self.target_g.addItem(u'HTML', u'html')
		self.target_g.setCurrentIndex(1)
		self.target_g.currentIndexChanged[int].connect(self.on_target_changed)
		butts.addWidget(self.target_g)

		lt.addLayout(butts)

		self.tree_canvas = Canvas()

		self.tree_area = QScrollArea()
		self.tree_area.setWidget(self.tree_canvas)

		self.interm_area = QTextEdit()
		self.interm_area.setFontPointSize(20)
		self.interm_area.setReadOnly(True)

		self.code_area = QTextEdit()
		self.code_area.setFontPointSize(20)
		self.code_area.setReadOnly(True)

		self.area = QTabWidget()
		self.area.addTab(self.tree_area, u'트리')
		self.area.addTab(self.interm_area, u'중간 코드')
		self.area.addTab(self.code_area, u'최종 코드')

		lt.addWidget(self.area)

		self.resize(800, 600)

		self.compiler = Compiler()
		try: self.compiler.set_rule_file('rules/rules.txt.barosl')
		except:
			e = sys.exc_info()[1]
			self.compiler = None
			QMessageBox.critical(self, None, str(e).decode('utf-8', 'replace'))

	def on_open(self):
		if not self.compiler:
			QMessageBox.critical(self, None, u'구문 분석자가 초기화되지 않았습니다.')
			return

		fpath = QFileDialog.getOpenFileName(self, None, 'input', u'바로슬 파일 (*.barosl);;C 파일 (*.c);;텍스트 파일 (*.txt);;모든 파일 (*)')[0]
		if not fpath: return

		try: tree = self.compiler.parser.parse_file(fpath)
		except ParseError, e:
			QMessageBox.critical(self, None, u'구분 분석에 실패했습니다: %s' % str(e).decode('utf-8', 'replace'))
			return

		self.fpath = fpath

		self.tree_canvas.boxes, self.tree_canvas.lines, w, h = draw_tree(tree)
		self.tree_canvas.resize(w, h)
		self.tree_area.ensureVisible(w/2, 0, self.tree_area.width()/2)
		self.tree_canvas.update()

		self.interm_area.setPlainText(u'')

		try: self.interm = IntermCodeGen(tree)
		except CodeGenError, e: self.interm_area.setPlainText(u'중간 코드를 만들 수 없습니다: %s' % str(e).decode('utf-8', 'replace'))
		else:
			self.interm_area.setPlainText('\n'.join(' '.join(str(y) for y in x) for x in self.interm.code).decode('utf-8', 'replace'))

		self.on_code()

	def on_code(self):
		self.code_area.setPlainText(u'')

		target = self.target_g.itemData(self.target_g.currentIndex())
		self.compiler.set_target(target)

		try:
			self.code = self.compiler.code_gen(self.interm).get_code()
			self.code_area.setPlainText(self.code.rstrip().decode('utf-8', 'replace'))
		except CodeGenError, e:
			self.code_area.setPlainText(u'최종 코드를 만들 수 없습니다: %s' % str(e).decode('utf-8', 'replace'))

	def on_target_changed(self, idx):
		self.on_code()

	def on_build(self):
		try:
			target = self.target_g.itemData(self.target_g.currentIndex())
			self.compiler.set_target(target)
			self.compiler.build(self.fpath)
		except CompileError, e:
			QMessageBox.critical(self, None, u'빌드할 수 없습니다: %s' % str(e).decode('utf-8', 'replace'))
		else:
			QMessageBox.information(self, None, u'빌드에 성공하였습니다.')

def main():
	app = QApplication(sys.argv)

	wnd = MainWnd()
	wnd.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
