# AsmViz

(That's the tentative name for this, at least.)

An interactive visualization tool for genomic assembly graphs. The goal
of this, as compared with other visualization tools, is to show the
pertinent parts of a graph instead of just displaying the entire graph at once.

To this end, AsmViz highlights certain patterns of contigs in the graph
(bubbles, frayed ropes, chains, and "linear" cycles), splits graphs up by
connected components (optionally displaying only a certain maximum number of
components and/or only displaying components with a certain minimum number
of contigs), and uses [GraphViz](http://www.graphviz.org/) to lay out each
component.

AsmViz is composed of two main components:

1. `collate_clusters.py`, a Python script that reads an assembly graph file,
   identifies patterns in it, separates it by connected components, and
   runs GraphViz on each component to be laid out (generating a .xdot
   layout file and, optionally, a .dot intermediate file).
   Currently, this supports LastGraph (Velvet) and GraphML
   (Bambus 3, IDBA-UD) assembly graph files, and support for GFA and
   FASTG (SPAdes) files is planned.    

2. `xdot2cy.js`, a Javascript program that reads an xdot file generated by
   GraphViz and renders the resulting graph in
   [Cytoscape.js](http://js.cytoscape.org/). This is coupled with an
   interface and "control panel" in which the graph can be searched,
   zoomed, panned, and fitted to the screen, nodes can be selected,
   and pattern-indicating groups of nodes can be collapsed (either on
   the level of individual nodes or for all node groups in the graph).

## System Requirements

### collate\_clusters.py

* Python 2.7 (with [sqlite3](https://docs.python.org/2/library/sqlite3.html) module, which should be installed by default)
* GraphViz (with `dot` layout manager, which should be installed by default)

### xdot2cy.js

* Any modern internet browser (recent mobile browsers should work, also)
  supported by Cytoscape.js

## Running collate\_clusters.py

`collate_clusters.py` is located in the graph\_collator folder. It can be
run from the command line;
see the [system requirements](#system-requirements) section above
for information on what other software needs to be installed.

Running `collate_clusters.py` will process an assembly graph file so that
it can be visualized. The syntax for this is

`./collate_clusters.py -i (input file) -o (.xdot/.gv file prefix)
    [-d (.xdot/.gv directory name)] [-p] [-w]`

The script will produce a directory containing the created .xdot/.gv files.
(If the directory already exists, it will just place the .xdot/.gv files in
that directory; however, unless `-w` is passed, this will throw an error
upon trying to overwrite any files in the directory.)

### Command-line argument descriptions

* `-i` The input assembly graph file to be used.
* `-o` The file prefix to be used for .xdot/.gv files generated. These files
  will be formatted something like foobar\_1.gv, foobar\_1.xdot, foobar\_2.gv,
  foobar\_2.xdot, ... for an argument of `foobar` to `-o`.
* `-d` This optional argument specifies the name of the directory in which
  .xdot/.gv output files will be stored. If no name is specified then the
  argument of `-o` will be used as the directory name (to be created or used
  in the current working directory; note, however,  that it's strongly
  recommended you explicitly specify an output directory using `-d` to ensure
  data is being stored in the intended location).
* `-p` This optional argument preserves DOT files (suffix .gv) in the output
  directory; if this argument is not given, then all .gv files will just be
  deleted after they are used to create their corresponding .xdot file.
* `-w` This optional argument overwrites output files (.xdot/.gv) in the
  output directory. If this argument is not given, then an error will be
  raised if writing an output file would cause another file in the output
  directory (if it already exists) to be overwritten.

## Running xdot2cy.js

Open `xdot_viewer/asmviz_viewer.html` in your favorite browser. Click
the "Choose File" button in the top-left corner of the screen and select
an xdot file generated by `collate_clusters.py`, then click the "Load xdot
file" button when you're ready. The status message field (located below the
"Choose File" button) will show you the status of the .xdot
parsing/rendering process while you wait.

Once the status field says "Finished rendering", the graph is ready to be
interacted with! Some features:

* You can **zoom in/out** on the graph by scrolling up/down.
* You can **pan** the graph by clicking on the screen (not on a node or edge)
  and dragging the mouse in accordance with the desired direction of
  movement.
* You can **drag** nodes/node groups by clicking on them and dragging them
  with your mouse.
* You can **select multiple nodes, edges, and node groups** by holding down
  the SHIFT or CTRL keys and clicking on the element in question. Selected
  nodes/node groups can be moved around by dragging them, but note that
  selected edges cannot be moved independently of their source/sink nodes.
* You can **search for nodes or edges** using the "Search" field located in
  the top-center of the screen. Note that edge IDs are (currently) given as
  `node1->node2`, where `node1` is the name of the source node and `node2`
  is the name of the sink (target) node.
* You can **scale** the graph to fit within the current window size using
  the "Fit Graph to Nodes" button located in the top-center of the screen.
  This is done by default after rendering the graph for the first time and
  after rotating the graph.
* You can **rotate** the graph so that its nodes are laid out in the general
  direction indicated by using the "Graph Rotation" selection list.
  Selecting a different rotation than the current one will cause the entire
  graph to be rotated in that direction, followed by the graph being scaled
  to optimally fit within the current window size. Note that this preserves
  the state of the graph, so any collapsed/uncollapsed node groups, selected
  elements, or other modified properties of the graph will remain across
  rotations.
* You can **collapse and uncollapse individual node groups** by
  right-clicking on them; however, note that you have to right-click on
  the node group itself to do this, not on any of the nodes/edges within
  the node group. Collapsing a node group will convert any incoming/outgoing
  edges to that node group to straight-line bezier edges, since no GraphViz
  data exists defining such an edge.
* You can **collapse and uncollapse all node groups in the graph** by using
  the "Collapse All Node Groups"/"Uncollapse All Node Groups" button located
  near the top-right corner of the screen. Note that this works perfectly
  fine with individually-collapsed node groups; already-collapsed node
  groups will be ignored upon collapsing all nodes, and already-uncollapsed
  node groups will be ignored upon uncollapsing all nodes.
