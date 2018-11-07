# -*- coding: utf-8 -*-
"""
Created on Mon Aug 08 10:51:41 2016

DEPRECATED

New version of class Lt_dependency. It enables to insert random
dependencies among choices in the tree for which the precedence
relation < holds. The comments in the class definition highlight
the beginning of each of the five steps.

input:
    -a process tree (reduced) in newick format
    -a probability of long-term dependencies
output:
    -unfolded form of process tree with lt-dependencies in newick format
@author: Toon Jouck

DEPRECATED

"""

import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
import itertools
import random
import uuid

def search_choices(t):
    '''Return a list of choice nodes in the given tree t'''
    choices = []

    for node in t.traverse(strategy="preorder"):
        if node.name == "choice":
            choices.append(node)
    return choices

def derive_precedence(t, choice1, choice2):
    '''Returns the precedence relation between two choices in a given tree t
        * precedence = 0 choice1 || choice2 (precedence is unknown)
        * precedence = 1 choice1 < choice2 (choice1 before choice2)
        * precedence = 2 choice1 > choice2 (choice2 before choice1)
        * precedence = 3 choice1 = choice2 (choice1 same time choice2)
        '''
        
    common_ancestor = t.get_common_ancestor(choice1, choice2)
    if choice1 == choice2 or common_ancestor == choice1 or common_ancestor == choice2:
        precedence = 3
    elif common_ancestor.name != "sequence":
        precedence = 0
    else:
        for node in common_ancestor.traverse(strategy="preorder"):
            if node == choice1:
                precedence = 1
                break
            elif node == choice2:
                precedence = 2
                break
    return precedence

def return_precedences(t,choices):
    '''Returns a list with all < precedence relations between pairs of choices
    in the tree'''
    precedences_list = []
    for choice1 in choices:
        for choice2 in choices:
            precedence = derive_precedence(t,choice1,choice2)
            if precedence == 1:
                precedences_list.append([choice1,choice2])
    return precedences_list

#####vvvvvMATRIXvvvvvv#####

def _initialize_choices_matrix(t,choices):
    '''Return a matrix with the precedence relation
    between every pair of choices in the tree'''
    matrix = []
    for choice1 in choices:
        row = []
        for choice2 in choices:
            row.append(derive_precedence(t,choice1,choice2))
        matrix.append(row)
    return matrix

def _readable_precedence_relations(matrix):
    '''convert precedence values into symbols easy for reading'''
    converted_matrix = []
    for row in matrix:
        new_row = []
        for el in row:
            if el == 0:
                new_row.append('||')
            elif el == 1:
                new_row.append('<')
            elif el == 2:
                new_row.append('>')
            else:
                new_row.append('=')
        converted_matrix.append(new_row)
    return converted_matrix

def _print_matrix(matrix,choices):
    '''pretty print the matrix with precedence relations'''
    row_format =("{:>" + str(len(max(choices,key=len)) + 1) +"}") * (len(choices) + 1)
    print row_format.format("", *choices)
    for c, row in zip(choices, matrix):
        print row_format.format(c, *row)
        
def make_print_matrix(t):
    '''calls all functions to make and print matrix of precedence relations'''
    choices = search_choices(t)
    matrix = _readable_precedence_relations(_initialize_choices_matrix(t,choices))
    _print_matrix(matrix,_name_choices(choices))

#####^^^^^^MATRIX^^^^^^#####

def _get_leaf(node):
    '''check if leaf, otherwise we use the first child to continue'''
    if node.is_leaf():
        return node
    else:
        return _get_leaf(node.get_children()[0])

def _get_choice_leaves(choice_node):
    '''returns a list of first leaves under the given choice node'''
    choice_leaves = []
    for child in choice_node.get_children():
        choice_leaves.append(_get_leaf(child))
    return choice_leaves

def _get_names(nodes):
    '''put names of list of leaf nodes in tuple'''
    names = tuple()
    for n in nodes:
        names += (_get_leaf(n).name,)
    return names

def _names_row_headers(tuples):
    '''print names of tuple choice leaves'''
    headers = []
    for t in tuples:
        names = tuple()
        for node in t:
            names += (_get_leaf(node).name,)
        headers.append(names)
    return headers

def _name_choices(choices):
    '''makes choice names as x(name_child_1, ..., name_child_n)'''
    names = []
    for choice in choices:
        names.append("x" + str(_get_names(choice.get_children())))
    return names

def _print_sequences(sequences):
    '''Pretty print the sequences of choices'''
    for s in sequences:
        print _name_choices(s)

def _print_rule(rule):
    '''pretty print a rule'''
    output = ""
    for el in rule:
        if el == rule[-1]:
            output += " -> (not)" + el.name
        else:
            output += el.name

    print output

def _print_dec_table(table,rows,columns):
    '''pretty print a decision table'''
    row_format ="{:>15}" * (len(columns) + 1)
    print row_format.format("", *columns)
    for header, row in zip(rows, table):
        print row_format.format(header, *row)

def common_antecedent(x,y):
    if x[:-1] == y[:-1]:
        return True
    else:
        return False

def common_consequent(x,y):
    if x[1:] == y[1:]:
        return True
    else:
        return False

def add_element_to_sequence(antecedent,x,y,precedences):
    sequence = []
    if antecedent:
        if [x[-1],y[-1]] in precedences:
            sequence = x[:-1] + [x[-1],y[-1]]
        elif [y[-1],x[-1]] in precedences:
            sequence = x[:-1] + [y[-1],x[-1]]
    else:
        if [x[0],y[0]] in precedences:
            sequence = [x[0],y[0]] + x[1:]
        elif [y[0],x[0]] in precedences:
            sequence = [y[0],x[0]] + x[1:]
    return sequence

def prune_sequences(k_minus, k):
    to_prune = []
    #only prune when there are new sequences!
    if not k:
        #means there are no sequences in k!
        pass
    else:
        #prune if consequents are the same AND
        #n of the n+1 choices are the same!
        for seq_k_minus in k_minus:
            for seq_k in k:
                if seq_k_minus[-1] == seq_k[-1]:
                    if len(set(seq_k) - set(seq_k_minus)) == 1:
                        to_prune.append(seq_k_minus)
                        break
    """
    print "PRUNE the following sequences:"
    for s in to_prune:
        print _name_choices(s)
    """
    return [seq for seq in k_minus if seq not in to_prune]

def return_sequences(precedences):
    '''return all sequences based on the given the precedence between pairs of
    choices'''
    sequences = []
    sequences_k_minus = precedences
    sequences_k = sequences_k_minus

    while(len(sequences_k_minus) > 1):
        sequences_k = []
        for i in range(len(sequences_k_minus)-1):
            for j in range(i+1,len(sequences_k_minus)):
                x = sequences_k_minus[i]
                y = sequences_k_minus[j]
                new_sequence = []
                #check antecedent (=head)
                if common_antecedent(x,y):
                    new_sequence = add_element_to_sequence(True,x,y,precedences)
                
                """ SUPERFLUOUS
                elif common_consequent(x,y):
                    #print 'common consequent'
                    new_sequence = add_element_to_sequence(False,x,y,precedences)"""
                    
                #prune sequences already added and not add empty sequences!
                if new_sequence not in sequences_k and not not new_sequence:
                    sequences_k.append(new_sequence)

        #prune sequences k-1 where maximal antecedent in sequences k
        sequences_k_minus = prune_sequences(sequences_k_minus, sequences_k)
        sequences.extend(sequences_k_minus)
        sequences_k_minus = sequences_k

    sequences.extend(sequences_k)
    return sequences

def create_all_rules(sequences):
    '''create all possible rules for each sequence in the sequences set
        input: sequences
        output: list of rules (rules_list)
                dictionary with rule as key and [sequence(s)] as value'''
    rules_list = []
    rules_dictionary = {}
    for sequence in sequences:
        #get choices antecedent and consequent
        ante_choices = sequence[:-1]
        conse_choice = sequence[-1]
        headers = []
        antecedents = []
        for choice in ante_choices:
            headers.append(_get_choice_leaves(choice))

        #makes cartesian product of all choice leaves in the antecedent
        for pair in itertools.product(*headers):
            antecedents.append(pair)

        #create a rule for each combination of antecedent and leaf in
        #the consequent choice
        for antecedent in antecedents:
            for leaf in _get_choice_leaves(conse_choice):
                rule = antecedent + (leaf,)
                #add rule to list of rules if not yet present!
                if rule not in rules_list:
                    rules_list.append(rule)
                    rules_dictionary[rule] = [sequence]
                else:
                    rules_dictionary[rule].append(sequence)

    return rules_list, rules_dictionary
    
    
"""vvvSUPERFLUOUSvvv"""
def add_decision_table(sequence_obj):
    no_rows = 1
    row_headers = []
    decision_table = []
    headers = []
    head = sequence_obj.sequence[:-1]
    body = sequence_obj.sequence[-1]
    #determine the number of rows of the table based on the head
    for choice in head:
        no_rows *= len(choice.get_children())
        headers.append(_get_choice_leaves(choice))
    #determine row headers
    for pair in itertools.product(*headers):
        row_headers.append(pair)
    #determine the number of columns of the table based on the body
    no_columns = len(body.get_children())
    column_headers = _get_choice_leaves(body)
    #make the decision table
    for i in range(no_rows):
        row = []
        for j in range(no_columns):
            row.append(0)
        decision_table.append(row)

    sequence_obj.table = decision_table
    sequence_obj.row_headers = row_headers
    sequence_obj.column_headers = column_headers

def add_decision_tables(s_dict):
    '''creates a decision table for each sequence'''
    sequences_dictionary = {}
    for s,obj in s_dict.iteritems():
        add_decision_table(obj)
    return sequences_dictionary

def find_cell_dec_table(sequence_obj,rule):
    '''lookup row and column in decision table'''
    ante = rule[:-1]
    conse = rule[-1]
    index_row = sequence_obj.row_headers.index(ante)
    index_column = sequence_obj.column_headers.index(conse)
    return index_row, index_column

def adapt_decision_table(sequence_obj,rule):
    '''given a rule, changes the value of corresponding cell in decision
    table to 1'''
    index_row,index_column = find_cell_dec_table(sequence_obj,rule)
    sequence_obj.table[index_row][index_column] = 1

def return_all_rules_row(sequence_obj, row_index):
    '''returns all the rules of a given row'''
    pruned_rules = []
    for j in range(len(sequence_obj.table[row_index])):
        pruned_rules.append(sequence_obj.row_headers[row_index] +
        (sequence_obj.column_headers[j],))
    return pruned_rules

def adapt_decision_table_super(sequence_obj,rule):
    '''adapts the cells of the dependent rules and returns the pruned rules'''
    #find rows to adapt
    row_indices = []
    for r_h in sequence_obj.row_headers:
        if set(rule).issubset(set(r_h)):
            row_indices.append(sequence_obj.row_headers.index(r_h))
    #adapt the row in the table to all 1's
    pruned_rules = []
    for index in row_indices:
        sequence_obj.table[index] = [1] * len(sequence_obj.table[index])
        pruned_rules.extend(return_all_rules_row(sequence_obj,index))
    return pruned_rules

def find_corresponding_rule_row(sequence_obj,row_index):
    '''return rule for a non valid cell in a given row'''
    for j in range(len(sequence_obj.table[row_index])):
        cell = sequence_obj.table[row_index][j]
        if cell == 0:
            rule = sequence_obj.row_headers[row_index] + (sequence_obj.column_headers[j],)
            """
            print "PRUNED RULE (ROW):"
            _print_rule(rule)
            """
            break
    return rule

def find_corresponding_rule_column(sequence_obj,col_index):
    '''return rule for a non valid cell in a given column'''
    for j in range(len(sequence_obj.table)):
        cell = sequence_obj.table[j][col_index]
        if cell == 0:
            rule = sequence_obj.row_headers[j] + (sequence_obj.column_headers[col_index],)
            """
            print "PRUNED RULE (COLUMN):"
            _print_rule(rule)
            """
            break
    return rule

def return_non_valid_rules(sequence_object,rules_list):
    '''given a decision table, returns the non valid rules'''
    non_valid_rules = []
    #check rows
    for i in range(len(sequence_object.table)):
        row = sequence_object.table[i]
        if sum(row) == len(row) -1:
            non_valid_rules.append(find_corresponding_rule_row(sequence_object,i))
    #check columns
    for i in range(len(sequence_object.table[0])):
        sum_c = 0
        for j in range(len(sequence_object.table)):
            sum_c += sequence_object.table[j][i]
        if sum_c == len(sequence_object.table) - 1:
            non_valid_rule = find_corresponding_rule_column(sequence_object,i)
            non_valid_rules.append(non_valid_rule)

            #may need to prune rules in subsequences above
            #search for antecedent of pruned rule in rules above
            #(pruning is too strict actually as we focus on just one decision table
            # when checking for dead parts using the column totals)
            for i in range(1,len(non_valid_rule)-1):
                if non_valid_rule[:-i] in rules_list:
                    non_valid_rules.append(non_valid_rule[:-i])
                    """
                    print "PRUNED RULE ABOVE:"
                    _print_rule(non_valid_rule[:-i])
                    """
    return non_valid_rules

def search_sequences(sequence, sequence_dict):
    '''return sequences (list of tuples!) of which sequence is a subsequence'''
    supersequences = []
    all_sequences = sequence_dict.keys()
    for s in all_sequences:
        if tuple(sequence) == s[:len(sequence)] and len(s) > len(tuple(sequence)):
            supersequences.append(s)
    return supersequences

def return_pruned_rules(rule,rule_sequences,sequences_dict,rules_list):
    '''returns a list of rules that are pruned based on the given rule'''
    pruned_rules = [rule]
    #for each sequence related to the rule we will prune!
    for sequence in rule_sequences:
        #adapt decision table related to rule itself
        adapt_decision_table(sequences_dict[tuple(sequence)],rule)
        """
        _print_dec_table(sequences_dict[tuple(sequence)].table,
                        _names_row_headers(sequences_dict[tuple(sequence)].row_headers),
                        _get_names(sequences_dict[tuple(sequence)].column_headers))
        print "\n"
        """
        #use decision table to prune rules in that table
        pruned_rules.extend(return_non_valid_rules(sequences_dict[tuple(sequence)],
                                                                  rules_list))

        #Prune dependent rules
        #find sequences with current sequence as subsequence
        sequences_to_check = search_sequences(sequence,sequences_dict)

        for supersequence in sequences_to_check:
            #adapt decision table(s) related to dependent rules
            extra_rules = adapt_decision_table_super(sequences_dict[supersequence],rule)
            pruned_rules.extend(extra_rules)
            """
            print "PRUNED DEPENDENT RULES:"
            for r in extra_rules:
                _print_rule(r)
            _print_dec_table(sequences_dict[supersequence].table,
                        _names_row_headers(sequences_dict[supersequence].row_headers),
                        _get_names(sequences_dict[supersequence].column_headers))
            print "\n"
            """
            #use decision table to prune rules in that table
            pruned_rules.extend(return_non_valid_rules(sequences_dict[supersequence],
                                                       rules_list))
    return pruned_rules
"""^^^SUPERFLUOUS^^^"""

def consequences_ok(canonical_tree,rules):
    '''Prune rules that create DEAD ACTIVITY: checks if after inserting a rule 
    each consequent appears at least once'''
    check_ok = True
    consequents = [rule[-1] for rule in rules]
    leaves = canonical_tree.get_leaves()
    for c in consequents:
        if c.name not in [leaf.name for leaf in leaves]:
            #print [leaf.name for leaf in leaves]
            #print c.name, " NOT IN CANONICAL FORM AFTER RULE:"
            check_ok = False
            break
    return check_ok
    
def antecedents_ok(candidate,inserted_rules,rules):
    '''Prune rules that create a DEADLOCK: check if after inserting a rule
    not all rules with same antecedent are activated'''
    check_ok = True
    not_inserted = [r for r in rules if r not in inserted_rules]
    not_inserted.remove(candidate)
    if candidate[:-1] not in [rule[:-1] for rule in not_inserted]:
        check_ok = False
    return check_ok
    
def return_activated(active_rule,rules):
    '''Returns rules that are activated by the activated rule A => (not) C:
        rules with (A U C) part or equal the antecedent'''
    activated = []
    union = set(active_rule)
    for rule in rules:
        if union.issubset(set(rule)) and union != set(rule):
            activated.append(rule)
    return activated

def randomly_select_rules(rules,rules_dictionary,lt_probability,sequences_dict,canonical_tree):
    '''randomly selects rules from the list of all rules and returns list
        of inserted rules'''
    #first shuffle the list of rules
    random.shuffle(rules)

    #create decision table for each sequence
    add_decision_tables(sequences_dict)

    eliminated_rules = []
    inserted_rules = []
    #go through the list of rules
    for rule in rules:
        if rule in eliminated_rules:
            continue
        else:
            x = random.random()
            if x < lt_probability:
                #Before accepting the rule,check whether it is ok wrt consequents
                copy_canonical_tree = canonical_tree.copy()
                prune_canonical_tree(copy_canonical_tree,rule)
                check_dead_activity = consequences_ok(copy_canonical_tree,rules)
                check_dead_lock = antecedents_ok(rule,inserted_rules,rules)
                if (check_dead_activity and check_dead_lock):
                    prune_canonical_tree(canonical_tree,rule)
                    #print "ACTIVATED RULE:"
                    #_print_rule(rule)
                    inserted_rules.append(rule)
                    
                    """ONLY PREVENT ACTIVATING DOUBLE RULES"""
                    
                    pruned_rules = return_activated(rule,rules)

                    #prevent adding doubles to eliminated rules
                    eliminated_rules = eliminated_rules + list(set(pruned_rules) -
                                                                set(eliminated_rules))
                else:
                    #if the rules removes a consequent, it is eliminated
                    eliminated_rules.append(rule)
            else:
                pass
    '''
    print "INSERTED RULES:"
    for r in inserted_rules:
        _print_rule(r)'''
    
    """SUPERFLUOUS
    print "FINAL DECISION TABLES:"
    for sequence,obj in sequences_dict.iteritems():
        _print_dec_table(obj.table,_names_row_headers(obj.row_headers),
                         _get_names(obj.column_headers))
        print "\n"
    return inserted_rules"""

######vvvvvTreeTransformationvvvvv#######
def initialize_new_choice(choice,parent,new_choice):
    '''initialize new choice with copies of its former parent as
       children'''
    choice_children = choice.get_children()
    for i in range(len(choice_children)):
        new_choice.add_child(child=parent.copy(),dist=choice_children[i].dist)

def retain_child_i(node,i):
    '''removes all children execpt child i from node'''
    children = node.get_children()
    for j in range(len(children)):
        if i != j:
            children[j].detach()

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

def move_choice_up(choice_nodes):
    '''Function takes the deepest choice node and moves it upward.
       Calling this function over and over transforms the tree into
       canonical form'''
    last_choice = choice_nodes[-1]
    parent_last_choice = last_choice.up

    if parent_last_choice.name == 'choice':
        '''merge the parent choice with the selected choice'''
        adjust_distances(last_choice)
        last_choice.delete(prevent_nondicotomic=False)
    else:
        '''Create a new tree with a root of type choice. Under this choice we copy the
        parent of the selected choice as much as the selected choice had children.'''
        c = Tree('choice:1;',format=1)
        initialize_new_choice(last_choice,parent_last_choice,c)
        '''traverse the new tree and each time we find a copy of the selected choice,
        we keep only one child'''
        counter = 0
        for node in c.traverse(strategy='preorder'):
            if node.name == 'choice' and node != c.get_tree_root():
                if node.node_id == last_choice.node_id:
                    retain_child_i(node,counter)
                    simplify_choice(node)
                    counter += 1
        '''replace the parent of the selected choice with new tree c'''
        replace_parent_choice(parent_last_choice,c)

######^^^^^TreeTransformation^^^^^#######

def prune_canonical_tree(tree,rule):
    '''remove branches from canonical tree that contain all activities
       in the given rule'''
    act_names = _get_names(rule)
    for branch in tree.get_children():
        checked = []
        for leaf in branch:
            if leaf.name in act_names:
                checked.append(leaf.name)
        if set(act_names) == set(checked):
            branch.detach()

def recompute_branch_probabilities(tree):
    '''make the sum of all branch probabilities equal to one again'''
    total = 0
    for child in tree.get_children():
        total += child.dist

    for child in tree.get_children():
        child.dist = child.dist/total


class Sequence:
    def __init__(self,sequence):
        self.sequence = sequence
        self.table = []
        self.row_headers = []
        self.column_headers = []

class Lt_dependency():
    '''Add random long-term-dependencies to given newick tree'''
    def __init__(self,tree,lt_probability):
        self.tree = tree
        self.dependencies_possible = True
        self.lt_probability = lt_probability

    #1) Derive precedence relations between choices

        self.choices = search_choices(self.tree)
        self.precedences = return_precedences(self.tree,self.choices)
        
        #test if dependencies are possible before proceeding
        if not self.precedences:
            self.dependencies_possible = False
            return
        else:
            #print "ORIGINAL TREE:"
            #print self.tree.get_ascii()
            #print "PRECEDENCE RELATIONS:"
            for choices in self.precedences:
                name_choices = _name_choices(choices)
                #print name_choices[0] + ' < ' + name_choices[1]
    
        #2) Identify sequences of choices
    
            self.sequences = return_sequences(self.precedences)
            #print "SEQUENCES (Sx):"
            #_print_sequences(self.sequences)
    
        #3) Construct all possible dependency rules
    
            self.rules, self.rules_dictionary = create_all_rules(self.sequences)
    
        #4) Randomly select rules and prune rule list
            #a) Transform the tree
            self.canonical_tree = self.tree.copy()
            choice_nodes = self.canonical_tree.search_nodes(name='choice')
            add_id_to_choices(choice_nodes)
    
            step = 1
    
            #start of iteration: each iteration moves one choice up in the canonical tree
            #until it reaches the root of the tree
            
            while(len(choice_nodes)>1 or not choice_nodes[0].is_root()):
                move_choice_up(choice_nodes)
                choice_nodes = self.canonical_tree.search_nodes(name='choice')
                step += 1
                
            #b) Make a sequence object for each sequence to store information
            self.sequences_dictionary = {}
            for s in self.sequences:
                self.sequences_dictionary[tuple(s)] = Sequence(s)
                
            #c) Insert random rules based on pruning rules
            self.inserted_rules = randomly_select_rules(self.rules,
                                                        self.rules_dictionary,
                                                        self.lt_probability,
                                                        self.sequences_dictionary,
                                                        self.canonical_tree)
    
        #5) Normalize branch probabilities of canonical tree
            recompute_branch_probabilities(self.canonical_tree)
            #print self.canonical_tree.get_ascii(attributes=['name','dist'])