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

import argparse
import glob
import sys
sys.path.insert(0, '../newick/')
sys.path.insert(0, '../simpy/')
sys.path.insert(0, '../source/')
from tree import TreeNode
from simulateLog import LogSimulator
from add_noise import NoiseGenerator

parser = argparse.ArgumentParser(description='Simulate event logs from process trees.')
parser.add_argument('--i', nargs='?', default='../data/trees/',
                    help='specify the relative address to the trees folder' \
                    ', default=../data/trees/', metavar='input_folder')
parser.add_argument('size', type=int, help='number of traces to simulate')
parser.add_argument('noise', type=float, help='probability to insert noise into trace')
parser.add_argument('--t', nargs='?', default=False, type=bool,
                    help='indicate whether to include timestamps or not, '\
                    'default=False', metavar='timestamps', choices=[False,True])

args = parser.parse_args()

if args.noise < 0.0 or args.noise > 1.0:
    print "ERROR: specify noise probability in range [0,1]"
    sys.exit()

print "start of plugin with arguments: ", args

#read the input parameters
no_cases = args.size
noise_probability = args.noise
tree_folder = args.i
record_timestamps = args.t

#specify the folder with the trees
tree_files = glob.glob(tree_folder + "*.nw")

#for each tree
for filepath in tree_files:
    #generate traces
    t = TreeNode(filepath,format=1)
    simulator = LogSimulator(t.write(format=1,format_root_node=True),no_cases, record_timestamps)
    traces = simulator.returnLog()

    #add noise
    noise_generator = NoiseGenerator(traces, noise_probability)
    traces = noise_generator.resulting_traces

    #write log to csv-file
    tree_index = filepath[filepath.find('_'):filepath.rfind('.nw')]
    csv_file = open("../data/logs/log" + tree_index + ".csv", 'w')
    if record_timestamps:
        csv_file.write("traceid,activity,start_time,end_time\n")
    else:
        csv_file.write("traceid,activity\n")
    trace_id = 0
    for trace in traces:
        trace_id += 1
        for event in trace:
            if record_timestamps:
                activity = event[0]
                start_time = event[1]
                end_time = event[2]
                csv_file.write(str(trace_id) + "," + activity + "," +
                str(start_time) + "," + str(end_time) + "\n")
            else:
                activity = event[0]
                csv_file.write(str(trace_id) + "," + activity + "\n")

    csv_file.close()
