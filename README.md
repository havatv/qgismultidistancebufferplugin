MultiDistanceBuffer
===================
QGIS Plugin for multi-distance / multi-ring / multi-zone buffering.

The *Standard* alternative uses QgsGeometryAnalyzer.buffer and
QgsGeometry.symDifference to create the buffer bands.

The other alternatives (*Segments to approximate* and *Maximum
deviation*) avoid QgsGeometryAnalyzer by using QgsGeometry.buffer,
QgsGeometry.combine and QgsGeometry.symDifference.

The plugin is available from the QGIS official plugin repository
(http://plugins.qgis.org).

Master contains code for QGIS version 3.

Branch qgis2 contains code for QGIS version 2.
