#!/usr/bin/python
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib as mpl
#mpl.use('Agg')
import matplotlib.pyplot as plt

def plot_modes(file_histo, file_modes, output_name, n_bins):

   fig = plt.figure()

   # Creation de l'axe des abscisses
   x = np.arange(n_bins)
   width = 0.85

   # Lecture des histogrammes
   f_h = open(file_histo)
   h = f_h.read().split()
   histo = [float(val)+0.01 for val in h] #+0.01 to force matplotlib to display even the bars with value 0

   # Lecture de la liste des modes
   f_m = open(file_modes)
   modes = f_m.read().split('\n')

   # Plot des histogrammes
   bars = plt.bar(x, histo, width, color='y')
   plt.axis([0,n_bins,min(histo),max(histo)])

   for m in modes:
       if m:
           (mode,theta,nfa) = m.split(';')
           (bound_l,bound_r) = mode.split(',')
           a = int(bound_l[1:])
           b = int(bound_r[:-2])
           if a <= b:
               x_m = np.arange(a,b+1,1)
               bars_m = plt.bar(x_m, histo[a:b+1], width, color='r')
           else:
               x_m1 = np.arange(a,n_bins,1)
               bars_m1 = plt.bar(x_m1, histo[a:n_bins], width, color='r')
               x_m2 = np.arange(0,b+1,1)
               bars_m2 = plt.bar(x_m2, histo[0:b+1], width, color='r')


   plt.grid(True)
#   plt.xlabel('Orientation, given by bin number (from -180 to 180 degrees)')
#   plt.ylabel('Weight of pixels')

   fig.savefig(output_name)
