var ps, pointCloud;
var yRot = 0.0;
var zoomed = -100;
var prog;

function zoom(amt){
  zoomed += amt * 2 * 1;
}

function pointLight(light){
  var lightName = "lights" + light.id;
  ps.uniformi( lightName + ".isOn", true);
  ps.uniformf( lightName + ".position", light.position);
  ps.uniformi( lightName + ".type", 2);
  ps.uniformf( lightName + ".attenuation", light.attenuation);
  
  if(light.ambient){ps.uniformf( lightName + ".ambient", light.ambient);}
  if(light.diffuse){ps.uniformf( lightName + ".diffuse", light.diffuse);}
  if(light.specular){ps.uniformf( lightName + ".specular", light.specular);}
}


function render() {
  ps.translate(0, 0, zoomed);
  ps.rotateY(yRot += 0.001);
  
  var c = pointCloud.getCenter();
  ps.translate(-c[0], -c[1], -c[2]);
  
  ps.clear();
  ps.render(pointCloud);  
}
  
function start(){
  ps = new PointStream();
  ps.setup(document.getElementById('canvas'));
  ps.background([1, 1, 0.7, 1]);

  var vertShader = ps.getShaderStr("../../shaders/fixed_function.vs");
  var fragShader = ps.getShaderStr("../../shaders/fixed_function.fs");
  
  var prog = ps.createProgram(vertShader, fragShader);
  ps.useProgram(prog);
  
  pointLight({id:0, ambient:[0,0,0], diffuse:[1,1,1], attenuation:[1,0,0], position: [0,0,50]});

  ps.onRender = render;
  ps.onMouseScroll = zoom;

  ps.pointSize(3);
  
  pointCloud = ps.load("../../clouds/ariusman_842K_n.psi");  
}
