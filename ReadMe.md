Process tree and log generator
==============================

Provides scripts to generate random process trees and simulate these trees into event logs.

Detailed information on the workings of the generator and simulator can be found in the paper: "Generating Artificial Data for Empirical Analysis of Process Discovery Algorithms: a Process Tree and Log Generator" in Zotero.

Process tree generator
----------------------

-Input: parameter file located in the '/data/parameter_files' folder. Each line of the csv-file characterizes one population.

-Output: collection of process trees in the 'data/trees' folder:
  -newick tree format (*.nw)
  -process tree markup language (*.ptml)
  -image file (*.png)
  
Log simulator
-------------

-Input: process trees in newick tree files

-Output: event log in csv-file format