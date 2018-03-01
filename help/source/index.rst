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

The **Multi-Distance Buffer** QGIS plugin creates a multi-distance /
multi-zone / multi-ring vector (memory) layer from an input vector
layer and a set of distances.

The resulting layer consists of one (multi)polygon ("donut type")
for each buffer distance.
The (multi)polygons do not overlap.
The attribute table of the result layer will have two columns /
fields named *distance* and *inner*, that contain the outer (maximum)
distance and the inner distance for each (multi)polygon.
For the innermost zone, the value of *inner* is not set.
The resulting (memory) layer is added to the QGIS table of contents.

If 100 and 200 are provided as distances, the result layer will
consist of two zones / bands / (multi)polygons - one will contain
all areas that are within 100 units from the geometries of the input
vector layer (including the geometries themselves) and will have its
*distance* field set to 100; the other will contain all areas that
are from 100 to 200 units from the geometries of the input vector
layer and will have its *distance* field set to 200, and its *inner*
field set to 100.

  The buffer distances (decimal numbers) can be specified by the user
  in any order.
  The list will be kept numerically sorted by the Plugin.

  Negative and 0.0 buffer distances are allowed for polygon layers
  only.
  Buffering a polygon with a negative buffer distance means shrinking
  the polygon and is also known as a *setback*.

  Buffer distances can be added and removed in the dialogue using the
  *Add*, *Remove* and *Clear all* buttons.
  The *Remove* button removes the selected entries, while the *Clear*
  button removes all entries.
  The keyboard can be used to add individual buffer distances quickly
  (number followed by <enter>).

  Fixed increment buffer distances can be added under the **Add
  multiple** tab, specifying the number of zones, the width of each
  zone and the start value.

  A checkbox (*Selected features only*) can be used to choose to
  only buffer around selected features.
  If the user selects a layer with a selection, the default will be
  set to only use selected features.
  If there is no selection in the chosen layer, the default will be
  set to not only use selected features.
  The user can modify this behaviour by using the checkbox.

Three approaches to buffering are offered by the plugin
-------------------------------------------------------

*Standard QGIS buffer operations*
  Will use five segments to represent a quarter circle
  for the buffer geometries in the result dataset.

  .. image:: illustrations/standard.png
   :width: 200

*Segments to approximate* (new in version 2.0)
  The user specifies the number of segments to use for a quarter
  circle.

  .. |seg2| image:: illustrations/segments2.png
   :width: 200
   :align: middle
  .. |seg10| image:: illustrations/segments10.png
   :width: 200
   :align: top

  +-------------+--------------+
  | 2 segments: | 10 segments: |
  +=============+==============+
  | |seg2|      | |seg10|      |
  +-------------+--------------+

*Maximum deviation* (new in version 2.0)
  The user provides the maximum radial deviation from the
  specified buffer distances in map units.
  The number of segments per quarter circle is calculated
  based on the buffer distance, and will increase with increasing
  buffer distances.
  In the illustrations, the buffer distances are 100 and 200.

  .. |dev1| image:: illustrations/deviation1.png
   :width: 200
   :align: middle
  .. |dev10| image:: illustrations/deviation10.png
   :width: 200
   :align: top

  +------------------+-------------------+
  | max deviation 1: | max deviation 10: |
  +==================+===================+
  | |dev1|           | |dev10|           |
  +------------------+-------------------+


Implementation
==================

The *buffer* function of *QgsGeometry* is used, and the resulting
buffer geometries are combined using the *dissolve* function of
*QgsGeometry*.

The buffers are combined to form the multi-distance buffer using the
*symDifference* function of *QgsGeometry*.

With the *standard* approach, buffers for all the distances used
to be created using the *buffer* function of *QgsGeometryAnalyzer*.
The *buffer* function of *QgsGeometryAnalyzer* did not support
the specification of buffer accuracy (segments / arc vertex distance
/ maximum deviation), so the default of 5 segments had to be used.

Citation
===========

Would you like to cite this plugin?

Tveite, Håvard.  2018.  The QGIS Multi-distance buffer Plugin, Version
2.2.2.
http://plugins.qgis.org/plugins/MultiDistanceBuffer/



Links
=======

`Multi-Distance Buffer Plugin`_

`Multi-Distance Buffer code repository`_

`Multi-Distance Buffer issues`_

.. _Multi-Distance Buffer code repository: https://github.com/havatv/qgismultidistancebufferplugin.git
.. _Multi-Distance Buffer Plugin: https://plugins.qgis.org/plugins/MultiDistanceBuffer/
.. _Multi-Distance Buffer issues: https://github.com/havatv/qgismultidistancebufferplugin/issues

