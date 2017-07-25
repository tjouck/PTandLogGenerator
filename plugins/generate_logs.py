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
from simulateTrace import TraceSimulator
from add_noise import NoiseGenerator
import xml.etree.ElementTree as xmltree
import timing
import random

def write_as_csv(traces,tree_index,record_timestamps):
    '''writes log to a csv-formatted file:
        case_id,act_name
        1,a
        1,b'''
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

def write_as_xes(traces,tree_index,record_timestamps):
    '''writes log to xes-formatted file'''
    xes_file = open("../data/logs/log" + tree_index + ".xes", 'w')
    xes_file.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    
    root = xmltree.Element('log')
    root.attrib['xes.version']="1.0" 
    root.attrib['xes.features']="nested-attributes"
    root.attrib['openxes.version']="1.0RC7" 
    root.attrib['xmlns']="http://www.xes-standard.org/"
    concept = xmltree.SubElement(root,'extension')
    concept.attrib['name']="Concept" 
    concept.attrib['prefix']="concept" 
    concept.attrib['uri']="http://www.xes-standard.org/concept.xesext"
    life = xmltree.SubElement(root,'extension')
    life.attrib['name']="Lifecycle" 
    life.attrib['prefix']="lifecycle"
    life.attrib['uri']="http://www.xes-standard.org/lifecycle.xesext"
    time = xmltree.SubElement(root,'extension')
    time.attrib['name']="Time" 
    time.attrib['prefix']="time"
    time.attrib['uri']="http://www.xes-standard.org/time.xesext"
    globalTrace = xmltree.SubElement(root,'global')
    globalTrace.attrib['scope']="trace"
    globalTraceAttr = xmltree.SubElement(globalTrace,'string')
    globalTraceAttr.attrib['key'] = "concept:name"
    globalTraceAttr.attrib['value'] = "name"
    globalEvent = xmltree.SubElement(root,'global')
    globalEvent.attrib['scope']="event"
    globalEventAttr = xmltree.SubElement(globalEvent,'string')
    globalEventAttr.attrib['key'] = "concept:name"
    globalEventAttr.attrib['value'] = "name"
    classifier = xmltree.SubElement(root,'classifier')
    classifier.attrib['name'] = "activity_classifier"
    classifier.attrib['keys'] = "concept:name"
    lname = xmltree.SubElement(root,'string')
    lname.attrib['key'] = "concept:name"
    lname.attrib['value'] = "log" + tree_index
    
    i = 1
    
    for t in traces:
        trace = xmltree.SubElement(root,'trace')
        tname = xmltree.SubElement(trace,'string')
        tname.attrib['key'] = "concept:name"
        tname.attrib['value'] = str(i)
        for act in t:
			if record_timestamps:
				start_event = xmltree.SubElement(trace,'event')
				start_ename = xmltree.SubElement(start_event,'string')
				start_ename.attrib['key'] = "concept:name"
				start_ename.attrib['value'] = act[0]
				start_elf = xmltree.SubElement(start_event,'string')
				start_elf.attrib['key'] = "lifecycle:transition"
				start_elf.attrib['value'] = 'start'
				start_etime = xmltree.SubElement(start_event,'date')
				start_etime.attrib['key'] = "time:timestamp"
				start_etime.attrib['value'] = act[1]
				
				end_event = xmltree.SubElement(trace,'event')
				end_ename = xmltree.SubElement(end_event,'string')
				end_ename.attrib['key'] = "concept:name"
				end_ename.attrib['value'] = act[0]
				end_elf = xmltree.SubElement(end_event,'string')
				end_elf.attrib['key'] = "lifecycle:transition"
				end_elf.attrib['value'] = 'complete'
				end_etime = xmltree.SubElement(end_event,'date')
				end_etime.attrib['key'] = "time:timestamp"
				end_etime.attrib['value'] = act[2]
			else:
				event = xmltree.SubElement(trace,'event')
				ename = xmltree.SubElement(event,'string')
				ename.attrib['key'] = "concept:name"
				ename.attrib['value'] = act
				elf = xmltree.SubElement(event,'string')
				elf.attrib['key'] = "lifecycle:transition"
				elf.attrib['value'] = 'complete'
        i += 1
    xes_file.write(xmltree.tostring(root))
    xes_file.close()
    
def select_child(children):
    x = random.random()
    cutoffs = []
    previous_cutoff = 0

    for i in range(len(children) - 1):
        cutoffs.append(previous_cutoff + children[i].dist)
        previous_cutoff = previous_cutoff + children[i].dist

    j = len(cutoffs)
    for i in range(len(cutoffs)):
        if x < cutoffs[i]:
            j = i
            break
    return children[j]
    


parser = argparse.ArgumentParser(description='Simulate event logs from process trees.')
parser.add_argument('--i', nargs='?', default='../data/trees/',
                    help='specify the relative address to the trees folder' \
                    ', default=../data/trees/', metavar='input_folder')
parser.add_argument('size', type=int, help='number of traces to simulate')
parser.add_argument('noise', type=float, help='probability to insert noise into trace')
parser.add_argument('--t', nargs='?', default=False, type=bool,
                    help='indicate whether to include timestamps or not, '\
                    'default=False', metavar='timestamps', choices=[False,True])
parser.add_argument('--f', nargs='?', default='xes',
                    help='indicate which format to use for the log: xes or csv, '\
                    'default=xes', metavar='format')

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
format_log = args.f

#specify the folder with the trees
tree_files = glob.glob(tree_folder + "*.nw")

#for each tree
for filepath in tree_files:
    
    #generate traces
    t = TreeNode(filepath,format=1)
    if t.get_tree_root().name == 'choice':
        traces = []
        children = t.get_children()
        for i in range(no_cases):
            child = select_child(children)
            if child.is_leaf():
                artificial_parent = TreeNode('sequence:1;')
                artificial_parent.add_child(child=child)
                simulator = TraceSimulator(artificial_parent.write(format=1,format_root_node=True),
                                           record_timestamps)
            else:
                simulator = TraceSimulator(child.write(format=1,format_root_node=True),
                                           record_timestamps)
            
            traces.append(simulator.case.trace)
    else:
        simulator = LogSimulator(t.write(format=1,format_root_node=True),no_cases, record_timestamps)
        traces = simulator.returnLog()

    #add noise
    noise_generator = NoiseGenerator(traces, noise_probability)
    traces = noise_generator.resulting_traces

    #write log to csv-file
    tree_index = filepath[filepath.find('_'):filepath.rfind('.nw')]
    if format_log == 'csv':
		write_as_csv(traces,tree_index,record_timestamps)
    elif format_log == 'xes':
		write_as_xes(traces,tree_index,record_timestamps)
	
timing.endlog()
