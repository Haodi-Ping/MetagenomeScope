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

import sys
import click
from .config import MAXN_DEFAULT, MAXE_DEFAULT
from .main import make_viz
from ._param_descriptions import (
    INPUT,
    OUTPUT_DIR,
    ASSUME_ORIENTED,
    MAXN,
    MAXE,
    MBF,
    UP,
    SPQR,
    STRUCTPATT,
    PG,
    PX,
    NBDF,
    NPDF,
)


# Make mgsc -h show the help text
@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.option("-i", "--input-file", required=True, help=INPUT)
@click.option("-o", "--output-dir", required=True, help=OUTPUT_DIR)
@click.option(
    "-ao",
    "--assume-oriented",
    required=False,
    default=False,
    help=ASSUME_ORIENTED,
)
@click.option(
    "-maxn",
    "--max-node-count",
    required=False,
    default=MAXN_DEFAULT,
    help=MAXN,
    show_default=True,
)
@click.option(
    "-maxe",
    "--max-edge-count",
    required=False,
    default=MAXE_DEFAULT,
    help=MAXE,
    show_default=True,
)
@click.option(
    "-mbf", "--metacarvel-bubble-file", required=False, default=None, help=MBF
)
@click.option(
    "-up", "--user-pattern-file", required=False, default=None, help=UP
)
@click.option(
    "-spqr",
    "--compute-spqr-data",
    required=False,
    is_flag=True,
    default=False,
    help=SPQR,
)
@click.option(
    "-sp",
    "--save-structural-patterns",
    is_flag=True,
    required=False,
    default=False,
    help=STRUCTPATT,
)
@click.option(
    "-pg",
    "--preserve-gv",
    is_flag=True,
    required=False,
    default=False,
    help=PG,
)
@click.option(
    "-px",
    "--preserve-xdot",
    required=False,
    is_flag=True,
    default=False,
    help=PX,
)
@click.option(
    "-nbdf",
    "--save-no-backfill-dot-files",
    is_flag=True,
    required=False,
    default=False,
    help=NBDF,
)
@click.option(
    "-npdf",
    "--save-no-pattern-dot-files",
    is_flag=True,
    required=False,
    default=False,
    help=NPDF,
)
def run_script(
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
) -> None:
    """Visualizes an assembly graph and identifies structural patterns therein.

    This generates a folder containing an interactive HTML/JS visualization of
    the graph's connected component(s).

    There are many options available to customize the visualization / output,
    but the only two you probably need to worry about are the input file and
    output directory: generating a visualization can be as simple as

        mgsc -i graph.gfa -o viz

    Which will generate an output directory viz/ containing an index.html
    file that visualizes the graph's connected components.
    """
    make_viz(
        input_file,
        output_dir,
        assume_oriented,
        max_node_count,
        max_edge_count,
        metacarvel_bubble_file,
        user_pattern_file,
        spqr,
        sp,
        pg,
        px,
        nbdf,
        npdf,
    )


if __name__ == "__main__":
    run_script()
