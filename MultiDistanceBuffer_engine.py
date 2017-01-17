# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer_engine

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
from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QGis
from qgis.core import QgsVectorLayer, QgsFeature, QgsSpatialIndex
from qgis.core import QgsFeatureRequest, QgsField, QgsGeometry
from qgis.core import QgsRectangle, QgsCoordinateTransform
from qgis.core import QgsMapLayer, QgsExpression, QgsVectorFileWriter
from qgis.analysis import QgsGeometryAnalyzer, QgsOverlayAnalyzer
from PyQt4 import QtCore
from PyQt4.QtCore import QCoreApplication, QVariant


class Worker(QtCore.QObject):
    '''The worker that does the heavy lifting.
    /* Leaves temporary files that should be deleted by the caller.
     * Removes all attributes of the input layer and adds a distance
     * attribute.
     *
    */
    '''
    # Define the signals used to communicate back to the application
    progress = QtCore.pyqtSignal(float)  # For reporting progress
    status = QtCore.pyqtSignal(str)      # For reporting status
    error = QtCore.pyqtSignal(str)       # For reporting errors
    # Signal for sending back the result:
    finished = QtCore.pyqtSignal(bool, object)

    def __init__(self, inputvectorlayer, inputvectorlayerpath, buffersizes,
                               outputlayername, selectedonly, tempfilepath):
        """Initialise.

        Arguments:
        inputvectorlayer --     (QgsVectorLayer) The base vector
                                layer for the buffer.
        inputvectorlayerpath -- Path to the input vector data set
                                for the buffer.
        buffersizes --          array of floats, sorted asc.
        outputlayername --      Name of the output vector layer.
        selectedonly --         (boolean) Should only selected
                                features be buffered.
        tempfilepath --         path to be used for temporary files
                                (all files with this prefix will be
                                deleted when the thread has finished.
        """

        QtCore.QObject.__init__(self)  # Essential!
        # Creating instance variables from the parameters
        self.inpvl = inputvectorlayer
        #self.inputpath = inputvectorlayerpath
        self.buffersizes = buffersizes
        self.outputlayername = outputlayername
        self.selectedonly = selectedonly
        self.tempfilepath = tempfilepath
        # Creating instance variables for the progress bar ++
        # Number of elements that have been processed - updated by
        # calculate_progress
        self.processed = 0
        # Current percentage of progress - updated by
        # calculate_progress
        self.percentage = 0
        # Number of features in the input layer - used by
        # calculate_progress
        self.worktodo = len(self.buffersizes)
        # The number of elements that is needed to increment the
        # progressbar - set early in run()
        self.increment = self.worktodo // 1000
        # Flag set by kill(), checked in the loop
        self.abort = False
        # Distance attribute name
        self.distAttrName = 'distance'
        # Directories and files
        self.tmpbuffbasename = self.tempfilepath + 'outbuff'
    # end of __init__

    # Should @pyqtSlot be used here?
    def run(self):
        bufferlayers = []
        try:
            layercopy = self.inpvl
            self.inpvl = None  # Remove the reference to the layer
            if layercopy is None:
                self.finished.emit(False, None)
                return
            pr = layercopy.dataProvider()
            # Remove all the existing attributes:
            while pr.deleteAttributes([0]):
                continue
            # Add the distance attribute
            pr.addAttributes([QgsField(self.distAttrName, QVariant.Double)])
            layercopy.updateFields()  # Commit the attribute changes
            # Create the memory layer for the results (have to specify a
            # CRS in order to avoid the select CRS dialogue)
            memresult = QgsVectorLayer('Polygon?crs=EPSG:4326',
                                       self.outputlayername, "memory")
            # Set the real CRS
            memresult.setCrs(layercopy.crs())
            # Add attributes to the memory layer
            for distfield in layercopy.dataProvider().fields().toList():
                memresult.dataProvider().addAttributes([distfield])
            memresult.updateFields()
            # Do the buffering (order: smallest to largest distances):
            j = 0
            for dist in self.buffersizes:
                if self.abort is True:
                    break
                self.status.emit(self.tr('Doing buffer distance ') +
                                 str(dist) + '...')
                outbuffername = self.tmpbuffbasename + str(dist) + '.shp'
                # The buffer operation (can only produce a Shapefile
                # format dataset)
                # parameters: layer, path to output data set,
                # distance, selected only, dissolve, attribute index
                ok = QgsGeometryAnalyzer().buffer(layercopy,
                                outbuffername, dist, False, True, -1)
                if not ok:
                    self.status.emit('The buffer operation failed!')
                blayername = 'buff' + str(dist)
                # Load the buffer data set
                bufflayer = QgsVectorLayer(outbuffername, blayername, "ogr")
                # Check if the buffer data set is empty
                if bufflayer.featureCount() == 0:
                    continue
                if bufflayer.featureCount() == 1:
                    thefeature = None
                    for f in bufflayer.getFeatures():
                        thefeature = f
                    if (not thefeature) or (thefeature.geometry() is None):
                        continue
                # Set the buffer distance attribute to the current distance
                for feature in bufflayer.getFeatures():
                    attrs = {0: dist}  # Set the value of the first attribute
                    bufflayer.dataProvider().changeAttributeValues(
                                           {feature.id(): attrs})
                bufferlayers.append(bufflayer)
                bufflayer = None
                # Calculate the current distance band
                if j == 0:     # The innermost buffer
                    for midfeature in bufferlayers[j].getFeatures():
                        memresult.dataProvider().addFeatures([midfeature])
                else:
                    for outerfeature in bufferlayers[j].getFeatures():
                        # Get the donut by subtracting the inner ring
                        # from this ring
                        outergeom = outerfeature.geometry()
                        for innerfeature in bufferlayers[j - 1].getFeatures():
                            innergeom = innerfeature.geometry()
                            newgeom = outergeom.symDifference(innergeom)
                            outergeom = newgeom
                        newfeature = QgsFeature()
                        newfeature.setGeometry(outergeom)
                        newfeature.setAttributes(outerfeature.attributes())
                        memresult.dataProvider().addFeatures([newfeature])
                self.calculate_progress()
                j = j + 1
            # Update the layer extents (after adding features)
            memresult.updateExtents()
            memresult.reload()
            # Remove references
            layercopy = None
            for outbufflayer in bufferlayers:
                outbufflayer = None
            outbufflayers = None
        except:
            # Remove references
            layercopy = None
            for outbufflayer in bufferlayers:
                outbufflayer = None
            outbufflayers = None
            import traceback
            self.error.emit(traceback.format_exc())
            self.finished.emit(False, None)
        else:
            if self.abort:
                self.finished.emit(False, None)
            else:
                if memresult is not None:
                    self.status.emit(self.tr('Delivering the layer...'))
                    self.finished.emit(True, memresult)
                    memresult = None
                else:
                    self.finished.emit(False, None)
    # end of run

    def calculate_progress(self):
        '''Update progress and emit a signal with the percentage'''
        self.processed = self.processed + 1
        # update the progress bar at certain increments
        if (self.increment == 0 or
                self.processed % self.increment == 0):
            perc_new = (self.processed * 100) / self.worktodo
            if perc_new > self.percentage:
                self.percentage = perc_new
                self.progress.emit(self.percentage)
    # end of calculate_progress

    def kill(self):
        '''Kill the thread by setting the abort flag'''
        self.abort = True
    # end of kill

    def tr(self, message):
        '''Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        '''
        # noinspection PyTypeChecker, PyArgumentList, PyCallByClass
        return QCoreApplication.translate('MultiDistanceBufferEngine', message)
    # end of tr
