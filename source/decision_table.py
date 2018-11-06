# -*- coding: utf-8 -*-
"""
Created on Fri May 19 11:26:43 2017

@author: lucp8356
"""
import sys
sys.path.insert(0, 'newick/')
from case_attribute import CaseAttribute
import tabulate as tab
from tree import TreeNode

#delete automatic escaping of characters
del(tab.LATEX_ESCAPE_RULES[u'$'])
del(tab.LATEX_ESCAPE_RULES[u'{'])
del(tab.LATEX_ESCAPE_RULES[u'}'])
del(tab.LATEX_ESCAPE_RULES[u'_'])
del(tab.LATEX_ESCAPE_RULES[u'\\'])

class DecisionTable():
    '''object storing the inputs (I), outputs (O) and rules of a table (R)'''
    def __init__(self,ID_d,d):
        self.I = ID_d
        self.O = d.get_children()
        self.R = []
        self.hit_policy = 'COLLECT'
        self.max_no_rules = 0
        self.min_no_rules = 0

    # @DEPRECATED
    def print_decision_table_indices(self,choice_labels,d,latex=None):
        '''prints the decision table with labels for the choice nodes and indices of the branches'''
        headers = [self.hit_policy]
        for i in self.I:
            if isinstance(i,CaseAttribute):
                if latex == True:
                    headers.append('$' + i.name + '$')
                else:
                    headers.append(i.name)
            else:
                if latex == True:
                    headers.append('$\\times_{' + choice_labels[i.id] + '}$')
                else:
                    headers.append('x_' + choice_labels[i.id])
        headers.append('')
        if latex == True:
            headers.append('$\\times_{' + choice_labels[d.id] + '}$')
        else:
            headers.append('x_' + choice_labels[d.id])

        table = []
        index = 0
        for rule in self.R:
            table_row = [index + 1]
            for i_value in rule[:-1]:
                if isinstance(i_value,TreeNode):
                    index_i = rule.index(i_value)
                    if latex == True:
                        try:
                            table_row.append('$\\times_{' + choice_labels[self.I[index_i].id]
                            + str(self.I[index_i].get_children().index(i_value) + 1) + '}$')
                        except ValueError:
                            table_row.append('$\\times_{' + choice_labels[self.I[index_i].id]
                            + str(self.I[index_i].get_children().index(i_value.get_ancestors()[0]) + 1) + '}$')
                    else:
                        try:
                            table_row.append('x_' + choice_labels[self.I[index_i].id]
                            + str(self.I[index_i].get_children().index(i_value) + 1))
                        except ValueError:
                            table_row.append('x_' + choice_labels[self.I[index_i].id]
                            + str(self.I[index_i].get_children().index(i_value.get_ancestors()[0]) + 1))
                else:
                    table_row.append(i_value)
            table_row.append('')
            if latex == True:
                try:
                    table_row.append('$\\times_{' + choice_labels[d.id] + str(d.get_children().index(rule[-1])+1) + '}$')
                except ValueError:
                    table_row.append(
                        '$\\times_{' + choice_labels[d.id] + str(d.get_children().index(rule[-1].get_ancestors()[0]) + 1) + '}$')
            else:
                try:
                    table_row.append(
                        'x_' + choice_labels[d.id] + str(d.get_children().index(rule[-1])+1))
                except ValueError:
                    table_row.append(
                        'x_' + choice_labels[d.id] + str(d.get_children().index(rule[-1].get_ancestors()[0]) + 1))
            table.append(table_row)
            index += 1
        if latex is None:
            print(tab.tabulate(table, headers, tablefmt='fancy_grid'))
        elif latex == True:
            print(tab.tabulate(table, headers, tablefmt='latex_booktabs'))

    def _get_first_leaf(self,node,first_leaves):
        '''gets the first leaf/leaves node(s) for a given branch (node) under a choice node
        this function is needed to print decision table with names of first leaves in a branch'''
        if node.is_leaf():
            first_leaves.append(node)
        elif node.name=='sequence' or node.name=='loop':
            self._get_first_leaf(node.get_children()[0],first_leaves)
        elif node.name in ['choice', 'parallel', 'or']:
            for child in node.get_children():
                self._get_first_leaf(child,first_leaves)
        return first_leaves

    def print_decision_table(self,choice_labels,d,tree_index,latex=None):
        '''prints the decision table with labels for the choice nodes and names of the first leaves of branches'''
        headers = [self.hit_policy]
        for i in self.I:
            if isinstance(i, CaseAttribute):
                if latex == True:
                    headers.append('$' + i.name + '$')
                else:
                    headers.append(i.name)
            else:
                if latex == True:
                    headers.append('$\\times_{' + choice_labels[i.id] + '}$')
                else:
                    headers.append('x_' + choice_labels[i.id])
        headers.append('')
        if latex == True:
            headers.append('$\\times_{' + choice_labels[d.id] + '}$')
        else:
            headers.append('x_' + choice_labels[d.id])

        table = []
        index = 0
        for rule in self.R:
            table_row = [index + 1]
            for i_value in rule[:-1]:
                if isinstance(i_value, TreeNode):
                    first_leaves_names = ''
                    for leaf in self._get_first_leaf(i_value,[]):
                        if len(first_leaves_names) < 1:
                            first_leaves_names += leaf.name
                        else:
                            first_leaves_names += ',' + leaf.name
                    table_row.append(first_leaves_names)
                else:
                    table_row.append(i_value)
            table_row.append('')
            first_leaves_names = ''
            for leaf in self._get_first_leaf(rule[-1], []):
                if len(first_leaves_names) < 1:
                    first_leaves_names += leaf.name
                else:
                    first_leaves_names += ',' + leaf.name
            table_row.append(first_leaves_names)
            table.append(table_row)
            index += 1
        if latex is None:
            rule_file = open("../data/trees/tree" + str(tree_index) + "_rules_" + choice_labels[d.id] + ".txt","w")
            rule_file.write((tab.tabulate(table, headers, tablefmt='grid')))
        elif latex == True:
            print(tab.tabulate(table, headers, tablefmt='latex_booktabs'))