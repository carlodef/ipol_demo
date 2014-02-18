#!/usr/bin/env python

# Copyright (C) 2013, Carlo de Franchis <carlodef@gmail.com>
# Copyright (C) 2013, Gabriele Facciolo <gfacciol@gmail.com>
# Copyright (C) 2013, Enric Meinhardt Llopis <enric.meinhardt@cmla.ens-cachan.fr>

import sys
import subprocess

if __name__ == '__main__':

    if len(sys.argv) == 2:
      config  = sys.argv[1]
    else:
      print """
      Incorrect syntax, use:
        > %s config.json

      Helper to plot a rectangle on the ROI that was processed, on the preview
      image. The config.json is needed to get the coordinates of the ROI. The
      plot is made with imagemagick.
      """ % sys.argv[0]
      sys.exit(1)

    # read the json configuration file
    import json
    f = open(config)
    cfg = json.load(f)
    f.close()

    if 'roi_preview' in cfg:
        # roi definition in the preview frame
        x = cfg['roi_preview']['x']
        y = cfg['roi_preview']['y']
        w = cfg['roi_preview']['w']
        h = cfg['roi_preview']['h']

        x1 = x
        y1 = y
        x2 = x1 + w
        y2 = y1 + h

        cmd = """
        convert input_0.png -fill 'rgba(0,255,255,0.4)' -draw 'rectangle %d,%d,%d,%d' input_0.png
        """ % (x1, y1, x2, y2)
        subprocess.call(cmd, shell=True)
    else:
        print "No roi_preview key in json file"
