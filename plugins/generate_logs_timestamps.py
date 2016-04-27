# -*- coding: utf-8 -*-
"""
Created on Thu Mar 10 20:35:43 2016

@author: lucp8356

This plugin creates logs with TIMESTAMPS for a set of newick trees

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

no_cases = 1000
tree_files = glob.glob("../data/trees/*.nw")
record_timestamps = True

for filepath in tree_files:
    t = TreeNode(filepath,format=1)
    simulator = LogSimulator(t.write(format=1,format_root_node=True),no_cases,record_timestamps)
    traces = simulator.returnLog()

    tree_index = filepath[filepath.find('_'):filepath.rfind('.nw')]
    csv_file = open("../data/logs/log" + tree_index + ".csv", 'w')
    csv_file.write("case_id,act_name,start_time,end_time\n")
    trace_id = 0
    for trace in traces:
        trace_id += 1
        for event in trace:
            activity = event[0]
            start_time = event[1]
            end_time = event[2]
            csv_file.write(str(trace_id) + "," + activity + "," +
            str(start_time) + "," + str(end_time) + "\n")

    csv_file.close()