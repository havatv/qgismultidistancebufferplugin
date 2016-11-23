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
import os.path
# Import the PyQt and QGIS libraries
from qgis.core import QgsMapLayerRegistry, QgsMapLayer, QGis
from PyQt4.QtCore import QFileInfo, QSettings, QCoreApplication
from PyQt4.QtGui import QAction, QIcon
# Initialize Qt resources from file resources.py
import sys
sys.path.append(os.path.dirname(__file__))
import resources_rc
# Import the code for the dialog
from MultiDistanceBuffer_gui import MultiDistanceBufferDialog


class MultiDistanceBuffer:

    def __init__(self, iface):
        # Save reference to the QGIS interface
        self.iface = iface
        pluginPath = QFileInfo(os.path.realpath(__file__)).path()
        # initialize locale using the QGIS locale
        locale = QSettings().value('locale/userLocale')[0:2]
        if QFileInfo(pluginPath).exists():
            self.localePath = os.path.join(
               pluginPath,
               'i18n',
               '{}.qm'.format(locale))
        # initialize locale
        #localeName = QLocale.system().name()
        #if QFileInfo(pluginPath).exists():
        #    self.localePath = (pluginPath + "/i18n/multidistancebuffer_"
        #                       + localeName + ".qm")
        if QFileInfo(self.localePath).exists():
            self.translator = QTranslator()
            self.translator.load(self.localePath)
            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        # Create the dialog and keep reference
        self.dlg = MultiDistanceBufferDialog(self.iface)
        self.menu = self.tr(u'&Multiple Distance Buffer')

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('MultiDistanceBuffer', message)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/MultiDistanceBuffer/icon.png"),
            u"MultiDistanceBuffer", self.iface.mainWindow())
        # connect the action to the run method
        self.action.triggered.connect(self.run)
        # Add toolbar button
        if hasattr(self.iface, 'addVectorToolBarIcon'):
            self.iface.addVectorToolBarIcon(self.action)
        else:
            self.iface.addToolBarIcon(self.action)
        # Add menu item
        if hasattr(self.iface, 'addPluginToVectorMenu'):
            self.iface.addPluginToVectorMenu(self.menu, self.action)
        else:
            self.iface.addPluginToMenu(self.menu, self.action)

    def unload(self):
        # Remove the plugin menu item
        if hasattr(self.iface, 'removePluginVectorMenu'):
            self.iface.removePluginVectorMenu(self.menu, self.action)
        else:
            self.iface.removePluginMenu(self.menu, self.action)
        # Remove the plugin toolbar icon
        if hasattr(self.iface, 'removeVectorToolBarIcon'):
            self.iface.removeVectorToolBarIcon(self.action)
        else:
            self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        layers = QgsMapLayerRegistry.instance().mapLayers()
        layerslist = []
        for id in layers.keys():
            if layers[id].type() == QgsMapLayer.VectorLayer:
                if layers[id].wkbType() != QGis.WKBNoGeometry:
                    layerslist.append((layers[id].name(), id))
        if len(layerslist) == 0 or len(layers) == 0:
            QMessageBox.information(None,
               self.tr('Information'),
               self.tr('Vector layers not found'))
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
