#!/usr/bin/env python
# -*- coding: utf-8 -*-

from lr_parser import Parser
import sys
from PySide.QtCore import *
from PySide.QtGui import *

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
			box = {'name': node['name'], 'x': x, 'y': y, 'w': NODE_W, 'h': NODE_H}
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

	min_x = 0
	max_x = 0
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
			pa.setPen(QColor(0, 0, 255))
			pa.drawText(box['x'], box['y'], box['w'], box['h'], Qt.AlignCenter, box['name'])

		for line in self.lines:
			pa.setPen(QColor(0, 0, 255))
			pa.drawLine(line['po_from'][0], line['po_from'][1], line['po_to'][0], line['po_to'][1])

class MainWnd(QWidget):
	canvas = None
	area = None
	parser = None

	def __init__(self):
		super(MainWnd, self).__init__()

		self.setWindowTitle(u'LR 파서')

		lt = QVBoxLayout(self)

		butts = QHBoxLayout()

		open_g = QPushButton(u'열기(&O)')
		open_g.clicked.connect(self.on_open)
		butts.addWidget(open_g)

		about_g = QPushButton(u'정보(&A)')
		about_g.clicked.connect(lambda: QMessageBox.information(self, None, u'Copyright (C) 2011 by 랜덤여신 <http://barosl.com/>'))
		butts.addWidget(about_g)

		lt.addLayout(butts)

		self.canvas = Canvas()

		self.area = QScrollArea(self)
		self.area.setWidget(self.canvas)

		lt.addWidget(self.area)

		self.resize(800, 600)

		self.parser = Parser()
		try: self.parser.load_rules('rules/rules.txt')
		except Exception, e:
			self.parser = None
			QMessageBox.critical(self, None, str(e).decode('utf-8', 'replace'))

	def on_open(self):
		if not self.parser:
			QMessageBox.critical(self, None, u'파서가 초기화되지 않았습니다.')
			return

		fpath = QFileDialog.getOpenFileName(self, None, 'input', u'C 파일 (*.c);;텍스트 파일 (*.txt);;모든 파일 (*)')[0]
		if not fpath: return

		tree = self.parser.parse_file(fpath)

		self.canvas.boxes, self.canvas.lines, w, h = draw_tree(tree)
		self.canvas.resize(w, h)

		self.area.ensureVisible(w/2, 0, self.area.width()/2)

		self.canvas.update()

#		self.area.resize(600, 600)
#		charm = FlickCharm()
#		charm.activateOn(self.area)

def main():
	app = QApplication(sys.argv)

	wnd = MainWnd()
	wnd.show()

	sys.exit(app.exec_())

if __name__ == '__main__':
	main()
