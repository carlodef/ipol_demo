# <a name="sgbm"></a>SGBM

OpenCV variant of the famous Semi-Global Matching (SGM) algorithm by Heiko
Hirschmuller [HH08], that differs from the original one as follows:

Mutual information cost function is not implemented. Instead, a simpler
Birchfield-Tomasi sub-pixel metric from [BT98] is used. Though, the color
images are supported as well.  Some pre- and post- processing steps from K.
Konolige algorithm are included, for example: pre-filtering
(CV_STEREO_BM_XSOBEL type) and post-filtering (uniqueness check, quadratic
interpolation and speckle filtering).


# <a name="msmw"></a>MSMW

Multi-scale multi-window block matching algorithm. As cost function we use the
zero-mean SSD (ZSSD) [27] which removes the average intensity of each patch
rendering the comparison independent of the mean intensity. This cost is
defined as


# <a name="mgm"></a>MGM

More Global Matching. Variant of SGM which injects information from the 2D
problem in the processing of SGM 1D paths.


# <a name="micmac"></a>MicMac

http://logiciels.ign.fr/?-Micmac,3-



[HH08] Hirschmuller, Heiko. Stereo Processing by Semiglobal Matching and Mutual Information, PAMI, volume 30, No. 2, February 2008, pp. 328-341.
