# -*- coding: utf-8 -*-
"""
Created on Tue Mar 08 20:09:31 2016

@author: lucp8356

This plugin generates a collection of trees from a specified population.

INPUT: parameterfile (csv-formatted)
    Each row is one population:
    mode;min;max;sequence;choice;parallel;loop;or;silent;duplicate;lt_dependency;infrequent;no_models

OUTPUT:
    newick tree files (*.nw)
"""
import sys
import argparse
sys.path.insert(0, '../newick/')
sys.path.insert(0, '../simpy/')
sys.path.insert(0, '../source/')

from generateTree import RandomTree
from convert_to_ptml import PtmlConverter
from tree_to_graphviz import GraphvizTree
import timing


parser = argparse.ArgumentParser(description='Generate process trees from input population.')
parser.add_argument('-i', help='give the csv-formatted file in which the' \
                     ' population parameters are specified, example: ' \
                     '../data/parameter_files/example_parameters.csv',
                     metavar='input_file')

args = parser.parse_args()
print "start of plugin with arguments: ", args

parameter_lines = ''
first_line = True
population_index = 1

parameter_lines = open(args.i)

#for each population generate trees
for line in parameter_lines:
    if first_line:
        first_line = False
        continue
    else:
        line = line.rstrip()
        parameters = line.split(';')

    no_trees = int(parameters[-1])

    #generate no_trees trees
    for i in range(1,no_trees + 1):
        random_tree = RandomTree(line)
        #print to newick tree file in folder Trees
        tree_name = "../data/trees/tree_" + str(population_index) + "_" + str(i)
        fname = tree_name + ".nw"
        random_tree.t.write(format=1, outfile=fname, format_root_node=True)
        #print to ptml file in folder Trees
        converter = PtmlConverter(tree_name,random_tree.t.write(format=1,format_root_node=True))
        #print tree to graphiv image file
        graphiv_converter = GraphvizTree(random_tree.t.write(format=1,format_root_node=True), population_index, i)
        #print random_tree.t.get_ascii()
    population_index += 1
