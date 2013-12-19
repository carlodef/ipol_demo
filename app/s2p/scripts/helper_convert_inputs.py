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

      Helper to convert the input coordinates from the preview frame to
      the full image.
      """ % sys.argv[0]
      sys.exit(1)

    # read the json configuration file
    import json
    f = open(config)
    cfg = json.load(f)
    f.close()

    if 'preview_coordinate_system' in cfg:
        # roi definition and output path
        x = cfg['roi']['x']
        y = cfg['roi']['y']
        w = cfg['roi']['w']
        h = cfg['roi']['h']
        rpc1 = cfg['images'][0]['rpc']

        prv_w, prv_h = common.image_size(preview)
        r1 = rpc_model.RPCModel(rpc1)
        cfg['roi']['x'] = (float(x) / prv_w) * r1.lastCol
        cfg['roi']['y'] = (float(y) / prv_h) * r1.lastRow
        cfg.pop('preview_coordinate_system')
        print prv_w, prv_h, x, y
        print cfg

        # write the parameters in a json file
        fp = open(config, 'w')
        json.dump(cfg, fp, indent=4)
        fp.close()
