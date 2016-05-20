Process tree and log generator
==============================

Provides scripts to generate random process trees and simulate these trees into event logs.

Detailed information on the workings of the generator and simulator can be found in the paper: "Generating Artificial Data for Empirical Analysis of Process Discovery Algorithms: a Process Tree and Log Generator" in Zotero.

Process tree generator
----------------------

  * Input: parameter file for populations (example parameter file located in the '/data/parameter_files' folder).  
    Each line of the csv-file characterizes one population.

  * Output: collection of process trees in the 'data/trees' folder:
    * newick tree format (*.nw)
    * process tree markup language (*.ptml)
    * image file (*.png)
  
  * Usage: callable from command line:
    * call plugin: $python generate_newick_tree.py -i <paramter_file>
    * help: $python generate_newick_tree.py -h prints help
  
Log simulator
-------------

  * Input:
    * process trees in newick tree files
    * size: the number of traces in the event log
    * noise: the probability of inserting noise
    * timestamps: include timestamps (start and end for each activity?)

  * Output: event log in csv-file format 'case_id', 'act_name'[,'start_time','end_time']

  * Usage: callable from command line
    * call plugin: $python generate_logs.py [-h] [--i [input_folder]] [--t [timestamps]] size noise  
      Simulate event logs from process trees.  
      
      positional arguments:  
      size                number of traces to simulate  
      noise               probability to insert noise into trace
      
      optional arguments:  
      -h, --help          show this help message and exit  
      --i [input_folder]  specify the relative address to the trees folder, default=../data/trees/  
      --t [timestamps]    indicate whether to include timestamps or not, default=False  