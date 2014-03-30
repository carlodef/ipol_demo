#!/usr/bin/env python

# Copyright (C) 2013, Carlo de Franchis <carlodef@gmail.com>
# Copyright (C) 2013, Gabriele Facciolo <gfacciol@gmail.com>
# Copyright (C) 2013, Enric Meinhardt Llopis <enric.meinhardt@cmla.ens-cachan.fr>

from python import common
from python import rpc_model
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
      frame the ROI is defined by its top-left corener (x, y) and its
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
        x = cfg['roi_preview']['x']
        y = cfg['roi_preview']['y']
        w = cfg['roi']['w']
        h = cfg['roi']['h']

        rpc1 = cfg['images'][0]['rpc']
        r1 = rpc_model.RPCModel(rpc1)
        prv_w, prv_h = common.image_size(preview)

        # convert x, y to the full image frame
        x = int((float(x) / prv_w) * r1.lastCol)
        y = int((float(y) / prv_h) * r1.lastRow)

        # add offset
        cfg['roi']['x'] = x - w / 2
        cfg['roi']['y'] = y - h / 2

        # convert w and h to preview coordinate system
        cfg['roi_preview']['w'] = int(w * (float(prv_w) / r1.lastCol))
        cfg['roi_preview']['h'] = int(h * (float(prv_h) / r1.lastRow))

        # cleanup and debug
        cfg.pop('preview_coordinate_system')
        print prv_w, prv_h, x, y
        print cfg

        # write the parameters in a json file
        fp = open(config, 'w')
        json.dump(cfg, fp, indent=4)
        fp.close()
