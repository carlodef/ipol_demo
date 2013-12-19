var ps, cat;

// Create an orbit camera halfway between the closest and farthest point
var cam = new OrbitCam({closest:-50, farthest:1000, distance: 200});
var isDragging = false;
var rotationStartCoords = [0, 0];


function zoom(amt){
  if(amt < 0){
    cam.goCloser(-amt);
  }
  else{
    cam.goFarther(amt);
  }   
}


function mousePressed(){
  rotationStartCoords[0] = ps.mouseX;
  rotationStartCoords[1] = ps.mouseY;
  
  isDragging = true;
}


function mouseReleased(){
  isDragging = false;
}


function ipol_zoom_in() {
	zoom(-10);
}

function ipol_zoom_out() {
	zoom(+10);
}


function keyDown(){
	switch (ps.key) {
		case 38: ipol_zoom_in(); break;
		case 40: ipol_zoom_out(); break;
	}
}




function render() {
  if(isDragging) {		
	// how much was the cursor moved compared to last time
	// this function was called?
    var deltaX = ps.mouseX - rotationStartCoords[0];
    var deltaY = ps.mouseY - rotationStartCoords[1];
		
	// now that the camera was updated, reset where the
	// rotation will start for the next time this function is called.
	rotationStartCoords = [ps.mouseX, ps.mouseY];

    cam.yaw(-deltaX * 0.015);
    cam.pitch(deltaY * 0.015);
  }

  var c = cat.getCenter();  
  ps.multMatrix(M4x4.makeLookAt(cam.position, cam.direction, cam.up));
  ps.translate(-cam.position[0]-c[0], -cam.position[1]-c[1], -cam.position[2]-c[2] );
  
  ps.clear();
  ps.render(cat);
      
  var status = document.getElementById("fileStatus");
  status.innerHTML = "";
  switch(cat.status){
    case 1: status.innerHTML = "STARTED"; break;
    case 2: status.innerHTML = "STREAMING"; break;
    case 3: status.innerHTML = "COMPLETE"; break;
    default:break;
  }
}

function ipol_3d_start(PC_url) {
  ps = new PointStream();
  
  /*$('#canvas')[0].addEventListener('touchmove', function(e) {
	  e.preventDefault();
	},false);*/

  control = document.getElementById('canvas');
  ps.setup(control);
  

  
  //ps.background([0, 0, 0, 0.5]);
  ps.background([0, 0, 0, 0.2]);
  ps.pointSize(50);

  ps.onRender = render;
  ps.onMouseScroll = zoom;
  ps.onMousePressed = mousePressed;
  ps.onMouseReleased = mouseReleased;
  ps.onKeyDown = keyDown;
  
  cat = ps.load(PC_url);
}
