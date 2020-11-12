/* Copyright (C) 2016-- Marcus Fedarko, Jay Ghurye, Todd Treangen, Mihai Pop
 * Authored by Marcus Fedarko
 *
 * This file is part of MetagenomeScope.
 *
 * MetagenomeScope is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * MetagenomeScope is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with MetagenomeScope.  If not, see <http://www.gnu.org/licenses/>.
 ****
 * Various utilities used by MetagenomeScope.
 */

/* Returns a #RRGGBB string indicating the color of a node, scaled by a
 * percentage (some value in the range [0, 1]).
 *
 * @param {Number} perc Value in the range [0, 1].
 * @param {Object} minRGB Has r, g, and b attributes in the range [0, 255].
 * @param {Object} maxRGB Has r, g, and b attributes in the range [0, 255].
 *
 * @returns {String} Hex color string of the format #RRGGBB.
 */
function getNodeColorization(perc, minRGB, maxRGB) {
    "use strict";
    // Linearly scale each RGB value between the extreme colors'
    // corresponding RGB values
    var red_i = perc * (mgsc.MAX_RGB.r - mgsc.MIN_RGB.r) + mgsc.MIN_RGB.r;
    var green_i = perc * (mgsc.MAX_RGB.g - mgsc.MIN_RGB.g) + mgsc.MIN_RGB.g;
    var blue_i = perc * (mgsc.MAX_RGB.b - mgsc.MIN_RGB.b) + mgsc.MIN_RGB.b;
    // Convert resulting RGB decimal values (should be in the range [0, 255])
    // to hexadecimal and use them to construct a color string
    var red = Math.round(red_i).toString(16);
    var green = Math.round(green_i).toString(16);
    var blue = Math.round(blue_i).toString(16);
    // Ensure that the color string is 6 characters long (for single-digit
    // channel values, we need to pad on the left with a zero)
    var channels = [red, green, blue];
    for (var ch = 0; ch < 3; ch++) {
        if (channels[ch].length === 1) {
            channels[ch] = "0" + channels[ch];
        }
    }
    return "#" + channels[0] + channels[1] + channels[2];
}

/* Redraws the gradient preview for node colorization.
 * If minOrMax is -1, then we use hexColor as the new minimum color.
 * Otherwise, we use hexColor as the new maximum color.
 */
function redrawGradientPreview(hexColor, minOrMax) {
    "use strict";
    var tmpColor;
    if (minOrMax === -1) {
        $("#0gp").css("background-color", hexColor);
        mgsc.MIN_RGB = $("#mincncp").data("colorpicker").color.toRGB();
        mgsc.MIN_HEX = hexColor;
        if (mgsc.MAX_RGB === undefined) {
            tmpColor = $("#maxcncp").data("colorpicker").color;
            mgsc.MAX_RGB = tmpColor.toRGB();
            mgsc.MAX_HEX = tmpColor.toHex();
        }
    } else {
        $("#100gp").css("background-color", hexColor);
        mgsc.MAX_RGB = $("#maxcncp").data("colorpicker").color.toRGB();
        mgsc.MAX_HEX = hexColor;
        if (mgsc.MIN_RGB === undefined) {
            tmpColor = $("#mincncp").data("colorpicker").color;
            mgsc.MIN_RGB = tmpColor.toRGB();
            mgsc.MIN_HEX = tmpColor.toHex();
        }
    }
    // Change intermediate colors in the gradient
    $("#25gp").css("background-color", getNodeColorization(0.25));
    $("#50gp").css("background-color", getNodeColorization(0.5));
    $("#75gp").css("background-color", getNodeColorization(0.75));
}

// Allows user to test one of Cytoscape.js' predefined layouts
function testLayout() {
    "use strict";
    if ($("#layoutInput").val() !== "") {
/* Converts an angle in degrees to radians (for use with Javascript's trig
 * functions).
 */
function degreesToRadians(angle) {
    "use strict";
    return angle * (Math.PI / 180);
}

/* Rotates a coordinate by a given clockwise angle (in degrees).
 * Returns an array of [x', y'] representing the new point.
 */
function rotateCoordinate(xCoord, yCoord, prevRotation = 0, nextRotation = 90) {
    "use strict";
    // NOTE The formula for a coordinate transformation here works for all
    // degree inputs of rotation. However, to save time, we just check
    // to see if the rotation is a factor of 360 (i.e. the rotated
    // point would be the same as the initial point), and if so we just
    // return the original coordinates.
    var rotation = prevRotation - nextRotation;
    if (rotation % 360 === 0) {
        return [xCoord, yCoord];
    } else {
        var newX =
            xCoord * Math.cos(degreesToRadians(rotation)) -
            yCoord * Math.sin(degreesToRadians(rotation));
        var newY =
            yCoord * Math.cos(degreesToRadians(rotation)) +
            xCoord * Math.sin(degreesToRadians(rotation));
        // TODO: why... did I write this like this? I'm leaving this as is for
        // now in case there is some bizarre precision issue that I have
        // forgetten about, but if I haven't figured this out soon then I
        // should really just return newX and newY as they are.
        newX = parseFloat(newX.toFixed(2));
        newY = parseFloat(newY.toFixed(2));
        return [newX, newY];
    }
}

/* Given the bounding box of the graph, a graph rotation angle (in degrees),
 * and a point specified by x and y coordinates, converts the point from
 * GraphViz' coordinate system to Cytoscape.js' coordinate system, rotating
 * the point if necessary (i.e. the rotation angle mod 360 !== 0).
 *
 * For reference -- GraphViz uses the standard Cartesian system in which
 * the bottom-left corner of the screen is the origin, (0, 0). Cytoscape.js
 * inverts the y-axis, with the origin (0, 0) being situated at the
 * top-left corner of the screen. So to transform a point (x, y) from
 * GraphViz to Cytoscape.js, you just return (x, y'), where
 * y' = the vertical length of the bounding box, minus y.
 * (The x-coordinate remains the same.)
 *
 * This is a purposely simple function -- in the event that we decide to
 * use another graphing library/layout system/etc. for some reason, we can
 * just modify this function accordingly.
 */
function gv2cyPoint(xCoord, yCoord, boundingbox) {
    "use strict";
    // Convert from GraphViz to Cytoscape.js
    var cyY = boundingbox[1] - yCoord;
    var cyX = xCoord;
    // Rotate the point about the axis if necessary
    return rotateCoordinate(cyX, cyY);
}

/* Converts a string of control points (defined in the form "x1 y1 x2 y2",
 * for an arbitrary number of points) to a 2-dimensional list of floats,
 * of the form [[x1, y1], [x2, y2], ...]. If the input string contains an
 * odd number of coordinate components for some reason (e.g.
 * "x1 y1 x2 y2 x3") then this will return null, since that's invalid.
 * This also takes care of converting each point in the input string from
 * GraphViz' coordinate system to Cytoscape.js' coordinate system.
 * (Hence why the graph's bounding box and rotation are parameters here.)
 */
function ctrlPtStrToList(ctrlPointStr, boundingbox) {
    "use strict";
    // Create coordList, where every coordinate is an element (e.g.
    // [x1, y1, x2, y2, ...]
    var coordList = ctrlPointStr.trim().split(" ");
    // Merge two elements of coordList at a time. NOTE that this is only
    // possible when coordList.length is even, so this is why we have to
    // wait until we're finished parsing all control points until doing
    // this conversion. (If coordList.length is odd, return null --
    // something went very wrong in that case.)
    var clLen = coordList.length;
    if (clLen % 2 !== 0) {
        return null;
    } else {
        var pointList = [];
        var currPoint = [];
        for (var i = 0; i < clLen; i++) {
            if (i % 2 === 0) {
                // i/2 is always an integer, since i is even
                pointList[i / 2] = gv2cyPoint(
                    parseFloat(coordList[i]),
                    parseFloat(coordList[i + 1]),
                    boundingbox
                );
            }
        }
        return pointList;
    }
}

/* Given two points, each in the form [x, y], returns the distance between
 * the points obtained using d = sqrt((x2 - x1)^2 + (y2 - y1)^2).
 * e.g. distance([1, 2], [3, 4]) = sqrt((3 - 1)^2 + (4 - 2)^2) = sqrt(8)
 */
function distance(point1, point2) {
    "use strict";
    return Math.sqrt(
        Math.pow(point2[0] - point1[0], 2) + Math.pow(point2[1] - point1[1], 2)
    );
}

/* Given a line that passes through two points (linePoint1 and linePoint2),
 * this function returns the perpendicular distance from a point to the
 * line. This assumes all points are given as lists in the form [x, y].
 *
 * Note that, unlike most formulations of point-to-line-distance, the value
 * returned here isn't necessarily nonnegative. This is because Cytoscape.js
 * expects the control-point-distances used for unbundled-bezier edges to have
 * a sign based on which "side" of the line from source node to sink node
 * they're on:
 *
 *       negative
 * SOURCE ------> TARGET
 *       positive
 *
 * So here, if this edge has a bend "upwards," we'd give the corresponding
 * control point a negative distance from the line, and if the bend was
 * "downwards" it'd have a positive distance from the line. You can see this
 * for yourself here (http://js.cytoscape.org/demos/edge-types/) -- notice how
 * the control-point-distances for the unbundled-bezier (multiple) edge are
 * [40, -40] (a downward bend, then an upwards bend).
 *
 * What that means here is that we don't take the absolute value of the
 * numerator in this formula; instead, we negate it. This makes these distances
 * match up with what Cytoscape.js expects. (I'll be honest: I don't know why
 * this works. This is just what I found back in 2016. As a big heaping TODO,
 * I should really make this more consistent, or at least figure out *why* this
 * works -- it's worth noting that if you swap around linePoint1 and
 * linePoint2, this'll negate the distance you get, and I have no idea why this
 * is working right now.)
 *
 * Also note that, if distance(linePoint1, linePoint2) is equal to 0, this
 * will throw an Error (since this would make the point-to-line-distance
 * formula undefined, due to having 0 in the denominator). So don't define a
 * line by the same point twice!
 *
 * CODELINK: The formula used here is based on
 * https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line#Line_defined_by_two_points.
 */
function pointToLineDistance(point, linePoint1, linePoint2) {
    "use strict";
    var lineDistance = distance(linePoint1, linePoint2);
    if (lineDistance === 0) {
        throw new Error(
            "pointToLineDistance() given a line of the same point twice"
        );
    }
    var ydelta = linePoint2[1] - linePoint1[1];
    var xdelta = linePoint2[0] - linePoint1[0];
    var x2y1 = linePoint2[0] * linePoint1[1];
    var y2x1 = linePoint2[1] * linePoint1[0];
    var numerator = ydelta * point[0] - xdelta * point[1] + x2y1 - y2x1;
    return -numerator / lineDistance;
}
