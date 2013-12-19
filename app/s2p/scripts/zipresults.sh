#!/bin/bash

# zip the results

export PATH=$PATH:/usr/bin/:/usr/local/bin/:/bin/

zip -r results.zip s2p_results

# now remove the tiff files
#rm output*.tif
