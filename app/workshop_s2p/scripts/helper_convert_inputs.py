#!/usr/bin/env python

# Copyright (C) 2013, Carlo de Franchis <carlodef@gmail.com>
# Copyright (C) 2013, Gabriele Facciolo <gfacciol@gmail.com>
# Copyright (C) 2013, Enric Meinhardt Llopis <enric.meinhardt@cmla.ens-cachan.fr>

from python import common
import sys

if __name__ == '__main__':

    if len(sys.argv) == 3:
      config  = sys.argv[1]
      preview  = sys.argv[2]
    else:
      print """
      Incorrect syntax, use:
        > %s config.json preview.jpg

      Helper to convert the input coordinates from the preview frame to the
      full image. In addition to the scale change, in the preview frame the ROI
      is defined by center (x, y) and dimensions (w, h) while in the full image
      frame the ROI is defined by its top-left corner (x, y) and its
      dimensions (w, h).
      """ % sys.argv[0]
      sys.exit(1)

    # read the json configuration file
    import json
    f = open(config)
    cfg = json.load(f)
    f.close()

    if 'preview_coordinate_system' in cfg:
        # roi definition in the preview frame
        xx = cfg['roi_preview']['x']
        yy = cfg['roi_preview']['y']
        w = cfg['roi']['w']
        h = cfg['roi']['h']

        img1 = cfg['images'][0]['img']
        prv_w, prv_h =   common.image_size(preview)
        full_w, full_h = common.image_size_tiffinfo(img1)

        # convert x, y to the full image frame
        x = int((float(xx) / prv_w) * full_w)
        y = int((float(yy) / prv_h) * full_h)

        # add offset
        cfg['roi']['x'] = x - w / 2
        cfg['roi']['y'] = y - h / 2

        # convert roi definition in the preview coordinate system
        ww = int(w * (float(prv_w) / full_w))
        hh = int(h * (float(prv_h) / full_h))
        xx -= ww / 2
        yy -= hh / 2
        cfg['roi_preview']['w'] = ww
        cfg['roi_preview']['h'] = hh 
        cfg['roi_preview']['x'] = xx
        cfg['roi_preview']['y'] = yy 

        # cleanup and debug
        cfg.pop('preview_coordinate_system')

        # write the parameters in a json file
        fp = open(config, 'w')
        json.dump(cfg, fp, indent=4)
        fp.close()
