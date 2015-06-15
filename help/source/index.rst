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

The Multi-Distance Buffer plugin creates a multi-distance buffer
vector dataset from an input vector layer and a set of distances.
The result dataset consists of bands (donut type) of regions
according to the buffer distances provided.
If 100 and 200 are provided as distances, the result dataset will
consist of two bands - one will contain all areas that are within
100 units from the geometries of the input vector layer, the other
will contain all areas that are from 100 to 200 units from the
geometries of the input vector layer.

The user can choose to only buffer around selected features.

Implementation
==================

Buffers for all the distances are created using the *buffer*
function of *QgsGeometryAnalyzer*.
This buffer function does not support memory layers as output, so
a temporary Shapefile format dataset is created for each buffer
distance.

The buffers are combined using the *symDifference* function of
*QgsGeometry*.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

