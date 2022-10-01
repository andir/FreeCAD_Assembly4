#!/usr/bin/env python3
# coding: utf-8
#
# makeBomCmd.py
#
# Parses the Assembly 4 Model tree and creates a list of parts

import os
import json

from PySide import QtGui, QtCore
import FreeCADGui as Gui
import FreeCAD as App

import Asm4_libs as Asm4
import infoPartCmd
import InfoKeys

crea = infoPartCmd.infoPartUI.makePartInfo
fill = infoPartCmd.infoPartUI.infoDefault

ConfUserDir = os.path.join(App.getUserAppDataDir(),'Templates')
ConfUserFilename = "Asm4_infoPartConf.json"
ConfUserFilejson = os.path.join(ConfUserDir, ConfUserFilename)

# Check if the configuration file exists
try:
    file = open(ConfUserFilejson, 'r')
    file.close()
except:
    partInfoDef = dict()
    for prop in InfoKeys.partInfo:
        partInfoDef.setdefault(prop, {'userData': prop, 'active': True, 'visible': True})
    for prop in InfoKeys.partInfo_Invisible:
        partInfoDef.setdefault(prop, {'userData': prop, 'active': True, 'visible': False})
    try:
        os.mkdir(ConfUserDir)
    except:
        pass
    file = open(ConfUserFilejson, 'x')
    json.dump(partInfoDef, file)
    file.close()

# Load user's config file
file = open(ConfUserFilejson, 'r')
infoKeysUser = json.load(file).copy()
file.close()


class makeBOM:

    def __init__(self, follow_subassemblies=1):
        super(makeBOM, self).__init__()
        self.follow_subassemblies = follow_subassemblies
        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()

    def GetResources(self):

        if self.follow_subassemblies:
            menutext = "Create Part List"
            tooltip  = "Create the Bill of Materials of the Assembly with the sub-assemblies"
            iconFile = os.path.join( Asm4.iconPath, 'Asm4_PartsList_Subassemblies.svg' )
        else:
            menutext = "Create Local Part List"
            tooltip  = "Create the Bill of Materials of the Assembly"
            iconFile = os.path.join( Asm4.iconPath, 'Asm4_PartsList.svg' )

        return {
            "MenuText": menutext,
            "ToolTip": tooltip,
            "Pixmap": iconFile
        }

    def IsActive(self):
        if Asm4.getAssembly() is None:
            return False
        else:
            return True

    def Activated(self):
        self.UI = QtGui.QDialog()
        self.modelDoc = App.ActiveDocument
        try:
            self.model = self.modelDoc.Assembly
            print("BOM of the Assembly 4 Model")
        except:
            try:
                self.model = self.modelDoc.Model
                print("BOM of the legacy Assembly 4 Model")
            except:
                print("BOM might not work with this file")
        self.drawUI()
        self.UI.show()
        self.BOM.clear()
        self.Verbose = str()
        self.PartsList = {}
        self.listParts(self.model)
        self.inSpreadsheet()
        self.BOM.setPlainText(self.Verbose)

    def indent(self, level, tag="|"):
        spaces = (level + 1) * "  "
        return "[{level}]{spaces}{tag} ".format(level=str(level), tag=tag, spaces=spaces)

    def listParts(self, obj, level=0, parent=None, grandparent=None):

        file = open(ConfUserFilejson, 'r')
        self.infoKeysUser = json.load(file).copy()
        file.close()

        max_level = 10
        if self.follow_subassemblies:
            max_level = 1;

        if obj == None:
            return

        if self.PartsList == None:
            self.PartsList = {}

        if obj.TypeId == 'App::Link':

            if obj.Visibility == False:
                return

            print("ASM4> {level}{obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId))

            self.Verbose += "> {level} | {type}: {label}, {fullname}".format(level=obj.Label, type="LINK", label=obj.Label, fullname=obj.FullName)
            self.Verbose += "- linked: {linked_obj}\n".format(linked_obj=obj.LinkedObject.Name)
            self.Verbose += '- not included in the BOM\n\n'

            self.listParts(obj.LinkedObject, level + 1, parent=obj, grandparent=parent)

        elif obj.TypeId == 'App::Part':

            if level > 0 and grandparent.TypeId == "App::Link" and obj.Visibility == True and obj.Label != "Model" and level <= max_level:

                if obj.Label in self.PartsList:

                    qtd = self.PartsList[obj.Label]['Qty.'] + 1

                    print("ASM4> {level}({qtd}) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId, qtd=qtd))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="PART", label=obj.Label, fullname=obj.FullName)
                    self.Verbose += "- object already added\n\n"
                    self.PartsList[obj.Label]['Qty.'] = qtd

                else:

                    print("ASM4> {level}(1) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="PART", label=obj.Label, fullname=obj.FullName)

                    self.PartsList[obj.Label] = dict()
                    for prop in self.infoKeysUser:

                        self.Verbose +=  "- " + prop + ': '

                        if self.infoKeysUser.get(prop).get('active'):
                            try: # to get partInfo
                                getattr(obj, self.infoKeysUser.get(prop).get('userData'))
                            except AttributeError:
                                crea(self,obj)
                                fill(obj)

                            if self.infoKeysUser.get(prop).get('visible'):
                                data = getattr(obj, self.infoKeysUser.get(prop).get('userData'))
                            else:
                                data = "-"

                            if data == "":
                                data = "-"

                            self.Verbose +=  data + '\n'
                            self.PartsList[obj.Label][self.infoKeysUser.get(prop).get('userData')] = data

                    self.PartsList[obj.Label]['Qty.'] = 1
                    self.Verbose += '\n'

        elif obj.TypeId == 'PartDesign::Body':

            if level > 0 and level <= max_level:

                if obj.Name[0:4] == "Body":
                    obj_label = parent.Label
                else:
                    obj_label = obj.Label

                if obj_label in self.PartsList:

                    qtd = self.PartsList[obj_label]['Qty.'] + 1

                    print("ASM4> {level}({qtd}) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj_label, obj_name=obj.FullName, obj_typeid=obj.TypeId, qtd=qtd))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj_label, type="PART", label=obj_label, fullname=obj.FullName)
                    self.Verbose += "- object already added\n\n"
                    self.PartsList[obj_label]['Qty.'] = qtd

                else:

                    print("ASM4> {level}(1) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="PARTDESIGN", label=obj.Label, fullname=obj.FullName)

                    self.PartsList[obj_label] = dict()
                    for prop in self.infoKeysUser:

                        self.Verbose +=  "- " + prop + ': '

                        if prop == 'Doc_Label':
                            data = obj.Document.Label
                        elif prop == 'Part_Label':
                            data = obj_label
                        else:
                            data = "-"

                        if data != "-":
                            self.Verbose += data + '\n'

                        self.PartsList[obj_label][self.infoKeysUser.get(prop).get('userData')] = data

                    self.PartsList[obj_label]['Qty.'] = 1
                    self.Verbose += '\n'

        elif obj.TypeId == 'Part::Feature':

            if level > 0 and grandparent.TypeId == "App::Link" and obj.Visibility == True and level <= max_level:

                if obj.Label in self.PartsList:

                    qtd = self.PartsList[obj.Label]['Qty.'] + 1

                    print("ASM4> {level}({qtd}) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId, qtd=qtd))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="PART", label=obj.Label, fullname=obj.FullName)
                    self.Verbose += "- object already added\n\n"
                    self.PartsList[obj.Label]['Qty.'] = qtd

                else:

                    print("ASM4> {level}(1) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="PARTFEATURE", label=obj.Label, fullname=obj.FullName)

                    self.PartsList[obj.Label] = dict()
                    for prop in self.infoKeysUser:

                        self.Verbose +=  "- " + prop + ': '

                        if prop == 'Doc_Label':
                            data = obj.Document.Label
                        elif prop == 'Part_Label':
                            data = obj.Label
                        else:
                            data = "-"

                        if data != "-":
                            self.Verbose += data + '\n'

                        self.PartsList[obj.Label][self.infoKeysUser.get(prop).get('userData')] = data

                    self.PartsList[obj.Label]['Qty.'] = 1
                    self.Verbose += '\n'

        elif obj.TypeId == 'Part::FeaturePython' and obj.Content.find("FastenersCmd") > -1:

            if level > 0 and obj.Visibility and level <= max_level:

                if obj.Label in self.PartsList:

                    qtd = self.PartsList[obj.Label]['Qty.'] + 1

                    print("ASM4> {level}({qtd}) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId, qtd=qtd))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="FASTENER", label=obj.Label, fullname=obj.FullName)
                    self.Verbose += "- object already added\n\n"
                    self.PartsList[obj.Label]['Qty.'] = qtd

                else: # if the part is a was not added already

                    print("ASM4> {level}(1) {obj_typeid} | {obj_name} | {obj_label}".format(level=self.indent(level, tag=" "), obj_label=obj.Label, obj_name=obj.FullName, obj_typeid=obj.TypeId))

                    self.Verbose += "> {level} | {type}: {label}, {fullname}\n".format(level=obj.Label, type="FASTENER", label=obj.Label, fullname=obj.FullName)

                    self.PartsList[obj.Label] = dict()
                    for prop in self.infoKeysUser:

                        self.Verbose +=  "- " + prop + ': '

                        if prop == 'Doc_Label':
                            data = obj.Document.Label
                        elif prop == 'Part_Label':
                            data = obj.Label
                        elif prop == "Fastener_Diameter":
                            data = obj.diameter
                        elif prop == "Fastener_Type":
                            data = obj.type
                        elif prop == "Fastener_Lenght":
                            try:
                                data = str(obj.length).strip("mm") # Strip unity in case of the custom length (assuming mm)?
                            except:
                                data = ""
                        else:
                            data = "-"

                        if data != "-":
                            self.Verbose += data + '\n'

                        self.PartsList[obj.Label][self.infoKeysUser.get(prop).get('userData')] = data

                    self.PartsList[obj.Label]['Qty.'] = 1
                    self.Verbose += '\n'

        # Continue walking inside the groups
        if obj.TypeId == 'App::Part' or obj.TypeId == 'App::DocumentObjectGroup' and level <= max_level:

            # Walk through nested objects
            for objname in obj.getSubObjects():
                subobj = obj.Document.getObject(objname[0:-1])
                self.listParts(subobj, level, parent=obj, grandparent=parent)

        return

        self.Verbose += '\nBOM creation is done\n'

    def inSpreadsheet(self):
        """
        Copy Parts list to Spreadsheet
        """
        document = App.ActiveDocument
        plist = self.PartsList

        if len(plist) == 0:
            return

        if self.follow_subassemblies:
            if not hasattr(document, 'BOM'):
                spreadsheet = document.addObject('Spreadsheet::Sheet', 'BOM')
            else:
                spreadsheet = document.BOM
            spreadsheet.Label = "BOM"
        else:
            if not hasattr(document, 'Local_BOM'):
                spreadsheet = document.addObject('Spreadsheet::Sheet', 'Local_BOM')
            else:
                spreadsheet = document.Local_BOM
            spreadsheet.Label = "Local_BOM"

        spreadsheet.clearAll()

        def wrow(drow: [str], row: int):
            """
            Write rows in the spreadsheet
            """
            for i, d in enumerate(drow):
                if row == 0:
                    spreadsheet.set(str(chr(ord('a') + i)).upper() + str(row + 1), infoPartCmd.decodeXml(str(d)))
                else:
                    spreadsheet.set(str(chr(ord('a') + i)).upper() + str(row + 1), str(d))

        data = list(plist.values())
        # data = sorted(data, key=lambda d: d['Doc_Label'])
        # data = sorted(data, key=itemgetter('Doc_Label', 'Part_Label'))

        wrow(data[0].keys(), 0)
        for i, _ in enumerate(data):
            wrow(data[i].values(), i + 1)

        document.recompute()

        self.Verbose += "\n" + spreadsheet.Label + ' spreadsheet was created.\n'


    def onOK(self):
        document = App.ActiveDocument
        if self.follow_subassemblies:
            Gui.Selection.addSelection(document.Name, 'BOM')
        else:
            Gui.Selection.addSelection(document.Name, 'Local_BOM')
        self.UI.close()

    def drawUI(self):
        """
        Define the UI (static elements, only)
        """

        # Main Window (QDialog)
        self.UI.setWindowTitle('Parts List (BOM)')
        self.UI.setWindowIcon(QtGui.QIcon(os.path.join(Asm4.iconPath , 'FreeCad.svg')))
        self.UI.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        self.UI.setModal(False)
        self.mainLayout = QtGui.QVBoxLayout(self.UI)

        # Help and Log
        self.LabelBOML1 = QtGui.QLabel()
        self.LabelBOML1.setText('BOM generates bill of materials.\n\nIt uses the Parts\' info to generate entries on BOM, unless autofill is set.\n')
        self.LabelBOML2 = QtGui.QLabel()
        self.LabelBOML2.setText("Check <a href='https://github.com/Zolko-123/FreeCAD_Assembly4/tree/master/Examples/ConfigBOM/README.md'>BOM tutorial</a>")
        self.LabelBOML2.setOpenExternalLinks(True)
        self.LabelBOML3 = QtGui.QLabel()
        self.LabelBOML3.setText('\n\nReport:')

        self.mainLayout.addWidget(self.LabelBOML1)
        self.mainLayout.addWidget(self.LabelBOML2)
        self.mainLayout.addWidget(self.LabelBOML3)

        # The Log view is a plain text field
        self.BOM = QtGui.QPlainTextEdit()
        self.BOM.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.mainLayout.addWidget(self.BOM)

        # the button row definition
        self.buttonLayout = QtGui.QHBoxLayout()

        # OK button
        self.OkButton = QtGui.QPushButton('OK')
        self.OkButton.setDefault(True)
        self.buttonLayout.addWidget(self.OkButton)
        self.mainLayout.addLayout(self.buttonLayout)

        # finally, apply the layout to the main window
        self.UI.setLayout(self.mainLayout)

        # Actions
        self.OkButton.clicked.connect(self.onOK)

# Add the command in the workbench
Gui.addCommand('Asm4_makeLocalBOM', makeBOM(follow_subassemblies=0))
Gui.addCommand('Asm4_makeBOM', makeBOM(follow_subassemblies=1))
