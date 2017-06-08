# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer_engine

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
#import datetime  # Testing... ???
#import time  # Testing ???
import math  # for beregning av segments to approximate
from qgis.core import QgsVectorLayer, QgsFeature
from qgis.core import QgsField, QgsGeometry
from qgis.analysis import QgsGeometryAnalyzer
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
                               outputlayername, selectedonly,
                               segments, deviation):
        """Initialise.

        Arguments:
        inputvectorlayer --     (QgsVectorLayer) The base vector
                                layer for the buffer.
        inputvectorlayerpath -- Path to the input vector data set
                                for the buffer.
        buffersizes --          array of floats, sorted asc.
        outputlayername --      Name of the output vector layer.
        selectedonly --         (boolean) Should only selected
                                features be buffered.  NOT USED!
        segments --             segments to approximate (apply if > 0).
        deviation --            maximum deviation (apply if > 0.0 and
                                not segments > 0).
        """

        QtCore.QObject.__init__(self)  # Essential!
        # Creating instance variables from the parameters
        self.inpvl = inputvectorlayer
        #self.inputpath = inputvectorlayerpath
        self.buffersizes = buffersizes
        self.outputlayername = outputlayername
        #self.selectedonly = selectedonly
        # Creating instance variables for the progress bar ++
        # Number of elements that have been processed - updated by
        # calculate_progress
        self.processed = 0
        # Current percentage of progress - updated by
        # calculate_progress
        self.percentage = 0
        # Number of buffer sizes - used by calculate_progress for
        # the standard method
        self.worktodo = len(self.buffersizes)
        # The number of elements that is needed to increment the
        # progressbar - set early in run()
        self.increment = self.worktodo // 1000
        # Flag set by kill(), checked in the loop
        self.abort = False
        # Distance attribute name
        self.distAttrName = 'distance'
        # Inner distance attribute name
        self.innerAttrName = 'inner'
        # Options
        self.segments = segments
        self.deviation = deviation
    # end of __init__

    # Should @pyqtSlot be used here?
    def run(self):
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
            # Add the distance attributes
            pr.addAttributes([QgsField(self.distAttrName, QVariant.Double)])
            pr.addAttributes([QgsField(self.innerAttrName, QVariant.Double)])
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
            buffergeomvector = []  # Not used by the "standard" method

            # Use feature increment for the non-"standard" methods
            if (self.segments > 0 or self.deviation > 0.0):
                self.worktodo = (layercopy.featureCount() *
                                 len(self.buffersizes))
                # The number of elements that is needed to increment the
                # progressbar - set early in run()
                self.increment = self.worktodo // 1000

            # Do the buffering (order: smallest to largest distances):
            j = 0
            prevdist = None
            for dist in self.buffersizes:
                if self.abort is True:
                    break
                self.status.emit(self.tr('Doing buffer distance ') +
                         str(dist) + '... '
                         #+str(datetime.datetime.now().strftime('%H:%M:%S.%f'))
                         )

                # Determine which buffer variant to use
                if (self.segments > 0):
                    segments = self.segments
                    #self.status.emit("Segments")
                else:
                    tolerance = self.deviation
                    # Calculate the number of segments per quarter circle
                    segments = 5
                    if dist != 0.0:
                        segments = int(math.pi / (4.0 * math.acos(1.0 -
                                   (tolerance / float(abs(dist)))))) + 1
                segments = max(segments, 1)
                multigeom = QgsGeometry()
                # Go through the features and buffer and combine the
                # feature geometries
                i = 0
                for feat in layercopy.getFeatures():
                    bgeom = feat.geometry().buffer(dist, segments)
                    if i == 0:
                        multigeom = bgeom
                    else:
                        multigeom = multigeom.combine(bgeom)
                    i = i + 1
                    self.calculate_progress()
                    if self.abort is True:
                        break
                buffergeomvector.append(multigeom)

                # Compute the donut and add it to the result dataset
                newgeom = None
                if j == 0:     # Just add the innermost buffer
                    newgeom = buffergeomvector[j]
                else:
                    # Get the donut by subtracting the inner ring
                    # from this ring
                    outergeom = buffergeomvector[j]
                    innergeom = buffergeomvector[j - 1]
                    newgeom = outergeom.symDifference(innergeom)
                newfeature = QgsFeature()
                newfeature.setGeometry(newgeom)
                newfeature.setAttributes([dist, prevdist])
                memresult.dataProvider().addFeatures([newfeature])
                j = j + 1
                prevdist = dist
            #self.status.emit(self.tr('Finished with buffer ')
            #  + str(datetime.datetime.now().strftime('%H:%M:%S.%f')))

            # Update the layer extents (after adding features)
            memresult.updateExtents()
            memresult.reload()
            # Remove references
            layercopy = None
            for buffgeom in buffergeomvector:
                buffgeom = None
            buffergeomvector = None
        except:
            # Remove references
            layercopy = None
            import traceback
            self.error.emit(traceback.format_exc())
            self.finished.emit(False, None)
            for buffgeom in buffergeomvector:
                buffgeom = None
            buffergeomvector = None
        else:
            if self.abort is True:
                self.finished.emit(False, None)
            else:
                if memresult is not None:
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
        self.status.emit("Worker told to abort")
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
