# -*- coding: utf-8 -*-
"""
Created on Tue May 16 16:12:37 2017

Class for adding data dependencies to a process tree.
The data dependencies are in the form of DRD and Decision Tables.

@author: lucp8356
"""

import sys
sys.path.insert(0, 'newick/')
from tree import TreeNode
from decision_table import DecisionTable
from case_attribute import CaseAttribute
import random
import graphviz
import uuid
import cPickle
import itertools

class TreeWithDataDependencies:
    """stores process tree and DRD objects
       contains methods to build random DRD
       instance variables:
       t: newick tree object containing the process tree
       precedence_dict:
       target_determinism_level: proportion of rules to be implemented
       D: set of decision nodes, i.e. choices in the tree
       ID: set of input data nodes, i.e. choices or data attributes
       IR: information requirements of D in terms of ID
       choice_labels: a dictionary of choice nodes of the tree object (keys) with their labels (values)
       Delta: dictionary of decisions (keys) with their decision tables (values)
    """

    def __init__(self, tree_string, tree_index, D=None, ID=None, IR=None, target_dl=None):
        # type: (TreeWithDataDependencies, str, int, list, list, float) -> None
        self.t = TreeNode(tree_string, format=1)
        self.precedence_dict = dict()
        if target_dl is None:
            self.target_determinism_level = 0.5
        else:
            self.target_determinism_level = target_dl
        if D is None:
            self.D = []
        else:
            self.D = D
        if ID is None:
            self.ID = []
        else:
            self.ID = ID
        if IR is None:
            self.IR = []
        else:
            self.IR = IR
        self.choice_labels = dict()
        self.Delta = dict()
        # test if there are choice nodes in tree to determine if data dependencies are possible
        self.data_dependencies_possible = (len(self.t.search_nodes(name='choice')) > 0)
        self.tree_index = tree_index

    def extend_tree_with_data_dependencies(self,max_input_nodes,max_cutoff_values):
        # type: (TreeWithDataDependencies,int,int) -> None
        '''method applies all the methods in this class to extend a tree with data dependencies
        -max_input_nodes: denotes the maximum number of input nodes for each routing decision
        -max_cutoff_values: denotes the maximum number of intervals for each numerical variable
        in the data dependencies'''
        # step 1: randomly decide for each routing decision the
        # dependent routing decision and case attributes
        self.build_drd(max_input_nodes)
        tries = 1
        while (not len(self.D) > 0 and tries < 21):
            self.build_drd(max_input_nodes)
            tries += 1
        # if no decisions with case attributes (including previous decisions)
        if (len(self.D) == 0):
            # print 'ended up with empty DRD'
            self.data_dependencies_possible = False
        else:
            # step 2: make all possible decision rules and put them in decision tables for each routing
            # decision, then search and replace impossible rules
            self.initialize_decision_tables(max_cutoff=max_cutoff_values)
            self.replace_impossible_rules()
            # step 3: remove random rules from decision tables to insert data dependencies
            self.removed_rules = dict()
            self.insert_dependencies()
            # preparatory steps for simulation: map of each routing decision branch to the first activity in it
            # also map the rules to each routing decision
            self.construct_choice_first_leaves_dictionary()
            self.rules_simulation = dict()
            self.format_rules_for_simulation()
            self.removed_rules_simulation = dict()
            self.format_removed_rules_for_simulation()

    def format_rules_for_simulation(self):
        '''Method that formats rules as input of simulation code'''
        for d, dt in self.Delta.items():
            rules = []
            for rule in dt.R:
                antecedent = dict()
                for index,i_value in enumerate(rule[:-1]):
                    if isinstance(i_value,TreeNode):
                        antecedent[i_value] = True
                    #do not add null values to antecedent, because null means this entry is missing
                    elif i_value == 'null':
                        continue
                    else:
                        antecedent[dt.I[index].name] = i_value
                rules.append((antecedent,rule[-1]))
            self.rules_simulation[d] = rules

    def format_removed_rules_for_simulation(self):
        '''Method that formats rules as input of simulation code'''
        for d, rules in self.removed_rules.items():
            new_rules = []
            dt = self.Delta[d]
            for rule in rules:
                antecedent = dict()
                for index,i_value in enumerate(rule[:-1]):
                    if isinstance(i_value,TreeNode):
                        antecedent[i_value] = True
                    #do not add null values to antecedent, because null means this entry is missing
                    elif i_value == 'null':
                        continue
                    else:
                        antecedent[dt.I[index].name] = i_value
                new_rules.append((antecedent,rule[-1]))
            self.removed_rules_simulation[d] = new_rules

    def _add_id_to_tree_nodes(self):
        '''adds a unique id to each node in the tree'''
        for n in self.t.traverse(strategy='preorder'):
            new_id = str(uuid.uuid4())
            n.add_feature("id", new_id)

    def load_drd(self):
        '''uses the given node labels of D,ID and IR for rebuilding the DRD from a file'''
        self._add_id_to_tree_nodes()
        self.case_attr = []
        choices = [n for n in self.t.traverse(strategy='preorder') if n.name == 'choice']
        # assign the references of the choice nodes to D instead of the initial indices
        new_D = [choices[int(d) - 1] for d in self.D]
        self.D = new_D
        # assign the references of the choice nodes/case attributes to ID instead of the initial indices
        new_ID = []
        for id_ in self.ID:
            # assumes no more than 9 choice nodes!
            if len(id_) < 2:
                new_ID.append(choices[int(id_) - 1])
            else:
                if id_.startswith('z_'):
                    case_attr = CaseAttribute('z_' + id_.split('_')[-1],type=random.choice(['bool','num']))
                else:
                    case_attr = CaseAttribute(id_,type=random.choice(['bool','num']))
                self.case_attr.append(case_attr)
                new_ID.append(case_attr)
        self.ID = new_ID
        # assign the references of the choice nodes/case attributes to IR instead of the initial indices
        new_IR = []
        for ir in self.IR:
            new_ir = tuple()
            for el in ir:
                if len(el) < 2:
                    new_ir += (choices[int(el) - 1],)
                else:
                    for case_attr in self.case_attr:
                        if case_attr.name == el:
                            new_ir += (case_attr,)
                            break
            new_IR.append(new_ir)
        self.IR = new_IR
        # visualize the final DRD
        self._make_dot_viz('loaded', view_=True)

    def build_drd(self,max_inputs):
        '''STEP 1: build random DRD'''
        #assert that there is no DRD present
        assert not self.D, 'D already contains nodes, create another instance'
        assert not self.ID, 'ID already contains nodes, create another instance'
        assert not self.IR, 'IR already contains edges, create another instance'
        self._add_id_to_tree_nodes()
        # initialize DRD and list for each choice node the choice nodes preceding it
        for choice1 in self.t.search_nodes(name='choice'):
            self.D.append(choice1)
            precedences = []
            for choice2 in self.t.search_nodes(name='choice'):
                r = self._derive_precedence(self.t, choice1, choice2)
                if r == 2:
                    precedences.append(choice2)
            # add choice node to dictionary
            self.precedence_dict[choice1] = precedences

        # visualize initial drd
        # self._make_dot_viz('0')

        # set the maximum number of input data nodes per decision
        self.max_inputs = max_inputs
        self.case_attr_counter = 0
        self.case_attr = []

        visited_choices = []
        # select a random choice node (decision node)
        for j in range(len(self.precedence_dict)):
            d = random.choice([c for c in self.precedence_dict.keys() if c not in visited_choices])
            visited_choices.append(d)

            # select a random subset of input data nodes
            ID_d = self._return_random_subset_id(d)
            if len(ID_d) > 0:
                self.ID = list(set(self.ID).union(ID_d))

            # add information requirements (source,target)
            for i in ID_d:
                self.IR.append((i, d))

            # self._make_dot_viz(str(j + 1))

        # remove decision nodes from drd that have no input
        to_remove = []
        for d in self.D:
            as_target = 0
            for ir in self.IR:
                if d == ir[1]:
                    as_target += 1
            if as_target == 0:
                to_remove.append(d)

        for d in to_remove:
            self.D.remove(d)

        # make choice label dict for printing the decision table
        choices = []
        for n in self.t.traverse(strategy='preorder'):
            if n.name == 'choice':
                choices.append(n.id)

        for d in self.D:
            self.choice_labels[d.id] = str(choices.index(d.id) + 1)

        for input in self.ID:
            if isinstance(input,TreeNode) and input.id not in self.choice_labels.keys():
                self.choice_labels[input.id] = str(choices.index(input.id) + 1)

        # visualize the final DRD
        # self._make_dot_viz('final', view_=True)

        # pickle and save the DRD in a file
        # self.save_drd('final_drd.pkl')

    def _derive_precedence(self, t, node1, node2):
        '''Returns the precedence relation between two choices in a given tree t
        * precedence = -1 precedence is unknown
        * precedence = 0 node1 happens at same time as node2
        * precedence = 1 node1 happens before node2
        * precedence = 2 node2 happens before node1
        '''
        common_ancestor = t.get_common_ancestor(node1, node2)
        if (node1 in node2.get_descendants()) \
                or (node2 in node1.get_descendants()) \
                or (node1 == node2):
            precedence = 0
        elif common_ancestor.name != "sequence":
            precedence = -1
        else:
            for node in common_ancestor.traverse(strategy="preorder"):
                if node == node1:
                    precedence = 1
                    break
                elif node == node2:
                    precedence = 2
                    break
        return precedence

    def _print_precedence_dict(self, precedence_dict):
        '''print each key value pair with node names'''
        for key, value in precedence_dict.iteritems():
            print key.name, [node.name for node in value]

    def _return_random_case_attr(self, ID_d):
        '''randomly chooses either an existing case attribute, or creates a new one
           case attributes are denoted by z_i'''
        if self.case_attr_counter == 0:
            self.case_attr_counter += 1
            case_attr = CaseAttribute('z_' + str(self.case_attr_counter),type=random.choice(['bool','num']))
            self.case_attr.append(case_attr)
            return case_attr
        else:
            if random.random() < 0.5:
                passed = []
                # take existing case_attr unless already part of input nodes d
                for i in range(len(self.case_attr)):
                    random_attr = random.choice([a for a in self.case_attr if a not in passed])
                    if random_attr not in ID_d:
                        return random_attr
                # when no existing attr can be added, add new attribute
                self.case_attr_counter += 1
                case_attr = CaseAttribute('z_' + str(self.case_attr_counter),type=random.choice(['bool','num']))
                self.case_attr.append(case_attr)
                return case_attr
            else:
                # create new case attribute
                self.case_attr_counter += 1
                case_attr = CaseAttribute('z_' + str(self.case_attr_counter),type=random.choice(['bool','num']))
                self.case_attr.append(case_attr)
                return case_attr

    def _return_random_subset_id(self, d):
        '''returns a random subset of input data nodes:
            the subset contains between zero and the maximum number of input nodes'''
        ID_d = set()
        no_input_nodes = random.choice(range(0, self.max_inputs + 1))

        # get first input data node
        for i in range(no_input_nodes):
            if len(self.precedence_dict[d]) > 0:
                candidate = random.choice(self.precedence_dict[d])
                if candidate not in ID_d:
                    ID_d.add(candidate)
                else:
                    ID_d.add(self._return_random_case_attr(ID_d))
            else:
                ID_d.add(self._return_random_case_attr(ID_d))

        return ID_d

    def _make_dot_viz(self, label, view_=False):
        '''makes a dot visualization of the DRD'''
        dot = graphviz.Digraph(format='png')
        dot.graph_attr.update({'fontname': 'sans-serif', 'ranksep': '0.5', 'nodesep': '0.1', 'rankdir': 'BT'})
        dot.node_attr.update({'fontname': 'sans-serif', 'fontsize': '20', 'fixedsize': 'False'})
        dot.edge_attr.update({'fontname': 'sans-serif'})

        # get choices for indices
        choices = []
        for n in self.t.traverse(strategy='preorder'):
            if n.name == 'choice':
                choices.append(n.id)

        for d in self.D:
            d_label = "<x<SUB>" + str(choices.index(d.id) + 1) + "</SUB>>"
            self.choice_labels[d.id] = str(choices.index(d.id) + 1)
            dot.node(d.id, label=d_label, shape="box")

        for i in self.ID:
            if i in self.D:
                continue
            else:
                if i.name == 'choice':
                    i_label = "<x<SUB>" + str(choices.index(i.id) + 1) + "</SUB>>"
                    self.choice_labels[i.id] = str(choices.index(i.id) + 1)
                    dot.node(i.id, label=i_label, shape="ellipse")
                else:
                    i.id = str(uuid.uuid4())
                    i_label = "<z<SUB>" + i.name.split('_')[-1] + "</SUB>>"
                    dot.node(i.id, label=i_label, shape="ellipse")

        for ir in self.IR:
            dot.edge(ir[0].id, ir[1].id)

        dot.render(filename="drd_" + label, view=view_)

    def save_drd(self, filename):
        '''pickles and saves DRD = (D,ID,IR) in a file
        D = choice_labels, ID = choice_labels and case_attribute labels,
        IR = (label,label)'''
        node_labels = dict()
        for d in self.D:
            node_labels[d] = self.choice_labels[d.id]
        for i in self.ID:
            if isinstance(i, TreeNode):
                node_labels[i] = self.choice_labels[i.id]
            else:
                node_labels[i] = i.name
        with open(filename, 'wb') as output:
            cPickle.dump(self.t, output, cPickle.HIGHEST_PROTOCOL)
            cPickle.dump([node_labels[d] for d in self.D], output, cPickle.HIGHEST_PROTOCOL)
            cPickle.dump([node_labels[i] for i in self.ID], output, cPickle.HIGHEST_PROTOCOL)
            cPickle.dump([(node_labels[ir[0]], node_labels[ir[1]]) for ir in self.IR], output, cPickle.HIGHEST_PROTOCOL)
        output.close()

    def _return_outgoing_branches(self,node):
        '''
        Return the outgoing branches for a given choice TreeNode.
        If the outgoing branch is a sequence node, attach the first
        child of the sequence instead.
        '''
        return [child if child.name != 'sequence' else child.get_children()[0] for child in node.get_children()]

    def random_cutoff_numerical_var(self,max_cutoff):
        '''decides the intervals of the numerical variables'''
        cutoffs = []
        for i in range(random.choice([j+1 for j in range(max_cutoff)])):
            cutoffs.append(random.random())
        # add extremes to cutoffs
        cutoffs += [0,1.0]
        cutoffs.sort()
        return [(cutoffs[x],cutoffs[x+1]) for x in range(len(cutoffs)-1)]

    def initialize_decision_tables(self,max_cutoff=3):
        '''STEP 2: initializes all decision tables: each decision table contains:
        |rules| = no possible combinations of input values * no output values
        e.g. d = x_2 and ID_d = {z_1,x_1} then the R = {
        z_1 = True AND x_11 THEN x_21,
        z_1 = True AND x_11 THEN x_22,
        z_1 = True AND x_12 THEN x_21,
        z_1 = True AND x_12 THEN x_22,
        z_1 = False AND x_11 THEN x_21,
        z_1 = False AND x_11 THEN x_22,
        z_1 = False AND x_12 THEN x_21,
        z_1 = False AND x_12 THEN x_22}
        
        rule is a tuple with TreeNode objects, Booleans and list of numerical intervals [num1,num2)
        '''
        for d in self.D:
            # print d.get_ascii()
            ID_d = []
            for ir in self.IR:
                if d == ir[1]:
                    ID_d.append(ir[0])
            dt = DecisionTable(ID_d, d)

            # list all possible values for each input node in ID_d
            inputs = ()
            for i in ID_d:
                if isinstance(i, CaseAttribute):
                    # inputs depend on type of case attribute
                    if i.type == 'bool':
                        inputs += ([True, False],)
                    else:
                        # MAX cutoff default 3
                        inputs += (self.random_cutoff_numerical_var(max_cutoff),)
                else:
                    inputs += (self._return_outgoing_branches(i),)

            # make all combinations to make rules
            all_combinations = inputs + (self._return_outgoing_branches(d),)
            dt.R = [x for x in itertools.product(*all_combinations)]
            # print the decision table
            # dt.print_decision_table(self.choice_labels, d)
            # link decision with decision table and set maximum and miminum number of rules
            self.Delta[d] = dt
            dt.max_no_rules = len(dt.R)
            dt.min_no_rules = self._determine_min_no_rules(dt, d)

    def _determine_min_no_rules(self, dt, d):
        '''returns the minimum number of decision rules in the decision table: this is the
        maximum of the number of children of d or the number of possible input combinations'''
        set_distinct_inputs = set([r[:-1] for r in dt.R])
        if len(set_distinct_inputs) > len(d.get_children()):
            return len(set_distinct_inputs)
        else:
            return len(d.get_children())

    def _search_for_impossible_combinations(self):
        '''impossible combinations are combinations of children from two choices that are mutually
        exclusive'''
        dict_impossible_combinations = dict()
        for d in self.D:
            impossible_combinations = []
            ID_d = []
            for ir in self.IR:
                if d == ir[1]:
                    ID_d.append(ir[0])

            ID_d_choices = [i for i in ID_d if isinstance(i, TreeNode)]

            for pair in [comb for comb in itertools.combinations(ID_d_choices, 2)]:
                if pair[0] == self.t.get_common_ancestor(pair[0], pair[1]):
                    # print 'x_' + self.choice_labels[pair[0].id] + ' common ancestor of ' + 'x_' + self.choice_labels[
                    #    pair[1].id]
                    for branch in self._return_outgoing_branches(pair[0]):
                        if branch != self.t.get_common_ancestor(branch, pair[1]):
                            impossible_combinations.append((branch, pair[1]))
                elif pair[1] == self.t.get_common_ancestor(pair[0], pair[1]):
                    # print 'x_' + self.choice_labels[pair[1].id] + ' common ancestor of ' + 'x_' + self.choice_labels[
                    #    pair[0].id]
                    for branch in self._return_outgoing_branches(pair[1]):
                        if branch != self.t.get_common_ancestor(branch, pair[0]):
                            impossible_combinations.append((branch, pair[0]))
            if len(impossible_combinations) > 0:
                dict_impossible_combinations[d] = impossible_combinations
        return dict_impossible_combinations

    def _remove_duplicate_rules(self, dt):
        '''removes duplicate rules while preserving the order of the remaining rules'''
        seen = set()
        seen_add = seen.add
        return [x for x in dt.R if not (x in seen or seen_add(x))]

    def replace_impossible_rules(self):
        '''STEP 3: searches for impossible rules: when two input values can never happen together
        because the branches of the input nodes are mutual exclusive. Then replaces the set of
        these impossible rules with rules of the form (input1, null, output1). The number of
        new rules depends on the number of children of a choice that can never happen together
        with the children of another choice * the number of possible output values'''

        # search for impossible combinations
        self.dict_impossible_combinations = self._search_for_impossible_combinations()
        '''
        for choice, imp_comb in self.dict_impossible_combinations.iteritems():
            print 'Impossible combinations for x_' + self.choice_labels[choice.id]
            for pair in imp_comb:
                if pair[1].name == 'choice':
                    print '(' + pair[0].name + ',' + 'x_' + self.choice_labels[pair[1].id] + ')'
        '''

        # get all rules matching the impossible combinations
        if len(self.dict_impossible_combinations) > 0:
            for d, impossible_combinations in self.dict_impossible_combinations.iteritems():
                dt = self.Delta[d]
                for pair in impossible_combinations:
                    index_c = dt.I.index(pair[1])
                    for branch in self._return_outgoing_branches(pair[1]):
                        dt.R = [rule[:index_c] + ('null',) + rule[index_c + 1:]
                                if set((pair[0], branch)).issubset(set(rule))
                                else rule for rule in dt.R]

                # remove duplicate rules
                dt.R = self._remove_duplicate_rules(dt)
                # print the adapted decision table
                # dt.print_decision_table(self.choice_labels, d)
                # set maximum and miminum number of rules
                dt.max_no_rules = len(dt.R)
                dt.min_no_rules = self._determine_min_no_rules(dt, d)

                # print 'determinism level:', str(self._calculate_determinism_decision_table(dt))

    def _calculate_determinism_decision_table(self, dt):
        '''calculates the level of determinism for a decision table:
                             (maximum_no_rules - current_no_rules)
        determinism_level = ------------------------------------------
                           (maximum_no_rules - no_possible_out_values)'''
        return (dt.max_no_rules - len(dt.R)) / ((dt.max_no_rules - dt.min_no_rules) / 1.0)

    def calculate_mean_determinism_level(self):
        '''calculates the mean level of determinism over all decision tables:
                                        sum(determinism_level(table)
            mean_determinism_level = ---------------------------------
                                            no_decision_tables
            '''
        sum_determinism = 0
        for d in self.D:
            sum_determinism += self._calculate_determinism_decision_table(self.Delta[d])
        return (sum_determinism / (len(self.D) / 1.0))

    def insert_dependencies(self):
        '''STEP 4: removes rules in decision tables to ensure that mean determinism level has at least
        the target determinism level'''
        # smaller than is needed as otherwise the while loop is infinite for target_dl = 1
        minimum_rules_reached = []
        while (self.calculate_mean_determinism_level() < self.target_determinism_level
               and len(minimum_rules_reached) < len(self.D)):
            # print 'overall determinism level:', str(self.calculate_mean_determinism_level())
            random_d = random.choice([d for d in self.D if d not in minimum_rules_reached])
            random_dt = self.Delta[random_d]
            while (len(random_dt.R) == random_dt.min_no_rules):
                random_d = random.choice([d for d in self.D if d not in minimum_rules_reached])
                random_dt = self.Delta[random_d]

            removed_rule = self._remove_random_rule(random_dt)
            # if the removed rule is not None, then we add it to the dictionary
            if removed_rule:
                self.removed_rules[random_d] = self.removed_rules.get(random_d,[]) + [removed_rule]
            # else it means that it is impossible to remove another rule from the decision table
            else:
                minimum_rules_reached.append(random_d)
        # print the final decision table and its determinism level
        # for d in self.D:
        #    self.Delta[d].print_decision_table(self.choice_labels, d, self.tree_index)
            # self.Delta[d].print_decision_table(self.choice_labels, d, latex=True)
            # print 'determinism:', str(self._calculate_determinism_decision_table(self.Delta[d]))
        # print 'overall determinism level:', str(self.calculate_mean_determinism_level())
        # save final determinism level
        self.final_average_determinism_level = self.calculate_mean_determinism_level()

    def _remove_random_rule(self, dt):
        '''removes random rule from a given decision table and returns removed rule'''
        seen = []
        random_rule = random.choice([r for r in dt.R if r not in seen])
        seen.append(random_rule)
        # print 'random rule', random_rule
        while (not self._determine_removing_possible(random_rule, dt)):
            try:
                random_rule = random.choice([r for r in dt.R if r not in seen])
                seen.append(random_rule)
            except IndexError:
                random_rule = None
                break

        if random_rule:
            dt.R = [r for r in dt.R if r != random_rule]
        # return removed rule for creating traces with data noise during simulation
        return random_rule
        # print 'determinism:', str(self._calculate_determinism_decision_table(dt))

    def _determine_removing_possible(self, rule, dt):
        '''determine if one can remove a rule from a decision table or not:
        -a decision table contains at least one rule for each possible output value
        -a decision table contains at least one rule for each combination of input values'''
        rules_without_rule = [r for r in dt.R if r != rule]
        try:
            # check output values
            if [r[-1] for r in rules_without_rule].count(rule[-1]) < 1:
                possible = False
            # check input values
            elif [r[:-1] for r in rules_without_rule].count(rule[:-1]) < 1:
                possible = False
            else:
                possible = True
        except TypeError:
            possible = False
        return possible

    def _are_mutual(self, node1, ID):
        '''returns True if two nodes are mutual'''
        for node2 in ID:
            if self.t.get_common_ancestor(node1, node2).name == 'choice':
                return True
        return False

    def _are_equal_precedence(self, node1, ID_d):
        '''returns True if node1 has = precedence with another node in ID_d'''
        for node2 in ID_d:
            if self._derive_precedence(self.t, node1, node2) == 0:
                return True
        return False

    def _print_node_name(self, n):
        if n.is_leaf():
            print n.name
        else:
            print n.get_ascii()

    def _derive_precedence_latex(self, t, node1, node2):
        '''Returns the precedence relation between two choices in a given tree t
        * precedence = || precedence is unknown
        * precedence = < node1 happens before node2
        * precedence = > node2 happens before node1
        '''
        common_ancestor = t.get_common_ancestor(node1, node2)
        if (node1 in node2.get_descendants()) \
                or (node2 in node1.get_descendants()) \
                or (node1 == node2):
            precedence = '$=$'
        elif common_ancestor.name != "sequence":
            precedence = '$||$'
        else:
            for node in common_ancestor.traverse(strategy="preorder"):
                if node == node1:
                    precedence = '$<$'
                    break
                elif node == node2:
                    precedence = '$>$'
                    break
        return precedence

    def _name_operators(self, node_name):
        '''makes operator names as latex code'''
        if node_name == 'sequence':
            node_name = '$\rightarrow$'
        elif node_name == 'choice':
            node_name = '$\times$'
        elif node_name == 'parallel':
            node_name = '$\wedge$'
        elif node_name == 'or':
            node_name = '$\vee$'
        elif node_name == 'loop':
            node_name = '$\circlearrowleft$'
        return node_name

    def _get_first_leaf(self,node,first_leaves):
        '''gets the first leaf/leaves node(s) for a given branch (node) under a choice node'''
        if node.is_leaf():
            first_leaves.append(node)
        elif node.name=='sequence' or node.name=='loop':
            self._get_first_leaf(node.get_children()[0],first_leaves)
        elif node.name in ['choice', 'parallel', 'or']:
            for child in node.get_children():
                self._get_first_leaf(child,first_leaves)
        return first_leaves

    def construct_choice_first_leaves_dictionary(self):
        '''a dictionary of choices that are input nodes with its corresponding
        first leaves is built. Keys are leaf ids, values are choice labels.'''
        self.input_choice_dictionary = dict()
        for input_node in self.ID:
            if isinstance(input_node, CaseAttribute):
                continue
            else:
                # for each branch of the choice node
                for child in input_node.get_children():
                    # get all first leaves and store them in dictionary as keys
                    for leaf in self._get_first_leaf(child,[]):
                        self.input_choice_dictionary[leaf.id] = self.choice_labels[input_node.id]

    # @NOT USED insufficiently tested to prevent dead parts completely
    def _get_implicit_dependencies(self):
        '''this functions creates a dictionary containing information on which decision (tables)
        implicitly influence other decision (tables): keys are decisions that if we insert a dependency
        on would impact the values, i.e. decisions of which some of the rules have become impossible'''
        implicit_dependencies = dict()
        for d1,dt1 in self.Delta.iteritems():
            dec_and_inputs = [d1] + dt1.I
            for d2,dt2 in self.Delta.iteritems():
                if d1 != d2 :
                    intersect = set(dec_and_inputs).intersection(set(dt2.I))
                    if (d1 in intersect and len(intersect) > 1):
                        implicit_dependencies[d1] = implicit_dependencies.get(d1,[]) + [(d2,) + tuple(intersect)]
                else:
                    continue

        return implicit_dependencies

    # @NOT USED insufficiently tested to prevent dead parts completely
    def _dead_part_due_implicit_dependency(self, rule, d, implicit_dependencies):
        '''determines whether the removal of a rule related to d would create a dead part in
        another dependent decision table'''
        # go through all the dependent decisions tuple: tuple = (dependent_decision,input_1,...,input_n)
        for i,dependent_decision_tuple in enumerate(implicit_dependencies[d]):
            # get decision table related to dependent decision
            dependent_table = self.Delta[implicit_dependencies[d][i][0]]
            # get indices of values in dependent rules to check
            indices_rule = [self.Delta[d].I.index(input)
                            if input != d
                            else len(rule)-1 for input in implicit_dependencies[d][i][1:]]
            indices_dependent_rule = [dependent_table.I.index(input) for input in implicit_dependencies[d][i][1:]]
            # identify rules in dependent table that depend on rule
            matching_rules = []
            for dependent_rule in dependent_table.R:
                matches = True
                for j,index in enumerate(indices_rule):
                    # make distinctive tests for numerical attributes and other attributes (case, decision)
                    if type(rule[index]) == tuple:
                        if not (dependent_rule[indices_dependent_rule[j]][0] >= rule[index][0] and
                                dependent_rule[indices_dependent_rule[j]][1] <= rule[index][1]):
                            matches = False
                            break
                    else:
                        if rule[index] != dependent_rule[indices_dependent_rule[j]]:
                            matches = False
                            break
                if matches:
                    matching_rules.append(dependent_rule)

            dependent_outcomes = [r[-1] for r in dependent_table.R]
            new_dependent_outcomes = [r[-1] for r in dependent_table.R if r not in matching_rules]
            if not set(new_dependent_outcomes).issubset(set(dependent_outcomes)):
                print('rule',rule,
                      'makes dead activity',set(new_dependent_outcomes).intersection(set(dependent_outcomes)),
                      'by removing',matching_rules)