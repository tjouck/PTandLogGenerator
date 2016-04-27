# -*- coding: utf-8 -*-
"""
Created on Mon Apr 25 11:13:15 2016

@author: lucp8356
"""

#function to recursively traverse a newick tree

def recurseTree(node):
    if (node.is_leaf()):
        print node.name
        return
    else:
        for child in node.get_children():
            recurseTree(child)
        print node.name

#function to make traces in a dictionary from a csv-formatted log-file

def make_traces(csv):
    entity_traces = {}
    first_line = True
    for line in csv:
        if first_line:
            first_line = False
            continue
        else:
            line = line.rstrip()
            attributes = line.split(',')
            entity_traces[attributes[0]] = entity_traces.setdefault(attributes[0],[])
            entity_traces[attributes[0]].append(attributes[1])
    return entity_traces

#function to print traces to a csv-formatted log-file (only control-flow)

def print_traces(entity_traces, log_file):
    log_file.write("case_id,act_name\n")
    for entity, trace in entity_traces.iteritems():
        for act in trace:
            log_file.write(entity + "," + act + "\n")

    log_file.close()