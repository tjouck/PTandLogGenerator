# -*- coding: utf-8 -*-
"""
Created on Thursday Dec 15 09:29:55 2016

Class Lt_dependency. The initialization inserts random
dependencies among choices in the tree using a tree
unfolding method. The comments in the class definition highlight
the beginning of the two steps.

input:
    -a process tree (reduced) in newick format
    -a probability of long-term dependencies
    -unfold loops with choices
    -maximum number of repetitions of a loop
output:
    -unfolded form of process tree with lt-dependencies in newick format
@author: Toon Jouck
"""

import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
import random
import uuid
from math import pow,fsum

def simplify_choice(choice_node):
    '''the only child of the choice node is added to the parent'''
    only_child = choice_node.get_children()[0]
    choice_node.name = only_child.name
    only_child.delete(prevent_nondicotomic=False)

def add_id_to_choices(choices):
    '''adds unique ids to choices in canonical tree'''
    for choice in choices:
        new_id = str(uuid.uuid4())
        choice.add_features(node_id=new_id)

def replace_parent_choice(node,new_choice):
    '''puts the new choice node instead of the old parent node'''
    for child in node.iter_descendants():
        child.detach()

    node.name = 'choice'
    new_id = str(uuid.uuid4())
    node.add_features(node_id=new_id)

    for child in new_choice.children:
        node.add_child(child)

def adjust_distances(choice_node):
    '''recomputes branch probabilities of choices'''
    for child in choice_node.children:
        child.dist = choice_node.dist * child.dist
        
def make_new_choice(original_choice,parent,new_choice):
    '''detach all children of original choice and add them to a list'''
    children_original_choice = []
    for child in original_choice.get_children():
        children_original_choice.append(child)
        child.detach()
        
    '''duplicate parent under new choice node (initialize new choice)'''
    for i in range(len(children_original_choice)):
        new_choice.add_child(child=parent.copy(),dist=children_original_choice[i].dist)
        
    '''traverse the new choice choice and each time add child of the original choice'''
    for choice in new_choice.search_nodes(name='choice'):
        if not choice.is_root():
            if choice.node_id == original_choice.node_id:
                '''take the first element in the list of remaining children'''
                choice.add_child(child=children_original_choice[:1][0].copy(),dist=1)
                '''simplifiy the original choice'''
                simplify_choice(choice)
                '''remove the first child from the list'''
                children_original_choice = children_original_choice[1:]
        
        
def move_choice_up_fast(choice_nodes):
    '''Function takes the deepest choice node and moves it upward.
       Calling this function over and over unfolds the tree with regard
       to choices'''
    last_choice = choice_nodes[-1]
    parent_last_choice = last_choice.up

    if parent_last_choice.name == 'choice':
        '''merge the parent choice with the selected choice'''
        adjust_distances(last_choice)
        last_choice.delete(prevent_nondicotomic=False)
    else:
        '''Create a new tree with a root of type choice. Under this choice we copy the
        trimmed parent of the selected choice as much as the selected choice had children.'''
        c = TreeNode('choice:1;',format=1)
        make_new_choice(last_choice,parent_last_choice,c)
        
        '''replace the parent of the selected choice with new tree c'''
        replace_parent_choice(parent_last_choice,c)
        
def compute_probabilities_loop(max_iterations):
    '''Function computes normalized probabilites of the unfolded loop in case
    the original loop has 50/50 chance to enter/exit the loop'''
    probabilities = [0.5]
    for i in range(1,max_iterations+1):
        probabilities.append(pow(0.5,i))
    sum_prob = fsum(probabilities)
    for i in range(len(probabilities)):
        probabilities[i] = probabilities[i]/sum_prob
    return probabilities
        
def make_redo_do(i,do,redo):
    '''Function adds redo and do i times to a given tree'''
    sequence = TreeNode('sequence:1;',format=1)
    for j in range(i):
        sequence.add_child(child=redo.copy())
        sequence.add_child(child=do.copy())
    return sequence
        
def unfold_loop(loop_nodes,max_iterations):
    '''Function takes the deepest loop node and unfolds this loop into a choice between
    zero and the maximum number of iterations of do and redo'''
    last_loop = loop_nodes[-1]
    branch_probabilities = compute_probabilities_loop(max_iterations)
    '''create a new tree with a sequence as root node and three children:
        -original do-child of the loop
        -a choice between 0,...,max_iterations of redo and do children
        -original exit-child'''
    unfolded_loop = TreeNode('sequence:1;',format=1)
    children_loop = last_loop.get_children()
    unfolded_loop.add_child(child=children_loop[0].copy())
    second_child = TreeNode('(tau:' + str(branch_probabilities[0]) + ')choice:1;',format=1)
    for i in range(max_iterations):
        sequence = make_redo_do(i+1,children_loop[0].copy(),children_loop[1].copy())
        second_child.add_child(child=sequence,dist=branch_probabilities[i+1])
    unfolded_loop.add_child(child=second_child)
    unfolded_loop.add_child(child=children_loop[2].copy())
    
    '''replace old loop node (with subtree) by unfolded loop node'''
    for child in last_loop.get_children():
        child.detach()

    last_loop.name = 'sequence'
    
    for child in unfolded_loop.get_children():
        last_loop.add_child(child)
    
def return_non_loop_choices(tree,choice_nodes):
    '''function returns all choices except the ones under a loop'''
    queue = [] 
    for choice in choice_nodes:
        if choice.is_root():
            continue
        elif choice.up.name == 'loop':
            if choice in choice.up.get_children()[:2] and choice not in queue:
                queue.append(choice)
    choice_nodes = [choice for choice in choice_nodes if choice not in set(queue)]
    return choice_nodes
    
def unfold_choices(tree,choice_nodes):
    '''function unfolds all choices in the tree, except the ones under a loop'''
    #start of iteration: each iteration moves one choice up in the canonical tree
    #until it reaches the root of the tree
    choice_nodes = return_non_loop_choices(tree,choice_nodes)
    if not choice_nodes:
        return
    while(len(choice_nodes)>1 or not choice_nodes[0].is_root()):
        move_choice_up_fast(choice_nodes)
        choice_nodes = return_non_loop_choices(tree,tree.search_nodes(name='choice'))
        if not choice_nodes:
            return
        
def choice_under_loop(tree):
    '''returns True if there at least one loop with a choice in the do or redo child'''
    check = False
    choice_nodes = tree.search_nodes(name='choice')
    for choice in choice_nodes:
        if not choice.is_root():
            check = True
            break
    return check
    
def return_loops_with_choices(loops):
    '''returns all the loop nodes that have a choice as the first or second child'''
    loops_with_choices = []
    for loop in loops:
        for child in loop.get_children()[:2]:
            if child.name == 'choice':
                loops_with_choices.append(loop)
                break
            
    return loops_with_choices
        
def add_id_to_subtrees(children):
    '''adds unique ids to subtrees in canonical tree'''
    for child in children:
        new_id = str(uuid.uuid4())
        child.add_features(node_id=new_id)
        
def pruning_mechanism(tree,node):
    '''returns true if removing the subtree of the given node does not create a dead activity'''
    pruning_ok = True
    '''get activities in subtree of node'''
    act_subtree = tree.get_leaf_names()
    '''get activities in subtree of all other nodes'''
    act_other = []
    for child in tree.get_children():
        if child.node_id != node.node_id:
            act_other.extend(child.get_leaf_names())
    '''compare sets of activities'''
    if not set(act_subtree).issubset(set(act_other)):
        pruning_ok = False
    return pruning_ok
    
def recompute_branch_probabilities(tree):
    '''make the sum of all branch probabilities equal to one again'''
    total = 0
    for child in tree.get_children():
        total += child.dist

    for child in tree.get_children():
        child.dist = child.dist/total

class Lt_dependency_naive():
    '''Add random long-term-dependencies to given newick tree'''
    def __init__(self,tree,lt_probability,unfold,max_iterations):
        self.tree = tree
        self.dependencies_possible = True
        self.lt_probability = lt_probability
        self.no_removed_subtrees = 0
        #fix the maximum of iterations for now
        self.unfold = unfold
        self.max_iterations = max_iterations
        
        #1) Transform the tree
        self.canonical_tree = self.tree.copy()
        choice_nodes = self.canonical_tree.search_nodes(name='choice')
        
        if choice_nodes == []:
            self.dependencies_possible = False
            return
        else:
        
            add_id_to_choices(choice_nodes)
        
            #unfold all choices untill only the root is a choice and possibly some
            #children of loop nodes
            unfold_choices(self.canonical_tree,choice_nodes)
            
            #check if the tree contains loop nodes
            
            loop_nodes = self.canonical_tree.search_nodes(name='loop')

            # check if the root node is a loop node
            if not loop_nodes:
                loop_is_root = False
            else:
                loop_is_root = loop_nodes[0].is_root()
            
            #if the root node is a choice and all other choices are stuck under a loop
            if len(loop_nodes)>0 and choice_under_loop(self.canonical_tree):
                
                #if the user wants to unfold, proceed
                if self.unfold == 1:
                    #get all loops with a choice as first or second child
                    loop_nodes = return_loops_with_choices(loop_nodes)
                    #unfold deepest loop
                    while(len(loop_nodes)>0):
                        unfold_loop(loop_nodes,self.max_iterations)
                        choice_nodes = self.canonical_tree.search_nodes(name='choice')
                        add_id_to_choices(choice_nodes)
                        unfold_choices(self.canonical_tree,choice_nodes)
                        loop_nodes = return_loops_with_choices(self.canonical_tree.search_nodes(name='loop'))
                
            #2) remove random subtrees of the root node
            # handle special case where the loop is the root node
            if loop_is_root and self.unfold == 0:
                # removing children of choices under the loop not correct as it is comparable
                # to directly unfolding choices under loops (without unfolding loops first)
                self.no_subtrees = 0
                self.no_removed_subtrees = 0
            else:
                add_id_to_subtrees(self.canonical_tree.get_children())
                self.no_subtrees = len(self.canonical_tree.get_children())
                for n in self.canonical_tree.get_children():
                    x = random.random()
                    if x < self.lt_probability and pruning_mechanism(self.canonical_tree, n):
                        self.no_removed_subtrees += 1
                        n.detach()

                # Normalize branch probabilities of canonical tree
                recompute_branch_probabilities(self.canonical_tree)