.. multidistancebuffer documentation master file, created by
   sphinx-quickstart on Sun Feb 12 17:11:03 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Multi-Distance Buffer's documentation!
=================================================

Contents:

.. toctree::
   :maxdepth: 2

   self

Functionality
==================

The Multi-Distance Buffer plugin creates a multi-distance /
multi-zone vector dataset from an input vector layer and a set of
distances.

The resulting dataset consists of one (multi)polygon ("donut type")
for each buffer distance.
The (multi)polygons do not overlap.
The attribute table will have one column / field named *distance*,
that contains the (maximum) distance for the (multi)polygon.
The memory layer containing the data set is added to the QGIS table
of contents.

If 100 and 200 are provided as distances, the result dataset will
consist of two zones / bands / (multi)polygons - one will contain
all areas that are within 100 units from the geometries of the input
vector layer (including the geometries themselves), the other will
contain all areas that are from 100 to 200 units from the geometries
of the input vector layer.

The buffer distances (decimal numbers) can be specified by the user
in any order.
The list will be kept numerically sorted by the Plugin.

Negative and 0.0 buffer distances are allowed for polygon layers.

Buffer distances can be added and deleted in the dialogue using the
*Add* and *Remove* buttons.

The keyboard can be used to add the buffer distances quickly (number
followed by <enter>).

A checkbox (*Use only selected features*) can be used to choose to
only buffer around selected features.
If the user selects a layer with a selection, the default will be
set to only use selected features.
If there is no selection in the chosen layer, the default will be
set to not only use selected features.
The user can modify this behaviour with the checkbox.

Implementation
==================

Buffers for all the distances are created using the *buffer*
function of *QgsGeometryAnalyzer*.

The *buffer* function of *QgsGeometryAnalyzer* function does not
support memory layers as output, so a temporary (using the Python
*tempfile* module) *Shapefile format* dataset is created for each
buffer distance.
The temporary datasets are deleted later.

The *buffer* function of *QgsGeometryAnalyzer* does not support the
specification of buffer accuracy (segments / arc vertex distance /
maximum deviation), so this is not available to the user.

The buffers are combined to form the multi-distance buffer using the
*symDifference* function of *QgsGeometry*.

Links
=======

`Multi-Distance Buffer Plugin`_

`Multi-Distance Buffer code repository`_

`Multi-Distance Buffer issues`_

.. _Multi-Distance Buffer code repository: https://github.com/havatv/qgismultidistancebufferplugin.git
.. _Multi-Distance Buffer Plugin: https://plugins.qgis.org/plugins/MultiDistanceBuffer/
.. _Multi-Distance Buffer issues: https://github.com/havatv/qgismultidistancebufferplugin/issues

