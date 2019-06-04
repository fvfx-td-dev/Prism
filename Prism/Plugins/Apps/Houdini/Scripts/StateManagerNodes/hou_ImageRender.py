# -*- coding: utf-8 -*-
#
####################################################
#
# PRISM - Pipeline for animation and VFX projects
#
# www.prism-pipeline.com
#
# contact: contact@prism-pipeline.com
#
####################################################
#
#
# Copyright (C) 2016-2019 Richard Frangenberg
#
# Licensed under GNU GPL-3.0-or-later
#
# This file is part of Prism.
#
# Prism is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Prism is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Prism.  If not, see <https://www.gnu.org/licenses/>.



try:
	from PySide2.QtCore import *
	from PySide2.QtGui import *
	from PySide2.QtWidgets import *
	psVersion = 2
except:
	from PySide.QtCore import *
	from PySide.QtGui import *
	psVersion = 1
	
import sys, os, shutil, time, traceback, platform
from ConfigParser import ConfigParser
from functools import wraps

try:
	import hou
except:
	pass

class ImageRenderClass(object):
	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - hou_ImageRender %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def setup(self, state, core, stateManager, node=None, stateData=None, renderer="Mantra"):
		self.state = state
		self.core = core
		self.stateManager = stateManager

		self.curCam = None
		self.className = "ImageRender"
		self.listType = "Export"
		

		self.e_name.setText(state.text(0))

		self.camlist = []

		self.renderers = [x for x in self.core.appPlugin.getRendererPlugins() if x.isActive()]
		self.cb_renderer.addItems([x.label for x in self.renderers])

		self.resolutionPresets = ["1920x1080", "1280x720", "640x360", "4000x2000", "2000x1000"]

		self.l_name.setVisible(False)
		self.e_name.setVisible(False)
		self.tw_passes.setColumnWidth(0,130)
		self.setPassDataEnabled = True
		self.gb_submit.setChecked(False)

		for i in self.core.rfManagers.values():
			self.cb_manager.addItem(i.pluginName)
			i.sm_houExport_startup(self)

		if self.cb_manager.count() == 0:
			self.gb_submit.setVisible(False)

		self.node = None

		if node is None:
			if stateData is None:
				if not self.connectNode():
					idx = self.cb_renderer.findText(renderer)
					if idx != -1:
						self.cb_renderer.setCurrentIndex(idx)
		else:
			self.node = node
			ropType = node.type().name()
			for i in self.renderers:
				if ropType in i.ropNames:
					self.cb_renderer.setCurrentIndex(self.cb_renderer.findText(i.label))

		self.rendererChanged(self.cb_renderer.currentText(), create=stateData is None)

		if hasattr(self, "node") and self.node is not None:
			self.sp_rangeStart.setValue(self.node.parm("f1").eval())
			self.sp_rangeEnd.setValue(self.node.parm("f2").eval())

		self.core.appPlugin.fixStyleSheet(self.gb_submit)

		self.connectEvents()

		self.managerChanged(True)
		
		self.b_changeTask.setStyleSheet("QPushButton { background-color: rgb(150,0,0); }")
		self.f_localOutput.setVisible(self.core.useLocalFiles)
		self.e_osSlaves.setText("All")

		if stateData is not None:
			self.loadData(stateData)
		else:
			if node is None:
				self.nameChanged(state.text(0))
			self.updateUi()


	@err_decorator
	def loadData(self, data):
		if "connectednode" in data:
			self.node = hou.node(data["connectednode"])
			if self.node is None:
				self.node = self.findNode(data["connectednode"])
			if self.node is not None:
				ropType = self.node.type().name()
				for i in self.renderers:
					if ropType in i.ropNames:
						self.cb_renderer.setCurrentIndex(self.cb_renderer.findText(i.label))
		if "connectednode2" in data:
			self.node2 = hou.node(data["connectednode2"])
			if self.node2 is None:
				self.node2 = self.findNode(data["connectednode2"])

		if "statename" in data:
			self.e_name.setText(data["statename"])
		if "taskname" in data:
			self.l_taskName.setText(data["taskname"])
			if data["taskname"] != "":
				self.b_changeTask.setStyleSheet("")
		if "globalrange" in data:
			self.chb_globalRange.setChecked(eval(data["globalrange"]))
		if "startframe" in data:
			self.sp_rangeStart.setValue(int(data["startframe"]))
		if "endframe" in data:
			self.sp_rangeEnd.setValue(int(data["endframe"]))
		if "camoverride" in data:
			res = eval(data["camoverride"])
			self.chb_camOverride.setChecked(res)
			if not res and self.node is not None:
				self.curCam = self.curRenderer.getCam(self.node)
		if "currentcam" in data:
			idx = self.cb_cams.findText(data["currentcam"])
			if idx != -1:
				if self.chb_camOverride.isChecked():
					self.curCam = self.camlist[idx]
				self.cb_cams.setCurrentIndex(idx)
				self.stateManager.saveStatesToScene()
		if "resoverride" in data:
			res = eval(data["resoverride"])
			self.chb_resOverride.setChecked(res[0])
			self.sp_resWidth.setValue(res[1])
			self.sp_resHeight.setValue(res[2])
		if "usetake" in data:
			self.chb_useTake.setChecked(eval(data["usetake"]))
		if "take" in data:
			idx = self.cb_take.findText(data["take"])
			if idx != -1:
				self.cb_take.setCurrentIndex(idx)
		if "localoutput" in data:
			self.chb_localOutput.setChecked(eval(data["localoutput"]))
		if "renderer" in data:
			idx = self.cb_renderer.findText(data["renderer"])
			if idx != -1:
				self.cb_renderer.setCurrentIndex(idx)
		if "submitrender" in data:
			self.gb_submit.setChecked(eval(data["submitrender"]))
		if "rjmanager" in data:
			idx = self.cb_manager.findText(data["rjmanager"])
			if idx != -1:
				self.cb_manager.setCurrentIndex(idx)
			self.managerChanged(True)
		if "rjprio" in data:
			self.sp_rjPrio.setValue(int(data["rjprio"]))
		if "rjframespertask" in data:
			self.sp_rjFramesPerTask.setValue(int(data["rjframespertask"]))
		if "rjtimeout" in data:
			self.sp_rjTimeout.setValue(int(data["rjtimeout"]))
		if "rjsuspended" in data:
			self.chb_rjSuspended.setChecked(eval(data["rjsuspended"]))
		if "osdependencies" in data:
			self.chb_osDependencies.setChecked(eval(data["osdependencies"]))
		if "osupload" in data:
			self.chb_osUpload.setChecked(eval(data["osupload"]))
		if "ospassets" in data:
			self.chb_osPAssets.setChecked(eval(data["ospassets"]))
		if "osslaves" in data:
			self.e_osSlaves.setText(data["osslaves"])
		if "curdlgroup" in data:
			idx = self.cb_dlGroup.findText(data["curdlgroup"])
			if idx != -1:
				self.cb_dlGroup.setCurrentIndex(idx)
		if "dlconcurrent" in data:
			self.sp_dlConcurrentTasks.setValue(int(data["dlconcurrent"]))
		if "dlgpupt" in data:
			self.sp_dlGPUpt.setValue(int(data["dlgpupt"]))
			self.gpuPtChanged()
		if "dlgpudevices" in data:
			self.le_dlGPUdevices.setText(data["dlgpudevices"])
			self.gpuDevicesChanged()
		if "lastexportpath" in data:
			lePath = self.core.fixPath(data["lastexportpath"])
			self.l_pathLast.setText(lePath)
			self.l_pathLast.setToolTip(lePath)
			pathIsNone = self.l_pathLast.text() == "None"
			self.b_openLast.setEnabled(not pathIsNone)
			self.b_copyLast.setEnabled(not pathIsNone)
		if "stateenabled" in data:
			self.state.setCheckState(0, eval(data["stateenabled"].replace("PySide.QtCore.", "").replace("PySide2.QtCore.", "")))

		self.nameChanged(self.e_name.text())


	@err_decorator
	def findNode(self, path):
		for node in hou.node("/").allSubChildren():
			if node.userData("PrismPath") is not None and node.userData("PrismPath") == path:
				node.setUserData("PrismPath", node.path())
				return node

		return None


	@err_decorator
	def connectEvents(self):
		self.e_name.textChanged.connect(self.nameChanged)
		self.e_name.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_changeTask.clicked.connect(self.changeTask)
		self.chb_globalRange.stateChanged.connect(self.rangeTypeChanged)
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.chb_camOverride.stateChanged.connect(self.camOverrideChanged)
		self.cb_cams.activated.connect(self.setCam)
		self.chb_resOverride.stateChanged.connect(self.resOverrideChanged)
		self.sp_resWidth.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_resHeight.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_resPresets.clicked.connect(self.showResPresets)
		self.chb_useTake.stateChanged.connect(self.useTakeChanged)
		self.cb_take.activated.connect(self.stateManager.saveStatesToScene)
		self.chb_localOutput.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.cb_renderer.currentIndexChanged[str].connect(self.rendererChanged)
		self.b_goTo.clicked.connect(self.goToNode)
		self.b_connect.clicked.connect(self.connectNode)
		self.gb_submit.toggled.connect(self.rjToggled)
		self.cb_manager.activated.connect(self.managerChanged)
		self.sp_rjPrio.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_rjFramesPerTask.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_rjTimeout.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.chb_rjSuspended.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osDependencies.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osUpload.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.chb_osPAssets.stateChanged.connect(self.stateManager.saveStatesToScene)
		self.e_osSlaves.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.b_osSlaves.clicked.connect(self.openSlaves)
		self.cb_dlGroup.activated.connect(self.stateManager.saveStatesToScene)
		self.sp_dlConcurrentTasks.editingFinished.connect(self.stateManager.saveStatesToScene)
		self.sp_dlGPUpt.editingFinished.connect(self.gpuPtChanged)
		self.le_dlGPUdevices.editingFinished.connect(self.gpuDevicesChanged)
		self.tw_passes.itemChanged.connect(self.setPassData)
		self.tw_passes.customContextMenuRequested.connect(self.rclickPasses)
		self.tw_passes.mouseDbcEvent = self.tw_passes.mouseDoubleClickEvent
		self.tw_passes.mouseDoubleClickEvent = self.passesDbClick

		self.b_addPasses.clicked.connect(self.showPasses)
		self.b_openLast.clicked.connect(lambda: self.core.openFolder(os.path.dirname(self.l_pathLast.text())))
		self.b_copyLast.clicked.connect(lambda: self.core.copyToClipboard(self.l_pathLast.text()))


	@err_decorator
	def rangeTypeChanged(self, state):
		self.l_rangeEnd.setEnabled(not state)
		self.sp_rangeStart.setEnabled(not state)
		self.sp_rangeEnd.setEnabled(not state)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def startChanged(self):
		if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
			self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

		self.stateManager.saveStatesToScene()


	@err_decorator
	def endChanged(self):
		if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
			self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

		self.stateManager.saveStatesToScene()


	@err_decorator
	def useTakeChanged(self, state):
		self.cb_take.setEnabled(state)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def setCam(self, index):
		self.curCam = self.camlist[index]
		self.stateManager.saveStatesToScene()


	@err_decorator
	def rendererChanged(self, renderer, create=True):
		self.curRenderer = [x for x in self.renderers if x.label == renderer][0]
		if self.node is None or self.node.type().name() not in self.curRenderer.ropNames:
			self.deleteNode()
			if create:
				self.curRenderer.createROP(self)
				self.node.moveToGoodPosition()

		self.refreshPasses()

		self.nameChanged(self.e_name.text())
		self.updateUi()
		self.stateManager.saveStatesToScene()


	@err_decorator
	def deleteNode(self):
		try:
			self.node.name()
		except:
			return

		msg = QMessageBox(QMessageBox.Question, "Renderer changed", ("Do you want to delete the current render node?\n\n%s" % (self.node.path())), QMessageBox.No)
		msg.addButton("Yes", QMessageBox.YesRole)
		msg.setParent(self.core.messageParent, Qt.Window)
		action = msg.exec_()

		if action == 0:
			try:
				self.node.destroy()
				if hasattr(self, "node2"):
					self.node2.destroy()
			except:
				pass


	@err_decorator
	def nameChanged(self, text):
		try:
			sText = text + " - %s (%s)" % (self.l_taskName.text(), self.node)
		except:
			sText = text + " - %s (None)" % self.l_taskName.text()

		if self.state.text(0).endswith(" - disabled"):
			sText += " - disabled"
			
		self.state.setText(0, sText)


	@err_decorator
	def changeTask(self):
		import CreateItem
		self.nameWin = CreateItem.CreateItem(startText=self.l_taskName.text(), showTasks=True, taskType="render", core=self.core)
		self.core.parentWindow(self.nameWin)
		self.nameWin.setWindowTitle("Change Taskname")
		self.nameWin.l_item.setText("Taskname:")
		self.nameWin.e_item.selectAll()
		result = self.nameWin.exec_()
		
		if result == 1:
			self.l_taskName.setText(self.nameWin.e_item.text())
			self.nameChanged(self.e_name.text())

			self.b_changeTask.setStyleSheet("")

			self.stateManager.saveStatesToScene()


	@err_decorator
	def camOverrideChanged(self, checked):
		self.cb_cams.setEnabled(checked)
		self.updateCams()

		self.stateManager.saveStatesToScene()


	@err_decorator
	def resOverrideChanged(self, checked):
		self.sp_resWidth.setEnabled(checked)
		self.sp_resHeight.setEnabled(checked)
		self.b_resPresets.setEnabled(checked)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def showResPresets(self):
		pmenu = QMenu()

		for i in self.resolutionPresets:
			pAct = QAction(i, self)
			pwidth = int(i.split("x")[0])
			pheight = int(i.split("x")[1])
			pAct.triggered.connect(lambda x=None, v=pwidth: self.sp_resWidth.setValue(v))
			pAct.triggered.connect(lambda x=None, v=pheight: self.sp_resHeight.setValue(v))
			pAct.triggered.connect(lambda: self.stateManager.saveStatesToScene())
			pmenu.addAction(pAct)

		pmenu.setStyleSheet(self.stateManager.parent().styleSheet())
		pmenu.exec_(QCursor.pos())


	@err_decorator
	def updateUi(self):
		try:
			self.node.name()
			self.l_status.setText(self.node.name())
			self.l_status.setStyleSheet("QLabel { background-color : rgb(0,150,0); }")
		except:
			self.node = None
			self.l_status.setText("Not connected")
			self.l_status.setStyleSheet("QLabel { background-color : rgb(150,0,0); }")

		curTake = self.cb_take.currentText()
		self.cb_take.clear()
		self.cb_take.addItems([x.name() for x in hou.takes.takes()])
		idx = self.cb_take.findText(curTake)
		if idx != -1:
			self.cb_take.setCurrentIndex(idx)

		self.refreshPasses()

		if self.cb_manager.currentText() in self.core.rfManagers:
			self.core.rfManagers[self.cb_manager.currentText()].sm_houRender_updateUI(self)

		#update Cams
		self.updateCams()
		self.nameChanged(self.e_name.text())

		return True


	@err_decorator
	def updateCams(self):
		if self.chb_camOverride.isChecked():
			self.cb_cams.clear()
			self.camlist = []

			for node in hou.node("/").allSubChildren():

				if (node.type().name() == "cam" and node.name() != "ipr_camera") or node.type().name() == "vrcam":
					self.camlist.append(node)
		
			self.cb_cams.addItems([i.name() for i in self.camlist])

			try:
				x = self.curCam.name()
			except:
				self.curCam = None

			if self.curCam is not None and self.curCam in self.camlist:
				self.cb_cams.setCurrentIndex(self.camlist.index(self.curCam))
			else:
				self.cb_cams.setCurrentIndex(0)
				if len(self.camlist) > 0:
					self.curCam = self.camlist[0]
				else:
					self.curCam = None
				self.stateManager.saveStatesToScene()
		elif self.node is not None:
			self.curCam = self.curRenderer.getCam(self.node)


	@err_decorator
	def goToNode(self):
		try:
			self.node.name()
		except:
			self.stateManager.showState()
			return False

		self.node.setCurrent(True, clear_all_selected=True)

		paneTab = hou.ui.paneTabOfType(hou.paneTabType.NetworkEditor)
		if paneTab is not None:
			paneTab.frameSelection()


	@err_decorator
	def connectNode(self):
		if len(hou.selectedNodes()) == 0:
			return False

		ropType = hou.selectedNodes()[0].type().name()
		for i in self.renderers:
			if ropType in i.ropNames:
				self.node = hou.selectedNodes()[0]
				self.cb_renderer.setCurrentIndex(self.cb_renderer.findText(i.label))
				self.rendererChanged(self.cb_renderer.currentText())
				return True

		return False


	@err_decorator
	def rjToggled(self,checked):
		self.f_localOutput.setEnabled(self.gb_submit.isHidden() or not checked or (checked and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal))
		self.stateManager.saveStatesToScene()


	@err_decorator
	def managerChanged(self, text=None):
		self.f_localOutput.setEnabled(self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal))

		if self.cb_manager.currentText() in self.core.rfManagers:
			self.core.rfManagers[self.cb_manager.currentText()].sm_houRender_managerChanged(self)

		self.stateManager.saveStatesToScene()


	@err_decorator
	def openSlaves(self):
		try:
			del sys.modules["SlaveAssignment"]
		except:
			pass

		import SlaveAssignment
		self.sa = SlaveAssignment.SlaveAssignment(core = self.core, curSlaves = self.e_osSlaves.text())
		result = self.sa.exec_()

		if result == 1:
			selSlaves = ""
			if self.sa.rb_exclude.isChecked():
				selSlaves = "exclude "
			if self.sa.rb_all.isChecked():
				selSlaves += "All"
			elif self.sa.rb_group.isChecked():
				selSlaves += "groups: "
				for i in self.sa.activeGroups:
					selSlaves += i + ", "

				if selSlaves.endswith(", "):
					selSlaves = selSlaves[:-2]

			elif self.sa.rb_custom.isChecked():
				slavesList = [x.text() for x in self.sa.lw_slaves.selectedItems()]
				for i in slavesList:
					selSlaves += i + ", "

				if selSlaves.endswith(", "):
					selSlaves = selSlaves[:-2]

			self.e_osSlaves.setText(selSlaves)
			self.stateManager.saveStatesToScene()


	@err_decorator
	def gpuPtChanged(self):
		self.w_dlGPUdevices.setEnabled(self.sp_dlGPUpt.value() == 0)
		self.stateManager.saveStatesToScene()


	@err_decorator
	def gpuDevicesChanged(self):
		self.w_dlGPUpt.setEnabled(self.le_dlGPUdevices.text() == "")
		self.stateManager.saveStatesToScene()


	@err_decorator
	def setPassData(self, item):
		if not self.setPassDataEnabled:
			return

		passNum = str(int(self.tw_passes.item(item.row(), 2).text()) + 1)
		self.curRenderer.setAOVData(self, self.node, passNum, item)


	@err_decorator
	def showPasses(self):
		steps = None
		if self.node is not None:
			steps = self.curRenderer.getDefaultPasses(self)

		if steps == None or len(steps) == 0:
			return False

		if type(steps) != list:
			steps = eval(steps)

		try:
			del sys.modules["ItemList"]
		except:
			pass

		import ItemList
		self.il = ItemList.ItemList(core = self.core)
		self.il.setWindowTitle("Select Passes")
		self.core.parentWindow(self.il)
		self.il.tw_steps.doubleClicked.connect(self.il.accept)
		self.il.b_addStep.setVisible(False)
		if self.curRenderer.label == "Mantra":
			self.il.tw_steps.horizontalHeaderItem(0).setText("Name")
			self.il.tw_steps.horizontalHeaderItem(1).setText("VEX Variable")
		else:
			self.il.tw_steps.horizontalHeaderItem(0).setText("Type")
			self.il.tw_steps.horizontalHeaderItem(1).setText("Name")

		for i in steps:
			rc = self.il.tw_steps.rowCount()
			self.il.tw_steps.insertRow(rc)
			item1 = QTableWidgetItem(i[0])
			self.il.tw_steps.setItem(rc, 0, item1)
			item2 = QTableWidgetItem(i[1])
			self.il.tw_steps.setItem(rc, 1, item2)

		self.il.tw_steps.resizeColumnsToContents()
	
		result = self.il.exec_()

		if result != 1:
			return False

		for i in self.il.tw_steps.selectedItems():
			if i.column() == 0:
				self.curRenderer.addAOV(self, steps[i.row()])

		self.updateUi()


	@err_decorator
	def refreshPasses(self):
		try:
			self.node.name()
		except:
			return

		self.setPassDataEnabled = False

		self.e_name.setText(self.e_name.text())
		self.tw_passes.setRowCount(0)
		self.tw_passes.setColumnCount(3)
		self.tw_passes.setColumnHidden(2, True)
		self.tw_passes.setStyleSheet("")
		self.curRenderer.refreshAOVs(self)

		self.setPassDataEnabled = True


	@err_decorator
	def rclickPasses(self, pos):
		if self.tw_passes.selectedIndexes() == []:
			return

		irow = self.tw_passes.selectedIndexes()[0].row()

		rcmenu = QMenu()

		delAct = QAction("Delete", self)
		delAct.triggered.connect(lambda: self.deletePass(irow))
		rcmenu.addAction(delAct)

		rcmenu.setStyleSheet(self.stateManager.parent().styleSheet())
		rcmenu.exec_(QCursor.pos())


	@err_decorator
	def deletePass(self, row):
		self.curRenderer.deleteAOV(self, row)
		self.updateUi()


	@err_decorator
	def passesDbClick(self, event):
		self.curRenderer.aovDbClick(self, event)


	@err_decorator
	def preDelete(self, item, silent=False):
		self.core.appPlugin.sm_preDelete(self, item, silent)


	@err_decorator
	def preExecuteState(self):
		self.updateCams()

		warnings = []

		if self.l_taskName.text() == "":
			warnings.append(["No taskname is given.", "", 3])

		if self.curCam is None:
			warnings.append(["No camera is selected", "", 3])

		try:
			self.node.name()
		except:
			warnings.append(["Node is invalid.", "", 3])

		if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
			warnings += self.core.rfManagers[self.cb_manager.currentText()].sm_houExport_preExecute(self)

		return [self.state.text(0), warnings]


	@err_decorator
	def getOutputName(self, useVersion="next"):
		if self.l_taskName.text() == "":
			return

		fileName = self.core.getCurrentFileName()
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)

		basePath = self.core.projectPath
		if self.core.useLocalFiles:
			if self.chb_localOutput.isChecked() and (self.gb_submit.isHidden() or not self.gb_submit.isChecked() or (self.gb_submit.isChecked() and self.core.rfManagers[self.cb_manager.currentText()].canOutputLocal)):
				basePath = self.core.localProjectPath
				if fileName.startswith(os.path.join(self.core.projectPath, sceneDir)):
					fileName = fileName.replace(self.core.projectPath, self.core.localProjectPath)
			elif fileName.startswith(os.path.join(self.core.localProjectPath, sceneDir)):
				fileName = fileName.replace(self.core.localProjectPath, self.core.projectPath)

		hVersion = ""
		if useVersion != "next":
			hVersion = useVersion.split(self.core.filenameSeperator)[0]
			pComment = useVersion.split(self.core.filenameSeperator)[1]

		fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
		if len(fnameData) == 8:
			outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Rendering", "3dRender", self.l_taskName.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData[5]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment, "beauty")
			outputFile = os.path.join( fnameData[0] + self.core.filenameSeperator + fnameData[1] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + self.core.filenameSeperator + "beauty.$F4.exr" )
		elif len(fnameData) == 6:
			if os.path.join(sceneDir, "Assets", "Scenefiles") in fileName:
				outputPath = os.path.join(self.core.fixPath(basePath), sceneDir, "Assets", "Rendering", "3dRender", self.l_taskName.text())
			else:
				outputPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, "Rendering", "3dRender", self.l_taskName.text()))
			if hVersion == "":
				hVersion = self.core.getHighestTaskVersion(outputPath)
				pComment = fnameData[3]

			outputPath = os.path.join(outputPath, hVersion + self.core.filenameSeperator + pComment, "beauty")
			outputFile = os.path.join( fnameData[0] + self.core.filenameSeperator + self.l_taskName.text() + self.core.filenameSeperator + hVersion + self.core.filenameSeperator + "beauty.$F4.exr" )
		else:
			return

		outputName = os.path.join(outputPath, outputFile)

		return outputName.replace("\\", "/"), outputPath.replace("\\", "/"), hVersion


	@err_decorator
	def executeState(self, parent, useVersion="next"):

		if self.l_taskName.text() == "":
			return [self.state.text(0) + ": error - No taskname is given. Skipped the activation of this state."]

		if self.curCam is None:
			return [self.state.text(0) + ": error - No camera is selected. Skipped the activation of this state."]

		try:
			self.curCam.name()
		except:
			return [self.state.text(0) + ": error - The selected camera is invalid. Skipped the activation of this state."]

		try:
			self.node.name()
		except:
			return [self.state.text(0) + ": error - Node is invalid."]

		if not self.curRenderer.setCam(self, self.node, self.curCam.path()):
			return [self.state.text(0) + ": error - Publish canceled"]

		fileName = self.core.getCurrentFileName()

		outputName, outputPath, hVersion = self.getOutputName(useVersion=useVersion)

		outLength = len(outputName)
		if platform.system() == "Windows" and outLength > 255:
			return [self.state.text(0) + " - error - The outputpath is longer than 255 characters (%s), which is not supported on Windows. Please shorten the outputpath by changing the comment, taskname or projectpath." % outLength]

		if not os.path.exists(outputPath):
			os.makedirs(outputPath)

		self.core.saveVersionInfo(location=os.path.dirname(outputPath), version=hVersion, origin=fileName)

		result = self.curRenderer.executeAOVs(self, outputName)
		if not result:
			return result

		self.l_pathLast.setText(outputName)
		self.l_pathLast.setToolTip(outputName)
		self.b_openLast.setEnabled(True)
		self.b_copyLast.setEnabled(True)
		self.stateManager.saveStatesToScene()

		if self.chb_resOverride.isChecked():				
			result = self.curRenderer.setResolution(self)
			if not result:
				return result

		if self.chb_useTake.isChecked():
			pTake = self.cb_take.currentText()
			takeLabels = [x.strip() for x in self.node.parm("take").menuLabels()]
			if pTake in takeLabels:
				idx = takeLabels.index(pTake)
				if idx != -1:
					token = self.node.parm("take").menuItems()[idx]
					if not self.core.appPlugin.setNodeParm(self.node, "take", val=token):
						return [self.state.text(0) + ": error - Publish canceled"]
			else:
				return [self.state.text(0) + ": error - take '%s' doesn't exist." % pTake]

		hou.hipFile.save()

		if self.chb_globalRange.isChecked():
			jobFrames = [self.stateManager.sp_rangeStart.value(), self.stateManager.sp_rangeEnd.value()]
		else:
			jobFrames = [self.sp_rangeStart.value(), self.sp_rangeEnd.value()]

		self.core.callHook("preRender", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[0], "outputName":outputName})

		if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
			result = self.core.rfManagers[self.cb_manager.currentText()].sm_houRender_submitJob(self, outputName, parent)
		else:
			if not self.core.appPlugin.setNodeParm(self.node, "trange", val=1):
				return [self.state.text(0) + ": error - Publish canceled"]

			if not self.core.appPlugin.setNodeParm(self.node, "f1", clear=True):
				return [self.state.text(0) + ": error - Publish canceled"]
			if not self.core.appPlugin.setNodeParm(self.node, "f2", clear=True):
				return [self.state.text(0) + ": error - Publish canceled"]

			if not self.core.appPlugin.setNodeParm(self.node, "f1", val=jobFrames[0]):
				return [self.state.text(0) + ": error - Publish canceled"]

			if not self.core.appPlugin.setNodeParm(self.node, "f2", val=jobFrames[1]):
				return [self.state.text(0) + ": error - Publish canceled"]

			try:
				result = self.curRenderer.executeRender(self)
				if not result:
					return result

			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - houImageRender %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, traceback.format_exc()))
				self.core.writeErrorLog(erStr)
				return [self.state.text(0) + " - unknown error (view console for more information)"]

		postResult = self.curRenderer.postExecute(self)
		if not postResult:
			return postResult

		self.core.callHook("postRender", args={"prismCore":self.core, "scenefile":fileName, "startFrame":jobFrames[0], "endFrame":jobFrames[0], "outputName":outputName})

		if not self.gb_submit.isHidden() and self.gb_submit.isChecked():
			if "Result=Success" in result:
				return [self.state.text(0) + " - success"]
			else:
				erStr = ("%s ERROR - houImageRenderPublish %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, result))
				if not result.startswith("Execute Canceled"):
					self.core.writeErrorLog(erStr)
				return [self.state.text(0) + " - error - " + result]
		else:
			if len(os.listdir(outputPath)) > 0:
				return [self.state.text(0) + " - success"]
			else:
				return [self.state.text(0) + " - unknown error (files do not exist)"]


	@err_decorator
	def getStateProps(self):
		try:
			curNode = self.node.path()
			self.node.setUserData("PrismPath", curNode)
		except:
			curNode = None

		try:
			curNode2 = self.node2.path()
			self.node2.setUserData("PrismPath", curNode2)
		except:
			curNode2 = None

		stateProps = {
			"statename":self.e_name.text(),
			"taskname":self.l_taskName.text(),
			"globalrange": str(self.chb_globalRange.isChecked()),
			"startframe":self.sp_rangeStart.value(),
			"endframe":self.sp_rangeEnd.value(),
			"camoverride": str(self.chb_camOverride.isChecked()),
			"currentcam": self.cb_cams.currentText(),
			"resoverride": str([self.chb_resOverride.isChecked(), self.sp_resWidth.value(), self.sp_resHeight.value()]),
			"usetake":str(self.chb_useTake.isChecked()),
			"take": self.cb_take.currentText(),
			"localoutput": str(self.chb_localOutput.isChecked()),
			"connectednode": curNode,
			"connectednode2": curNode2,
			"renderer": str(self.cb_renderer.currentText()),
			"submitrender": str(self.gb_submit.isChecked()),
			"rjmanager":str(self.cb_manager.currentText()),
			"rjprio":self.sp_rjPrio.value(),
			"rjframespertask":self.sp_rjFramesPerTask.value(),
			"rjtimeout":self.sp_rjTimeout.value(),
			"rjsuspended": str(self.chb_rjSuspended.isChecked()),
			"osdependencies": str(self.chb_osDependencies.isChecked()),
			"osupload": str(self.chb_osUpload.isChecked()),
			"ospassets": str(self.chb_osPAssets.isChecked()),
			"osslaves": self.e_osSlaves.text(),
			"curdlgroup":self.cb_dlGroup.currentText(),
			"dlconcurrent":self.sp_dlConcurrentTasks.value(),
			"dlgpupt":self.sp_dlGPUpt.value(),
			"dlgpudevices":self.le_dlGPUdevices.text(),
			"lastexportpath": self.l_pathLast.text().replace("\\", "/"),
			"stateenabled":str(self.state.checkState(0))
		}
		return stateProps