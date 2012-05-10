"""
Some small functions for the Angulo demo
"""
from lib import image

def plot_cross(input_image, x, y, output_image):
    """
    draw a cross at the position (x,y)
    """
    img = image(input_image)
    img.draw_cross((x,y), size=4, color="white")
    img.draw_cross((x,y), size=2, color="red")
    img.save(output_image)

def plot_rectangle(input_image, x0, y0, x1, y1, output_image):
    """
    draw a rectangle defined by the two provided corners
    """
    img = image(input_image)
    img.draw_line([(x0,y0), (x1,y0), (x1,y1), (x0,y1), (x0,y0)], color="red")
    img.draw_line([(x0+1,y0+1), (x1-1,y0+1), (x1-1,y1-1), (x0+1,y1-1), (x0+1,y0+1)], color="white")
    img.save(output_image)

def crop_image(input_image, x0, y0, x1, y1, output_image):
    """
    copy the part of the input image contained in the rectangle defined by the
    two provided corners into the output image
    """
    img = image(input_image)
    (x0, x1) = (min(x0,x1), max(x0,x1))
    (y0, y1) = (min(y0,y1), max(y0,y1))
    img.crop((x0, y0, x1, y1))
    img.save(output_image)


    
    
