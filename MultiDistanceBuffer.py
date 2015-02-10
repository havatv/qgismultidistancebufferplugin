# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer
                                 A QGIS plugin

                              -------------------
        begin                : 2015-02-05
        copyright            : (C) 2015 by Håvard Tveite
        email                : havard.tveite@nmbu.no
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import os.path
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from MultiDistanceBuffer_gui import MultiDistanceBufferDialog


class MultiDistanceBuffer:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        # Create the dialog and keep reference
        self.dlg = MultiDistanceBufferDialog(self.iface)

        # initialize locale
        pluginPath = QFileInfo(os.path.realpath(__file__)).path()
        localeName = QLocale.system().name()

        if QFileInfo(pluginPath).exists():
            self.localePath = (pluginPath + "/i18n/multidistancebuffer_"
                               + localeName + ".qm")

        if QFileInfo(self.localePath).exists():
            self.translator = QTranslator()
            self.translator.load(self.localePath)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/MultiDistanceBuffer/icon.png"),
            u"MultiDistanceBuffer", self.iface.mainWindow())
        # connect the action to the run method
        QObject.connect(self.action, SIGNAL("triggered()"), self.run)

        # Add toolbar button and menu item
        if hasattr(self.iface, 'addDatabaseToolBarIcon'):
            self.iface.addVectorToolBarIcon(self.action)
        else:
            self.iface.addToolBarIcon(self.action)
        if hasattr(self.iface, 'addPluginToVectorMenu'):
            self.iface.addPluginToVectorMenu(u"&Multiple Distance Buffer",
                                                               self.action)
        else:
            self.iface.addPluginToMenu("&Multiple Distance Buffer",
                                                        self.action)

    def unload(self):
        # Remove the plugin menu item and icon
        if hasattr(self.iface, 'removePluginVectorMenu'):
            self.iface.removePluginVectorMenu(u"&Multiple Distance Buffer",
                                                               self.action)
        else:
            self.iface.removePluginMenu(u"&Multiple Distance Buffer",
                                                         self.action)
        if hasattr(self.iface, 'removeVectorToolBarIcon'):
            self.iface.removeVectorToolBarIcon(self.action)
        else:
            self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        layers = QgsMapLayerRegistry.instance().mapLayers()
        layerslist = []
        for id in layers.keys():
            if layers[id].type() == 0:  # 0: Vector Layer
                layerslist.append((layers[id].name(), id))
        if len(layerslist) == 0 or len(layers) == 0:
            QMessageBox.information(None,
               QCoreApplication.translate('MultiDistanceBuffer',
                                                'Information'),
               QCoreApplication.translate('MultiDistanceBuffer',
                                      'Vector layers not found'))
            return
        self.dlg.iface = self.iface
        self.dlg.progressBar.setValue(0.0)

        # Add the layers to the layers combobox
        self.dlg.inputLayer.clear()
        for layerdescription in layerslist:
            self.dlg.inputLayer.addItem(layerdescription[0],
                                        layerdescription[1])
        self.dlg.outputLayerName.setText('buffer')

        # show the dialog
        self.dlg.show()
