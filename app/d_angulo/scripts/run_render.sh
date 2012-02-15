#load params
. params

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin

echo "Generating tif 3D rendering"
plambda out_disp.tif "x(0,0) x(1,1) -" > out_render.tif 2> /dev/null
plambda out_disp_minfiltered.tif "x(0,0) x(1,1) -" > out_render_minfiltered.tif 2> /dev/null
plambda out_disp_minfiltered2.tif "x(0,0) x(1,1) -" > out_render_minfiltered2.tif 2> /dev/null

echo "save_png.sh out_render.tif out_render.png -2 2"
save_png.sh out_render.tif out_render.png -2 2
save_png.sh out_render_minfiltered.tif out_render_minfiltered.png -2 2
save_png.sh out_render_minfiltered2.tif out_render_minfiltered2.png -2 2
