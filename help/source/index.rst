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
multi-zone buffer vector dataset from an input vector layer and a set
of distances.

The result polygon dataset consists of bands (donut type) of regions
(multi polygons) according to the buffer distances provided.
The attribute table will consist of one column / field named
*distance*, that contains the maximum distance for that band.


If 100 and 200 are provided as distances, the result dataset will
consist of two bands - one will contain all areas that are within
100 units from the geometries of the input vector layer (including
the geometry itself), the other will contain all areas that are from
100 to 200 units from the geometries of the input vector layer.

Negative and 0.0 buffer distances are allowed for polygon layers.

Buffer distances can be added and deleted.

The keyboard can be used to add the buffer distances quickly (number
followed by <enter>).

The user can choose to only buffer around selected features.
If the user selects a layer with a selection, the default will be
set to use only selected features.
If there is no selection in the chosen layer, the default will be
set to not using selected features only.
The user can then modify this behaviour by using a checkbox.

Implementation
==================

Buffers for all the distances are created using the *buffer*
function of *QgsGeometryAnalyzer*.

The *buffer* function of *QgsGeometryAnalyzer* function does not
support memory layers as output, so a temporary Shapefile format
dataset is created for each buffer distance.

The *buffer* function of *QgsGeometryAnalyzer* does not support the
specification of buffer accuracy (segments / arc vertex distance /
maximum deviation), so this is not available to the user.

The buffers are combined to form the multi-distance buffer by using
the *symDifference* function of *QgsGeometry*.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

