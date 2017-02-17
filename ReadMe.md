Process tree and log generator
==============================

Provides scripts to generate random process trees and simulate these trees into event logs.

Detailed information on the workings of the generator and simulator can be found in the paper: "Generating Artificial Data for Empirical Analysis of Process Discovery Algorithms: a Process Tree and Log Generator".

Process tree generator
----------------------

  * Input: parameter file for populations (example parameter file located in the '/data/parameter_files' folder).  
    Each line of the csv-file characterizes one population:
    mode;min;max;sequence;choice;parallel;loop;or;silent;duplicate;lt_dependency;infrequent;no_models;unfold;max_repeat
    * mode: most frequent number of visible activities
    * min: minimum number of visible activities
    * max: maximum number of visible activities
    * sequence: probability to add a sequence operator to tree
    * choice: probability to add a choice operator to tree
    * parallel: probability to add a parallel operator to tree
    * loop: probability to add a loop operator to tree
    * or: probability to add an or operator to tree
    * silent: probability to add silent activity to a choice or loop operator
    * duplicate: probability to duplicate an activity label
    * lt_dependency: probability to add a random dependency to the tree
    * infrequent: probability to make a choice have infrequent paths
    * no_models: number of trees to generate from model population
    * unfold: whether or not to unfold loops in order to include choices underneath in dependencies: 0=False, 1=True
      * if lt_dependency <= 0: this should always be 0 (False)
      * if lt_dependency > 0: this can be 1 or 0 (True or False)
    * max_repeat: maximum number of repetitions of a loop (only used when unfolding is True)

  * Output: collection of process trees in the 'data/trees' folder:
    * newick tree format (*.nw)
    * process tree markup language (*.ptml)
    * (optional) image file (*.png)
  
  * Usage: callable from command line:  
    $python generate_newick_trees.py [-h] [-i input_file] [--m [rules]] [--g [graphviz]]
    
    Generate process trees from input population.
    
    optional arguments:  
    -h, --help :     show this help message and exit  
    -i input_file  give the csv-formatted file in which the population  
    parameters are specified, example: ../data/parameter_files/example_parameters.csv
    --m indicate whether to work with long-term dependencies as rules, default=False  
    --g indicate whether to render graphviz image of tree, default=False  
	
  
Log simulator
-------------

  * Input:
    * process trees in newick tree files
    * size: the number of traces in the event log
    * noise: the probability of inserting noise
    * timestamps: include timestamps (start and end for each activity?)

  * Output: event log in XES format (default) or csv-file format 'case_id', 'act_name'[,'start_time','end_time']

  * Usage: callable from command line  
    call plugin: $python generate_logs.py [-h] [--i [input_folder]] [--t [timestamps]] [--f [format]] size noise
    
    Simulate event logs from process trees.  
      
    positional arguments:  
    size:                number of traces to simulate  
    noise:               probability to insert noise into trace
      
    optional arguments:  
    -h, --help :          show this help message and exit  
    --i [input_folder] : specify the relative address to the trees folder, default=../data/trees/  
    --t [timestamps] :   indicate whether to include timestamps or not, default=False  
    --f [format] : indicate which format to use for the log: xes or csv, default=xes  