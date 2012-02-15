#!/usr/bin/python
# -*- coding: utf-8 -*-

import Image, ImageDraw
from math import cos
from math import sin
from math import pi

def plot_orientations(input_image, x, y, r, file_modes, output_name):

    #im = Image.new('RGBA', Image.open(input_image).size)
    im = Image.open(input_image)
    draw = ImageDraw.Draw(im)

    draw.arc((int(x-r),int(y-r),int(x+r),int(y+r)),0,360,fill=(255,0,0))

    modes = open(file_modes)
    m = modes.read().split('\n')
    for val in m:
        if val:
            (mode,theta,score) = val.split(';')
            theta = float(theta)
            x_1 = x+r*cos(theta)
            y_1 = y-r*sin(theta)
            draw.line((x,y,x_1,y_1),fill=(255,0,0))
            x_2 = x_1+(r/4)*cos(theta+5*pi/6)
            y_2 = y_1-(r/4)*sin(theta+5*pi/6)
            x_3 = x_1+(r/4)*cos(theta+7*pi/6)
            y_3 = y_1-(r/4)*sin(theta+7*pi/6)
            draw.line((x_1,y_1,x_2,y_2),fill=(255,0,0))
            draw.line((x_1,y_1,x_3,y_3),fill=(255,0,0))

    del draw
    im.save(output_name, "PNG")
