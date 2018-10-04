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
 This script initializes the plugin, making it known to QGIS.
"""

__author__ = 'Håvard Tveite'
__date__ = '2018-10-04'
__copyright__ = '(C) 2018 by Håvard Tveite'


def classFactory(iface):
    # load MultiDistanceBuffer class from file MultiDistanceBuffer
    from .MultiDistanceBuffer import MultiDistanceBuffer
    return MultiDistanceBuffer(iface)
