# -*- coding: utf-8 -*-

import os
import glob
import tempfile
import uuid
from os.path import dirname, join
from qgis.core import QgsMapLayerRegistry, QgsMessageLog
from qgis.core import QgsVectorFileWriter, QgsVectorLayer
from PyQt4 import uic
from PyQt4.QtCore import QCoreApplication, QObject, SIGNAL, QThread
from PyQt4.QtGui import QDialog, QDialogButtonBox, QStandardItem
from PyQt4.QtGui import QStandardItemModel

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
        QObject.connect(self.addButton, SIGNAL("clicked()"),
                                            self.addDistance)
        QObject.connect(self.removeButton, SIGNAL("clicked()"),
                                            self.removeDistance)
        QObject.connect(self.bufferSB, SIGNAL("editingFinished()"),
                                              self.addDistanceEnter)
        # Connect the buttons in the buttonbox
        okButton.clicked.connect(self.startWorker)
        cancelButton.clicked.connect(self.killWorker)
        closeButton.clicked.connect(self.reject)
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
        selectedonly = self.selectedOnlyCB.isChecked()
        layerindex = self.inputLayer.currentIndex()
        layerId = self.inputLayer.itemData(layerindex)
        inputlayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        # Make a copy of the input layer (with selected features)
        error = QgsVectorFileWriter.writeAsVectorFormat(inputlayer,
                self.layercopypath, inputlayer.dataProvider().encoding(),
                None, "ESRI Shapefile", selectedonly)
        error = None
        layercopy = QgsVectorLayer(self.layercopypath, "copy", "ogr")
        bufferdistances = []
        for i in range(self.listModel.rowCount()):
            bufferdistances.append(float(self.listModel.item(i).text()))
        tempfilepathprefix = self.tempfilepathprefix
        self.showInfo('Starting worker: ' + str(bufferdistances))
        worker = Worker(layercopy, self.layercopypath, bufferdistances,
                      self.workerlayername, selectedonly, tempfilepathprefix)
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
            resultlayercopy = QgsVectorLayer(
                        "Polygon?crs=%s" % result_layer.crs().authid(),
                        outputlayername, "memory")
            resfields = result_layer.dataProvider().fields()
            for field in resfields:
                resultlayercopy.dataProvider().addAttributes([field])
            resultlayercopy.updateFields()
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
        QDialog.reject(self)
    # end of reject

    def addDistance(self):
        # 0.0 can not be accepted as a buffer distance
        if float(self.bufferSB.value()) == 0.0:
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
        if (self.bufferList.selectedIndexes() == None or
            len(self.bufferList.selectedIndexes()) == 0):
            self.removeButton.setEnabled(False)
        else:
            self.removeButton.setEnabled(True)
    # end of distanceSelectionChanged

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
