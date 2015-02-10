# -*- coding: utf-8 -*-

import os, glob
import sys
import tempfile
import uuid
from os.path import dirname
from os.path import join
from PyQt4 import uic
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from qgis.gui import *
import pickle
from math import *
import os
import csv
import webbrowser

from MultiDistanceBuffer_engine import Worker

FORM_CLASS, _ = uic.loadUiType(join(
    dirname(__file__), 'ui_multidistancebuffer.ui'))

class MultiDistanceBufferDialog(QDialog, FORM_CLASS):
#class MultiDistanceBufferDialog(QDialog, FORM_CLASS):
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
        cancelButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        cancelButton.setText(self.CANCEL)
        closeButton = self.buttonBox.button(QDialogButtonBox.Close)
        closeButton.setText(self.CLOSE)
        # Connect the user interface signals        
        QObject.connect(self.addButton,SIGNAL("clicked()"), self.addDistance)
        QObject.connect(self.removeButton,SIGNAL("clicked()"), self.removeDistance)
        QObject.connect(self.bufferSB,SIGNAL("editingFinished()"), self.addDistanceEnter)
        # Connect the buttons in the buttonbox
        okButton.clicked.connect(self.startWorker)
        cancelButton.clicked.connect(self.killWorker)
        closeButton.clicked.connect(self.reject)
        # Initialise the model for the QListView
        self.listModel = QStandardItemModel(self.bufferList)
        self.bufferList.setModel(self.listModel)
        self.bufferList.sizeHintForColumn(20)
        self.tmpdir = tempfile.gettempdir()
        # Temporary file prefix, for easy removal of temporary files:
        self.tempfilepathprefix = self.tmpdir + '/MDBtemp'
        self.layercopypath = self.tempfilepathprefix + 'copy.shp'
        #self.resultpath = self.tmpdir + '/MDBresult.shp'

    def startWorker(self):
        if self.bufferSB.hasFocus():
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
        self.showInfo('uuid: ' + str(uuid.uuid4()))
        bufferdistances = []
        for i in range(self.listModel.rowCount()):
            bufferdistances.append(float(self.listModel.item(i).text()))
        outputlayername = self.outputLayerName.text()
        tempfilepathprefix = self.tempfilepathprefix
        QgsMessageLog.logMessage('Starting worker: ' +
                                 str(bufferdistances),
                                 self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.INFO)
        worker = Worker(layercopy, self.layercopypath, bufferdistances, outputlayername, selectedonly, tempfilepathprefix)
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
        
    
    def workerFinished(self, ok, ret):
        """Handles the output from the worker and cleans up after the
           worker has finished."""
        # clean up the worker and thread
        self.worker.deleteLater()
        self.thread.quit()
        self.thread.wait()
        self.thread.deleteLater()
        # Remove temporary files (errors out on Windows - used by another process)
        try:
            copypattern = self.tempfilepathprefix + '*'
            tmpfiles = glob.glob(copypattern)
            for tmpfile in tmpfiles:
                os.remove(tmpfile)
        except:
            QgsMessageLog.logMessage('Info: Unable to delete temporary files...',
                                self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)

        if ok and ret is not None:
            # report the result
            result_layer = ret
            QgsMessageLog.logMessage(self.tr('MultiDistanceBuffer finished'),
                                     self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)
            result_layer.dataProvider().updateExtents()
            result_layer.commitChanges()
            self.layerlistchanging = True
            result_layer.removeSelection()
            QgsMapLayerRegistry.instance().addMapLayer(result_layer)
            result_layer = None
            self.layerlistchanging = False
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
        
    def workerError(self, exception_string):
        """Report an error from the worker."""
        #QgsMessageLog.logMessage(self.tr('Worker failed - exception') +
        #                         ': ' + str(exception_string), self.MULTIDISTANCEBUFFER,
        #                         QgsMessageLog.CRITICAL)
        self.showError(exception_string)

    def workerInfo(self, message_string):
        """Report an info message from the worker."""
        QgsMessageLog.logMessage(self.tr('Worker') + ': ' + message_string,
                                 self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)

    def killWorker(self):
        """Kill the worker thread."""
        if self.worker is not None:
            QgsMessageLog.logMessage(self.tr('Killing worker'),
                                     self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)
            self.worker.kill()

    def showError(self, text):
        """Show an error."""
        QgsMessageLog.logMessage('Error: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.CRITICAL)

    def showWarning(self, text):
        """Show a warning."""
        QgsMessageLog.logMessage('Warning: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.WARNING)

    def showInfo(self, text):
        """Show info."""
        QgsMessageLog.logMessage('Info: ' + text, self.MULTIDISTANCEBUFFER,
                                 QgsMessageLog.INFO)

    def reject(self):
        """Reject override."""
        # exit the dialog
        # Remove temporary files (errors out on Windows - used by another process)
        try:
            copypattern = self.tempfilepathprefix + '*'
            tmpfiles = glob.glob(copypattern)
            for tmpfile in tmpfiles:
                os.remove(tmpfile)
        except:
            QgsMessageLog.logMessage('Info: Unable to delete temporary files...',
                                self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)
        QDialog.reject(self)

    def addDistance(self):
        for i in range(self.listModel.rowCount()):
            # Check if the value is already in the list
            if self.listModel.item(i).text() == str(self.bufferSB.value()):
                #QgsMessageLog.logMessage('Add Distance: Duplicate ' +
                #                      self.listModel.item(i).text(),
                #                      self.MULTIDISTANCEBUFFER,
                #                      QgsMessageLog.INFO)
                return
            else:
                # Maintain a sorted list of distances
                if float(self.listModel.item(i).text()) > float(str(self.bufferSB.value())):
                    item = QStandardItem(str(self.bufferSB.value()))
                    self.listModel.insertRow(i, item)
                    return
        item = QStandardItem(str(self.bufferSB.value()))
        self.listModel.appendRow(item)

    def addDistanceEnter(self):
        # Check that the spinbox has not lost focus - then we can
        # "accept" the editingFinished signal
        if not self.bufferSB.hasFocus():
            #QgsMessageLog.logMessage('Add Distance Enter: No Focus',
            #               self.MULTIDISTANCEBUFFER, QgsMessageLog.INFO)
            return
        for i in range(self.listModel.rowCount()):
            # Check if the value is already in the list
            if self.listModel.item(i).text() == str(self.bufferSB.value()):
                #QgsMessageLog.logMessage('Add Distance Enter: Duplicate ' +
                #        self.listModel.item(i).text(), self.MULTIDISTANCEBUFFER,
                #        QgsMessageLog.INFO)
                return
            else:
                # Maintain a sorted list of distances
                if float(self.listModel.item(i).text()) > float(str(self.bufferSB.value())):
                    item = QStandardItem(str(self.bufferSB.value()))
                    self.listModel.insertRow(i, item)
                    return
        item = QStandardItem(str(self.bufferSB.value()))
        self.listModel.appendRow(item)

    def removeDistance(self):
        self.bufferList.setUpdatesEnabled(False);
        indexes = self.bufferList.selectedIndexes();
        indexes.sort();
        for i in range(len(indexes)-1, -1, -1):
            self.listModel.removeRow(indexes[i].row());
        self.bufferList.setUpdatesEnabled(True);

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        return QCoreApplication.translate('MultiDistanceBufferDialog', message)
