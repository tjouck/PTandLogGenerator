# -*- coding: utf-8 -*-
"""
Created on Tue Mar 08 21:06:39 2016

@author: lucp8356

This plugin creates logs for a set of newick trees

INPUT:
    set of newick trees
    number of cases

OUTPUT:
    logs in csv-file format

"""

import glob
import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
from simulateLog import LogSimulator
from add_noise import NoiseGenerator

#specify the input parameters
no_cases = 1000
noise_probability = 0.0

#specify the folder with the trees
tree_files = glob.glob("../data/trees/*.nw")

#for each tree
for filepath in tree_files:
    #generate traces
    t = TreeNode(filepath,format=1)
    simulator = LogSimulator(t.write(format=1,format_root_node=True),no_cases, record_timestamps = False)
    traces = simulator.returnLog()

    #add noise
    noise_generator = NoiseGenerator(traces, noise_probability)
    traces = noise_generator.resulting_traces

    #write log to csv-file
    tree_index = filepath[filepath.find('_'):filepath.rfind('.nw')]
    csv_file = open("../data/logs/log" + tree_index + ".csv", 'w')
    csv_file.write("case_id,act_name\n")
    trace_id = 0
    for trace in traces:
        trace_id += 1
        for act in trace:
            csv_file.write(str(trace_id) + "," + act + "\n")

    csv_file.close()