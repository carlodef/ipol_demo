Subsampling the ground truth disparity
--------------------------------------
Instead of subsampling the ground truth disparity we compute its median on windows the size of the subsampling factor.

Subsampling the images
----------------------
The original images are already convolved by a gaussian with std=1.4, which is almost the good variance for subsampling (1.6 = 2 x 0.8) the imaged by a factor 2. To attain this level of filtering we filter by a gaussian with std   sqrt(1.6^2 - 1.4^2) = 0.775. 
If we whant to subsample by a larger factor let's say 4, then we need to filter the original image with a gaussian with std = 0.8 x 4 = 3.2, and the correction should be a gaussian with std sqrt(3.2^2 - 1.4^2)  = 2.877







Compute the occlusions of a disparity map 
-----------------------------------------

We assume that for each point of the disparity map we know the true depth.
Then we can compute the disparity d from the depth D, 
using d = f*b/D  (d: disparity, f: focal lenght, b: baseline, D: depth).
However no stereo algorithm will be able to produce this map without 
uncertainty, because of the self occlusions in the model.

The objective of this program is to estimate the occlusions. 

We are going to consider the left image as reference in a left-right pair,
and the depth map is corresponds to the left image.
Therefore the signed disparityes of the nearby objects will be less than 
the the far objects ( they will be all negative in general ). 
This implies that the occlusions are always going to appear at the left 
of the objects.


The procedure to compute the occlusions is simple, 
given a scanline d(x) of the disparity map, we define f(x) = x + d(x), 
and F_y = \{ x : f(x)  =y \}.
Then the non occluded portions of the scanline will be recovered as: 
Occ = \cup_y \max_x(F_y)


The occlusions algorith
-----------------------
F[] : is an array of lists, each position in the array represents an F_y, and pixel 
in the secondary scanline, the list will contain the index of the 
points in the reference scanline that correspond to the same poit ( fall nearby ) i.e. f(x) = y.

We process all discrete point x in the reference scanline from left to right.
For each one we compute x+f(x) and the two nearest integer positions 
y1=ceil(x+f(x)), y2=floor(x+f(x)). Then we add the index of x, in both lists F[y_1]  F[y_2].


Then the occlusion mask is constructed scanning each list in F[].
By default all the points are occluded.
Scanning backwards each list the first indexes (the last in the list) 
corredpond to the non occluded pixels, and are removed from the occluded mask.
In practice we mask as non occluded several pixels (not only the last one) 
as long as they are consecutive, because they may correspond to a sisible plane but slanted.




