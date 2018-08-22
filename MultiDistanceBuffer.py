# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer
                                 A QGIS plugin

                              -------------------
        begin                : 2015-02-05
        copyright            : (C) 2015-2018 by Håvard Tveite
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
from qgis.core import QgsProject, QgsMapLayer, QgsWkbTypes
from qgis.PyQt.QtCore import QSettings, QCoreApplication
from qgis.PyQt.QtCore import QTranslator, qVersion
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .MultiDistanceBuffer_gui import MultiDistanceBufferDialog


class MultiDistanceBuffer:

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # plugin directory
        pluginPath = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        localePath = os.path.join(
            pluginPath,
            'i18n',
            '{}.qm'.format(locale))
        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)
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
            QIcon(":/plugins/MultiDistanceBuffer/multidistbuff.png"),
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
        layers = QgsProject.instance().mapLayers()
        layerslist = []
        for id in layers.keys():
            if layers[id].type() == QgsMapLayer.VectorLayer:
                if not layers[id].isValid():
                    QMessageBox.information(None,
                        self.tr('Information'),
                        'Layer ' + layers[id].name() + ' is not valid')
                if layers[id].wkbType() != QgsWkbTypes.NoGeometry:
                    layerslist.append((layers[id].name(), id))
        if len(layerslist) == 0 or len(layers) == 0:
            QMessageBox.information(None,
               self.tr('Information'),
               self.tr('Vector layers not found'))
            return
        self.dlg.iface = self.iface
        self.dlg.progressBar.setValue(0.0)

        # Sort the layers by name
        layerslist.sort(key=lambda x: x[0], reverse=False)
        # Add the layers to the layers combobox
        self.dlg.inputLayer.clear()
        for layerdescription in layerslist:
            self.dlg.inputLayer.addItem(layerdescription[0],
                                        layerdescription[1])
        self.dlg.outputLayerName.setText('buffer')

        # show the dialog
        self.dlg.show()
