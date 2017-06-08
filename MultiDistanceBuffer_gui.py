# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer_gui

                             -------------------
        begin                : 2014-09-04
        git sha              : $Format:%H$
        copyright            : (C) 2015-2017 by Håvard Tveite
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
#import datetime # Testing... ???
import os
import glob
import tempfile
import uuid
from os.path import dirname, join
from PyQt4 import uic
from PyQt4.QtCore import QCoreApplication, QObject, QThread
from PyQt4.QtGui import QDialog, QDialogButtonBox, QStandardItem
from PyQt4.QtGui import QStandardItemModel
from qgis.core import QgsMessageLog
from qgis.core import QgsMapLayerRegistry, QGis
from qgis.core import QgsVectorFileWriter, QgsVectorLayer
from qgis.utils import showPluginHelp

from MultiDistanceBuffer_engine import Worker

FORM_CLASS, _ = uic.loadUiType(join(
    dirname(__file__), 'ui_multidistancebuffer.ui'))


class MultiDistanceBufferDialog(QDialog, FORM_CLASS):
    def __init__(self, iface, parent=None):
        self.iface = iface
        self.plugin_dir = dirname(__file__)
        # Some translated text (to enable reuse)
        self.MULTIDISTANCEBUFFER = self.tr('MultiDistanceBuffer')
        self.CANCEL = self.tr('Cancel')
        self.HELP = self.tr('Help')
        self.CLOSE = self.tr('Close')
        #self.HELP = self.tr('Help')
        self.OK = self.tr('OK')
        super(MultiDistanceBufferDialog, self).__init__(parent)
        self.setupUi(self)
        # Initialise som local variables and set translations
        okButton = self.buttonBox.button(QDialogButtonBox.Ok)
        okButton.setText(self.OK)
        okButton.setEnabled(False)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.cancelButton.setText(self.CANCEL)
        self.cancelButton.setEnabled(False)
        helpButton = self.helpButton
        helpButton.setText(self.HELP)
        closeButton = self.buttonBox.button(QDialogButtonBox.Close)
        closeButton.setText(self.CLOSE)
        self.removeButton.setEnabled(False)
        self.clearButton.setEnabled(False)

        # Connect the user interface signals
        self.addButton.clicked.connect(self.addDistanceClick)
        self.addringsButton.clicked.connect(self.addRings)
        self.removeButton.clicked.connect(self.removeDistance)
        self.clearButton.clicked.connect(self.clearDistances)
        self.bufferSB.editingFinished.connect(self.addDistanceEnter)
        # Connect the buttons in the buttonbox
        okButton.clicked.connect(self.startWorker)
        #cancelButton.clicked.connect(self.killWorker)
        helpButton.clicked.connect(self.giveHelp)
        closeButton.clicked.connect(self.reject)
        # Add handler for layer selection
        self.inputLayer.currentIndexChanged.connect(self.layerSelectionChanged)
        # Initialise the model for the QListView
        self.listModel = QStandardItemModel(self.bufferList)
        self.bufferList.setModel(self.listModel)
        self.bufferList.sizeHintForColumn(20)
        blSelModel = self.bufferList.selectionModel()
        blSelModel.selectionChanged.connect(self.distanceSelectionChanged)
        self.workerlayername = 'mdblayer'
        self.tmpdir = tempfile.gettempdir()
        # Temporary file prefix, for easy removal of temporary files:
        self.tempfilepathprefix = self.tmpdir + '/MDBtemp'
        self.layercopypath = self.tempfilepathprefix + 'copy.shp'
    # end of __init__

    def startWorker(self):
        if self.bufferSB.hasFocus():
            return
        # Return if there are no buffer distances specified
        if self.listModel.rowCount() == 0:
            return
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        inputlayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        # Should only selected features be considered
        selectedonly = self.selectedOnlyCB.isChecked()
        if selectedonly and inputlayer.selectedFeatureCount() == 0:
            self.showWarning(self.tr("The layer has no selected features!"))
            return
        # Make a copy of the input data set
        # (considering selected features or not)
        error = QgsVectorFileWriter.writeAsVectorFormat(inputlayer,
                self.layercopypath, inputlayer.dataProvider().encoding(),
                inputlayer.crs(), "ESRI Shapefile",
                selectedonly)
        if error:
            self.showWarning("Copying the input layer failed! ("
                             + str(error) + ")")
            return
        error = None
        layercopy = QgsVectorLayer(self.layercopypath, "copy", "ogr")
        # Check if the geometries of the layer are valid
        valid = True
        for feature in layercopy.getFeatures():
            if not feature.isValid():
                valid = False
        if valid is False:
            self.showWarning("The layer has invalid features!")
        bufferdistances = []
        for i in range(self.listModel.rowCount()):
            bufferdistances.append(float(self.listModel.item(i).text()))
        segments = 0
        deviation = 0.0
        if self.segmentsRB.isChecked():
            segments = self.segmentsSB.value()
        if self.deviationRB.isChecked():
            deviation = self.deviationSB.value()
        if self.standardRB.isChecked():
            # Standard means segments to approximate with 5 segments
            segments = 5

        #self.showInfo('Starting worker: ' + str(bufferdistances))
        worker = Worker(layercopy, self.layercopypath, bufferdistances,
                      self.workerlayername, selectedonly,
                      segments, deviation)
        thread = QThread(self)
        worker.progress.connect(self.progressBar.setValue)
        worker.status.connect(self.workerInfo)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        self.cancelButton.clicked.connect(worker.kill)  # Before movetothread!
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.moveToThread(thread)  # Before thread.started.connect!
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)  # Useful?
        #worker.error.connect(worker.deleteLater)
        #worker.error.connect(thread.quit)
        thread.start()
        self.thread = thread
        self.worker = worker  # QT requires this
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(True)
        layercopy = None
    # end of startWorker

    def workerFinished(self, ok, ret):
        """Handles the output from the worker, adds the generated
           layer to the legend and cleans up after the worker has
           finished."""
        ## clean up the worker and thread
        #self.worker.deleteLater()
        #self.thread.quit()
        #self.thread.wait()
        #self.thread.deleteLater()
        # For some reason, there are problems with selection
        # highlighting if the returned memory layer is added.  To
        # avoid this, a new memory layer is created and features are
        # copied there"""

        if ok and ret is not None:
            # get the name of the outputlayer
            outputlayername = self.outputLayerName.text()
            # report the result
            result_layer = ret
            #result_layer.setName(outputlayername) # 2.14
            #result_layer.setLayerName(outputlayername) # from QGIS 2.16
            self.showInfo(self.tr('MultiDistanceBuffer completed'))
            #self.layerlistchanging = True
            # Create a (memory) copy of the result layer
            layeruri = 'Polygon?'
            # A coordinate reference system apparently needs to be
            # specified here in order to avoid the select CRS
            # dialogue.
            # Use PROJ4 as it should be available for all layers
            crstext = "PROJ4:%s" % result_layer.crs().toProj4()
            layeruri = (layeruri + 'crs=' + crstext)
            resultlayercopy = QgsVectorLayer(layeruri, outputlayername,
                                                              "memory")
            # Set the CRS to the original CRS object
            resultlayercopy.setCrs(result_layer.crs())
            resfields = result_layer.dataProvider().fields()
            for field in resfields:
                resultlayercopy.dataProvider().addAttributes([field])
            resultlayercopy.updateFields()
            for feature in result_layer.getFeatures():
                resultlayercopy.dataProvider().addFeatures([feature])
            resultlayercopy.commitChanges()  # should not be necessary
            resultlayercopy.updateExtents()
            resultlayercopy.reload()
            QgsMapLayerRegistry.instance().addMapLayer(resultlayercopy)
            self.iface.mapCanvas().refresh()
            result_layer = None
            resultlayercopy = None
            #self.layerlistchanging = False
        else:
            # notify the user that something went wrong
            if not ok:
                self.showError(self.tr('Aborted') + '!')
            else:
                self.showError(self.tr('No layer created') + '!')
        self.progressBar.setValue(0.0)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(False)
    # end of workerFinished

    def workerError(self, exception_string):
        """Report an error from the worker."""
        self.showError(self.tr('Worker failed - exception: ') +
                       exception_string)
    # end of workerError

    def workerInfo(self, message_string):
        """Report an info message from the worker."""
        self.showInfo(self.tr('Worker: ') + message_string)
    # end of workerInfo

    def killWorker(self):
        """Kill the worker thread."""
        #if self.worker is not None:
        #    self.showInfo('Killing worker')
        #    self.worker.kill()
    # end of killWorker

    def showError(self, text):
        """Show an error."""
        QgsMessageLog.logMessage('Error: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.CRITICAL)
    # end of showError

    def showWarning(self, text):
        """Show a warning."""
        QgsMessageLog.logMessage('Warning: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.WARNING)
    # end of showWarning

    def showInfo(self, text):
        """Show info."""
        QgsMessageLog.logMessage('Info: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.INFO)
    # end of showInfo

    def giveHelp(self):
        #QDesktopServices.openUrl(QUrl.fromLocalFile(
        #                 self.plugin_dir + "/help/html/index.html"))
        showPluginHelp(None, "help/html/index")
    # end of giveHelp

    def reject(self):
        """Reject override."""
        # exits the dialog
        self.listModel.clear()
        QDialog.reject(self)
    # end of reject

    def addDistance(self, buffdist):
        # Event handler - add (distance) button pressed
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        thelayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if thelayer is None:
            return
        # 0.0 is only meaningful for polygons
        if (buffdist == 0.0
            and not thelayer.geometryType() == QGis.Polygon):
            self.showInfo(
                self.tr('Buffer radius 0 is only accepted for polygons'))
            return
        for i in range(self.listModel.rowCount()):
            # Check if the value is already in the list
            if self.listModel.item(i).text() == str(buffdist):
                return
            else:
                # Maintain a sorted list of distances
                if (float(self.listModel.item(i).text()) > buffdist):
                    item = QStandardItem(str(buffdist))
                    self.listModel.insertRow(i, item)
                    return
        item = QStandardItem(str(buffdist))
        self.listModel.appendRow(item)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
        self.clearButton.setEnabled(True)
    # end of addDistance

    def addDistanceClick(self):
        # Event handler - add (buffer distance) button pressed
        buffdist = float(self.bufferSB.value())
        self.addDistance(buffdist)
    # end of addDistancePush

    def addDistanceEnter(self):
        # Event handler - enter pressed (buffer distance)
        # Check that the spinbox has not lost focus - then we can
        # "accept" the editingFinished signal
        if not self.bufferSB.hasFocus():
            return
        self.addDistanceClick()
    # end of addDistanceEnter

    def addRings(self):
        # Event handler - add (rings) button pressed
        start = float(self.startSB.value())
        delta = float(self.widthsSB.value())
        zones = int(self.ringsSB.value())
        for i in range(zones):
            buffdist = start + delta * float(i)
            self.addDistance(buffdist)
    # end of addRings

    def distanceSelectionChanged(self):
        # Event handler
        if (self.bufferList.selectedIndexes() is None or
            len(self.bufferList.selectedIndexes()) == 0):
            self.removeButton.setEnabled(False)
        else:
            self.removeButton.setEnabled(True)
    # end of distanceSelectionChanged

    def layerSelectionChanged(self):
        # Event handler - new layer selected
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        # We know that all the layers in inputLayer are valid vector layers
        thelayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if thelayer is None:
            return
        if thelayer.geometryType() == QGis.Polygon:
            # Allow negative buffer distances for polygon layers
            self.bufferSB.setMinimum(-999999999.0)
            self.startSB.setMinimum(-999999999.0)
        else:
            # Allow only positive buffer distances for point and line layers
            self.bufferSB.setMinimum(0.0)
            self.startSB.setMinimum(0.0)
            i = 0
            # Remove all 0 or negative buffer distance values
            while i < self.listModel.rowCount():
                if float(self.listModel.item(i).text()) <= 0.0:
                    self.listModel.removeRow(i)
                else:
                    i = i + 1
            if self.startSB.value() <= 0.0:
                self.startSB.setValue(100.0)

            # Disable the OK button if no buffer distances are specified
            if self.listModel.rowCount() == 0:
                self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        # Check if there is a selection and update the "use only
        # selected features" checkbox accordingly
        if thelayer.selectedFeatureCount() == 0:
            self.selectedOnlyCB.setChecked(False)
        else:
            self.selectedOnlyCB.setChecked(True)
    # end of layerSelectionChanged

    def removeDistance(self):
        # Event handler - remove (distance) button pressed
        self.bufferList.setUpdatesEnabled(False)
        indexes = self.bufferList.selectedIndexes()
        indexes.sort()
        for i in range(len(indexes) - 1, -1, -1):
            self.listModel.removeRow(indexes[i].row())
        self.bufferList.setUpdatesEnabled(True)
        if self.listModel.rowCount() == 0:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
            self.clearButton.setEnabled(False)
        self.removeButton.setEnabled(False)
    # end of removeDistance

    def clearDistances(self):
        # Event handler - clear (distance) button pressed
        self.bufferList.setUpdatesEnabled(False)
        self.listModel.removeRows(0, self.listModel.rowCount())
        self.bufferList.setUpdatesEnabled(True)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.removeButton.setEnabled(False)
        self.clearButton.setEnabled(False)
    # end of clearDistance

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('MultiDistanceBufferDialog', message)
