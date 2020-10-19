#!/usr/bin/env python3.6
# Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
# Authored by Marcus Fedarko
#
# This file is part of MetagenomeScope.
#
# MetagenomeScope is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MetagenomeScope is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.

from subprocess import check_output, STDOUT
import pygraphviz
import os
import re
import numpy
import errno
import sqlite3
import time

from . import graph_objects, config, arg_utils
from .file_utils import check_file_existence, safe_file_remove, save_aux_file
from .msg_utils import operation_msg, conclude_msg


def assembly_gc(gc_ct, total_bp):
    """Returns the G/C content of an assembly, where total_bp is the number of
    base pairs (2 * the number of nucleotides) and gc_ct is the number of
    G/C nucleotides in the entire assembly.
    """
    if gc_ct is None:
        return None
    else:
        return float(gc_ct) / (2 * total_bp)


def n50(node_lengths):
    """Determines the N50 statistic of an assembly, given its node lengths.

    Note that multiple definitions of the N50 statistic exist (see
    https://en.wikipedia.org/wiki/N50,_L50,_and_related_statistics for
    more information).

    CODELINK: Here, we use the calculation method described by Yandell and
    Ence (2012), Nature Reviews Genetics 13(5). Box 1 in the paper describes
    the method for calculating the N50 statistic that is used in this
    function.
    """

    if len(node_lengths) == 0:
        raise ValueError(config.EMPTY_LIST_N50_ERR)
    sorted_lengths = sorted(node_lengths, reverse=True)
    i = 0
    running_sum = 0
    half_total_length = 0.5 * sum(sorted_lengths)
    while running_sum < half_total_length:
        if i >= len(sorted_lengths):
            # This should never happen, but just in case
            raise IndexError(config.N50_CALC_ERR)
        running_sum += sorted_lengths[i]
        i += 1
    # Return length of shortest node that was used in the running sum
    return sorted_lengths[i - 1]


def add_node_to_stdmode_mapping(nodeid2obj, n, rc=None):
    """Adds a Node object n to nodeid2obj.

    If rc is defined, also adds rc to nodeid2obj.

    This checks to make sure n and rc's IDs are not already in nodeid2obj.
    If either of their IDs are already in nodeid2obj before adding them, an
    AttributeError is raised.

    Returns the modified nodeid2obj.
    """
    # Check for duplicate IDs
    if n.id_string in nodeid2obj:
        raise AttributeError(config.DUPLICATE_ID_ERR + n.id_string)
    # Actually add to nodeid2obj
    nodeid2obj[n.id_string] = n
    if rc is not None:
        if rc.id_string in nodeid2obj:
            raise AttributeError(config.DUPLICATE_ID_ERR + rc.id_string)
        nodeid2obj[rc.id_string] = rc
    return nodeid2obj


def make_viz(
    input_file: str,
    output_dir: str,
    assume_oriented: bool,
    max_node_count: int,
    max_edge_count: int,
    metacarvel_bubble_file: str,
    user_pattern_file: str,
    spqr: bool,
    sp: bool,
    pg: bool,
    px: bool,
    nbdf: bool,
    npdf: bool,
):
    arg_utils.create_output_dir(output_dir)
    arg_utils.validate_max_counts(max_node_count, max_edge_count)

    # Parse the assembly graph!
    operation_msg(
        "Reading and parsing input file {}...".format(os.path.basename(asm_fn))
    )
    asm_graph = graph_objects.AssemblyGraph(asm_fn)
    conclude_msg()

    # Hierarchically decompose graph, creating duplicate nodes where needed
    # TODO: Have this utilize user-supplied bubbles and patterns. They should
    # be "lowest level" patterns, i.e. collapsed first.
    # ALSO TODO: Have this use fancier complex bubble detection, similar to
    # what's described in the MaryGold / MetaFlye papers. For now very complex
    # bubbles are assumed to be covered by decomposition or by user input, but
    # this will not always be the case.
    operation_msg("Running hierarchical pattern decomposition...")
    asm_graph.hierarchically_identify_patterns()
    conclude_msg()

    operation_msg("Scaling nodes based on lengths...")
    asm_graph.scale_nodes()
    conclude_msg()

    # Immediate TODO:
    # -For each component in the graph, do edge scaling.
    #   - will need to modify asm graph parsers to return edge attrs,
    #     and then use this to determine if edge weights available. add method
    #     that (conditionally upon that) does said scaling within asm graph.
    #
    # -Compute graph layouts. For each component:
    #   -Lay out individual patterns, starting at lowest level and moving up.
    #    Similar to SPQR layout code.
    #   -Finally, lay out the entire graph for the component, with patterns
    #    replaced with their bounding box.
    #   -Backfill all node/edge coordinates in.
    #
    #   At this point we can create AssemblyGraph.to_dot(), to_cytoscape(),
    #   etc. methods for temporary testing.
    #
    # -Use jinja2 to pass data to the viewer index.html file.
    #
    # -Modify the JS to prepare the graph summary, etc. and get ready for
    #  component drawing. Replace DB operations with just looking at the JSON.

    # TODO from here on down.
    # -Identify user-supplied bubbles.
    # -Identify user-supplied misc. patterns.
    # -If -spqr passed, compute SPQR trees and record composition/structure.
    # -Output identified pattern info if -sp passed
    # -Identify connected components for the "single" graph (SPQR mode).
    # -Identify connected components for the "normal" graph (non-SPQR mode).
    # -Compute node scaling for each connected component
    # -Compute edge scaling for each connected component
    # -SPQR layout!
    # -Normal layout!

    ## Maps Node ID (as int) to the Node object in question
    ## This is nice, since it allows us to do things like
    ## list(nodeid2obj.values()) to get a list of every Node object that's been
    ## processed
    ## (And, more importantly, to reconcile edge data with prev.-seen node data)
    # nodeid2obj = {}

    ## Like nodeid2obj, but for preserving references to clusters (NodeGroups)
    # clusterid2obj = {}

    ## Like nodeid2obj but for "single" Nodes, to be used in the SPQR-integrated
    ## graph
    # singlenodeid2obj = {}
    ## List of 2-tuples, where each 2-tuple contains two node IDs
    ## For GML files this will just contain all the normal connections in the graph
    ## For LastGraph/GFA files, though, this will contain half of the connections
    ## in the graph, due to no edges being "implied"
    # single_graph_edges = []

    ## Like nodeid2obj but using labels as the key instead; used when processing
    ## user-specified bubble/misc. pattern files if the user specifies the -ubl or
    ## -upl options above
    # nodelabel2obj = {}
    ## Will be True if we need to populate nodelabel2obj
    # need_label_mapping = False

    ## Pertinent Assembly-wide information we use
    # graph_filetype = ""
    # distinct_single_graph = True
    ## If DNA is given for each contig, then we can calculate GC content
    ## (In LastGraph files, DNA is always given; in GML files, DNA is never given;
    ## in GFA files, DNA is sometimes given.)
    ## (That being said, it's ostensibly possible to store DNA in an external FASTA
    ## file along with GML/GFA files that don't have DNA explicitly given -- so
    ## these constraints are subject to change.)
    # dna_given = True
    ## Whether or not repeat data for nodes is provided. Currently this is only
    ## passed through certain GML files, so we assume it's false until we encounter
    ## a node with repeat data provided.
    # repeats_given = False
    # total_node_count = 0
    # total_edge_count = 0
    # total_all_edge_count = 0
    # total_length = 0
    # total_gc_nt_count = 0
    # total_component_count = 0
    # total_single_component_count = 0
    # total_bicomponent_count = 0
    ## Used to determine whether or not we can scale edges by multiplicity/bundle
    ## size. Currently we make the following assumptions (might need to change) --
    ## -All LastGraph files contain edge multiplicity values
    ## -Some GML files contain edge bundle size values, and some do not
    ##   -The presence of a single edge in a GML file without a bundle size
    ##    attribute will result in edge_weights_available being set to False.
    ## -All GFA files do not contain edge multiplicity values
    # edge_weights_available = True
    ## List of all the node lengths in the assembly. Used when calculating n50.
    # bp_length_list = []

    # Try to collapse special "groups" of Nodes (Bubbles, Ropes, etc.)
    # As we check nodes, we add either the individual node (if it can't be
    # collapsed) or its collapsed "group" (if it could be collapsed) to a list
    # of nodes to draw, which will later be processed and output to the .gv file.

    # We apply "precedence" here: identify all user-specified patterns, bubbles,
    # then frayed ropes, then cycles, then chains. A minor TODO is making that
    # precedence configurable; see #87 (and generalizing this code to get rid
    # of redundant stuff, maybe?)

    nodes_to_try_collapsing = list(nodeid2obj.values())
    nodes_to_draw = []

    # Identify user-supplied bubbles in the graph.
    if ububbles_fullfn is not None:
        operation_msg(config.USERBUBBLES_SEARCH_MSG)
        with open(ububbles_fullfn, "r") as ub_file:
            bubble_lines = ub_file.readlines()
            bubble_line_ct = 1
            for b in bubble_lines:
                bubble_line_node_ids = b.strip().split("\t")[2:]
                if len(bubble_line_node_ids) < 1:
                    raise ValueError(
                        config.LINE_NOUN
                        + str(bubble_line_ct)
                        + config.UBUBBLE_NOTENOUGH_ERR
                    )
                # Ensure that the node identifiers (either labels or IDs)
                # for this user-supplied bubble are valid.
                # 1. Do all of the identifiers correspond to actual nodes in the
                #    graph? If not, raise a KeyError.
                # 2. Is the "vertex-induced subgraph" of nodes in the user-supplied
                #    bubble somehow contiguous? If so, create a Bubble. If not,
                #    raise a KeyError.
                # 3. Have we used any of these nodes in collapsing before? Since
                #    user-supplied bubbles are the highest-priority node groups,
                #    this will only be the case at this stage if any of the nodes
                #    have previously been incorporated into another user-supplied
                #    bubble. If this is the case, ignore this user-supplied bubble.
                curr_bubble_nodeobjs = []
                exists_duplicate_node = False
                for node_id in bubble_line_node_ids:
                    try:
                        if ububbles_labels:
                            # nodelabel2obj must exist if ububbles_labels is True,
                            # per the code above
                            nobj = nodelabel2obj[node_id]
                        else:
                            node_id = fastg_long_id_to_id(node_id)
                            nobj = nodeid2obj[node_id]
                        if nobj.used_in_collapsing:
                            exists_duplicate_node = True
                        curr_bubble_nodeobjs.append(nobj)
                    except KeyError as e:
                        raise KeyError(config.UBUBBLE_NODE_ERR + str(e))

                if len(curr_bubble_nodeobjs) > 1:
                    # Test that the nodes' "induced subgraph" is contiguous.
                    # For each node in the user-supplied bubble, construct a
                    # set of all incident nodes (not including the node itself,
                    # in the case that the node has an edge to itself). If this
                    # set has some intersection with the nodes in the
                    # user-supplied bubble, the node is ok; move on to the next.
                    # Otherwise, this node is disconnected from the other nodes
                    # in the user-supplied bubble, so reject this bubble by
                    # raising a ValueError.
                    for nobj in curr_bubble_nodeobjs:
                        incidents = set(
                            nobj.outgoing_nodes + nobj.incoming_nodes
                        )
                        # disqualify nodes with self-loops as being automatically
                        # considered valid by clearing this node from its set of
                        # incident nodes
                        incidents.discard(nobj)
                        if incidents.isdisjoint(curr_bubble_nodeobjs):
                            raise ValueError(
                                config.UBUBBLE_ERR_PREFIX
                                + b.strip()
                                + config.CONTIGUOUS_ERR
                            )

                if exists_duplicate_node:
                    # A given node can only belong to a max of 1 structural
                    # pattern, so for now we handle this by continuing.
                    # Might want to eventually throw an error/warning here--need
                    # to see if this is a common case in the input data.
                    #
                    # We abstain from breaking when we first set
                    # exists_duplicate_node = True above, or before we test the
                    # induced subgraph's contiguity afterwards, in order to
                    # ensure that this bubble is validated before skipping it.
                    # Otherwise, weird behavior would manifest
                    # where Errors are sometimes raised for user-defined bubbles
                    # but sometimes not. I'd prefer to make the behavior
                    # consistent wherever possible (although I'd be open to
                    # changing this in the future if people ask for it).
                    continue
                new_bubble = graph_objects.Bubble(*curr_bubble_nodeobjs)
                nodes_to_draw.append(new_bubble)
                clusterid2obj[new_bubble.id_string] = new_bubble
                bubble_line_ct += 1
        conclude_msg()

    # Identify miscellaneous user-supplied patterns in the graph.
    # This code is pretty similar to the above code for identifying user-supplied
    # bubbles, but it's not identical. Might be a good idea to merge this with that
    # code somehow in the future (although that's fairly low-priority).
    if upatterns_fullfn is not None:
        operation_msg(config.USERPATTERNS_SEARCH_MSG)
        with open(upatterns_fullfn, "r") as up_file:
            pattern_lines = up_file.readlines()
            pattern_line_ct = 1
            for p in pattern_lines:
                pattern_items = p.strip().split("\t")
                pattern_line_node_ids = pattern_items[1:]
                if len(pattern_line_node_ids) < 1:
                    raise ValueError(
                        config.LINE_NOUN
                        + str(pattern_line_ct)
                        + config.UPATTERN_NOTENOUGH_ERR
                    )
                # Ensure that the node identifiers are valid.
                curr_pattern_nodeobjs = []
                exists_duplicate_node = False
                for node_id in pattern_line_node_ids:
                    try:
                        if upatterns_labels:
                            nobj = nodelabel2obj[node_id]
                        else:
                            node_id = fastg_long_id_to_id(node_id)
                            nobj = nodeid2obj[node_id]
                        if nobj.used_in_collapsing:
                            exists_duplicate_node = True
                        curr_pattern_nodeobjs.append(nobj)
                    except KeyError as e:
                        raise KeyError(config.UPATTERN_NODE_ERR + str(e))

                if len(curr_pattern_nodeobjs) > 1:
                    # Test that the nodes' "induced subgraph" is contiguous.
                    for nobj in curr_pattern_nodeobjs:
                        incidents = set(
                            nobj.outgoing_nodes + nobj.incoming_nodes
                        )
                        # disqualify nodes with self-loops as being automatically
                        # considered valid
                        incidents.discard(nobj)
                        if incidents.isdisjoint(curr_pattern_nodeobjs):
                            raise ValueError(
                                config.UPATTERN_ERR_PREFIX
                                + p.strip()
                                + config.CONTIGUOUS_ERR
                            )

                if exists_duplicate_node:
                    # A given node can only belong to a max of 1 structural
                    # pattern, so for now we handle this by continuing.
                    # Might want to eventually throw an error/warning here.
                    continue
                # At this point, we've validated this pattern sufficiently.
                # We're ready to create an actual object for it.
                new_pattern = None
                for poss_type in (graph_objects.Bubble, graph_objects.Rope):
                    if pattern_items[0] == poss_type.type_name:
                        new_pattern = poss_type(*curr_pattern_nodeobjs)
                        break
                if new_pattern is None:
                    new_pattern = graph_objects.MiscPattern(
                        pattern_items[0], *curr_pattern_nodeobjs
                    )
                nodes_to_draw.append(new_pattern)
                clusterid2obj[new_pattern.id_string] = new_pattern
                # TODO this will break when we use "continue." Add a test case
                # to demonstrate the broken-ness of this, then fix this -- both
                # here and in the user bubble code.
                pattern_line_ct += 1
        conclude_msg()

    # this line marks the start of simple bubble stuff
    operation_msg(config.BUBBLE_SEARCH_MSG)

    # Find "standard" bubbles. Our algorithm here classifies a bubble as a set of
    # nodes with a starting node, a set of middle nodes, and ending node, where the
    # starting node has at least two outgoing paths: all of which linearly extend
    # to the ending node.
    # This ignores some types of bubbles that exhibit a more complex structure,
    # hence the option for user-defined bubbles to be passed in (and/or for
    # MetaCarvel's bubbles.txt output to be used).
    for (
        n
    ) in nodes_to_try_collapsing:  # Test n as the "starting" node for a bubble
        if n.used_in_collapsing or len(n.outgoing_nodes) <= 1:
            # If n doesn't lead to multiple nodes, it couldn't be a bubble start
            continue
        bubble_validity, member_nodes = graph_objects.Bubble.is_valid_bubble(n)
        if bubble_validity:
            # Found a bubble!
            new_bubble = graph_objects.Bubble(*member_nodes)
            nodes_to_draw.append(new_bubble)
            clusterid2obj[new_bubble.id_string] = new_bubble

    conclude_msg()
    if args.computespqrdata:
        # Run the SPQR script, use its output to create SPQR trees
        operation_msg(config.SPQR_MSG)

        # Clear extraneous SPQR auxiliary files from the output directory, if
        # present (see issue #191 on the GitHub page)
        cfn_regex = re.compile(r"component_(\d+)\.info")
        sfn_regex = re.compile(r"spqr\d+\.gml")
        for fn in os.listdir(output_dir):
            match = cfn_regex.match(fn)
            if match is not None:
                c_fullfn = os.path.join(output_dir, fn)
                if check_file_existence(c_fullfn, overwrite):
                    safe_file_remove(c_fullfn)
            else:
                s_match = sfn_regex.match(fn)
                if s_match is not None:
                    s_fullfn = os.path.join(output_dir, fn)
                    if check_file_existence(s_fullfn, overwrite):
                        safe_file_remove(s_fullfn)

        # Construct links file for the single graph
        # (this is unnecessary for MetaCarvel GML files, but for LastGraph/GFA
        # files it's needed in order to generate the SPQR tree)
        s_edges_fullfn = None
        if distinct_single_graph:
            s_edges_fn = output_fn + "_single_links"
            s_edges_fn_text = ""
            for e in single_graph_edges:
                # (the other values we add are just dummy values -- they don't
                # impact the biconnected components/SPQR trees that we obtain from
                # the script)
                line = e[0] + "\tB\t" + e[1] + "\tB\t0\t0\t0\n"
                s_edges_fn_text += line
            save_aux_file(
                s_edges_fn,
                s_edges_fn_text,
                output_dir,
                False,
                overwrite,
                warnings=False,
            )
            s_edges_fullfn = os.path.join(output_dir, s_edges_fn)

        # Prepare non-single-graph _links file
        # (unnecessary for the case where -b is passed and the input graph has a
        # distinct single graph)
        edges_fullfn = None
        if bicmps_fullfn is None or not distinct_single_graph:
            edges_fn = output_fn + "_links"
            edges_fn_text = ""
            for n in nodes_to_try_collapsing:
                for e in n.outgoing_nodes:
                    line = (
                        n.id_string + "\tB\t" + e.id_string + "\tB\t0\t0\t0\n"
                    )
                    edges_fn_text += line
            save_aux_file(
                edges_fn,
                edges_fn_text,
                output_dir,
                False,
                overwrite,
                warnings=False,
            )
            edges_fullfn = os.path.join(output_dir, edges_fn)

        # Get the location of the spqr script -- it should be in the same dir as
        # collate.py, i.e. the currently running python script
        #
        # NOTE: Some of the spqr script's output is sent to stderr, so when we run
        # the script we merge that with the output. Note that we don't really check
        # the output of this, although we could if the need arises -- the main
        # purpose of using check_output() here is to catch all the printed output
        # of the spqr script.
        #
        # TODO: will need to change some script miscellany to work in non-Unix
        # envs.
        spqr_fullfn = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "spqr"
        )
        spqr_invocation = []
        if bicmps_fullfn is not None:
            # -b has been passed: we already have the file indicating separation
            # pairs. This means we only need to call the script once, to output the
            # SPQR tree
            if not distinct_single_graph:
                # Input file has oriented contigs (e.g. MetaCarvel GML output)
                # Call script once with -t and the normal links file
                spqr_invocation = [
                    spqr_fullfn,
                    "-l",
                    edges_fullfn,
                    "-t",
                    "-d",
                    output_dir,
                ]
            else:
                # Input file has unoriented contigs (e.g. Velvet LastGraph output)
                # Call script once with -t and the single links file
                spqr_invocation = [
                    spqr_fullfn,
                    "-l",
                    s_edges_fullfn,
                    "-t",
                    "-d",
                    output_dir,
                ]
        else:
            # -b has not been passed: we need to call the SPQR script to generate
            # the separation pairs file
            # Detect (and remove) a file with a conflicting name, if present
            bicmps_fn = output_fn + "_bicmps"
            bicmps_fullfn = os.path.join(output_dir, bicmps_fn)
            if check_file_existence(bicmps_fullfn, overwrite):
                safe_file_remove(bicmps_fullfn)

            if not distinct_single_graph:
                # Input file has oriented contigs
                # Call script once with -s and -t, and the normal links file
                spqr_invocation = [
                    spqr_fullfn,
                    "-l",
                    edges_fullfn,
                    "-t",
                    "-s",
                    "-o",
                    bicmps_fn,
                    "-d",
                    output_dir,
                ]
            else:
                # Input files has unoriented contigs
                # Call script twice: once with -s and the normal links file, and
                # once with -t and the single links file
                spqr_invocation = [
                    spqr_fullfn,
                    "-l",
                    edges_fullfn,
                    "-s",
                    "-o",
                    bicmps_fn,
                    "-d",
                    output_dir,
                ]
                spqr_invocation_2 = [
                    spqr_fullfn,
                    "-l",
                    s_edges_fullfn,
                    "-t",
                    "-d",
                    output_dir,
                ]
                run_spqr_script(spqr_invocation_2)
        run_spqr_script(spqr_invocation)

        # NOTE we make the assumption that the generated component and spqr files
        # aren't deleted after running the SPQR script but before they're read
        # here.
        # If they are for whatever reason, then this script will fail to recognize
        # the corresponding biconnected component information (thus failing to draw
        # a SPQR tree, and likely causing an error of some sort when creating the
        # .db file).
        #
        # (As with the potential case where the separation pairs file is deleted
        # after being generated but before being read, this falls under the scope
        # of "silly race conditions that probably won't ever happen but are still
        # ostensibly possible".)

        conclude_msg()
        operation_msg(config.SPQR_LAYOUT_MSG)
        # Identify the component_*.info files representing the SPQR tree's
        # composition
        bicomponentid2fn = {}
        for fn in os.listdir(output_dir):
            match = cfn_regex.match(fn)
            if match is not None:
                c_fullfn = os.path.join(output_dir, fn)
                if os.path.isfile(c_fullfn):
                    bicomponentid2fn[match.group(1)] = c_fullfn

        # Get info from the SPQR tree auxiliary files (component_*.info and
        # spqr*.gml)
        bicomponentid2obj = {}
        metanode_id_regex = re.compile(r"^\d+$")
        metanode_type_regex = re.compile(r"^[SPR]$")
        edge_line_regex = re.compile(r"^v|r")
        for cfn_id in bicomponentid2fn:
            with open(bicomponentid2fn[cfn_id], "r") as component_info_file:
                metanodeid2obj = {}
                curr_id = ""
                curr_type = ""
                curr_nodes = []
                curr_edges = []
                for line in component_info_file:
                    if edge_line_regex.match(line):
                        curr_edges.append(line.split())
                    elif metanode_id_regex.match(line):
                        if curr_id != "":
                            # save previous metanode info
                            new_metanode = graph_objects.SPQRMetaNode(
                                cfn_id,
                                curr_id,
                                curr_type,
                                curr_nodes,
                                curr_edges,
                            )
                            metanodeid2obj[curr_id] = new_metanode
                        curr_id = line.strip()
                        curr_type = ""
                        curr_nodes = []
                        curr_edges = []
                    elif metanode_type_regex.match(line):
                        curr_type = line.strip()
                    else:
                        # This line must describe a node within the metanode
                        curr_nodes.append(singlenodeid2obj[line.split()[1]])
                # Save the last metanode in the file (won't be "covered" in loop
                # above)
                new_metanode = graph_objects.SPQRMetaNode(
                    cfn_id, curr_id, curr_type, curr_nodes, curr_edges
                )
                metanodeid2obj[curr_id] = new_metanode
            # At this point, we have all nodes in the entire SPQR tree for a
            # given biconnected component saved in metanodeid2obj.
            # For now, let's just parse the structure of this tree and lay it out
            # using GraphViz -- will implement in the web visualization tool soon.
            tree_structure_fn = os.path.join(
                output_dir, "spqr%s.gml" % (cfn_id)
            )
            # List of 2-tuples of SPQRMetaNode objects.
            with open(tree_structure_fn, "r") as spqr_structure_file:
                parsing_edge = False
                source_metanode = None
                target_metanode = None
                for line in spqr_structure_file:
                    if line.strip().startswith("edge ["):
                        parsing_edge = True
                    elif parsing_edge:
                        if line.strip().startswith("]"):
                            parsing_edge = False
                            # save edge data
                            source_metanode.add_outgoing_edge(target_metanode)
                            source_metanode = None
                            target_metanode = None
                        else:
                            id_line_parts = line.strip().split()
                            if id_line_parts[0] == "source":
                                source_metanode = metanodeid2obj[
                                    id_line_parts[1]
                                ]
                            elif id_line_parts[0] == "target":
                                target_metanode = metanodeid2obj[
                                    id_line_parts[1]
                                ]
            # Determine root of the bicomponent and store it as part of the
            # bicomponent
            curr_metanode = list(metanodeid2obj.values())[0]
            while len(curr_metanode.incoming_nodes) > 0:
                # A metanode in the tree can have at most 1 parent (because that is
                # how trees work), so it's ok to just move up in the tree like so
                # (because the .incoming_node lists of SPQRMetaNode objects will
                # always have length 1)
                curr_metanode = curr_metanode.incoming_nodes[0]
            # At this point, we've obtained the full contents of the tree: both the
            # skeletons of its metanodes, and the edges between metanodes. (This
            # data is stored as attributes of the SPQRMetaNode objects in
            # question.)
            metanode_list = list(metanodeid2obj.values())
            bicomponentid2obj[cfn_id] = graph_objects.Bicomponent(
                cfn_id, metanode_list, curr_metanode
            )
            total_bicomponent_count += 1
        conclude_msg()

    operation_msg(config.FRAYEDROPE_SEARCH_MSG)
    for (
        n
    ) in nodes_to_try_collapsing:  # Test n as the "starting" node for a rope
        if n.used_in_collapsing or len(n.outgoing_nodes) != 1:
            # If n doesn't lead to a single node, it couldn't be a rope start
            continue
        rope_validity, member_nodes = graph_objects.Rope.is_valid_rope(n)
        if rope_validity:
            # Found a frayed rope!
            new_rope = graph_objects.Rope(*member_nodes)
            nodes_to_draw.append(new_rope)
            clusterid2obj[new_rope.id_string] = new_rope

    conclude_msg()
    operation_msg(config.CYCLE_SEARCH_MSG)
    for (
        n
    ) in nodes_to_try_collapsing:  # Test n as the "starting" node for a cycle
        if n.used_in_collapsing:
            continue
        cycle_validity, member_nodes = graph_objects.Cycle.is_valid_cycle(n)
        if cycle_validity:
            # Found a cycle!
            new_cycle = graph_objects.Cycle(*member_nodes)
            nodes_to_draw.append(new_cycle)
            clusterid2obj[new_cycle.id_string] = new_cycle

    conclude_msg()
    operation_msg(config.CHAIN_SEARCH_MSG)
    for (
        n
    ) in nodes_to_try_collapsing:  # Test n as the "starting" node for a chain
        if n.used_in_collapsing or len(n.outgoing_nodes) != 1:
            # If n doesn't lead to a single node, it couldn't be a chain start
            continue
        chain_validity, member_nodes = graph_objects.Chain.is_valid_chain(n)
        if chain_validity:
            # Found a chain!
            new_chain = graph_objects.Chain(*member_nodes)
            nodes_to_draw.append(new_chain)
            clusterid2obj[new_chain.id_string] = new_chain

    conclude_msg()

    # Output files containing IDs of nodes in each type of cluster
    if output_spatts:
        clustertype2instances = {}
        for clust in clusterid2obj.values():
            t = type(clust)
            if t not in clustertype2instances:
                clustertype2instances[t] = [clust]
            else:
                clustertype2instances[t].append(clust)

        for ct in clustertype2instances:
            input_text = ""
            for clust in clustertype2instances[ct]:
                for child in clust.nodes:
                    input_text += "%s\t%s" % (
                        clust.cy_id_string,
                        child.id_string,
                    )
                    input_text += "\n"
            save_aux_file(
                "sp_" + ct.plural_name + ".txt",
                input_text,
                output_dir,
                False,
                overwrite,
            )

    # Add individual (not used in collapsing) nodes to the nodes_to_draw list
    # We could build this list up at the start and then gradually remove nodes as
    # we use nodes in collapsing, but remove() is an O(n) operation so that'd make
    # the above runtime O(4n^2) or something, so I figure just doing this here is
    # generally faster.
    for n in nodes_to_try_collapsing:
        if not n.used_in_collapsing:
            nodes_to_draw.append(n)

    # Identify connected components in the "single" graph
    # We'll need to actually run DFS if distinct_single_graph is True.
    # However, if it's False, then we can just run DFS on the "double" graph to
    # identify its connected components -- and then use those connected components'
    # nodes' IDs to construct the single graph's connected components.
    operation_msg(config.COMPONENT_MSG)
    if args.computespqrdata:
        single_connected_components = []
        if distinct_single_graph:
            for n in singlenodeid2obj.values():
                if not n.seen_in_ccomponent:
                    # We've identified a node within an unseen connected component.
                    # Run DFS to identify all nodes in its connected component.
                    # (Also identify all bicomponents in the connected component)
                    node_list = dfs(n)
                    bicomponent_set = set()
                    for m in node_list:
                        m.seen_in_ccomponent = True
                        bicomponent_set = bicomponent_set.union(
                            m.parent_bicomponents
                        )
                    single_connected_components.append(
                        graph_objects.Component(node_list, bicomponent_set)
                    )
                    total_single_component_count += 1

    # Identify connected components in the normal (non-"single") graph
    # NOTE that nodes_to_draw only contains node groups and nodes that aren't in
    # node groups. This allows us to run DFS on the nodes "inside" the node
    # groups, preserving the groups' existence while not counting them in DFS.
    connected_components = []
    for n in nodes_to_draw:
        if not n.seen_in_ccomponent and not n.is_subsumed:
            # If n is actually a group of nodes: since we're representing
            # groups here as clusters, without any adjacencies themselves, we
            # have to run DFS on the nodes within the groups of nodes to
            # discover them.
            node_list = []
            node_group_list = []
            if issubclass(type(n), graph_objects.NodeGroup):
                # n is a node group
                if n.nodes[0].seen_in_ccomponent:
                    continue
                node_list = dfs(n.nodes[0])
            else:
                # It's just a normal Node, but it could certainly be connected
                # to a group of nodes (not that it really matters)
                node_list = dfs(n)

            # Now that we've ran DFS to discover all the nodes in this
            # connected component, we go through each node to identify their
            # groups (if applicable) and add those to node_group_list if the
            # group is not already on that list. (TODO, there's probably a
            # more efficient way to do this using sets/etc.)
            for m in node_list:
                m.seen_in_ccomponent = True
                if m.used_in_collapsing and m.group not in node_group_list:
                    node_group_list.append(m.group)
            connected_components.append(
                graph_objects.Component(node_list, node_group_list)
            )
            total_component_count += 1
    connected_components.sort(reverse=True, key=lambda c: len(c.node_list))

    # Loop through connected_components. For each cc:
    #   Set edge_weights = []
    #   For all nodes in the cc:
    #     For all outgoing edges of the node:
    #       Append the edge's multiplicity to edge_weights
    #   Get min_mult = min(edge_weights), max_mult = max(edge_weights)
    #   For all nodes in the cc, again:
    #     For all outgoing edges of the node:
    #       Scale the edge's thickness relative to min/max mult (see xdot2cy.js)
    # ... later we'll do IQR stuff (using numpy.percentile(), maybe?)

    if args.computespqrdata:
        if not distinct_single_graph:
            # Get single_connected_components from connected_components
            for c in connected_components:
                single_node_list = []
                bicomponent_set = set()
                for n in c.node_list:
                    s = singlenodeid2obj[n.id_string]
                    single_node_list.append(s)
                    bicomponent_set = bicomponent_set.union(
                        s.parent_bicomponents
                    )
                single_connected_components.append(
                    graph_objects.Component(single_node_list, bicomponent_set)
                )
                total_single_component_count += 1

        # At this point, we have single_connected_components ready. We're now able
        # to iterate through it and lay out each connected component, with
        # biconnected components replaced with solid rectangles.
        single_connected_components.sort(
            reverse=True, key=lambda c: len(c.node_list)
        )

    conclude_msg()
    # Scale contigs' log sizes relatively.
    # Due to the initial logarithmic scaling, we don't bother using outlier
    # detection (e.g. using Tukey fences, as is done with edge thicknesses).
    operation_msg(config.CONTIG_SCALING_MSG)
    if args.computespqrdata:
        component_collections = (
            connected_components,
            single_connected_components,
        )
    else:
        component_collections = (connected_components,)
    for c_collection in component_collections:
        for c in c_collection:
            # bp_length_list does exist, but it's across all components. Probably
            # easiest to just go through each component here, then -- shouldn't
            # take a significant amount of time.
            # TODO hold off on computing logs until we get past checking if
            # len(c.node_list) >= 2? Not really a huge optimization, though.
            contig_lengths = []
            for n in c.node_list:
                contig_lengths.append(n.logbp)
            # Perform relative scaling for the log lengths of contigs in the
            # component to determine 1) the area of the contig and 2) the
            # long-side proportion for the contig.
            # (This only happens if not all contigs in the component are of the
            # same length; this precondition also excludes components containing
            # just one contig.)
            # If this condition isn't met, then the contig "relative length" for
            # area scaling will remain at the default value of 0.5, and its
            # long-side proportion will remain at the default value of
            # config.MID_LONGSIDE_PROPORTION.
            # (We can avoid having to compute the min_bp and max_bp figures if the
            # component only contains one contig by just checking up front if the
            # component has >= 2 contigs. Granted, len(), min(), and max() are all
            # super quick for 1-length lists, so performance tweaks here are
            # probably negligible except for extremely large assembly graphs.)
            if len(c.node_list) >= 2:
                min_bp = min(contig_lengths)
                max_bp = max(contig_lengths)
                if min_bp == max_bp:
                    # All the contigs have the same length: we don't need to bother
                    # with scaling them relatively, and attempting to do so would
                    # just result in a division-by-zero error
                    continue
                bp_range = float(max_bp - min_bp)
                q25, q75 = numpy.percentile(contig_lengths, [25, 75])
                # NOTE: I don't know why I had the following line of code here,
                # but I'm keeping it in as a comment just in case it ends up
                # being important later.
                # scaling_node_groups = False
                for n in c.node_list:
                    n.relative_length = (n.logbp - min_bp) / bp_range
                    if n.logbp < q25:
                        n.longside_proportion = config.LOW_LONGSIDE_PROPORTION
                    elif n.logbp < q75:
                        n.longside_proportion = config.MID_LONGSIDE_PROPORTION
                    else:
                        n.longside_proportion = config.HIGH_LONGSIDE_PROPORTION
        # TODO: After going through all components in the first component
        # collection, the only components left to perform scaling for are
        # single components (used for the SPQR modes). Since "node groups"
        # (effectively, Bicomponents) in these components don't need to have
        # collapsed dimensions, we can set a flag variable to let us know to
        # not bother doing that for those node groups.
        # scaling_single_ccs = True
    conclude_msg()

    # Scale "non-outlier" edges relatively. We use "Tukey fences" to identify
    # outlier edge weights (see issue #184 on GitHub for context on this).
    # Note that the "fences" we use are the "inner" fences that Tukey describes in
    # Exploratory Data Analysis (1977).
    if edge_weights_available:
        operation_msg(config.EDGE_SCALING_MSG)
        for c in connected_components:
            edge_weights = []
            for n in c.node_list:
                for e in n.outgoing_edge_objects.values():
                    edge_weights.append(e.multiplicity)
            # At this point, we have a list of every edge weight contained within
            # this connected component.
            non_outlier_edges = []
            non_outlier_edge_weights = []
            # (If there are < 4 edges in this connected component, don't bother
            # with flagging outliers -- at that point, computing quartiles becomes
            # a bit silly)
            if len(edge_weights) >= 4:
                # Now, calculate lower and upper Tukey fences.
                # First, calculate lower and upper quartiles (aka the
                # 25th and 75th percentiles)
                lq, uq = numpy.percentile(edge_weights, [25, 75])
                # Then, determine 1.5 * the interquartile range
                # (we can use other values than 1.5 if desired -- not set in stone)
                d = 1.5 * (uq - lq)
                # Now we can calculate the actual Tukey fences:
                lf = lq - d
                uf = uq + d
                # Now, iterate through every edge again and flag outliers.
                # Non-outlier edges will be added to a list of edges that we will
                # scale relatively
                for n in c.node_list:
                    for e in n.outgoing_edge_objects.values():
                        if e.multiplicity > uf:
                            e.is_outlier = 1
                            e.thickness = 1
                        elif e.multiplicity < lf:
                            e.is_outlier = -1
                            e.thickness = 0
                        else:
                            non_outlier_edges.append(e)
                            non_outlier_edge_weights.append(e.multiplicity)
            else:
                for n in c.node_list:
                    for e in n.outgoing_edge_objects.values():
                        non_outlier_edges.append(e)
                        non_outlier_edge_weights.append(e.multiplicity)
            # Perform relative scaling for non_outlier_edges
            # (Assuming, of course, that we have at least 2 non_outlier_edges)
            if len(non_outlier_edges) >= 2:
                min_ew = min(non_outlier_edge_weights)
                max_ew = max(non_outlier_edge_weights)
                if min_ew == max_ew:
                    # All the outliers have the same value: we don't need to bother
                    # with scaling the non-outliers
                    continue
                ew_range = float(max_ew - min_ew)
                for e in non_outlier_edges:
                    e.thickness = (e.multiplicity - min_ew) / ew_range
        conclude_msg()

    operation_msg(config.DB_INIT_MSG + "%s..." % (db_fn))
    # Now that we've done all our processing on the assembly graph, we create the
    # output file: a SQLite database in which we store biological and graph layout
    # information. This will be opened in the Javascript graph viewer.
    #
    # Note that there's technically a race condition here, but SQLite handles
    # itself so well that we don't need to bother catching it. If, somehow, a
    # file with the name db_fullfn is created in between when we run
    # check_file_existence(db_fullfn) and sqlite3.connect(db_fullfn), then that
    # file will either:
    # -Be repurposed as a database containing this data in addition to
    #  its original data (if the file is a SQLite database, but stores other
    #  data -- expected behavior for this case)
    # -Cause the first cursor.execute() call to fail since the database already
    #  has a nodes table (if the file is a SQLite database this program has
    #  generated -- expected behavior for this case)
    # -Cause the first cursor.execute() call to fail since the file is not a
    #  SQLite database (expected behavior for this case)
    # Essentially, we're okay here -- SQLite will handle the race condition
    # properly, should one arise. (I doubt that race conditions will happen
    # here, but I suppose you can't be too safe.)
    connection = sqlite3.connect(db_fullfn)
    cursor = connection.cursor()
    # Define statements used for inserting a value into these tables
    # The number of question marks has to match the number of table columns
    NODE_INSERTION_STMT = (
        "INSERT INTO nodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    EDGE_INSERTION_STMT = "INSERT INTO edges VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    CLUSTER_INSERTION_STMT = (
        "INSERT INTO clusters VALUES (?,?,?,?,?,?,?,?,?,?)"
    )
    COMPONENT_INSERTION_STMT = "INSERT INTO components VALUES (?,?,?,?,?,?,?)"
    ASSEMBLY_INSERTION_STMT = (
        "INSERT INTO assembly VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    SINGLENODE_INSERTION_STMT = (
        "INSERT INTO singlenodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    SINGLEEDGE_INSERTION_STMT = "INSERT INTO singleedges VALUES (?,?,?,?,?)"
    BICOMPONENT_INSERTION_STMT = (
        "INSERT INTO bicomponents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    METANODE_INSERTION_STMT = (
        "INSERT INTO metanodes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    METANODEEDGE_INSERTION_STMT = (
        "INSERT INTO metanodeedges VALUES (?,?,?,?,?,?)"
    )
    SINGLECOMPONENT_INSERTION_STMT = (
        "INSERT INTO singlecomponents VALUES (?,?,?,?,?,?,?,?,?,?,?,?)"
    )
    cursor.execute(
        """CREATE TABLE nodes
            (id text, label text, length integer, gc_content real, depth real,
            is_repeat integer, component_rank integer, x real, y real, w real,
            h real, shape text, parent_cluster_id text)"""
    )
    cursor.execute(
        """CREATE TABLE edges
            (source_id text, target_id text, multiplicity integer, thickness real,
            is_outlier integer, orientation text, mean real, stdev real,
            component_rank integer, control_point_string text,
            control_point_count integer, parent_cluster_id text)"""
    )
    cursor.execute(
        """CREATE TABLE clusters (cluster_id text, length integer,
            component_rank integer, left real, bottom real, right real, top real,
            w real, h real, cluster_type text)"""
    )
    cursor.execute(
        """CREATE TABLE components
            (size_rank integer, node_count integer, edge_count integer,
            total_length integer, boundingbox_x real, boundingbox_y real,
            too_large integer)"""
    )
    cursor.execute(
        """CREATE TABLE assembly
            (filename text, filetype text, node_count integer,
            edge_count integer, all_edge_count integer, component_count integer,
            bicomponent_count integer, single_component_count integer,
            total_length integer, n50 integer, gc_content real,
            dna_given integer, repeats_given integer, spqr_given integer,
            smallest_viewable_component_rank integer)"""
    )
    if args.computespqrdata:
        # SPQR view tables
        cursor.execute(
            """CREATE TABLE singlenodes
                (id text, label text, length integer, gc_content real, depth real,
                is_repeat integer, scc_rank integer, x real, y real, i_x real,
                i_y real, w real, h real, parent_metanode_id text,
                parent_bicomponent_id text)"""
        )
        cursor.execute(
            """CREATE TABLE singleedges
                (source_id text, target_id text, scc_rank integer,
                parent_metanode_id text, is_virtual integer)"""
        )
        cursor.execute(
            """CREATE TABLE bicomponents
                (id_num integer, root_metanode_id string, scc_rank integer,
                node_count integer, left real, bottom real, right real, top real,
                i_left real, i_bottom real, i_right real, i_top real)"""
        )
        cursor.execute(
            """CREATE TABLE metanodes
                (metanode_id text, scc_rank integer,
                parent_bicomponent_id_num integer,
                descendant_metanode_count integer, node_count integer,
                total_length integer, left real, bottom real, right real,
                top real, i_left real, i_bottom real, i_right real, i_top real)"""
        )
        cursor.execute(
            """CREATE TABLE metanodeedges
                (source_metanode_id text, target_metanode_id text,
                scc_rank integer, control_point_string text,
                control_point_count integer, parent_bicomponent_id_num integer)"""
        )
        cursor.execute(
            """CREATE TABLE singlecomponents
                (size_rank integer, ex_uncompressed_node_count integer,
                ex_uncompressed_edge_count integer,
                im_uncompressed_node_count integer,
                im_uncompressed_edge_count integer, compressed_node_count integer,
                compressed_edge_count integer, bicomponent_count integer,
                boundingbox_x real, boundingbox_y real, i_boundingbox_x real,
                i_boundingbox_y real)"""
        )
    connection.commit()

    conclude_msg()

    # Total time taken for the layout in all "modes"
    total_layout_time = 0

    # Lay out both the implicit and explicit SPQR tree views; store stuff for the
    # SPQR decomposition modes in the database
    # NOTE that the order of implicit then explicit layout matters, since things
    # are written to the database after laying out the explicit mode but not
    # after laying out the implicit mode (that's done because many rows in the
    # database are used for both layouts)

    if args.computespqrdata:
        # list of all the (right, top) coords of the bounding boxes of each
        # implicit single connected component
        implicit_spqr_bounding_boxes = []
        # lists of uncompressed node counts and of uncompressed edge counts for
        # each implicit single connected component (see #223 on GitHub)
        implicit_spqr_node_counts = []
        implicit_spqr_edge_counts = []
        # Some of the explicit mode calculations rely on the implicit layout
        # already having been performed, so please don't switch the ordering
        # around to ("explicit", "implicit") or something
        for mode in ("implicit", "explicit"):
            t1 = time.time()
            single_component_size_rank = 1
            no_print = False
            for scc in single_connected_components:
                # Layout this "single" connected component of the SPQR view

                first_small_component = False
                if not no_print:
                    # We want to figure out the uncollapsed node count for this
                    # scc, to give the user a preview of how long layout will
                    # take for the current scc.
                    unc_component_node_ct = 0
                    # Add number of "unaffiliated" nodes (nodes with no parent
                    # bicmp.)
                    for n in scc.node_list:
                        if len(n.parent_bicomponents) == 0:
                            unc_component_node_ct += 1
                    if mode == "implicit":
                        # Add number of nodes in each bicomponent (the same node
                        # might be present in multiple bicomponents, hence why
                        # we have to figure all this out)
                        for bicmp in scc.node_group_list:
                            unc_component_node_ct += len(bicmp.snid2obj)
                    else:
                        # Add number of nodes in each metanode in each bicomponent
                        # (the same node could be present in both multiple
                        # metanodes and multiple bicomponents)
                        for bicmp in scc.node_group_list:
                            unc_component_node_ct += bicmp.singlenode_count
                    if unc_component_node_ct < 5:
                        # The current component is included in the small "single"
                        # component count
                        small_component_ct = (
                            total_single_component_count
                            - single_component_size_rank
                            + 1
                        )
                        if small_component_ct > 1:
                            no_print = True
                            first_small_component = True
                            operation_msg(
                                config.LAYOUT_MSG
                                + "%d " % (small_component_ct)
                                + config.SMALL_COMPONENTS_MSG
                            )
                        # If only one small component is left, just treat it as a
                        # normal component: there's no point pointing it out as a
                        # small component
                    if not no_print:
                        operation_msg(
                            config.LAYOUT_MSG
                            + mode
                            + config.SPQR_COMPONENTS_MSG
                            + "%d (%d total nodes)..."
                            % (
                                single_component_size_rank,
                                unc_component_node_ct,
                            )
                        )

                # Lay out each Bicomponent in this component (this also lays out
                # its child metanodes, if we're in explicit mode)
                for bicomp in scc.node_group_list:
                    if mode == "explicit":
                        bicomp.explicit_layout_isolated()
                    else:
                        bicomp.implicit_layout_isolated()
                scc_prefix = "%s_%s_spqr_%d" % (
                    output_fn,
                    mode[:2],
                    single_component_size_rank,
                )
                gv_input = ""
                gv_input += "graph single_ccomp {\n"
                if config.GRAPH_STYLE != "":
                    gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
                gv_input += '\toverlap="false";\n'
                if config.GLOBALNODE_STYLE != "":
                    gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
                # In the layout of this single connected component, include:
                # -rectangle nodes representing each bicomponent (will be
                #  backfilled)
                # -nodes that aren't present in any biconnected components
                # -edges that are not "in" any biconnected components (includes
                #  edges incident on biconnected components)

                # Keep track of counts of singlenodes and singleedges that are
                # specifically contained within either the root metanodes of the
                # graph, or outside of any bicomponents. Since these nodes and
                # edges are going to be drawn when the SPQR view is initially
                # rendered, we need to know these counts so we can update the
                # progress bar accordingly.
                sc_compressed_node_count = 0
                sc_compressed_edge_count = 0
                sc_bicomponent_count = len(scc.node_group_list)
                for bicomp in scc.node_group_list:
                    if mode == "implicit":
                        gv_input += bicomp.implicit_backfill_node_info()
                    else:
                        gv_input += bicomp.node_info()
                    sc_compressed_node_count += len(bicomp.root_metanode.nodes)
                    sc_compressed_edge_count += len(
                        bicomp.root_metanode.internal_edges
                    )
                for m in scc.node_list:
                    # Get node info for nodes not present in any bicomponents
                    # Also get edge info for edges "external" to bicomponents
                    if len(m.parent_bicomponents) == 0:
                        gv_input += m.node_info()
                        sc_compressed_node_count += 1
                        # We know m is not in a bicomponent. Get its "outgoing"
                        # edge info.
                        for n in m.outgoing_nodes:
                            if len(n.parent_bicomponents) == 0:
                                # This edge is between two nodes, neither of which
                                # is in a bicomponent. We can lay this edge out.
                                gv_input += "\t%s -- %s;\n" % (
                                    m.id_string,
                                    n.id_string,
                                )
                                sc_compressed_edge_count += 1
                            else:
                                # m is not in a bicomponent, but n is. Lay out
                                # edges between m and all of the parent
                                # bicomponents of n.
                                for b in n.parent_bicomponents:
                                    gv_input += "\t%s -- cluster_%s;\n" % (
                                        m.id_string,
                                        b.id_string,
                                    )
                                    sc_compressed_edge_count += 1
                    else:
                        # We know m is in at least one bicomponent.
                        # Get its "outgoing" edge info (in case there are edges
                        # incident on m from outside one of its parent
                        # bicomponents)
                        for n in m.outgoing_nodes:
                            if len(n.parent_bicomponents) == 0:
                                # m is in a bicomponent, but n is not. Lay out
                                # edges between n and all of the parent
                                # bicomponents of m.
                                for b in m.parent_bicomponents:
                                    gv_input += "\tcluster_%s -- %s;\n" % (
                                        b.id_string,
                                        n.id_string,
                                    )
                                    sc_compressed_edge_count += 1
                            else:
                                # Both nodes are in at least one bicomponent.
                                if (
                                    len(
                                        m.parent_bicomponents.intersection(
                                            n.parent_bicomponents
                                        )
                                    )
                                    > 0
                                ):
                                    # Since these two nodes share at least one
                                    # bicomponent, the edge between them must be
                                    # present within a bicomponent. Therefore
                                    # rendering that edge would be redundant.
                                    continue
                                else:
                                    # Although both nodes are in >= 1 bicmps,
                                    # they're in different bicomponents
                                    # (this is entirely possible; consider the case
                                    # where two 4-node "bubbles" in an undirected
                                    # graph are joined by a single edge between
                                    # two of their nodes).
                                    # Thus, this edge info is not present in either
                                    # set of bicomponents. So we should lay out
                                    # edge(s) between the parent bicomponents of m
                                    # and n.
                                    for b1 in m.parent_bicomponents:
                                        for b2 in n.parent_bicomponents:
                                            gv_input += (
                                                "\tcluster_%s -- cluster_%s;\n"
                                                % (b1.id_string, b2.id_string)
                                            )
                                            sc_compressed_edge_count += 1
                gv_input += "}"
                if (
                    len(scc.node_group_list) == 0
                    and sc_compressed_edge_count == 0
                    and len(scc.node_list) == 1
                ):
                    curr_node = scc.node_list[0]
                    wpts = curr_node.width * config.POINTS_PER_INCH
                    hpts = curr_node.height * config.POINTS_PER_INCH
                    if mode == "implicit":
                        # first time looking at this node and component
                        curr_node.set_dimensions()
                        curr_node.xdot_ix = wpts / 2
                        curr_node.xdot_iy = hpts / 2
                        implicit_spqr_bounding_boxes.append((wpts, hpts))
                        implicit_spqr_node_counts.append(1)
                        implicit_spqr_edge_counts.append(0)
                    else:
                        curr_node.xdot_x = wpts / 2
                        curr_node.xdot_y = hpts / 2
                        curr_node.set_component_rank(
                            single_component_size_rank
                        )
                        curr_node.xdot_shape = curr_node.get_shape()
                        cursor.execute(
                            SINGLENODE_INSERTION_STMT, curr_node.s_db_values()
                        )
                        # we don't bother getting values from
                        # implicit_spqr_bounding_boxes/_node_counts/_edge_counts
                        # because we already know those values
                        cursor.execute(
                            SINGLECOMPONENT_INSERTION_STMT,
                            (
                                single_component_size_rank,
                                1,
                                0,
                                1,
                                0,
                                1,
                                0,
                                0,
                                wpts,
                                hpts,
                                wpts,
                                hpts,
                            ),
                        )
                    if (
                        total_single_component_count
                        == single_component_size_rank
                    ):
                        conclude_msg()
                    single_component_size_rank += 1
                    continue
                h = pygraphviz.AGraph(gv_input)

                layout_msg_printed = (not no_print) or first_small_component
                r = True
                # save the .gv file if the user requested .gv preservation
                if preserve_gv:
                    r = save_aux_file(
                        scc_prefix + ".gv",
                        gv_input,
                        output_dir,
                        layout_msg_printed,
                        overwrite,
                    )
                # lay out the graph (singlenodes and singleedges outside of
                # bicomponents, and bicomponent general structures)
                h.layout(prog="sfdp")
                # h.draw(scc_prefix + ".png")
                # save the .xdot file if the user requested .xdot preservation
                if preserve_xdot:
                    if not r:
                        layout_msg_printed = False
                    save_aux_file(
                        scc_prefix + ".xdot",
                        h,
                        output_dir,
                        layout_msg_printed,
                        overwrite,
                    )

                sc_node_count = 0
                sc_edge_count = 0
                # Retrieve layout information and use it to populate the .db file
                # with the necessary information to render the SPQR-integrated
                # graph view will be the bounding box of this single connected
                # component's graph
                bounding_box_right = 0
                bounding_box_top = 0
                # Record layout info of nodes (incl. temporarily-"empty"
                # Bicomponents)
                for n in h.nodes():
                    try:
                        curr_node = singlenodeid2obj[str(n)]
                        # Since we didn't just get a KeyError, curr_node must be a
                        # single node that was just laid out (and not a
                        # Bicomponent). So we can process its position, width, etc.
                        # info accordingly.
                        posns = tuple(
                            float(c) for c in n.attr[u"pos"].split(",")
                        )
                        exx = exy = None
                        if mode == "explicit":
                            curr_node.xdot_x, curr_node.xdot_y = posns
                            exx = curr_node.xdot_x
                            exy = curr_node.xdot_y
                        else:
                            curr_node.xdot_ix, curr_node.xdot_iy = posns
                            exx = curr_node.xdot_ix
                            exy = curr_node.xdot_iy
                        # Try to expand the component bounding box
                        right_side = exx + (
                            config.POINTS_PER_INCH * (curr_node.width / 2.0)
                        )
                        top_side = exy + (
                            config.POINTS_PER_INCH * (curr_node.height / 2.0)
                        )
                        if right_side > bounding_box_right:
                            bounding_box_right = right_side
                        if top_side > bounding_box_top:
                            bounding_box_top = top_side
                        # Save this single node in the .db
                        sc_node_count += 1
                        if mode == "explicit":
                            curr_node.set_component_rank(
                                single_component_size_rank
                            )
                            cursor.execute(
                                SINGLENODE_INSERTION_STMT,
                                curr_node.s_db_values(),
                            )
                    except KeyError:
                        # This error would arise from us trying to find
                        # singlenodeid2obj[a bicomponent id].
                        # We use [9:] to slice off the "cluster_I" prefix on every
                        # bicomponent node here
                        curr_cluster = bicomponentid2obj[str(n)[9:]]
                        ep = n.attr[u"pos"].split(",")
                        # We use half_width_pts for both the implicit and explicit
                        # SPQR modes, so can we avoid a bit of redundant code via
                        # just setting the xdot_width and xdot_height variables
                        # based on which mode we're in.
                        if mode == "explicit":
                            curr_cluster.xdot_x = float(ep[0])
                            curr_cluster.xdot_y = float(ep[1])
                            xdot_width = curr_cluster.xdot_c_width
                            xdot_height = curr_cluster.xdot_c_height
                        else:
                            curr_cluster.xdot_ix = float(ep[0])
                            curr_cluster.xdot_iy = float(ep[1])
                            xdot_width = curr_cluster.xdot_ic_width
                            xdot_height = curr_cluster.xdot_ic_height
                        half_width_pts = config.POINTS_PER_INCH * (
                            xdot_width / 2.0
                        )
                        half_height_pts = config.POINTS_PER_INCH * (
                            xdot_height / 2.0
                        )
                        exr = ext = None
                        if mode == "explicit":
                            curr_cluster.xdot_left = (
                                curr_cluster.xdot_x - half_width_pts
                            )
                            curr_cluster.xdot_right = (
                                curr_cluster.xdot_x + half_width_pts
                            )
                            curr_cluster.xdot_bottom = (
                                curr_cluster.xdot_y - half_height_pts
                            )
                            curr_cluster.xdot_top = (
                                curr_cluster.xdot_y + half_height_pts
                            )
                            exr = curr_cluster.xdot_right
                            ext = curr_cluster.xdot_top
                        else:
                            curr_cluster.xdot_ileft = (
                                curr_cluster.xdot_ix - half_width_pts
                            )
                            curr_cluster.xdot_iright = (
                                curr_cluster.xdot_ix + half_width_pts
                            )
                            curr_cluster.xdot_ibottom = (
                                curr_cluster.xdot_iy - half_height_pts
                            )
                            curr_cluster.xdot_itop = (
                                curr_cluster.xdot_iy + half_height_pts
                            )
                            exr = curr_cluster.xdot_iright
                            ext = curr_cluster.xdot_itop
                        # Try to expand the component bounding box
                        if exr > bounding_box_right:
                            bounding_box_right = exr
                        if ext > bounding_box_top:
                            bounding_box_top = ext
                        # Reconcile metanodes in this bicomponent
                        # No need to attempt to expand the component bounding box
                        # here, since we know that all children of the bicomponent
                        # must fit inside the bicomponent's area
                        if mode == "implicit":
                            sc_node_count += len(curr_cluster.snid2obj)
                            sc_edge_count += len(curr_cluster.real_edges)
                            # compute positions of metanodes relative to child
                            # nodes
                            for mn in curr_cluster.metanode_list:
                                mn.assign_implicit_spqr_borders()
                            continue
                        for mn in curr_cluster.metanode_list:
                            mn.xdot_x = curr_cluster.xdot_left + mn.xdot_rel_x
                            mn.xdot_y = (
                                curr_cluster.xdot_bottom + mn.xdot_rel_y
                            )
                            mn_hw_pts = config.POINTS_PER_INCH * (
                                mn.xdot_c_width / 2.0
                            )
                            mn_hh_pts = config.POINTS_PER_INCH * (
                                mn.xdot_c_height / 2.0
                            )
                            mn.xdot_left = mn.xdot_x - mn_hw_pts
                            mn.xdot_right = mn.xdot_x + mn_hw_pts
                            mn.xdot_bottom = mn.xdot_y - mn_hh_pts
                            mn.xdot_top = mn.xdot_y + mn_hh_pts
                            mn.xdot_ileft += curr_cluster.xdot_ileft
                            mn.xdot_iright += curr_cluster.xdot_ileft
                            mn.xdot_itop += curr_cluster.xdot_ibottom
                            mn.xdot_ibottom += curr_cluster.xdot_ibottom
                            mn.set_component_rank(single_component_size_rank)
                            cursor.execute(
                                METANODE_INSERTION_STMT, mn.db_values()
                            )
                            # Add nodes in this metanode (...in this bicomponent)
                            # to the .db file. I'm a bit miffed that "double
                            # backfilling" is the fanciest name I can come up with
                            # for this process now.
                            for sn in mn.nodes:
                                # Node.s_db_values() uses the parent metanode
                                # information to set the position of the node in
                                # question.
                                # This is done this way because the "same" node can
                                # be in multiple metanodes in a SPQR tree, and --
                                # even crazier, I know -- the same node can be in
                                # multiple bicomponents.
                                sc_node_count += 1
                                sn.set_component_rank(
                                    single_component_size_rank
                                )
                                cursor.execute(
                                    SINGLENODE_INSERTION_STMT,
                                    sn.s_db_values(mn),
                                )
                            # Add edges between nodes within this metanode's
                            # skeleton to the .db file. We just treat these edges
                            # as straight lines in the viewer, so we don't bother
                            # saving their layout info.
                            for se in mn.edges:
                                se.xdot_ctrl_pt_str = (
                                    se.xdot_ctrl_pt_count
                                ) = None
                                # Save this edge in the .db
                                sc_edge_count += 1
                                se.component_size_rank = (
                                    single_component_size_rank
                                )
                                cursor.execute(
                                    SINGLEEDGE_INSERTION_STMT, se.s_db_values()
                                )
                        # Reconcile edges between metanodes in this bicomponent
                        for e in curr_cluster.edges:
                            # Adjust the control points to be relative to the
                            # entire component. Also, try to expand to the
                            # component bounding box.
                            p = 0
                            coord_list = [
                                float(c)
                                for c in e.xdot_rel_ctrl_pt_str.split()
                            ]
                            e.xdot_ctrl_pt_str = ""
                            while p <= len(coord_list) - 2:
                                if p > 0:
                                    e.xdot_ctrl_pt_str += " "
                                xp = coord_list[p]
                                yp = coord_list[p + 1]
                                e.xdot_ctrl_pt_str += str(
                                    curr_cluster.xdot_left + xp
                                )
                                e.xdot_ctrl_pt_str += " "
                                e.xdot_ctrl_pt_str += str(
                                    curr_cluster.xdot_bottom + yp
                                )
                                # Try to expand the component bounding box --
                                # interior edges should normally be entirely within
                                # the bounding box of their node group, but some
                                # might have interior edges that go outside of the
                                # node group's bounding box
                                if xp > bounding_box_right:
                                    bounding_box_right = xp
                                if yp > bounding_box_top:
                                    bounding_box_top = yp
                                p += 2
                            # Save this edge in the .db
                            sc_edge_count += 1
                            cursor.execute(
                                METANODEEDGE_INSERTION_STMT,
                                e.metanode_edge_db_values(),
                            )
                        # Save this bicomponent's information in the .db
                        curr_cluster.component_size_rank = (
                            single_component_size_rank
                        )
                        cursor.execute(
                            BICOMPONENT_INSERTION_STMT,
                            curr_cluster.db_values(),
                        )
                # We don't need to get edge info or store anything in the .db just
                # yet, so just move on to the next single connected component.
                # We'll populate the .db file during the explicit layout process.
                if mode == "implicit":
                    # Call conclude_msg() after a non-small component is done, or
                    # when the last small component is done.
                    if (
                        not no_print
                        or total_single_component_count
                        == single_component_size_rank
                    ):
                        conclude_msg()
                    implicit_spqr_bounding_boxes.append(
                        (bounding_box_right, bounding_box_top)
                    )
                    # Account for edges not in any bicomponents
                    sc_edge_count += len(h.edges())
                    implicit_spqr_node_counts.append(sc_node_count)
                    implicit_spqr_edge_counts.append(sc_edge_count)
                    single_component_size_rank += 1
                    continue
                # Record layout info of edges that aren't inside any bicomponents.
                # Due to the possible construction of duplicates of these edges,
                # we don't actually create Edge objects for these particular edges.
                # So we have to fill in the single edge insertion statement
                # ourselves (I guess we could just declare Edge objects right here,
                # but that'd be kind of silly)
                for e in h.edges():
                    source_id = e[0]
                    target_id = e[1]
                    # slice off the "cluster_" prefix if this edge is incident on
                    # one or more biconnected components (this'll save space in
                    # the database, and it'll make interpreting this edge in the
                    # viewer application easier)
                    if source_id.startswith("cluster_"):
                        source_id = source_id[8:]
                    if target_id.startswith("cluster_"):
                        target_id = target_id[8:]
                    (
                        xdot_ctrl_pt_str,
                        coord_list,
                        xdot_ctrl_pt_count,
                    ) = graph_objects.Edge.get_control_points(e.attr[u"pos"])
                    # Try to expand the component bounding box (just to be safe)
                    p = 0
                    while p <= len(coord_list) - 2:
                        x_coord = coord_list[p]
                        y_coord = coord_list[p + 1]
                        if x_coord > bounding_box_right:
                            bounding_box_right = x_coord
                        if y_coord > bounding_box_top:
                            bounding_box_top = y_coord
                        p += 2
                    # Save this edge in the .db
                    # NOTE -- as of now we don't bother rendering this edge's
                    # control points in the viewer interface, since
                    # most of these edges end up being normal straight
                    # lines/bezier curves anyway (at least the ones from sfdp).
                    # If we decide to change this behavior to display these
                    # edges with control point info, then we can modify
                    # SINGLEEDGE_INSERTION_STMT above (as well as the database
                    # schema for the singleedges table) to store this data
                    # accordingly.
                    # (At this point, we've already computed xdot_ctrl_pt_str
                    # and xdot_ctrl_pt_count, so all that would really remain
                    # is storing that info in the database and handling it
                    # properly in the viewer interface.)
                    db_values = (
                        source_id,
                        target_id,
                        single_component_size_rank,
                        None,
                        0,
                    )
                    sc_edge_count += 1
                    cursor.execute(SINGLEEDGE_INSERTION_STMT, db_values)

                if (
                    not no_print
                    or total_single_component_count
                    == single_component_size_rank
                ):
                    conclude_msg()

                # Output component information to the database
                cursor.execute(
                    SINGLECOMPONENT_INSERTION_STMT,
                    (
                        single_component_size_rank,
                        sc_node_count,
                        sc_edge_count,
                        implicit_spqr_node_counts[
                            single_component_size_rank - 1
                        ],
                        implicit_spqr_edge_counts[
                            single_component_size_rank - 1
                        ],
                        sc_compressed_node_count,
                        sc_compressed_edge_count,
                        sc_bicomponent_count,
                        bounding_box_right,
                        bounding_box_top,
                        implicit_spqr_bounding_boxes[
                            single_component_size_rank - 1
                        ][0],
                        implicit_spqr_bounding_boxes[
                            single_component_size_rank - 1
                        ][1],
                    ),
                )

                h.clear()
                h.close()
                single_component_size_rank += 1
            t2 = time.time()
            difference = t2 - t1
            print("SPQR %s view layout time:" % (mode), end=" ")
            print("%g seconds" % (difference))
            total_layout_time += difference

        if not no_print:
            conclude_msg()
    # Lay out the "standard mode" view of the graph and store information about it
    # in the database.
    t3 = time.time()
    component_size_rank = (
        1  # largest component is 1, the 2nd largest is 2, etc
    )
    no_print = (
        False  # used to reduce excess printing (see issue #133 on GitHub)
    )
    # Should be the default value in the (standard mode) component selector in
    # the viewer interface. TODO: put this in the assembly table of the db file
    smallest_viewable_comp_rank = -1
    for component in connected_components:
        if component.node_ct > max_node_ct or component.edge_ct > max_edge_ct:
            # Save the component in the db file, but with bounding box
            # dimensions of 0 and too_large set to 1 (for True).
            cursor.execute(
                COMPONENT_INSERTION_STMT,
                (
                    component_size_rank,
                    component.node_ct,
                    component.edge_ct,
                    component.total_length,
                    0,
                    0,
                    1,
                ),
            )
            # TODO: insert all elements (nodes/edges/clusters) in this component
            # with dummy coords, to enable global searching (#140 on the marbl
            # github page)? Or not -- space issues will probably manifest
            # inevitably. But I think that's a good idea eventually. Maybe make
            # it configurable?
            operation_msg(
                config.LARGE_COMPONENT_MSG.format(
                    cr=component_size_rank,
                    nc=component.node_ct,
                    ec=component.edge_ct,
                ),
                True,
            )
            component_size_rank += 1
            continue
        if smallest_viewable_comp_rank == -1:
            smallest_viewable_comp_rank = component_size_rank
        component_node_ct = len(component.node_list)
        # used in a silly corner case in which we 1) trigger the small component
        # message below and 2) the first "small" component has aux file(s) that
        # cannot be saved.
        first_small_component = False
        if not no_print:
            if component_node_ct < 5:
                # The current component is included in the small component count
                small_component_ct = (
                    total_component_count - component_size_rank + 1
                )
                if small_component_ct > 1:
                    no_print = True
                    first_small_component = True
                    operation_msg(
                        config.LAYOUT_MSG
                        + "%d " % (small_component_ct)
                        + config.SMALL_COMPONENTS_MSG
                    )
                # If only one small component is left, just treat it as a normal
                # component: there's no point pointing it out as a small component
            if not no_print:
                operation_msg(
                    config.START_LAYOUT_MSG
                    + "%d (%d nodes)..."
                    % (component_size_rank, component_node_ct)
                )

        if component_node_ct == 1 and len(component.node_group_list) == 0:
            # If the current connected component has no edges (this is possible in
            # this case if the individual node has a self-implied edge), then we
            # can "fake" the layout and avoid having to call pygraphviz, which
            # should save us some time.
            if len(component.node_list[0].outgoing_nodes) == 0:
                # fake layout based on component.node_list[0]'s dimensions,
                # insert node info and cc info into the database, then continue
                curr_node = component.node_list[0]
                curr_node.set_dimensions()
                wpts = curr_node.width * config.POINTS_PER_INCH
                hpts = curr_node.height * config.POINTS_PER_INCH
                curr_node.xdot_x = wpts / 2.0
                curr_node.xdot_y = hpts / 2.0
                curr_node.xdot_shape = curr_node.get_shape()
                curr_node.set_component_rank(component_size_rank)
                cursor.execute(NODE_INSERTION_STMT, curr_node.db_values())
                cursor.execute(
                    COMPONENT_INSERTION_STMT,
                    (component_size_rank, 1, 0, curr_node.bp, wpts, hpts, 0),
                )
                component_size_rank += 1
                continue
        # Lay out all clusters individually, to be backfilled
        for ng in component.node_group_list:
            ng.layout_isolated()
        # OK, we're displaying this component.
        # Get the node info (for both normal nodes and clusters), and the edge
        # info (obtained by just getting the outgoing edge list for each normal
        # node in the component). This is an obviously limited subset of the
        # data we've ascertained from the file; once we parse the layout
        # information (.xdot) generated by GraphViz, we'll reconcile that data
        # with the previously-stored biological data.
        node_info, edge_info = component.node_and_edge_info()
        component_prefix = "%s_%d" % (output_fn, component_size_rank)
        # We've just printed a layout message (and haven't printed a \n yet) if:
        # -we're laying out a "not small" component (i.e. no_print is False), or
        # -we're laying out a "small" component, but we just printed the "laying
        #  out small components" message (i.e. first_small_component is True)
        # In either case, we need to prepend a \n to the start of whatever we print
        # before the conclude_msg() following our prior layout message.
        # (Failing to prepend a \n will result in something looking like
        # "Laying out connected component [x] ([y] nodes)... Warning: uh oh",
        # where "Warning: uh oh" should've been printed on the line following
        # the "Laying out..." stuff.
        layout_msg_printed = (not no_print) or first_small_component
        # We use "r" to determine whether or not to print a newline before the
        # normal .gv file error message, if we would print an error message there
        r = True
        if make_no_backfilled_dot_files:
            r = save_aux_file(
                component_prefix + "_nobackfill.gv",
                component.produce_non_backfilled_dot_file(component_prefix),
                output_dir,
                layout_msg_printed,
                overwrite,
            )
        if make_no_patterned_dot_files:
            # TODO figure out how to take into account the previous r value here,
            # then use this r value for the next instance. right now -npdf is not
            # guaranteed to not slightly mess up the output newlines
            r = save_aux_file(
                component_prefix + "_nopatterns.gv",
                component.produce_non_patterned_dot_file(component_prefix),
                output_dir,
                layout_msg_printed,
                overwrite,
            )
        # NOTE: Currently, we reduce each component of the asm. graph to a DOT
        # string that we send to pygraphviz. However, we could also send
        # nodes/edges procedurally, using add_edge(), add_node(), etc.
        # That might be faster, and it might be worth doing;
        # however, for now I think this approach should be fine (knock on wood).
        gv_input = ""
        gv_input += "digraph asm {\n"
        if config.GRAPH_STYLE != "":
            gv_input += "\t%s;\n" % (config.GRAPH_STYLE)
        if config.GLOBALNODE_STYLE != "":
            gv_input += "\tnode [%s];\n" % (config.GLOBALNODE_STYLE)
        if config.GLOBALEDGE_STYLE != "":
            gv_input += "\tedge [%s];\n" % (config.GLOBALEDGE_STYLE)
        gv_input += node_info
        gv_input += edge_info
        gv_input += "}"
        h = pygraphviz.AGraph(gv_input)
        # save the .gv file if the user requested .gv preservation
        if preserve_gv:
            if not r:
                layout_msg_printed = False
            r = save_aux_file(
                component_prefix + ".gv",
                gv_input,
                output_dir,
                layout_msg_printed,
                overwrite,
            )

        # lay out the graph in .xdot -- this step is the main bottleneck in the
        # python side of MetagenomeScope
        # NOTE if dot is taking a really long time to lay stuff out, then other
        # Graphviz layout programs (e.g. sfdp) can be used instead -- however
        # they'll generally produce less useful drawings for directed graphs
        h.layout(prog="dot")
        # save the .xdot file if the user requested .xdot preservation
        if preserve_xdot:
            # AGraph.draw() doesn't perform graph positioning if layout()
            # has already been called on the given AGraph and no prog is
            # specified -- so this should be relatively fast
            if not r:
                layout_msg_printed = False
            save_aux_file(
                component_prefix + ".xdot",
                h,
                output_dir,
                layout_msg_printed,
                overwrite,
            )

        # Record the layout information of the graph's nodes, edges, and clusters

        # various stats we build up about the current component as we parse layout
        component_node_count = 0
        component_edge_count = 0
        component_total_length = 0
        # We use the term "bounding box" here, where "bounding box" refers to
        # just the (x, y) coord of the rightmost & topmost point in the graph:
        # (0, 0) is always the bottom left corner of the total bounding box
        # (although I have seen some negative "origin" points, which is confusing
        # and might contribute to a loss of accuracy for iterative drawing -- see
        # #148 for further information).
        #
        # So: we don't need the bounding box for positioning the entire graph.
        # However, we do use it for positioning clusters/nodes individually when we
        # "iteratively" draw the graph -- without an accurate bounding box, the
        # iterative drawing is going to look weird if clusters aren't positioned
        # "frequently" throughout the graph. (See #28 for reference.)
        #
        # We can't reliably access h.graph_attr due to a bug in pygraphviz.
        # See https://github.com/pygraphviz/pygraphviz/issues/113 for context.
        # If we could access the bounding box, here's how we'd do it --
        # bb = h.graph_attr[u'bb'].split(',')[2:]
        # bounding_box = [float(c) for c in bb]
        #
        # So, then, we obtain the bounding box "approximately," by finding the
        # right-most and top-most coordinates within the graph from:
        # -Cluster bounding boxes (which we can access fine, for some reason.)
        # -Node boundaries (we use some math to determine the actual borders of
        #  nodes, since node position refers to the center of the node)
        # -Edge control points -- note that this may cause something of a loss in
        #  precision if we convert edge control points in Cytoscape.js in a way
        #  that changes the edge structure significantly
        bounding_box_right = 0
        bounding_box_top = 0

        # Record layout info of nodes (incl. rectangular "empty" node groups)
        for n in h.nodes():
            try:
                curr_node = nodeid2obj[str(n)]
                component_node_count += 1
                component_total_length += curr_node.bp
                if curr_node.group is not None:
                    continue
                ep = n.attr[u"pos"].split(",")
                curr_node.xdot_x, curr_node.xdot_y = tuple(
                    float(c) for c in ep
                )
                # Try to expand the component bounding box
                right_side = curr_node.xdot_x + (
                    config.POINTS_PER_INCH * (curr_node.width / 2.0)
                )
                top_side = curr_node.xdot_y + (
                    config.POINTS_PER_INCH * (curr_node.height / 2.0)
                )
                if right_side > bounding_box_right:
                    bounding_box_right = right_side
                if top_side > bounding_box_top:
                    bounding_box_top = top_side
                # Save this cluster in the .db
                curr_node.xdot_shape = str(n.attr[u"shape"])
                curr_node.set_component_rank(component_size_rank)
                cursor.execute(NODE_INSERTION_STMT, curr_node.db_values())
            except KeyError:  # arising from nodeid2obj[a cluster id]
                # We use [8:] to slice off the "cluster_" prefix on every rectangle
                # node that is actually a node group that will be backfilled (#80)
                curr_cluster = clusterid2obj[str(n)[8:]]
                component_node_count += curr_cluster.node_count
                component_edge_count += curr_cluster.edge_count
                component_total_length += curr_cluster.bp
                ep = n.attr[u"pos"].split(",")
                curr_cluster.xdot_x = float(ep[0])
                curr_cluster.xdot_y = float(ep[1])
                half_width_pts = config.POINTS_PER_INCH * (
                    curr_cluster.xdot_c_width / 2.0
                )
                half_height_pts = config.POINTS_PER_INCH * (
                    curr_cluster.xdot_c_height / 2.0
                )
                curr_cluster.xdot_left = curr_cluster.xdot_x - half_width_pts
                curr_cluster.xdot_right = curr_cluster.xdot_x + half_width_pts
                curr_cluster.xdot_bottom = (
                    curr_cluster.xdot_y - half_height_pts
                )
                curr_cluster.xdot_top = curr_cluster.xdot_y + half_height_pts
                # Try to expand the component bounding box
                if curr_cluster.xdot_right > bounding_box_right:
                    bounding_box_right = curr_cluster.xdot_right
                if curr_cluster.xdot_top > bounding_box_top:
                    bounding_box_top = curr_cluster.xdot_top
                # Reconcile child nodes -- add to .db
                for n in curr_cluster.nodes:
                    n.xdot_x = curr_cluster.xdot_left + n.xdot_rel_x
                    n.xdot_y = curr_cluster.xdot_bottom + n.xdot_rel_y
                    n.set_component_rank(component_size_rank)
                    cursor.execute(NODE_INSERTION_STMT, n.db_values())
                # Reconcile child edges -- add to .db
                for e in curr_cluster.edges:
                    # Adjust the control points to be relative to the entire
                    # component. Also, try to expand to the component bounding box.
                    p = 0
                    coord_list = [
                        float(c) for c in e.xdot_rel_ctrl_pt_str.split()
                    ]
                    e.xdot_ctrl_pt_str = ""
                    while p <= len(coord_list) - 2:
                        if p > 0:
                            e.xdot_ctrl_pt_str += " "
                        xp = coord_list[p]
                        yp = coord_list[p + 1]
                        e.xdot_ctrl_pt_str += str(curr_cluster.xdot_left + xp)
                        e.xdot_ctrl_pt_str += " "
                        e.xdot_ctrl_pt_str += str(
                            curr_cluster.xdot_bottom + yp
                        )
                        # Try to expand the component bounding box -- interior
                        # edges should normally be entirely within the bounding box
                        # of their node group, but complex bubbles might contain
                        # interior edges that go outside of the node group's b. box
                        if xp > bounding_box_right:
                            bounding_box_right = xp
                        if yp > bounding_box_top:
                            bounding_box_top = yp
                        p += 2
                    # Save this edge in the .db
                    cursor.execute(EDGE_INSERTION_STMT, e.db_values())
                # Save the cluster in the .db
                curr_cluster.component_size_rank = component_size_rank
                cursor.execute(
                    CLUSTER_INSERTION_STMT, curr_cluster.db_values()
                )
        # Record layout info of edges (that aren't inside node groups)
        for e in h.edges():
            # Since edges could point to/from node groups, we store their actual
            # source/target nodes in a comment attribute
            source_id, target_id = e.attr[u"comment"].split(",")
            source = nodeid2obj[source_id]
            curr_edge = source.outgoing_edge_objects[target_id]
            component_edge_count += 1
            if curr_edge.group is not None:
                continue
            (
                curr_edge.xdot_ctrl_pt_str,
                coord_list,
                curr_edge.xdot_ctrl_pt_count,
            ) = graph_objects.Edge.get_control_points(e.attr[u"pos"])
            if source_id != e[0]:
                # Adjust edge to point from interior node "source"'s tailport
                pts_height = source.height * config.POINTS_PER_INCH
                tail_y = source.xdot_y - (pts_height / 2.0)
                new_points = "%g %g " % (source.xdot_x, tail_y)
                xcps = curr_edge.xdot_ctrl_pt_str
                # Remove first control point (at tailport of the bounding box
                # rectangle of the node group that "source" is in)
                xcps = xcps[xcps.index(" ") + 1 :]
                xcps = xcps[xcps.index(" ") + 1 :]
                curr_edge.xdot_ctrl_pt_str = new_points + xcps
            if target_id != e[1]:
                # Adjust edge to point to interior node "target"'s headport
                target = nodeid2obj[target_id]
                pts_height = target.height * config.POINTS_PER_INCH
                tail_y = target.xdot_y + (pts_height / 2.0)
                new_points = "%g %g" % (target.xdot_x, tail_y)
                xcps = curr_edge.xdot_ctrl_pt_str
                # Remove last control point (at headport of the bounding box
                # rectangle of the node group that "target" is in)
                xcps = xcps[: xcps.rindex(" ")]
                xcps = xcps[: xcps.rindex(" ")]
                curr_edge.xdot_ctrl_pt_str = xcps + " " + new_points
            # Try to expand the component bounding box
            p = 0
            while p <= len(coord_list) - 2:
                x_coord = coord_list[p]
                y_coord = coord_list[p + 1]
                if x_coord > bounding_box_right:
                    bounding_box_right = x_coord
                if y_coord > bounding_box_top:
                    bounding_box_top = y_coord
                p += 2
            # Save this edge in the .db
            cursor.execute(EDGE_INSERTION_STMT, curr_edge.db_values())

        if not no_print:
            conclude_msg()
        # Output component information to the database
        cursor.execute(
            COMPONENT_INSERTION_STMT,
            (
                component_size_rank,
                component_node_count,
                component_edge_count,
                component_total_length,
                bounding_box_right,
                bounding_box_top,
                0,
            ),
        )

        h.clear()
        h.close()
        component_size_rank += 1

    # Insert general assembly information into the database
    asm_gc = None
    dna_given_val = 0
    if dna_given:
        asm_gc = assembly_gc(total_gc_nt_count, total_length)
        dna_given_val = 1
    repeats_given_val = 1 if repeats_given else 0
    spqr_given_val = 1 if args.computespqrdata else 0
    graphVals = (
        os.path.basename(asm_fn),
        graph_filetype,
        total_node_count,
        total_edge_count,
        total_all_edge_count,
        total_component_count,
        total_bicomponent_count,
        total_single_component_count,
        total_length,
        n50(bp_length_list),
        asm_gc,
        dna_given_val,
        repeats_given_val,
        spqr_given_val,
        smallest_viewable_comp_rank,
    )
    cursor.execute(ASSEMBLY_INSERTION_STMT, graphVals)
    # ...Ok, now we're finally done!
    t4 = time.time()
    difference = t4 - t3
    total_layout_time += difference
    if no_print:
        conclude_msg()
    if args.computespqrdata:
        print("Standard view layout time: %g seconds" % (difference))
    print("Total layout time: %g seconds" % (total_layout_time))

    operation_msg(config.DB_SAVE_MSG + "%s..." % (db_fn))
    connection.commit()
    conclude_msg()
    # Close the database connection
    connection.close()
