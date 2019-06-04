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

import sys, os, traceback, time, imp
from functools import wraps

if sys.version[0] == "3":
	from configparser import ConfigParser
	from io import StringIO
	pVersion = 3
else:
	from ConfigParser import ConfigParser
	from StringIO import StringIO
	pVersion = 2

sys.path.append(os.path.join(os.path.dirname(__file__), "UserInterfaces"))

for i in ["StateManager_ui", "StateManager_ui_ps2", "CreateItem"]:
	try:
		del sys.modules[i]
	except:
		pass

if psVersion == 1:
	import StateManager_ui
else:
	import StateManager_ui_ps2 as StateManager_ui

try:
	import EnterText
except:
	modPath = imp.find_module("EnterText")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import EnterText

try:
	import CreateItem
except:
	modPath = imp.find_module("CreateItem")[1]
	if modPath.endswith(".pyc") and os.path.exists(modPath[:-1]):
		os.remove(modPath)
	import CreateItem


class StateManager(QMainWindow, StateManager_ui.Ui_mw_StateManager):
	def __init__(self, core, stateDataPath=None):
		QMainWindow.__init__(self)
		self.setupUi(self)

		self.core = core
		self.core.parentWindow(self)

		self.setWindowTitle("Prism - State Manager - " + self.core.projectName)

		self.scenename = self.core.getCurrentFileName()

		self.enabledCol = QBrush(self.tw_import.palette().color(self.tw_import.foregroundRole()))
		self.b_stateFromNode.setVisible(False)
		self.b_createDependency.setVisible(False)

		self.layout().setContentsMargins(6,6,6,0)

		self.disabledCol = QBrush(QColor(100,100,100))
		self.styleExists = "QPushButton { border: 1px solid rgb(100,200,100); }"
		self.styleMissing = "QPushButton { border: 1px solid rgb(200,100,100); }"

		self.draggedItem = None

		for i in ["TaskSelection"]:
			try:
				del sys.modules[i]
			except:
				pass

			try:
				del sys.modules[i + "_ui"]
			except:
				pass

			try:
				del sys.modules[i + "_ui_ps2"]
			except:
				pass

		self.states = []
		self.stateTypes = {}

		self.description = ""
		self.previewImg = None

		foldercont = ["","",""]

		self.saveEnabled = True
		self.loading = False
		self.shotcamFileType = ".abc"
		self.publishPaused = False

		files = []
		pluginUiPath = os.path.join(self.core.pluginPathApp, self.core.appPlugin.pluginName, "Scripts", "StateManagerNodes", "StateUserInterfaces")
		if os.path.exists(pluginUiPath):
			sys.path.append(os.path.dirname(pluginUiPath))
			sys.path.append(pluginUiPath)

			for i in os.walk(os.path.dirname(pluginUiPath)):
				foldercont = i
				break
			files += foldercont[2]

		sys.path.append(os.path.join(os.path.dirname(__file__), "StateManagerNodes"))
		sys.path.append(os.path.join(os.path.dirname(__file__), "StateManagerNodes", "StateUserInterfaces"))

		for i in os.walk(os.path.join(os.path.dirname(__file__), "StateManagerNodes")):
			foldercont = i
			break
		files += foldercont[2]

		for i in files:
			try:
				if os.path.splitext(i)[1] != ".pyc" or (os.path.splitext(i)[1] == ".pyc" and not os.path.exists(os.path.splitext(i)[0] + ".py") and i != "__init__.pyc"):
					stateName = os.path.splitext(i)[0]
					stateNameBase = stateName

					if stateName.startswith("default_") or stateName.startswith(self.core.appPlugin.appShortName.lower()):
						stateNameBase = stateNameBase.replace(stateName.split("_", 1)[0] + "_", "")

					if stateNameBase in self.stateTypes:
						continue

					if psVersion == 1:
						stateUi = stateName + "_ui"
					else:
						stateUi = stateName + "_ui_ps2 as " + stateName + "_ui"

					try:
						del sys.modules[stateName]
					except:
						pass

					try:
						del sys.modules[stateName + "_ui"]
					except:
						pass

					try:
						del sys.modules[stateName + "_ui_ps2"]
					except:
						pass


					try:
						exec("""
import %s
import %s
class %s(QWidget, %s.%s, %s.%sClass):
	def __init__(self):
		QWidget.__init__(self)
		self.setupUi(self)""" % ( stateName, stateUi, stateNameBase + "Class", stateName + "_ui", "Ui_wg_" + stateNameBase, stateName, stateNameBase))
						validState = True
					except:
						validState = False

					if validState:
						self.stateTypes[stateNameBase] = eval(stateNameBase + "Class")

			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - StateManager %s:\n%s" % (time.strftime("%d/%m/%y %X"), self.core.version, traceback.format_exc()))
				self.core.writeErrorLog(erStr)

		fileName = self.core.getCurrentFileName()
		fileNameData = os.path.basename(fileName).split(self.core.filenameSeperator)

		self.b_shotCam.setEnabled(len(fileNameData) == 8 and fileNameData[0] == "shot")

		self.core.callback(name="onStateManagerOpen", types=["curApp", "custom"], args=[self])
		self.loadLayout()
		self.setListActive(self.tw_import)
		self.core.smCallbacksRegistered = True
		self.connectEvents()
		self.loadStates()
		self.showState()
		self.activeList.setFocus()

		self.commentChanged(self.e_comment.text())

		screenW = QApplication.desktop().screenGeometry().width()
		screenH = QApplication.desktop().screenGeometry().height()
		space = 100
		if screenH < (self.height()+space):
			self.resize(self.width(), screenH-space)

		if screenW < (self.width()+space):
			self.resize(screenW-space, self.height())


	def err_decorator(func):
		@wraps(func)
		def func_wrapper(*args, **kwargs):
			try:
				return func(*args, **kwargs)
			except Exception as e:
				exc_type, exc_obj, exc_tb = sys.exc_info()
				erStr = ("%s ERROR - StateManager %s:\n%s\n\n%s" % (time.strftime("%d/%m/%y %X"), args[0].core.version, ''.join(traceback.format_stack()), traceback.format_exc()))
				args[0].core.writeErrorLog(erStr)

		return func_wrapper


	@err_decorator
	def loadLayout(self):
		helpMenu = QMenu("Help")

		self.actionWebsite = QAction("Visit website", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("home"))
		helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Tutorials", self)
		self.actionWebsite.triggered.connect(lambda:self.core.openWebsite("tutorials"))
		helpMenu.addAction(self.actionWebsite)

		self.actionWebsite = QAction("Documentation", self)
		self.actionWebsite.triggered.connect(lambda: self.core.openWebsite("documentation"))
		helpMenu.addAction(self.actionWebsite)

		self.actionSendFeedback = QAction("Send feedback/feature requests...", self)
		self.actionSendFeedback.triggered.connect(self.core.sendFeedback)
		helpMenu.addAction(self.actionSendFeedback)

		self.actionCheckVersion = QAction("Check for Prism updates", self)
		self.actionCheckVersion.triggered.connect(self.core.checkPrismVersion)
		helpMenu.addAction(self.actionCheckVersion)

		self.actionAbout = QAction("About...", self)
		self.actionAbout.triggered.connect(self.core.showAbout)
		helpMenu.addAction(self.actionAbout)
	
		self.menubar.addMenu(helpMenu)

		self.core.appPlugin.setRCStyle(self, helpMenu)

		rprojects = self.core.getConfig(cat="recent_projects", getOptions=True)
		if rprojects is None:
			rprojects = []

		cData = {}
		for i in rprojects:
			cData[i] = ["recent_projects", i]

		rPrjPaths = self.core.getConfig(data=cData)

		for prjName in rPrjPaths:
			prj = rPrjPaths[prjName]
			if prj == "" or prj == self.core.prismIni:
				continue

			rpconfig = ConfigParser()
			rpconfig.read(prj)
			if not rpconfig.has_option("globals", "project_name"):
				continue

			rpName = rpconfig.get("globals", "project_name")

			rpAct = QAction(rpName, self)
			rpAct.setToolTip(prj)

			rpAct.triggered.connect(lambda y=None, x=prj: self.core.changeProject(x))
			self.menuRecentProjects.addAction(rpAct)

		if self.menuRecentProjects.isEmpty():
			self.menuRecentProjects.setEnabled(False)

		if self.description == "":
			self.b_description.setStyleSheet(self.styleMissing)
		else:
			self.b_description.setStyleSheet(self.styleExists)
		self.b_preview.setStyleSheet(self.styleMissing)


	@err_decorator
	def setTreePalette(self, listWidget, inactive, inactivef, activef):
		actStyle = "QTreeWidget { border: 1px solid rgb(150,150,150); }"
		inActStyle = "QTreeWidget { border: 1px solid rgb(30,30,30); }"
		listWidget.setStyleSheet(listWidget.styleSheet().replace(actStyle, "").replace(inActStyle, "") + actStyle)
		inactive.setStyleSheet(inactive.styleSheet().replace(actStyle, "").replace(inActStyle, "") + inActStyle)


	@err_decorator
	def collapseFolders(self):
		if not hasattr(self, "collapsedFolders"):
			return
			
		for i in self.collapsedFolders:
			i.setExpanded(False)

	@err_decorator
	def loadStates(self, stateText=None):
		self.saveEnabled = False
		self.loading = True
		if stateText is None:
			stateText = self.core.appPlugin.sm_readStates(self)

		stateData = None
		if stateText is not None:
			buf = StringIO(stateText)

			stateData = []

			stateConfig = ConfigParser()
			validStateData = False
			try:
				stateConfig.readfp(buf)
				validStateData = True
			except:
				QMessageBox.warning(self.core.messageParent,"Load states", "Loading states failed.")
				stateData = None

			if validStateData:
				if stateConfig.has_option("publish", "startframe"):
					self.sp_rangeStart.setValue(stateConfig.getint("publish", "startframe"))
				if stateConfig.has_option("publish", "endframe"):
					self.sp_rangeEnd.setValue(stateConfig.getint("publish", "endframe"))
				if stateConfig.has_option("publish", "comment"):
					self.e_comment.setText(stateConfig.get("publish", "comment"))
				if stateConfig.has_option("publish", "description"):
					self.description = stateConfig.get("publish", "description")
					if self.description == "":
						self.b_description.setStyleSheet(self.styleMissing)
					else:
						self.b_description.setStyleSheet(self.styleExists)

				for i in stateConfig.sections():
					if i == "publish":
						continue

					stateProps = {}
					stateProps["statename"] = i
					for k in stateConfig.options(i):
						stateProps[k] = stateConfig.get(i, k)

					stateData.append(stateProps)

		self.collapsedFolders = []

		if stateData is not None and len(stateData) != 0:
			loadedStates = []
			for i in stateData:
				stateParent = None
				if i["stateparent"] != "None":
					stateParent = loadedStates[int(i["stateparent"])-1]
				state = self.createState(i["stateclass"], parent=stateParent, stateData=i)
				loadedStates.append(state)

		self.loading = False
		self.saveEnabled = True
		self.saveStatesToScene()


	@err_decorator
	def showState(self):
		try:
			grid = QGridLayout()
		except:
			return False

		if self.activeList.currentItem() is not None:
			grid.addWidget(self.activeList.currentItem().ui)

		widget = QWidget()
		policy = QSizePolicy()
		policy.setHorizontalPolicy(QSizePolicy.Fixed)
		widget.setSizePolicy(policy)
		widget.setLayout(grid)

		if hasattr(self, "curUi"):
			self.lo_stateUi.removeWidget(self.curUi)
			self.curUi.setVisible(False)

		self.lo_stateUi.addWidget(widget)
		if self.activeList.currentItem() is not None:
			self.activeList.currentItem().ui.updateUi()

		self.curUi = widget


	@err_decorator
	def stateChanged(self, cur, prev, activeList):
		if self.loading:
			return False

		self.showState()


	@err_decorator
	def setListActive(self, listWidget):
		if listWidget == self.tw_import:
			inactive = self.tw_export
			inactivef = self.f_export
			activef = self.f_import
		else:
			inactive = self.tw_import
			inactivef = self.f_import
			activef = self.f_export

		getattr(self.core.appPlugin, "sm_setActivePalette", lambda x1,x2,x3,x4,x5: self.setTreePalette(x2,x3,x4,x5))(self, listWidget, inactive, inactivef, activef)

		self.activeList = listWidget


	@err_decorator
	def focusImport(self, event):
		self.setListActive(self.tw_import)
		self.tw_export.setCurrentIndex(self.tw_export.model().createIndex(-1,0))
		event.accept()


	@err_decorator
	def focusExport(self, event):
		self.setListActive(self.tw_export)
		self.tw_import.setCurrentIndex(self.tw_import.model().createIndex(-1,0))
		event.accept()


	@err_decorator
	def updateForeground(self, item=None, column=None, activeList=None):
		if activeList is not None:
			if activeList == self.tw_import:
				inactive = self.tw_export
			else:
				inactive = self.tw_import
			#inactive.setCurrentIndex(inactive.model().createIndex(-1,0))


		for i in range(self.tw_export.topLevelItemCount()):
			item = self.tw_export.topLevelItem(i)
			if item.checkState(0) == Qt.Checked:
				fcolor = self.enabledCol
				if item.text(0).endswith(" - disabled"):
					item.setText(0, item.text(0)[:-len(" - disabled")])
			else:
				fcolor = self.disabledCol
				if not item.text(0).endswith(" - disabled"):
					item.setText(0, item.text(0) + " - disabled")

			item.setForeground(0, fcolor)
			for k in range(item.childCount()):
				self.enableChildren(item.child(k), fcolor)


	@err_decorator
	def enableChildren(self, item, fcolor):
		if item.checkState(0) == Qt.Unchecked:
			fcolor = self.disabledCol

		if fcolor == self.disabledCol:
			if not item.text(0).endswith(" - disabled"):
				item.setText(0, item.text(0) + " - disabled")
		elif item.text(0).endswith(" - disabled"):
			item.setText(0, item.text(0)[:-len(" - disabled")])
			
		item.setForeground(0, fcolor)
		for i in range(item.childCount()):
			self.enableChildren(item.child(i),fcolor)


	@err_decorator
	def updateStateList(self):
		stateData = []
		for i in range(self.tw_import.topLevelItemCount()):
			stateData.append([self.tw_import.topLevelItem(i), None])
			self.appendChildStates(stateData[len(stateData)-1][0], stateData)

		for i in range(self.tw_export.topLevelItemCount()):
			stateData.append([self.tw_export.topLevelItem(i), None])
			self.appendChildStates(stateData[len(stateData)-1][0], stateData)

		self.states = [x[0] for x in stateData]


	@err_decorator
	def connectEvents(self):
		self.actionPrismSettings.triggered.connect(self.core.prismSettings)
		self.actionProjectBrowser.triggered.connect(self.core.projectBrowser)
		self.actionCopyStates.triggered.connect(self.copyAllStates)
		self.actionPasteStates.triggered.connect(self.pasteStates)
		self.actionRemoveStates.triggered.connect(self.removeAllStates)

		self.tw_import.customContextMenuRequested.connect(lambda x: self.rclTree(x, self.tw_import))
		self.tw_import.currentItemChanged.connect(lambda x,y: self.stateChanged(x, y, self.tw_import))
		self.tw_import.itemClicked.connect(lambda x,y: self.updateForeground(x, y, self.tw_import))
		self.tw_import.itemDoubleClicked.connect(self.focusRename)
		self.tw_import.focusOutEvent = self.checkFocusOut
		self.tw_import.keyPressEvent = self.checkKeyPressed
		self.tw_import.focusInEvent = self.focusImport
		self.tw_import.origDropEvent = self.tw_import.dropEvent
		self.tw_import.dropEvent = self.handleImportDrop
		self.tw_import.itemCollapsed.connect(self.saveStatesToScene)
		self.tw_import.itemExpanded.connect(self.saveStatesToScene)

		self.tw_export.customContextMenuRequested.connect(lambda x: self.rclTree(x, self.tw_export))
		self.tw_export.currentItemChanged.connect(lambda x,y: self.stateChanged(x, y, self.tw_export))
		self.tw_export.itemClicked.connect(lambda x, y: self.updateForeground(x, y, self.tw_export))
		self.tw_export.itemChanged.connect(lambda x,y: self.saveStatesToScene())
		self.tw_export.itemDoubleClicked.connect(self.focusRename)
		self.tw_export.focusOutEvent = self.checkFocusOut
		self.tw_export.keyPressEvent = self.checkKeyPressed
		self.tw_export.focusInEvent = self.focusExport
		self.tw_export.origDropEvent = self.tw_export.dropEvent
		self.tw_export.dropEvent = self.handleExportDrop
		self.tw_export.itemCollapsed.connect(self.saveStatesToScene)
		self.tw_export.itemExpanded.connect(self.saveStatesToScene)

		self.b_createImport.clicked.connect(lambda: self.createPressed("ImportFile"))
		self.b_createExport.clicked.connect(lambda: self.createPressed("Export"))
		self.b_createRender.clicked.connect(lambda: self.core.appPlugin.sm_createRenderPressed(self))
		self.b_createPlayblast.clicked.connect(lambda: self.createPressed("Playblast"))
		self.b_createDependency.clicked.connect(lambda: self.createPressed("Dependency"))
		self.b_shotCam.clicked.connect(self.shotCam)
		self.b_stateFromNode.clicked.connect(lambda: self.core.appPlugin.sm_openStateFromNode(self))

		self.e_comment.textChanged.connect(self.commentChanged)
		self.e_comment.editingFinished.connect(self.saveStatesToScene)
		self.b_description.clicked.connect(self.showDescription)
		self.b_description.customContextMenuRequested.connect(self.clearDescription)
		self.b_preview.clicked.connect(self.getPreview)
		self.b_preview.customContextMenuRequested.connect(self.clearPreview)
		self.b_description.setMouseTracking(True)
		self.b_description.mouseMoveEvent = lambda x: self.detailMoveEvent(x, "d")
		self.b_description.leaveEvent = lambda x: self.detailLeaveEvent(x, "d")
		self.b_description.focusOutEvent = lambda x: self.detailFocusOutEvent(x, "d")
		self.b_preview.setMouseTracking(True)
		self.b_preview.mouseMoveEvent = lambda x: self.detailMoveEvent(x, "p")
		self.b_preview.leaveEvent = lambda x: self.detailLeaveEvent(x, "p")
		self.b_preview.focusOutEvent = lambda x: self.detailFocusOutEvent(x, "p")

		self.b_getRange.clicked.connect(self.getRange)
		self.b_setRange.clicked.connect(lambda: self.core.setFrameRange(self.sp_rangeStart.value(), self.sp_rangeEnd.value()))
		self.sp_rangeStart.editingFinished.connect(self.startChanged)
		self.sp_rangeEnd.editingFinished.connect(self.endChanged)
		self.b_publish.clicked.connect(self.publish)


	@err_decorator
	def closeEvent(self, event):
		self.core.callback(name="onStateManagerClose", types=["custom"], args=[self])
		event.accept()


	@err_decorator
	def focusRename(self,item, column):
		if item is not None:
			item.ui.e_name.setFocus()


	@err_decorator
	def checkKeyPressed(self,event):
		if event.key() == Qt.Key_Tab:
			self.showStateList()

		event.accept()


	@err_decorator
	def checkFocusOut(self,event):
		if event.reason() == Qt.FocusReason.TabFocusReason:
			event.ignore()
			self.activeList.setFocus()
			self.showStateList()
		else:
			event.accept()


	@err_decorator
	def handleImportDrop(self, event):
		self.tw_import.origDropEvent(event)
		self.updateForeground()
		self.saveStatesToScene()


	@err_decorator
	def handleExportDrop(self, event):
		self.tw_export.origDropEvent(event)
		self.updateForeground()
		self.updateStateList()
		self.saveStatesToScene()


	@err_decorator
	def showStateList(self):
		pos = self.activeList.mapFromGlobal(QCursor.pos())
		idx = self.activeList.indexAt(pos)

		state = self.activeList.itemFromIndex(idx)

		if state is not None and state.ui.className != "Folder":
			return True

		createMenu = QMenu()

		stateNames = self.stateTypes.keys()
		stateNames.sort()

		for val in stateNames:
			showImportTypes = self.activeList == self.tw_import
			if val == "Folder" or ("Import" in val) == showImportTypes:
				actStates1 = QAction(val, self)
				actStates1.triggered.connect(lambda x=None, i=val: self.createState(i, state))
				createMenu.addAction(actStates1)

		self.core.appPlugin.setRCStyle(self, createMenu)

		createMenu.exec_(self.activeList.mapToGlobal(pos))


	@err_decorator
	def rclTree(self, pos, activeList):
		rcmenu = QMenu()
		idx = self.activeList.indexAt(pos)
		state = self.activeList.itemFromIndex(idx)
		self.rClickedItem = state

		createMenu = QMenu("Create")

		stateNames = list(self.stateTypes.keys())
		stateNames.sort()
		for val in stateNames:
			showImportTypes = self.activeList == self.tw_import
			if val == "Folder" or ("Import" in val) == showImportTypes:
				actStates1 = QAction(val, self)
				actStates1.triggered.connect(lambda x=None, i=val: self.createState(i, state))
				createMenu.addAction(actStates1)

		self.core.appPlugin.setRCStyle(self, createMenu)

		actExecute = QAction("Execute", self)
		actExecute.triggered.connect(lambda: self.publish(executeState=True))

		menuExecuteV = QMenu("Execute as previous version", self)

		actCopy = QAction("Copy", self)
		actCopy.triggered.connect(self.copyState)

		actPaste = QAction("Paste", self)
		actPaste.triggered.connect(self.pasteStates)

		actDel = QAction("Delete", self)
		actDel.triggered.connect(self.deleteState)

		if state is None:
			actCopy.setEnabled(False)
			actDel.setEnabled(False)
			actExecute.setEnabled(False)
			menuExecuteV.setEnabled(False)
		elif hasattr(state.ui, "l_pathLast"):
			outPath = state.ui.getOutputName()
			if outPath is None:
				menuExecuteV.setEnabled(False)
			else:
				outPath = outPath[0]
				existingVersions = []
				versionDir = os.path.dirname(os.path.dirname(outPath))
				if state.ui.className != "Playblast":
					versionDir = os.path.dirname(versionDir)

				if os.path.exists(versionDir):
					for i in reversed(sorted(os.listdir(versionDir))):
						if len(i) < 5 or not i.startswith("v"):
							continue

						if pVersion == 2:
							if not unicode(i[1:5]).isnumeric():
								continue
						else:
							if not i[1:5].isnumeric():
								continue

						existingVersions.append(i)

				for i in existingVersions:
					actV = QAction(i, self)
					actV.triggered.connect(lambda y=None, x=actV: self.publish(executeState=True, useVersion=x.text()))
					menuExecuteV.addAction(actV)

			if menuExecuteV.isEmpty():
				menuExecuteV.setEnabled(False)
	
		if state is None or state.ui.className == "Folder":
			rcmenu.addMenu(createMenu)

		if self.activeList == self.tw_export:
			rcmenu.addAction(actExecute)
			rcmenu.addMenu(menuExecuteV)
		rcmenu.addAction(actCopy)
		rcmenu.addAction(actPaste)
		rcmenu.addAction(actDel)

		self.core.appPlugin.setRCStyle(self, rcmenu)

		rcmenu.exec_(self.activeList.mapToGlobal(pos))


	@err_decorator
	def createState(self, statetype, parent=None, node=None, importPath=None, stateData=None, setActive=False, renderer=None):
		if statetype not in self.stateTypes:
			return False

		item = QTreeWidgetItem([statetype])
		item.ui = self.stateTypes[statetype]()

		if node is None:
			if importPath is None:
				if renderer is None:
					stateSetup = item.ui.setup(item, self.core, self, stateData=stateData)
				else:
					stateSetup = item.ui.setup(item, self.core, self, stateData=stateData, renderer=renderer)
			else:
				stateSetup = item.ui.setup(item, self.core, self, importPath=importPath, stateData=stateData)
		else:
			stateSetup = item.ui.setup(item, self.core, self, node)

		if stateSetup == False:
			return

		self.core.scaleUI(item)

		if item.ui.className == "Folder" and stateData is None:
			if self.activeList == self.tw_import:
				listType = "Import"
			else:
				listType = "Export"
		else:
			listType = item.ui.listType

		if listType == "Import":
			pList = self.tw_import
		else:
			pList = self.tw_export

		if stateData is None and pList == self.tw_export:
			item.setCheckState(0, Qt.Checked)
			if psVersion == 2:
				item.setFlags(item.flags() & ~Qt.ItemIsAutoTristate)
		
		if parent is None:
			pList.addTopLevelItem(item)
		else:
			parent.addChild(item)
			parent.setExpanded(True)

		self.updateStateList()

		if statetype != "Folder":
			item.setFlags(item.flags() & ~Qt.ItemIsDropEnabled)

		self.core.callback(name="onStateCreated", types=["custom"], args=[self])

		if setActive:
			self.setListActive(pList)
		pList.setCurrentItem(item)
		self.updateForeground()

		if statetype == "ImportFile":
			self.saveImports()

		self.saveStatesToScene()

		return item


	@err_decorator
	def copyAllStates(self):
		stateData = self.core.appPlugin.sm_readStates(self)

		cb = QClipboard()
		cb.setText(stateData)


	@err_decorator
	def pasteStates(self):
		cb = QClipboard()
		try:
			rawText = cb.text("plain")[0]
		except:
			QMessageBox.warning(self.core.messageParent,"Paste states", "No valid state data in clipboard.")
			return

		self.loadStates(rawText)

		self.showState()
		self.activeList.clearFocus()
		self.activeList.setFocus()


	@err_decorator
	def removeAllStates(self):
		msg = QMessageBox(QMessageBox.Warning, "Publish", "Are you sure you want to delete all states in the current scene?", QMessageBox.Cancel)
		msg.addButton("Yes", QMessageBox.YesRole)
		self.core.parentWindow(msg)
		action = msg.exec_()

		if action != 0:
			return

		self.core.appPlugin.sm_deleteStates(self)
		self.core.closeSM(restart=True)


	@err_decorator
	def copyState(self):
		selStateData = []
		selStateData.append([self.activeList.currentItem(), None])
		self.appendChildStates(selStateData[len(selStateData)-1][0], selStateData)

		stateConfig = ConfigParser()

		for idx, i in enumerate(selStateData):
			stateConfig.add_section(str(idx))
			stateConfig.set(str(idx), "stateparent", str(i[1]))
			stateConfig.set(str(idx), "stateclass", i[0].ui.className)
			stateProps = i[0].ui.getStateProps()
			for k in stateProps:
				stateConfig.set(str(idx), k, str(stateProps[k]))

		buf = StringIO()
		stateConfig.write(buf)		

		cb = QClipboard()
		cb.setText(buf.getvalue())


	@err_decorator
	def deleteState(self, state=None):
		if state is None:
			item = self.activeList.currentItem()
		else:
			item = state

		for i in range(item.childCount()):
			self.deleteState(item.child(i))

		getattr(item.ui, "preDelete", lambda item: None)(item=item)

		#self.states.remove(item) #buggy in qt 4

		newstates = []
		for i in self.states:
			if id(i) != id(item):
				newstates.append(i)

		self.states = newstates

		parent = item.parent()
		if parent is None:
			if item.ui.listType == "Export":
				iList = self.tw_export
			else:
				iList = self.tw_import
			try:

				idx = iList.indexOfTopLevelItem(item)
			except:
				# bug in PySide2
				for i in range(iList.topLevelItemCount()):
					if iList.topLevelItem(i) is item:
						idx = i

			if "idx" in locals():
				iList.takeTopLevelItem(idx)
		else:
			idx = parent.indexOfChild(item)
			parent.takeChild(idx)

		self.core.callback(name="onStateDeleted", types=["custom"], args=[self])

		if item.ui.className == "ImportFile":
			self.saveImports()

		self.activeList.setCurrentItem(None)
		self.saveStatesToScene()


	@err_decorator
	def createPressed(self, stateType, renderer=None):
		curSel = self.activeList.currentItem()
		if stateType == "ImportFile":
			if self.activeList == self.tw_import and curSel is not None and curSel.ui.className == "Folder":
				parent = curSel
			else:
				parent = None

			self.createState("ImportFile", parent=parent)
			self.setListActive(self.tw_import)
			self.activateWindow()

		elif stateType == "Export":
			if self.activeList == self.tw_export and curSel is not None and curSel.ui.className == "Folder":
				parent = curSel
			else:
				parent = None

			self.createState("Export", parent=parent)
			self.setListActive(self.tw_export)

		elif stateType == "Render":
			if self.activeList == self.tw_export and curSel is not None and curSel.ui.className == "Folder":
				parent = curSel
			else:
				parent = None

			self.createState("ImageRender", parent=parent, renderer=renderer)

			self.setListActive(self.tw_export)

		elif stateType == "Playblast":
			if self.activeList == self.tw_export and curSel is not None and curSel.ui.className == "Folder":
				parent = curSel
			else:
				parent = None

			self.createState("Playblast", parent=parent)
			self.setListActive(self.tw_export)

		elif stateType == "Dependency":
			if self.activeList == self.tw_export and curSel is not None and curSel.ui.className == "Folder":
				parent = curSel
			else:
				parent = None

			self.createState("Dependency", parent=parent)
			self.setListActive(self.tw_export)

		self.activeList.setFocus()


	@err_decorator
	def shotCam(self):
		self.saveEnabled = False
		for i in self.states:
			if i.ui.className == "ImportFile" and i.ui.taskName == "ShotCam":
				mCamState = i.ui
				camState = i

		if "mCamState" in locals():
			mCamState.importLatest()
			self.tw_import.setCurrentItem(camState)
		else:
			fileName = self.core.getCurrentFileName()
			fnameData = os.path.basename(fileName).split(self.core.filenameSeperator)
			sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
			if not (os.path.exists(fileName) and len(fnameData) == 8 and (os.path.join(self.core.projectPath, sceneDir) in fileName or ( self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir) in fileName))):
				QMessageBox.warning(self.core.messageParent,"Could not save the file", "The current file is not inside the Pipeline.\nUse the Project Browser to create a file in the Pipeline.")
				self.saveEnabled = True
				return False

			if self.core.useLocalFiles and self.core.localProjectPath in fileName:
				fileName = fileName.replace(self.core.localProjectPath, self.core.projectPath)

			camPath = os.path.abspath(os.path.join(fileName, os.pardir, os.pardir, os.pardir, os.pardir, "Export", "_ShotCam"))

			for i in os.walk(camPath):
				camFolders = i[1]
				break

			if not "camFolders" in locals():
				QMessageBox.warning(self.core.messageParent,"Warning", "Could not find a shotcam for the current shot.")
				self.saveEnabled = True
				return False

			highversion = 0
			for i in camFolders:
				fname = i.split(self.core.filenameSeperator)
				if len(fname) == 3 and fname[0][0] == "v" and len(fname[0]) == 5 and int(fname[0][1:5]) > highversion:
					highversion = int(fname[0][1:5])
					highFolder = i

			if not "highFolder" in locals():
				QMessageBox.warning(self.core.messageParent,"Warning", "Could not find a shotcam for the current shot.")
				self.saveEnabled = True
				return False

			camPath = os.path.join(camPath, highFolder, self.core.appPlugin.preferredUnit)

			if not os.path.exists(camPath):
				QMessageBox.warning(self.core.messageParent,"Warning", "Could not find a shotcam for the current shot.")
				self.saveEnabled = True
				return False

			for camFile in os.listdir(camPath):
				if camFile.endswith(self.shotcamFileType):
					camPath = os.path.join(camPath, camFile)
					break

			importData = ["ShotCam", camPath]
			self.createState("ImportFile", importPath=importData)

		self.setListActive(self.tw_import)
		self.activateWindow()
		self.activeList.setFocus()
		self.saveEnabled = True
		self.saveStatesToScene()


	def enterEvent(self, event):
		try:
			QApplication.restoreOverrideCursor()
		except:
			pass


	@err_decorator
	def saveStatesToScene(self, param=None):
		if not self.saveEnabled:
			return False

		getattr(self.core.appPlugin, "sm_preSaveToScene", lambda x: None)(self)

	#	print "save to scene"

		self.stateData = []
		for i in range(self.tw_import.topLevelItemCount()):
			self.stateData.append([self.tw_import.topLevelItem(i), None])
			self.appendChildStates(self.stateData[len(self.stateData)-1][0], self.stateData)

		for i in range(self.tw_export.topLevelItemCount()):
			self.stateData.append([self.tw_export.topLevelItem(i), None])
			self.appendChildStates(self.stateData[len(self.stateData)-1][0], self.stateData)

		stateConfig = ConfigParser()

		stateConfig.add_section("publish")
		stateConfig.set("publish", "startframe", str(self.sp_rangeStart.value()))
		stateConfig.set("publish", "endframe", str(self.sp_rangeEnd.value()))
		stateConfig.set("publish", "comment", str(self.e_comment.text()))
		stateConfig.set("publish", "description", self.description)

		for idx, i in enumerate(self.stateData):
			stateConfig.add_section(str(idx))
			stateConfig.set(str(idx), "stateparent", str(i[1]))
			stateConfig.set(str(idx), "stateclass", i[0].ui.className)
			stateProps = i[0].ui.getStateProps()
			for k in stateProps:
				stateConfig.set(str(idx), k, str(stateProps[k]))

		buf = StringIO()
		stateConfig.write(buf)

		self.core.appPlugin.sm_saveStates(self, buf.getvalue())


	@err_decorator
	def saveImports(self):
		importPaths = str(self.getFilePaths(self.tw_import.invisibleRootItem(), []))
		self.core.appPlugin.sm_saveImports(self, importPaths)


	@err_decorator
	def getFilePaths(self, item, paths=[]):
		if hasattr(item, "ui") and item.ui.className == "ImportFile":
			paths.append([item.ui.e_file.text(), item.ui.taskName])
		for i in range(item.childCount()):
			paths = self.getFilePaths(item.child(i), paths)

		return paths


	@err_decorator
	def appendChildStates(self, state, stateList):
		stateNum = len(stateList)
		for i in range(state.childCount()):
			stateList.append([state.child(i), stateNum])
			self.appendChildStates(state.child(i), stateList)


	@err_decorator
	def commentChanged(self, text):
		minLength = 2
		self.validateComment()
		text = self.e_comment.text()
		if len(text) > minLength:
			self.b_publish.setEnabled(True)
			self.b_publish.setText("Publish")
		else:
			self.b_publish.setEnabled(False)
			self.b_publish.setText("Publish - (%s more chars needed in comment)" % (1+minLength - len(text)))


	@err_decorator
	def showDescription(self):
		descriptionDlg = EnterText.EnterText()
		descriptionDlg.buttonBox.removeButton(descriptionDlg.buttonBox.buttons()[1])
		descriptionDlg.setModal(True)
		self.core.parentWindow(descriptionDlg)
		descriptionDlg.setWindowTitle("Enter description")
		descriptionDlg.l_info.setText("Description:")
		descriptionDlg.te_text.setPlainText(self.description)
		descriptionDlg.exec_()

		self.description = descriptionDlg.te_text.toPlainText()
		if self.description == "":
			self.b_description.setStyleSheet(self.styleMissing)
		else:
			self.b_description.setStyleSheet(self.styleExists)
		self.saveStatesToScene()


	@err_decorator
	def getPreview(self):
		from PrismUtils import ScreenShot
		self.previewImg = ScreenShot.grabScreenArea(self.core)
		if self.previewImg is None:
			self.b_preview.setStyleSheet(self.styleMissing)
		else:
			self.previewImg = self.previewImg.scaled(500, 281, Qt.KeepAspectRatio, Qt.SmoothTransformation)
			self.b_preview.setStyleSheet(self.styleExists)


	@err_decorator
	def clearDescription(self, pos=None):
		self.description = ""
		self.b_description.setStyleSheet(self.styleMissing)
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()
		self.saveStatesToScene()


	@err_decorator
	def clearPreview(self, pos=None):
		self.previewImg = None
		self.b_preview.setStyleSheet(self.styleMissing)
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()


	@err_decorator
	def detailMoveEvent(self, event, table):
		self.showDetailWin(event, table)
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.move(QCursor.pos().x()+20, QCursor.pos().y()-self.detailWin.height())


	@err_decorator
	def showDetailWin(self, event, detailType):
		if detailType == "d":
			detail = self.description
		elif detailType == "p":
			detail = self.previewImg

		if not detail:
			if hasattr(self, "detailWin") and self.detailWin.isVisible():
				self.detailWin.close()
			return
	
		if not hasattr(self, "detailWin") or not self.detailWin.isVisible() or self.detailWin.detail != detail:
			if hasattr(self, "detailWin"):
				self.detailWin.close()

			self.detailWin = QFrame()
			ss = getattr(self.core.appPlugin, "getFrameStyleSheet", lambda x: "")(self)
			self.detailWin.setStyleSheet(ss +""" .QFrame{ border: 2px solid rgb(100,100,100);} """)

			self.detailWin.detail = detail
			self.core.parentWindow(self.detailWin)
			winwidth = 320
			winheight = 10
			VBox = QVBoxLayout()
			if detailType is "p":
				l_prv = QLabel()
				l_prv.setPixmap(detail)
				l_prv.setStyleSheet( """
					border: 1px solid rgb(100,100,100);
				""")
				VBox.addWidget(l_prv)
				VBox.setContentsMargins(0,0,0,0)
			elif detailType is "d":
				descr = QLabel(self.description)
				VBox.addWidget(descr)
			self.detailWin.setLayout(VBox)
			self.detailWin.setWindowFlags(
					  Qt.FramelessWindowHint # hides the window controls
					| Qt.WindowStaysOnTopHint # forces window to top... maybe
					| Qt.SplashScreen # this one hides it from the task bar!
					)
		
			self.detailWin.setGeometry(0, 0, winwidth, winheight)
			self.detailWin.move(QCursor.pos().x()+20, QCursor.pos().y())
			self.detailWin.show()


	@err_decorator
	def getImgPMap(self, path):
		if platform.system() == "Windows":
			return QPixmap(path)
		else:
			try:
				im = Image.open(path)
				im = im.convert("RGBA")
				r,g,b,a = im.split()
				im = Image.merge("RGBA", (b,g,r,a))
				data = im.tobytes("raw", "RGBA")

				qimg = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)

				return QPixmap(qimg)
			except:
				return QPixmap(path)


	@err_decorator
	def detailLeaveEvent(self, event, table):
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()


	@err_decorator
	def detailFocusOutEvent(self, event, table):
		if hasattr(self, "detailWin") and self.detailWin.isVisible():
			self.detailWin.close()


	@err_decorator
	def startChanged(self):
		if self.sp_rangeStart.value() > self.sp_rangeEnd.value():
			self.sp_rangeEnd.setValue(self.sp_rangeStart.value())

		self.saveStatesToScene()


	@err_decorator
	def endChanged(self):
		if self.sp_rangeEnd.value() < self.sp_rangeStart.value():
			self.sp_rangeStart.setValue(self.sp_rangeEnd.value())

		self.saveStatesToScene()


	@err_decorator
	def getRange(self):
		shotFile = os.path.join(os.path.dirname(self.core.prismIni), "Shotinfo", "shotInfo.ini")
		if not os.path.exists(shotFile):
			return False

		shotConfig = ConfigParser()
		shotConfig.read(shotFile)

		fileName = self.core.getCurrentFileName()
		fileNameData = os.path.basename(fileName).split(self.core.filenameSeperator)
		sceneDir = self.core.getConfig('paths', "scenes", configPath=self.core.prismIni)
		if (os.path.join(self.core.projectPath, sceneDir) in fileName or (self.core.useLocalFiles and os.path.join(self.core.localProjectPath, sceneDir) in fileName)) and len(fileNameData) == 8 and shotConfig.has_option("shotRanges", fileNameData[1]):
			shotRange = eval(shotConfig.get("shotRanges", fileNameData[1]))
			if type(shotRange) == list and len(shotRange) == 2:
				self.sp_rangeStart.setValue(shotRange[0])
				self.sp_rangeEnd.setValue(shotRange[1])
				self.saveStatesToScene()


	@err_decorator
	def getChildStates(self, state):
		states = [state]

		for i in range(state.childCount()):
			states.append(state.child(i))
			if state.child(i).ui.className == "Folder":
				states += self.getChildStates(state.child(i))

		return states


	@err_decorator
	def publish(self, executeState=False, continuePublish=False, useVersion="next"):
		if self.publishPaused and not continuePublish:
			return

		if continuePublish:
			executeState = self.publishType == "execute"

		if executeState:
			self.publishType = "execute"
			self.execStates = self.getChildStates(self.tw_export.currentItem())
			actionString = "Execute"
			actionString2 = "execution"
		else:
			self.publishType = "publish"
			self.execStates = self.states
			actionString = "Publish"
			actionString2 = "publish"

		if continuePublish:
			skipStates = [x["state"].state for x in self.publishResult if "publish paused" not in x["result"][0]]
			self.execStates = [x for x in self.execStates if x not in set(skipStates)]
			self.publishPaused = False
		else:
			if useVersion != "next":
				msg = QMessageBox(QMessageBox.Information, actionString, "Are you sure you want to execute this state as version \"%s\"?\nThis may overwrite existing files." % useVersion, QMessageBox.Cancel)
				msg.addButton("Continue", QMessageBox.YesRole)
				self.core.parentWindow(msg)
				action = msg.exec_()

				if action != 0:
					return

			result = []
			extResult = self.core.appPlugin.sm_getExternalFiles(self)
			if extResult is not None:
				extFiles, extFilesSource = extResult
			else:
				extFiles = []
				extFilesSource = []

			invalidFiles = []
			nonExistend = []
			for idx, i in enumerate(extFiles):
				i = self.core.fixPath(i)

				if not (i.startswith(self.core.projectPath) or (self.core.useLocalFiles and i.startswith(self.core.localProjectPath))):
					if os.path.exists(i) and not i in invalidFiles:
						invalidFiles.append(i)
				
				if not os.path.exists(i) and not i in nonExistend and i != self.core.getCurrentFileName():
					exists = getattr(self.core.appPlugin, "sm_existExternalAsset", lambda x,y:False)(self, i)
					if exists:
						continue

					nonExistend.append(i)

			if len(invalidFiles) > 0:
				depTitle = "The current scene contains dependencies from outside the project folder:\n\n"
				depwarn = ""
				for i in invalidFiles:
					parmStr = getattr(self.core.appPlugin, "sm_fixWarning", lambda x1,x2,x3,x4: "")(self, i, extFiles, extFilesSource)

					depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

				result.append([depTitle, depwarn, 2])

			if len(nonExistend) > 0:
				depTitle = "The current scene contains dependencies, which does not exist:\n\n"
				depwarn = ""
				for i in nonExistend:
					parmStr = getattr(self.core.appPlugin, "sm_fixWarning", lambda x1,x2,x3,x4: "")(self, i, extFiles, extFilesSource)
					depwarn += "\t%s\n\t%s\n\n" % (parmStr, i)

				result.append([depTitle, depwarn, 2])

			warnings = []
			if len(result) > 0:
				warnings.append(["", result])

			if executeState:
				warnings.append(self.execStates[0].ui.preExecuteState())
			else:
				for i in range(self.tw_export.topLevelItemCount()):
					curState = self.tw_export.topLevelItem(i)
					if curState.checkState(0) == Qt.Checked and curState in set(self.execStates):
						warnings.append(curState.ui.preExecuteState())

			warnString = ""
			for i in warnings:
				if len(i[1]) == 0:
					continue

				if i[0] == "":
					warnBase = ""
				else:
					warnString += "- <b>%s</b>\n\n" % i[0]
					warnBase = "\t"

				for k in i[1]:
					if k[2] == 2:
						warnString += warnBase + ("- <font color=\"yellow\">%s</font>\n  %s\n" % (k[0], k[1])).replace("\n", "\n" + warnBase) + "\n"
					elif k[2] == 3:
						warnString += warnBase + ("- <font color=\"red\">%s</font>\n  %s\n" % (k[0], k[1])).replace("\n", "\n" + warnBase) + "\n"
		
			if warnString != "" and self.core.uiAvailable:
				warnDlg = QDialog()

				warnDlg.setWindowTitle("Publish warnings")
				l_info = QLabel(str("The following warnings have occurred:\n"))

				warnString = "<pre>%s</pre>" % warnString.replace("\n", "<br />").replace("\t", "    ")
				l_warnings = QLabel(warnString)
				l_warnings.setAlignment(Qt.AlignTop)

				sa_warns = QScrollArea()

				lay_warns = QHBoxLayout()
				lay_warns.addWidget(l_warnings)
				lay_warns.setContentsMargins(10,10,10,10)
				lay_warns.addStretch()
				w_warns = QWidget()
				w_warns.setLayout(lay_warns)
				sa_warns.setWidget(w_warns)
				sa_warns.setWidgetResizable(True)
			
				bb_warn = QDialogButtonBox()

				bb_warn.addButton("Continue", QDialogButtonBox.AcceptRole)
				bb_warn.addButton("Cancel", QDialogButtonBox.RejectRole)

				bb_warn.accepted.connect(warnDlg.accept)
				bb_warn.rejected.connect(warnDlg.reject)

				bLayout = QVBoxLayout()
				bLayout.addWidget(l_info)
				bLayout.addWidget(sa_warns)
				bLayout.addWidget(bb_warn)
				warnDlg.setLayout(bLayout)
				warnDlg.setParent(self.core.messageParent, Qt.Window)
				warnDlg.resize(1000*self.core.uiScaleFactor,500*self.core.uiScaleFactor)

				action = warnDlg.exec_()

				if action == 0:
					return

			else:
				print (warnString)

			details = {}
			if self.description != "":
				details = {"description":self.description, "username":self.core.getConfig("globals", "UserName")}

			if executeState:
				sceneSaved = self.core.saveScene(versionUp=False, details=details, preview=self.previewImg)
			else:
				sceneSaved = self.core.saveScene(comment=self.e_comment.text(), publish=True, details=details, preview=self.previewImg)

			if not sceneSaved:
				if self.core.uiAvailable:
					QMessageBox.warning(self.core.messageParent, actionString, actionString + " canceled")
				return

			self.description = ""
			self.previewImg = None
			self.b_description.setStyleSheet(self.styleMissing)
			self.b_preview.setStyleSheet(self.styleMissing)
			self.saveStatesToScene()

			self.publishResult = []
			self.osSubmittedJobs = {}
			self.osDependencies = []
			self.dependencies = []
			self.reloadScenefile = False
			self.publishInfos = { "updatedExports": {}, "backgroundRender": None}
			self.core.sceneOpenChecksEnabled = False

			getattr(self.core.appPlugin, "sm_preExecute", lambda x:None)(self)
			self.core.callback(name="onPublish", types=["custom"], args=[self])

		if executeState:
			if self.execStates[0].ui.className in ["ImageRender", "Export", "Playblast", "Folder"]:
				result = self.execStates[0].ui.executeState(parent=self, useVersion=useVersion)
			else:
				result = self.execStates[0].ui.executeState(parent=self)

			if self.execStates[0].ui.className == "Folder":
				self.publishResult += result

				for k in result:
					if "publish paused" in k["result"][0]:
						self.publishPaused = True
						return
			else:
				self.publishResult.append({"state": self.execStates[0].ui, "result":result})

				if "publish paused" in result[0]:
					self.publishPaused = True
					return

		else:
			for i in range(self.tw_export.topLevelItemCount()):
				curUi = self.tw_export.topLevelItem(i).ui
				if self.tw_export.topLevelItem(i).checkState(0) == Qt.Checked and curUi.state in set(self.execStates):
					exResult = curUi.executeState(parent=self)
					if curUi.className == "Folder":
						self.publishResult += exResult

						for k in exResult:
							if "publish paused" in k["result"][0]:
								self.publishPaused = True
								return
					else:
						self.publishResult.append({"state": curUi, "result":exResult})

						if "publish paused" in exResult[0]:
							self.publishPaused = True
							return

		getattr(self.core.appPlugin, "sm_postExecute", lambda x:None)(self)

		self.publishInfos = { "updatedExports": {}, "backgroundRender": None}
		self.osSubmittedJobs = {}
		self.osDependencies = []
		self.dependencies = []
		self.core.sceneOpenChecksEnabled = True

		success = True
		for i in self.publishResult:
			if "error" in i["result"][0]:
				success = False

		
		if success:
			msgStr = "The %s was successfull." % actionString2
			if self.core.uiAvailable:
				QMessageBox.information(self.core.messageParent, actionString, msgStr)
			else:
				print (msgStr)
		else:
			infoString = ""
			for i in self.publishResult:
				if not "publish paused" in i["result"][0]:
					infoString += i["result"][0] +"\n"

			msgStr = "Errors occured during the %s:\n\n" % actionString2 + infoString

			if self.core.uiAvailable:
				QMessageBox.warning(self.core.messageParent, actionString, msgStr)
			else:
				print (msgStr)

		if self.reloadScenefile:
			self.core.appPlugin.openScene(self, self.core.getCurrentFileName())


	@err_decorator
	def validateComment(self):
		origComment = self.e_comment.text()
		validText = self.core.validateStr(origComment)
		startpos = self.e_comment.cursorPosition()
		
		if len(origComment) != len(validText):
			self.e_comment.setText(validText)
			self.e_comment.setCursorPosition(startpos-1)


	@err_decorator
	def getStateProps(self):
		return {"startframe":self.sp_rangeStart.value(), "endframe":self.sp_rangeEnd.value(), "comment":self.e_comment.text(), "description":self.description}