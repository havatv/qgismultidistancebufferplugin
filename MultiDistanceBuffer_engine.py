# -*- coding: utf-8 -*-
"""
/***************************************************************************
 MultiDistanceBuffer_engine

                             -------------------
        begin                : 2014-09-04
        git sha              : $Format:%H$
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
#from qgis.core import *
from qgis.core import QgsMessageLog, QgsMapLayerRegistry, QGis
from qgis.core import QgsVectorLayer, QgsFeature, QgsSpatialIndex
from qgis.core import QgsFeatureRequest, QgsField, QgsGeometry
from qgis.core import QgsRectangle, QgsCoordinateTransform
from qgis.core import QgsMapLayer, QgsExpression, QgsVectorFileWriter
from qgis.analysis import QgsGeometryAnalyzer, QgsOverlayAnalyzer
#from processing.core.Processing import Processing
#import processing
#from processing import *
from PyQt4 import QtCore
from PyQt4.QtCore import QCoreApplication, QVariant


class Worker(QtCore.QObject):
    '''The worker that does the heavy lifting.
    /*
     *
    */
    '''
    # Define the signals used to communicate back to the application
    progress = QtCore.pyqtSignal(float)  # For reporting progress
    status = QtCore.pyqtSignal(str)      # For reporting status
    error = QtCore.pyqtSignal(str)       # For reporting errors
    #killed = QtCore.pyqtSignal()
    # Signal for sending over the result:
    finished = QtCore.pyqtSignal(bool, object)

    def __init__(self, inputvectorlayer, inputvectorlayerpath, buffersizes,
                               outputlayername, selectedonly, tempfilepath):
        """Initialise.

        Arguments:
        inputvectorlayer -- (QgsVectorLayer) The base vector layer
                            for the buffer
        inputvectorlayerpath -- Path to the input vector data set
                            for the buffer
        buffersizes -- array of floats
        outputlayername -- Name of the output vector layer
        selectedonly -- (boolean) Should only selected features be
                        buffered
        tempfilepath -- path to be used for temporary files (all
                        files with this prefix will be deleted
                        when the thread has finished
        """

        QtCore.QObject.__init__(self)  # Essential!
        # Creating instance variables from the parameters
        self.inpvl = inputvectorlayer
        self.inputpath = inputvectorlayerpath
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
        # Flag set by kill(), checked in the loop
        self.abort = False
        # Number of features in the input layer - used by
        # calculate_progress
        self.worktodo = len(self.buffersizes)
        # The number of elements that is needed to increment the
        # progressbar - set early in run()
        self.increment = self.worktodo // 1000
        # Directories and files
        self.tmpbuffbasename = self.tempfilepath + 'outbuff'
        self.ringpath = self.tempfilepath + 'rings.shp'
    # end of __init__

    def run(self):
        try:
            #layercopy = QgsVectorLayer(self.inputpath, "layercopy", "ogr")
            layercopy = self.inpvl
            self.inpvl = None  # Remove the reference to the layer
            if layercopy is None:
                self.finished.emit(False, None)
                return
            pr = layercopy.dataProvider()
            # Delete all the attributes:
            while pr.deleteAttributes([0]):
                continue
            # Add the distance attribute
            pr.addAttributes([QgsField("distance", QVariant.Double)])
            layercopy.updateFields()  # Necessary also for provider
            # Do the buffering:
            outbuffers = []
            outbufferlayers = []
            j = 0
            for dist in self.buffersizes:
                if self.abort is True:
                    break
                self.status.emit('Buffering distance ' + str(dist) + '...')
                outbuffername = self.tmpbuffbasename + str(dist) + '.shp'
                # Do the buffer operation (can only produce a Shapefile
                #   format dataset)
                # parameters: layer, path to output data set,
                # distance, selected only, dissolve, attribute index
                ok = QgsGeometryAnalyzer().buffer(layercopy,
                                outbuffername, dist, False, True, -1)
                layername = 'buff' + str(dist)
                bufflayer = QgsVectorLayer(outbuffername, layername, "ogr")
                for feature in bufflayer.getFeatures():
                    attrs = {0: dist}
                    bufflayer.dataProvider().changeAttributeValues(
                                           {feature.id(): attrs})
                outbuffers.append(outbuffername)
                outbufferlayers.append(bufflayer)
                bufflayer = None
                # Calculate the ring (to be moved from below)
                #if j > 0:
                #
                #
                self.calculate_progress()
                j = j + 1
            # Make a copy for the rings
            error = QgsVectorFileWriter.writeAsVectorFormat(outbufferlayers[0],
                    self.ringpath,
                    outbufferlayers[0].dataProvider().encoding(),
                    None, "ESRI Shapefile")
            #ringlayer = QgsVectorLayer(self.ringpath, 'rings', "ogr")

            # Create a memory layer for the result:
            # Prepare the string describing the geometry
            layeruri = 'Polygon?'
            layeruri = (layeruri + 'crs=' +
                        str(outbufferlayers[0].dataProvider().crs().authid()))
            mem2result = QgsVectorLayer(layeruri, self.outputlayername,
                                                              "memory")
            for ringfield in outbufferlayers[0].dataProvider().fields().toList():
                mem2result.dataProvider().addAttributes([ringfield])
            mem2result.updateFields()
            self.status.emit('Merging')
            for j in reversed(range(len(outbufferlayers))):
                if j == 0:
                    for midfeature in outbufferlayers[j].getFeatures():
                        mem2result.dataProvider().addFeatures([midfeature])
                    #continue  # We already have the inner buffer included
                for outerfeature in outbufferlayers[j].getFeatures():
                    # Get the donut by subtracting the inner ring from this ring
                    outergeom = outerfeature.geometry()
                    for innerfeature in outbufferlayers[j - 1].getFeatures():
                        innergeom = innerfeature.geometry()
                        newgeom = outergeom.symDifference(innergeom)
                        outergeom = newgeom
                    newfeature = QgsFeature()
                    newfeature.setGeometry(outergeom)
                    newfeature.setAttributes(outerfeature.attributes())
                    #ringlayer.dataProvider().addFeatures([newfeature])
                    mem2result.dataProvider().addFeatures([newfeature])
            # Create a memory layer for the result:
            # Prepare the string describing the geometry
            #layeruri = 'Polygon?'
            #layeruri = (layeruri + 'crs=' +
            #            str(ringlayer.dataProvider().crs().authid()))
            #memresult = QgsVectorLayer(layeruri, self.outputlayername,
            #                                                  "memory")
            #for ringfield in ringlayer.dataProvider().fields().toList():
            #    memresult.dataProvider().addAttributes([ringfield])
            #memresult.updateFields()
            #for feature in ringlayer.getFeatures():
            #    fet = QgsFeature()
            #    fet.setGeometry(feature.geometry())
            #    fet.setAttributes(feature.attributes())
            #    memresult.dataProvider().addFeatures([fet])
            #memresult.updateExtents()
            mem2result.updateExtents()
            # Remove references
            outbufflayers = None
            #ringlayer = None
            layercopy = None
        except:
            # Remove references
            layercopy = None  # Remove the reference
            ringlayer = None
            outbufflayers = None
            import traceback
            self.error.emit(traceback.format_exc())
            self.finished.emit(False, None)
        else:
            if self.abort:
                self.finished.emit(False, None)
            else:
                #if memresult is not None:
                if mem2result is not None:
                    self.status.emit('Delivering the layer...')
                    self.finished.emit(True, mem2result)
                    mem2result = None
                    #self.finished.emit(True, memresult)
                    #memresult = None
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
        return QCoreApplication.translate('NNJoinEngine', message)
