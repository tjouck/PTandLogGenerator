# -*- coding: utf-8 -*-
"""
Created on Tue Mar 08 19:43:23 2016

@author: lucp8356

Application can generate random trees using a population as input.
This population is based on the number of activities and the probability
of different workflow patterns.
It includes the patterns: sequence, choice, parallel, loop and or.
Silent actions will be added according to a given probability to the
patterns: loop (middle) and choice (one). Duplicate tasks will be
added to the final tree (after it is reduced).

"""

import string
import itertools
import random
import math
import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
from add_lt_dependencies_class import Lt_dependency
import scipy.stats as stats

class RandomTree():

    #initialize population parameters

    def __init__(self, parameterLine):
        self.parameterLine = parameterLine
        parameterLine = parameterLine.rstrip()
        parameters = parameterLine.split(';')
        mode = float (parameters[0])
        min_act = float (parameters[1])
        max_act = float (parameters[2])

        #define the probabilities for each of the patterns to include

        self.O = ["sequence","choice","parallel","loop","or"]
        self.pattern_probabilities = []
        operators = []
        _index = 3
        for operator in self.O:
            if float(parameters[_index]) > 0.0:
                self.pattern_probabilities.append((operator,float(parameters[_index])))
                operators.append(operator)
            _index += 1

        #create activity distribution function
        self.set_act_distribution(mode, min_act, max_act)
        self.total_activities = int(math.ceil(self.retrieve_no_act()))
        self.copy_total_activities = self.total_activities

        #include silent activities?
        self.prob_silent = float(parameters[8])

        #add duplicate activities?
        self.perc_duplicate = float(parameters[9])

        if self.perc_duplicate > 0.5:
            self.perc_duplicate = 0.5

        #add long-term dependencies?
        self.prob_lt_dependencies = float(parameters[10])

        #infrequent paths?
        self.infrequent_paths = parameters[11]

        #initialize tree object
        self.t = TreeNode()

        self.t = self.create_tree()

        #add lt-dependencies
        if self.prob_lt_dependencies > 0:
            tree_with_lt_dep = Lt_dependency(self.t, self.prob_lt_dependencies)
            added_lt_dependencies = tree_with_lt_dep.possible
            while not added_lt_dependencies:
                #print "GENERATE NEW TREE"
                tree_with_lt_dep = Lt_dependency(self.create_tree(), self.prob_lt_dependencies)
                added_lt_dependencies = tree_with_lt_dep.possible

            self.t = tree_with_lt_dep.t

            #reduce tree again
            self.reduce_tree()

        #add execution priorities to choices
        self.add_execution_priorities()

    ##################################################
    ##################################################

    def create_tree(self):
        self.t = TreeNode()
        #generate necessary number of activity labels
        alphabet = string.lowercase
        no_act_labels = 0
        self.total_activities = self.copy_total_activities
        self.set_act_labels = []
        r = 1

        while (self.total_activities > no_act_labels):
            l = itertools.product(alphabet,repeat = r)
            for t in l:
                label = ""
                for i in range(len(t)):
                    label += str (t[i])
                self.set_act_labels.append(label)
            no_act_labels = len(self.set_act_labels)
            r += 1

        step = 1

        #assign root operator

        #print "STEP ", step
        last_act_label = self.assign_root_operator()
        step += 1

        #add nodes to tree

        while (self.total_activities > 0):
            #print "STEP ", step
            last_act_label = self.add_node(last_act_label)
            step += 1

        #reduce tree
        self.reduce_tree()
        #print self.t.get_ascii(attributes=["name"], show_internal=True, compact=False)

        #add duplicates
        leaves = []

        duplicates_possible = self.check_dupl_poss()

        if duplicates_possible:

            for leaf in self.t.get_leaves():
                if leaf.name != "tau":
                    leaves.append(leaf)

            selected_duplicates = self.select_duplicates(leaves)
            if len(selected_duplicates) > 0:
                possible_replacements = [leaf for leaf in leaves if leaf not in selected_duplicates]
                self.add_duplicates(selected_duplicates,possible_replacements)

        return self.t



    def assign_root_operator(self):

        #select root
        r = self.t.get_tree_root()

        #select a random operator
        operator = self.select_operator()
        r.name = operator
        act = "a"

        #silent activity?
        prob_silent_act = self.prob_silent
        silent = False
        x = random.random()
        if x < prob_silent_act:
            silent = True

        #add two children if the replaced leaf is NOT a loop, otherwise add three
        #children

        if operator == 'loop':
            r.add_child(name = act)
            next_act = self.next_act_name(act)
            if silent:
                r.add_child(name = "tau")
            else:
                r.add_child(name = next_act)
                next_act = self.next_act_name(next_act)
                self.total_activities -= 1
            r.add_child(name = next_act)

        else:
            if silent and operator == "choice":
                number = random.choice([1,2])
                if number == 1:
                    r.add_child(name = "tau")
                    next_act = act
                    r.add_child(name = act)
                else:
                    next_act = act
                    r.add_child(name = act)
                    r.add_child(name = "tau")
                self.total_activities += 1
            else:
                r.add_child(name = act)
                next_act = self.next_act_name(act)
                r.add_child(name = next_act)

        #always at least two activities added
        self.total_activities -= 2

        #print "Remaining activities to integrate:", self.total_activities
        #print self.t.get_ascii(attributes=["name", "dist"], show_internal=True, compact=False)

        last_act_label = next_act

        return last_act_label


    def add_node(self, last_act_label):

        #select a random leaf node that is not a silent activity
        leaf_nok = True
        while (leaf_nok):
            l = self.select_random_leaf()
            if l.name != "tau":
                leaf_nok = False

        #select a random operator from O
        operator_nok = True
        while(operator_nok):
            operator = self.select_operator()
            if self.total_activities > 1:
                operator_nok = False
            else:
                if operator != "loop":
                    operator_nok = False
        #print "The selected operator is:", operator

        #rename the selected leaf and save the old name

        act = l.name
        l.name = operator

        #silent activity?
        prob_silent_act = self.prob_silent
        silent = False
        x = random.random()
        if x < prob_silent_act:
            silent = True

        #add two children if the replaced leaf is NOT a loop, otherwise add three
        #children

        if operator == 'loop':
            l.add_child(name = act)
            next_act = self.next_act_name(last_act_label)
            if silent:
                l.add_child(name = "tau")
            else:
                l.add_child(name = next_act)
                next_act = self.next_act_name(next_act)
                self.total_activities -= 1
            l.add_child(name = next_act)
            self.total_activities -= 1

        else:
            if silent and operator == "choice":
                number = random.choice([1,2])
                if number == 1:
                    l.add_child(name = "tau")
                    next_act = last_act_label
                    l.add_child(name = act)
                else:
                    next_act = last_act_label
                    l.add_child(name = act)
                    l.add_child(name = "tau")

            else:
                l.add_child(name = act)
                next_act = self.next_act_name(last_act_label)
                l.add_child(name = next_act)
                self.total_activities -= 1

        #print "Remaining activities to integrate:", self.total_activities

        #return last activity label so function can continue labeling on the
        #next call
        last_act_label = next_act

        return last_act_label


    def select_operator(self):
        x = random.random()
        cutoffs = []
        previous_cutoff = 0

        for i in range(len(self.pattern_probabilities) - 1):
            cutoffs.append(previous_cutoff + self.pattern_probabilities[i][1])
            previous_cutoff = previous_cutoff + self.pattern_probabilities[i][1]
        #print "cutoffs" , cutoffs

        j = len(cutoffs)
        for i in range(len(cutoffs)):
            if x < cutoffs[i]:
                j = i
                break

        #print "random number: " + str(x) + " --> " +  str(self.pattern_probabilities[j][0])
        return self.pattern_probabilities[j][0]

    def next_act_name(self,current_act):
        current_index = self.set_act_labels.index(current_act)
        act_name = self.set_act_labels[current_index+1]

        return act_name

    def select_random_leaf(self):
        leaves = self.t.get_leaves()
        leaf = random.choice(leaves)
        return leaf

    def reduce_tree(self):
        for descendant in self.t.iter_descendants():
            stop = False
            while stop == False:
                parent = descendant.get_ancestors()[0]
                if parent == self.t.get_tree_root():
                    stop = True
                    continue
                grandparent = descendant.get_ancestors()[1]
                if parent.name == grandparent.name and parent.name not in ["loop","sequence"]:
                    for child in parent.get_children(): child.dist = child.dist * parent.dist
                    parent.delete()
                elif parent.name == grandparent.name and parent.name != "loop":
                    sisters = grandparent.get_children()
                    for sister in sisters: sister.detach()
                    parent_index = sisters.index(parent)
                    for i in range(len(sisters)):
                        if i == parent_index :
                            for child in parent.get_children():
                                grandparent.add_child(child)
                        else:
                            grandparent.add_child(sisters[i])
                else:
                    stop = True

    def select_duplicates(self,leaves):
        selected = []
        for leaf in leaves:
            x = random.random()
            if x < self.perc_duplicate:
                selected.append(leaf)
        return selected

    def add_duplicates(self,selected, possible_duplicates):
        for task in selected:
            no_tries = 0
            duplicate_nok = True
            sisters = [sister.name for sister in task.get_sisters()]
            while duplicate_nok and no_tries < 30:
                duplicate = random.choice(possible_duplicates)
                if duplicate.name not in sisters:
                    duplicate_nok = False
                else:
                    no_tries += 1
            if no_tries < 30:
                #print task.name, " becomes ",  duplicate.name
                task.name = duplicate.name

    def add_execution_priorities(self):
        for node in self.t.traverse(strategy = "preorder"):
            if node.name == "choice" and self.infrequent_paths == "False":
                children = node.get_children()
                for child in children:
                    prob = 1.0/len(children)
                    child.dist = prob
            elif node.name == "choice" and self.infrequent_paths == "True":
                children = node.get_children()
                dominant_child = random.choice(children)
                dominant_child.dist = 0.9
                children.remove(dominant_child)
                for child in children:
                    prob = 0.1/len(children)
                    child.dist = prob

    def check_dupl_poss(self):
        possible = False
        for leaf in self.t.get_leaves():
            if leaf.get_ancestors()[0] != self.t.get_tree_root():
                return True
                break
        return possible

    def set_act_distribution(self, mode, min_act, max_act):
        c = (mode/1.0-min_act)/(max_act-min_act)
        act_distr_fu = stats.triang(c, loc=min_act, scale=max_act-min_act)
        self.act_distr = act_distr_fu

    def retrieve_no_act(self):
        return self.act_distr.rvs(1)

    def returnTree(self):
        return self.t.write(format=1,format_root_node=True)
