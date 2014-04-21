#!/bin/bash

# usage:
# /path/to/stuff.sh alpha niter

# IMPLICIT INPUT FILES
#  a.png
#  b.png
#  t.tiff (OP)
#
# IMPLICIT OUTPUT FILES
#
#  stuff_rof.{tiff,png}       "F"
#  stuff_rof_div.{tiff,png}   "divF"
#  stuff_rof_abs.{tiff,png}   "|F|"
#  stuff_rof_inv.png          "F*B"
#  stuff_rof_apinv.png        "(A+F*B)/2"
#  stuff_rof_aminv.{tiff,png} "A-F*B"
#  stuff_rof_fmt.{tiff,png}   "F-T"
#  stuff_rof_afmt.{tiff,png}  "|F-T|"
#

DIVRANG=4
FLORANG=10
IDIFRAD=50
FDIFRAD=4

set -e

testex() {
	if which $1 > /dev/null ; then
		echo > /dev/null
	else
		echo "ERROR: executable file $1 not available" >&2
		exit 1
	fi
}

usgexit() {
	echo -e "usage:\n\t `basename $0` [nico|luis|warp|ldof...]"
	rm -rf $TPD
	exit 1
}

echo STUFF ARGC: $#
echo STUFF ARGV: $*

# check input
if [ $# != "9" ]; then
	usgexit
fi

echo STUFF ARGS: $*

test -f a.png || (echo "I need a file \"a.png\"!" ; exit 1)
test -f b.png || (echo "I need a file \"b.png\"!" ; exit 1)
#test -f t.tiff || (echo "I need a file \"t.tiff\"!" ; exit 1)
if test -f t.tiff; then
	HASTRUTH="yes"
else
	HASTRUTH=""
fi

mv a.png orig.a.png
mv b.png orig.b.png
unalpha orig.a.png a.png
unalpha orig.b.png b.png

if test $HASTRUTH; then
	mv t.tiff orig.t.tiff
	plambda orig.t.tiff "x[0] x[1] hypot 1000 > >1 <1 nan x[0] if <1 nan x[1] if join" > t.tiff
fi

NPROCS=$1
ALPHA=$2
GAMMA=$3
NSCALES=$4
ZOOM_FACTOR=$5
TOL=$6
INNER=$7
OUTER=$8
VERBOSE=$9


export MRANGE=4
VIEWFLOWPARAM=nan

FTYPE=rof
P=stuff_rof

echo "ALPHA = ${ALPHA}"
echo "GAMMA = ${GAMMA}"
echo "NSCALES = ${NSCALES}"
echo "ZOOM_FACTOR = ${ZOOM_FACTOR}"
echo "TOL = ${TOL}"
echo "INNER = ${INNER}"
echo "OUTER = ${OUTER}"

echo "FTYPE = ${FTYPE}"
echo "P = ${P}"



#if [ $FTYPE = "truth" ]; then
#	cp t.tiff ${P}.tiff
#else
#	flowany.sh ${FTYPE} a.png b.png > ${P}.tiff
#fi

#testex tvl1flow
testex brox2004


##jzach 1 a.png b.png $TAU $LAMBDA $THETA $NSCALES 0.5 $NITER ${P}.tiff 0
#echo /usr/bin/time -f "stufftime %e s" tvl1flow $NPROCS a.png b.png $TAU $LAMBDA $THETA $NSCALES 0.5 $NWARPS $EPSILON ${P}.tiff 0
#/usr/bin/time -f "stufftime %e s" tvl1flow $NPROCS a.png b.png $TAU $LAMBDA $THETA $NSCALES 0.5 $NWARPS $EPSILON ${P}.tiff 0  2> ${P}.stime
#cat ${P}.stime | /bin/grep stufftime  | cut -c11- > ${P}.time


echo /usr/bin/time -f "stufftime %e s" brox2004 a.png b.png ${P}.tiff ${ALPHA} ${GAMMA} ${NSCALES} ${ZOOM_FACTOR} ${TOL} ${INNER} ${OUTER} ${VERBOSE}
/usr/bin/time -f "stufftime %e s" brox2004 a.png b.png ${P}.tiff ${ALPHA} ${GAMMA} ${NSCALES} ${ZOOM_FACTOR} ${TOL} ${INNER} ${OUTER} ${VERBOSE}  2> ${P}.stime 
cat ${P}.stime | /bin/grep stufftime  | cut -c11- > ${P}.time

iion ${P}.tiff ${P}.uv
iion ${P}.tiff ${P}.flo


#hs $NITER $ALPHA a.png b.png ${P}.tiff

#  stuff_X.{tiff,png}       "F"
#  stuff_X_div.{tiff,png}   "divF"
#  stuff_X_abs.{tiff,png}   "|F|"
#  stuff_X_inv.png          "F*B"
#  stuff_X_apinv.png        "(A+F*B)/2"
#  stuff_X_aminv.{tiff,png} "A-F*B"
#  stuff_X_ofce.png         "|grad(A)*F + dA/dt|"

flowdiv ${P}.tiff ${P}_div.tiff
qeasy -$DIVRANG $DIVRANG  ${P}_div.tiff ${P}_div.png
flowgrad ${P}.tiff ${P}_grad.tiff
plambda ${P}_grad.tiff "x[0] x[1] hypot x[2] x[3] hypot join" | viewflow 10 - ${P}_grad.png
fnorm ${P}.tiff ${P}_abs.tiff
if test $HASTRUTH; then
	export MRANGE=`fnorm t.tiff -|imprintf "%a" -`
	#viewflow $VIEWFLOWPARAM t.tiff t.png
else
	export MRANGE=`imprintf "%q[99]" ${P}_abs.tiff`
fi
if test $COCOCOLORS; then
	export $VIEWFLOWPARAM=-$MRANGE
fi
FLORANG=$MRANGE
qeasy 0 $FLORANG ${P}_abs.tiff ${P}_abs.png
backflow ${P}.tiff b.png ${P}_inv.tiff; qeasy 0 255 ${P}_inv.tiff ${P}_inv.png
plambda a.png ${P}_inv.png "x y + 0 512 qe" | iion - PNG:- > ${P}_apinv.png
plambda a.png ${P}_inv.tiff "x y -" |tee ${P}_aminv.txt | qeasy -${IDIFRAD} ${IDIFRAD}  |iion - ${P}_aminv.png
#viewflow $VIEWFLOWPARAM ${P}.tiff ${P}.png


#  stuff_X_fmt.{tiff,png}   "F-T"
#  stuff_X_afmt.{tiff,png}  "|F-T|"
#  stuff_X_aerr.png  "angle(F,T)"

if test $FTYPE != "truth" && test $HASTRUTH; then
	plambda ${P}.tiff t.tiff "x y -" > ${P}_fmt.tiff
	plambda ${P}_fmt.tiff "x x = x 0 0 join if" > ${P}_fmt_nonan.tiff
	#viewflow $VIEWFLOWPARAM ${P}_fmt.tiff ${P}_fmt.png
	fnorm ${P}_fmt.tiff ${P}_afmt.tiff
	qeasy 0 $FDIFRAD ${P}_afmt.tiff ${P}_afmt.png
	plambda t.tiff ${P}.tiff "x[0] y[0] * x[1] y[1] * 1 + + x[0] x[1] 1 hypot hypot y[0] y[1] 1 hypot hypot * / acos pi / 180 *" | tee ${P}_aerr.txt | qeasy 0 180 - ${P}_aerr.png
fi

if [ $FTYPE == "truth" ]; then
	SIXE_BACK=`imprintf "%e %r" ${P}_aminv.txt`
	SIXE_EUCL="0 0"
	SIXE_ANGL="0 0"
else
	SIXE_BACK=`imprintf "%e %r" ${P}_aminv.txt`
	if test $HASTRUTH; then
		SIXE_EUCL=`imprintf "%e %r" ${P}_afmt.tiff`
		SIXE_ANGL=`imprintf "%e %r" ${P}_aerr.txt`
	else
		SIXE_EUCL="nan nan"
		SIXE_ANGL="nan nan"
	fi
fi

echo "$SIXE_BACK $SIXE_EUCL $SIXE_ANGL" > sixerror_$FTYPE.txt

#flowany.sh $FTYPE a.png b.png > f.tiff
#viewflow -1 f.tiff f.png
#flowdiv f.2d
