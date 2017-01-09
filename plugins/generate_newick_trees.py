# -*- coding: utf-8 -*-
"""
Created on Tue Mar 08 20:09:31 2016

@author: lucp8356

This plugin generates a collection of trees from a specified population.

INPUT: parameterfile (csv-formatted)
    Each row is one population:
    mode;min;max;sequence;choice;parallel;loop;or;silent;duplicate;lt_dependency;infrequent;no_models;unfold;max_repeat
    
    -mode: most frequent number of visible activities
    -min: minimum number of visible activities
    -max: maximum number of visible activities
    -sequence: probability to add a sequence operator to tree
    -choice: probability to add a choice operator to tree
    -parallel: probability to add a parallel operator to tree
    -loop: probability to add a loop operator to tree
    -or: probability to add an or operator to tree
    -silent: probability to add silent activity to a choice or loop operator
    -duplicate: probability to duplicate an activity label
    -lt_dependency: probability to add a random dependency to the tree
    -infrequent: probability to make a choice have infrequent paths
    -no_models: number of trees to generate from model population
    -unfold: whether or not to unfold loops in order to include choices underneath in dependencies: 0=False, 1=True
        ~ if lt_dependency <= 0: this should always be 0 (False)
        ~ if lt_dependency > 0: this can be 1 or 0 (True or False)
    -max_repeat: maximum number of repetitions of a loop (only used when unfolding is True)

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
parser.add_argument('--m', nargs='?', default=False, type=bool,
                    help='indicate whether to work with long-term dependencies as rules, '\
                    'default=False', metavar='rules', choices=[False,True])

parser.add_argument('--g', nargs='?', default=False, type=bool,
                    help='indicate whether to render graphviz image of tree, '\
                    'default=False', metavar='graphviz', choices=[False,True])

args = parser.parse_args()
print "start of plugin with arguments: ", args

parameter_lines = ''
first_line = True
population_index = 1

use_rules = args.m
render_image = args.g
parameter_lines = open(args.i)

#for each population generate trees
for line in parameter_lines:
    if first_line:
        first_line = False
        continue
    else:
        line = line.rstrip()
        parameters = line.split(';')

    no_trees = int(parameters[12])

    #generate no_trees trees
    for i in range(1,no_trees + 1):
        random_tree = RandomTree(line,use_rules)
        #print to newick tree file in folder Trees
        tree_name = "../data/trees/tree_" + str(population_index) + "_" + str(i)
        fname = tree_name + ".nw"
        random_tree.t.write(format=1, outfile=fname, format_root_node=True)
        #print to ptml file in folder Trees
        converter = PtmlConverter(tree_name,random_tree.t.write(format=1,format_root_node=True))
        #print tree to graphiv image file
        if render_image == True:
            graphiv_converter = GraphvizTree(random_tree.t.write(format=1,format_root_node=True), population_index, i)
    population_index += 1
    
    timing.endlog()