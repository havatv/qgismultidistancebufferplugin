# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer_gui

                             -------------------
        begin                : 2014-09-04
        git sha              : $Format:%H$
        copyright            : (C) 2015-2016 by Håvard Tveite
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
import os
import glob
import tempfile
import uuid
from os.path import dirname, join
from qgis.core import QgsMapLayerRegistry, QgsMessageLog
from qgis.core import QgsWkbTypes
from qgis.core import QgsVectorFileWriter, QgsVectorLayer
from PyQt5 import uic
from PyQt5.QtCore import QCoreApplication, QObject, QThread
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QDialog, QDialogButtonBox

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
        self.CLOSE = self.tr('Close')
        #self.HELP = self.tr('Help')
        self.OK = self.tr('OK')
        super(MultiDistanceBufferDialog, self).__init__(parent)
        self.setupUi(self)
        # Initialise som local variables and set translations
        okButton = self.buttonBox.button(QDialogButtonBox.Ok)
        okButton.setText(self.OK)
        okButton.setEnabled(False)
        cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        cancelButton.setText(self.CANCEL)
        cancelButton.setEnabled(False)
        closeButton = self.buttonBox.button(QDialogButtonBox.Close)
        closeButton.setText(self.CLOSE)
        self.removeButton.setEnabled(False)
        # Connect the user interface signals
        self.addButton.clicked.connect(self.addDistance)
        self.removeButton.clicked.connect(self.removeDistance)
        self.bufferSB.editingFinished.connect(self.addDistanceEnter)
        # Connect the buttons in the buttonbox
        okButton.clicked.connect(self.startWorker)
        cancelButton.clicked.connect(self.killWorker)
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
        self.layercrs = None  # The CRS of the layer
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
        # Get the layer CRS
        self.layercrs = inputlayer.crs()
        # Should only selected features be considered
        selectedonly = self.selectedOnlyCB.isChecked()
        if selectedonly and inputlayer.selectedFeatureCount() == 0:
            self.showWarning("The layer has no selected features!")
            return
        # Make a copy of the input data set
        # (considering selected features or not)
        # "None": no crs reprojection
        error = QgsVectorFileWriter.writeAsVectorFormat(inputlayer,
                self.layercopypath, inputlayer.dataProvider().encoding(),
                self.layercrs, "ESRI Shapefile",
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
        self.showInfo('Starting worker: ' + str(bufferdistances))
        worker = Worker(layercopy, self.layercopypath, bufferdistances,
                      self.workerlayername, selectedonly,
                      self.tempfilepathprefix)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.finished.connect(self.workerFinished)
        worker.error.connect(self.workerError)
        worker.status.connect(self.workerInfo)
        worker.progress.connect(self.progressBar.setValue)
        thread.started.connect(worker.run)
        thread.start()
        self.thread = thread
        self.worker = worker
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.Cancel).setEnabled(True)
        layercopy = None
    # end of startWorker

    def workerFinished(self, ok, ret):
        """Handles the output from the worker and cleans up after the
           worker has finished.
           Makes a copy of the returned layer to fix selection issues"""
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # Remove temporary files
        try:
            copypattern = self.tempfilepathprefix + '*'
            tmpfiles = glob.glob(copypattern)
            for tmpfile in tmpfiles:
                os.remove(tmpfile)
        except:
            self.showInfo(self.tr('Unable to delete temporary files...'))
        if ok and ret is not None:
            # get the name of the outputlayer
            outputlayername = self.outputLayerName.text()
            # report the result
            result_layer = ret
            #QgsMapLayerRegistry.instance().addMapLayer(result_layer)
            self.showInfo(self.tr('MultiDistanceBuffer finished'))
            self.layerlistchanging = True
            self.layerlistchanging = False
            # Create a (memory) copy of the result layer
            layeruri = 'Polygon?'
            # Coordinate reference system needs to be specified
            # Use PROJ4 as it should be available for all layers
            crstext = "PROJ4:%s" % self.layercrs.toProj4()
            layeruri = (layeruri + 'crs=' + crstext)
            resultlayercopy = QgsVectorLayer(layeruri, outputlayername,
                                                              "memory")
            resfields = result_layer.dataProvider().fields()
            for field in resfields:
                resultlayercopy.dataProvider().addAttributes([field])
            resultlayercopy.updateFields()
            # If EPSG is not available, set the CRS to the original one,
            # just in case
            if str(resultlayercopy.crs().authid())[:5] != 'EPSG:':
                resultlayercopy.setCrs(self.layercrs)
            QgsMapLayerRegistry.instance().addMapLayer(resultlayercopy)
            for feature in result_layer.getFeatures():
                resultlayercopy.dataProvider().addFeatures([feature])
            resultlayercopy.updateExtents()
            resultlayercopy.reload()
            self.iface.mapCanvas().refresh()
            result_layer = None
            resultlayercopy = None
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
        #self.close()
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
        if self.worker is not None:
            self.showInfo('Killing worker')
            self.worker.kill()
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

    def reject(self):
        """Reject override."""
        # exit the dialog
        # Remove temporary files
        try:
            copypattern = self.tempfilepathprefix + '*'
            tmpfiles = glob.glob(copypattern)
            for tmpfile in tmpfiles:
                os.remove(tmpfile)
        except:
            self.showInfo('Unable to delete temporary files...')
        self.listModel.clear()
        QDialog.reject(self)
    # end of reject

    def addDistance(self):
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        thelayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if thelayer is None:
            return
        # 0.0 is only meaningful for polygons
        if (float(self.bufferSB.value()) == 0.0
            and not thelayer.geometryType() == QgsWkbTypes.PolygonGeometry):
            self.showInfo('Buffer radius 0 is not accepted')
            return
        for i in range(self.listModel.rowCount()):
            # Check if the value is already in the list
            if self.listModel.item(i).text() == str(self.bufferSB.value()):
                return
            else:
                # Maintain a sorted list of distances
                if (float(self.listModel.item(i).text()) >
                                 float(str(self.bufferSB.value()))):
                    item = QStandardItem(str(self.bufferSB.value()))
                    self.listModel.insertRow(i, item)
                    return
        item = QStandardItem(str(self.bufferSB.value()))
        self.listModel.appendRow(item)
        self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
    # end of addDistance

    def addDistanceEnter(self):
        # Check that the spinbox has not lost focus - then we can
        # "accept" the editingFinished signal
        if not self.bufferSB.hasFocus():
            return
        self.addDistance()
    # end of addDistanceEnter

    def distanceSelectionChanged(self):
        if (self.bufferList.selectedIndexes() is None or
            len(self.bufferList.selectedIndexes()) == 0):
            self.removeButton.setEnabled(False)
        else:
            self.removeButton.setEnabled(True)
    # end of distanceSelectionChanged

    def layerSelectionChanged(self):
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        # We know that all the layers in inputLayer are valid vector layers
        thelayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        if thelayer is None:
            return
        if thelayer.geometryType() == QgsWkbTypes.PolygonGeometry:
            # Allow negative buffer distances for polygon layers
            self.bufferSB.setMinimum(-999999999.0)
        else:
            # Allow only positive buffer distances for point and line layers
            self.bufferSB.setMinimum(0.0)
            i = 0
            # Remove all negative buffer distance values
            while i < self.listModel.rowCount():
                if float(self.listModel.item(i).text()) < 0.0:
                    self.listModel.removeRow(i)
                else:
                    i = i + 1
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
        self.bufferList.setUpdatesEnabled(False)
        indexes = self.bufferList.selectedIndexes()
        indexes.sort()
        for i in range(len(indexes) - 1, -1, -1):
            self.listModel.removeRow(indexes[i].row())
        self.bufferList.setUpdatesEnabled(True)
        if self.listModel.rowCount() == 0:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        self.removeButton.setEnabled(False)
    # end of removeDistance

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('MultiDistanceBufferDialog', message)
