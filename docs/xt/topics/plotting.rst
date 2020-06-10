.. _plotting:

======================================
XT Plotting 
======================================

This page gives an overview of the plot command and explains some of its options.

The XT plot command helps the user create ad-hoc plots of logged metrics across multiple runs.  The general syntax is:   
    - xt plots <run list> [ <column list> ] [ <options> ]

The run list is a comma separted list of any of the following:
    - run name (e.g., run2232.1)
    - run name range (e.g., run2300-2315)
    - run name with wilcards (e.g., run3223.*)

The column list is a comma separated list of:
    - app logged metric name (e.g., test-acc)
    
--------------------------
Multiple Plots and Layout
--------------------------

By default, all runs and metric are plotted in a single plot.  You can create multiple plots by setting the **--break-on** option to one of the following:
    - **col**   (this will put each metric in its own plot)
    - **run**   (this will put each run in its own plot)
    - **run+col**"  (this will create a plot for each unique run/col combination)

When multiple plots are produced, by default they are layed out in a single row (horizontally).  You can use the **--layout option** to specify the rows and columns, as shown here:
    - "2x3"   (this specifies plots should be arranged in 2 rows of 3 columns)
    - "x3"    (this specifies plots should be arranged in multiple rows of 3 columns)
    - "4x"    (this specifies plots should be arranged in 4 rows of multiple columns)

--------------------------
Titles and Legend
--------------------------

You can specify the plot window's title using the **--title** option.

You can specify the title of each plot using the **--plot-titles** option.  If not specified, 
a default title will be supplied under most conditions.  

You can specify the titles for each line/marker in the legend using the **--legend-titles** option.
If not specified, a default will be supplied.

For all of these titles, you can use special symbols that will be expanded by XT according to the 
run/metric associated with the title:

    - **$run**   (expanded to the run name)
    - **$col**   (expanded to the metric name)

The legend is shown by default; it can be hidden by setting the **--show-legend** option to 0 or false.

--------------------------
Plot Types
--------------------------

By default, a line plot is produced.  This can be controlled by setting the **--plot-type** option to one of the following:

    - **line**          (produce a line plot)
    - **scatter**       (produce a scatterplot)
    - **histogram**     (produce a histogram)

The **--smoothing-factor** is a number between 0 and 1 that can be used to smooth the data before it is plotted, 
using exponential smoothing.

By default, the data used by the X axis of the plot is the index of the metric values, and the data used by the Y axis are the metric values themselves.  
You can specify a different value to plot on the X axis by setting the **--x-col** option to the name of a logger metric.

--------------------------
Colors and Markers
--------------------------
   
The color scheme of the markers default to "blue", *red*, *green*, and *orange*.  You are override these by specifying a list of colors
with the **--colors** option.

You can specify the edge color (outline color) of the plot markers using the **--edge-color** option.  

The type of marker (marker shape) used to plot can be controlled using the **--marker-shape** option.  A few common values:
    - **.**       (point type marker)
    - **,**       (pixel marker)
    - **o**       (circle)
    - **v**       (triangle down)

Since XT plots are built on top of matplotlib, refer to their website for the full set: `matplotlib markers <https://matplotlib.org/api/markers_api.html>`_

Finally, the alpha (transparency) of the shapes can be specified with the **--alpha** option, accepting a value between 0 and 1 inclusive.

.. seealso:: 

    - :ref:`xt plot command <plotting>`
