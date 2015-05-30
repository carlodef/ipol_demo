// SCRIPT TO DRAW POINTS IN IMAGE, TO BE USED IN params.html

// Creates canvas
var paper = Raphael("canvas_div");

var points_x=[];  // fill with previous points
var points_y=[];
var circles=[];

function draw_previous_points(){
    for (var i =0; i<prev_xs.length; i++){
        draw_point(prev_xs[i],prev_ys[i]);
    }
}

function search_point_in_array(x,y){
    for (var i=0;i<points_x.length;i++){
        if ( Math.abs(points_x[i]-x)<=(2/WIDTH) &&
             Math.abs(points_y[i]-y)<=(2/HEIGHT) ) return i;
    }
    return -1;
}

function draw_point(pos_x,pos_y){
    exists = search_point_in_array(pos_x,pos_y);

    if (exists == -1) { // it's a new point
        // draw circle and paint red
        circle = paper.circle( Math.round(pos_x*WIDTH),
                               Math.round(pos_y*HEIGHT), 3);
        circle.attr("fill", "#f00");
        circle.attr("stroke", "#f00");
        circles.push(circle)

        // add to array list of points
        points_x.push(pos_x);
        points_y.push(pos_y);
    } else { // point was already drawn, delete
        points_x.splice(exists,1);
        points_y.splice(exists,1);
        circles[exists].remove();
        circles.splice(exists,1);
    }

    // add to hidden fields in the form with list of points
    document.getElementById("points_x").value=points_x;
    document.getElementById("points_y").value=points_y;
}

function click_point(event){
    // get click position
    pos_x = event.offsetX?(event.offsetX):event.pageX-document.getElementById("canvas_div").offsetLeft;
    pos_y = event.offsetY?(event.offsetY):event.pageY-document.getElementById("canvas_div").offsetTop;

    // draw point in the canvas
    draw_point(pos_x/WIDTH,pos_y/HEIGHT);

    // mark the data as "original" so as to keep it in the archive
    document.getElementById("original").value="True";
}

function add_noise(){
    N = document.getElementById("noise_points").value
    N = Number(N)

    if (N==0) return;

    for (i=0;i<N;i++){
        x= Math.random();
        y= Math.random();
        draw_point(x,y);
    }

    // mark the data as "original" so as to keep it in the archive
    document.getElementById("original").value="True";
}

function checkPoints(url){
    if (points_x.length==0){
        alert("You need to draw some points!")
        return false;
    } else {
       document.theform.action=url;
       return true;
    }
}
