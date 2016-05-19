# -*- coding: utf-8 -*-
"""
Created on Mon Apr 25 11:04:33 2016

This class will let users calculate the number of unique paths in a given process
tree.

Input:
    tree_string: newick tree (*.nw) in string notation
    loop_iterations: number of iterations of a loop

Output:
    no_unique_traces: the number of unique traces in the tree

@author: lucp8356
"""

import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
import scipy as sp
import itertools

def simplify(paths):
    results = []
    d = dict(paths)
    keys = d.keys()
    for key in keys:
        matches = [item for item in paths if item[0] == key]
        x_0 = 0
        for (z_i, x_i) in matches:
            x_0 += x_i
        results.append((z_i, x_0))
    return results

def sequence(r,path):
    results = []
    for (z_r, x_r) in r:
        for (z_i, x_i) in path:
            x_0 = x_r * x_i
            z_0 = z_r + z_i
            results.append((z_0,x_0))
    return results

def choice(r,path):
    results = r
    for (z_i, x_i) in path:
        results.append((z_i, x_i))
    return results

def parallel(r,path):
    results = []
    for (z_r, x_r) in r:
        for (z_i, x_i) in path:
            x_0 = x_r * sp.special.binom(z_r + z_i, z_r) * x_i * sp.special.binom(z_i, z_i)
            z_0 = z_r + z_i
            results.append((z_0,x_0))
    return results

def loop(paths,iterations):
    do = paths[0]
    redo = paths[1]
    exit_ = paths[2]
    repeat = [(0,1)]
    xor_set = repeat
    for i in range(iterations):
        repeat = sequence(sequence(repeat,redo),do)
        xor_set = choice(xor_set,repeat)
    results = sequence(sequence(do,xor_set),exit_)
    return results

def or_(paths):
    results = []
    for i in range(1,len(paths)+1):
        for c in itertools.combinations(paths,i):
            if len(list(c)) < 2:
                for (z_i, x_i) in c[0]:
                    results.append((z_i, x_i))
            else:
                r = c[0]
                for i in range(1,len(c)):
                    r = parallel(r,c[i])
                for (z_i, x_i) in r:
                    results.append((z_i, x_i))
    return results

def numberOfPaths(node,paths,k):
    if (node.is_leaf()):
        if node.name == "tau":
            #print node.name, [(0,1)]
            return [(0,1)]
        else:
            #print node.name, [(1,1)]
            return [(1,1)]

    else:
        paths = []
        for child in node.get_children():
            paths.append(numberOfPaths(child,paths,k))
        if node.name == "sequence":
            results = paths[0]
            for i in range(1,len(node.get_children())):
                results = sequence(results,paths[i])
            #print node.name, simplify(results)
            return simplify(results)

        elif node.name == "choice":
            results = paths[0]
            for i in range(1,len(node.get_children())):
                results = choice(results,paths[i])
            #print node.name, simplify(results)
            return simplify(results)

        elif node.name == "parallel":
            results = paths[0]
            for i in range(1,len(node.get_children())):
                results = parallel(results,paths[i])
            #print node.name, simplify(results)
            return simplify(results)

        elif node.name == "loop":
            results = loop(paths,k)
            #print node.name, simplify(results)
            return simplify(results)

        elif node.name == "or":
            results = or_(paths)
            #print node.name, simplify(results)
            return simplify(results)

def sumOfPaths(paths):
    total_paths = 0
    for (z_i, x_i) in paths:
        total_paths += x_i
    return total_paths


class NoUniqueTraces:
    def __init__(self,tree_string,loop_iterations):
        t = TreeNode(tree_string,format = 1)
        print t.get_ascii(show_internal=True, compact=False)
        paths = []
        paths = numberOfPaths(t.get_tree_root(),paths,loop_iterations)
        self.no_unique_traces = sumOfPaths(paths)