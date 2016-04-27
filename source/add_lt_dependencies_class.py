# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 11:02:51 2015

@author: lucp8356

This script implements a method to add LT-dependencies to a process tree in
newick format.

============================
Parameters:
============================

input: newick tree file *.nw

output: newick tree file *.nw

"""
import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
import random
import itertools
import uuid

def search_choices(t):
    choices = []

    for node in t.traverse(strategy="preorder"):
        if node.name == "choice":
            choices.append(node)
    return choices

def _get_leaf(node):
    if node.is_leaf():
        return node
    #otherwise we use the first child to continue
    #this would affect the rules with children of the or-construct
    else:
        return _get_leaf(node.get_children()[0])

def get_first_leaves(choice):
    first_leaves = []
    children = choice.get_children()
    for child in children:
        first_leaf = _get_leaf(child)
        first_leaves.append(first_leaf)
    return first_leaves

def get_first_leaves2(choice):
    first_leaves = []
    children = choice.get_children()
    node_names_parent = {}
    for child in children:
        new_id = str(uuid.uuid4())
        first_leaf = _get_leaf(child)
        child.add_features(parent=new_id)
        try:
            if first_leaf.parent != None:
                first_leaf.parent = new_id
        except:
            first_leaf.add_features(parent=new_id)
        node_names_parent[first_leaf.name] = new_id
        first_leaves.append(first_leaf)
    return first_leaves, node_names_parent

def create_decision_table(head, body, choice_leaves):
    no_rows = 1
    row_headers = []
    decision_table = []
    headers = []
    #determine the number of rows of the table based on the head
    for choice in head:
        no_rows *= len(choice.get_children())
        headers.append(choice_leaves[choice])
    #determine row headers
    for pair in itertools.product(*headers):
        row_headers.append(pair)
    #determine the number of columns of the table based on the body
    no_columns = len(body.get_children())
    column_headers = choice_leaves[body]
    #make the decision table
    for i in range(no_rows):
        row = []
        for j in range(no_columns):
            row.append(0)
        decision_table.append(row)
    return decision_table, row_headers, column_headers


def _same_common_ancestor(choices, new_choice,t):
    same_ancestor = True
    for choice in choices:
        common_ancestor = t.get_common_ancestor(choice, new_choice)
        if common_ancestor.name != "sequence":
            same_ancestor = False
            break

    return same_ancestor

def _restore_order(set_choices, ordered_choices):
    ordered_set = []
    for choice in ordered_choices:
        if choice in set_choices:
            ordered_set.append(choice)

    return ordered_set

def search_candidates(t, choices, choice_leaves):
    seq_choices = {}
    seq_candidates = {}
    seq_candidate_tree = {}

    #group choices with common sequence and keep their order!
    #SIMPLIFICATION: if sequence has a parallel, or, loop with multiple
    ################ choices as children, then only one will be in a candidate!
    for i in range(len(choices)):
        for j in range(i+1,len(choices)):
            common_anc = t.get_common_ancestor(choices[i], choices[j])
            if common_anc.name == "sequence":
                seq_choices[common_anc] = seq_choices.setdefault(common_anc,[])
                #check if common ancestor is sequence for all choices
                if choices[i] not in seq_choices[common_anc] and \
                    _same_common_ancestor(seq_choices[common_anc],choices[i],t):
                    seq_choices[common_anc].append(choices[i])
                    #print choices[i]

                #check if common ancestor is sequence for all choices
                if choices[j] not in seq_choices[common_anc] and \
                    _same_common_ancestor(seq_choices[common_anc],choices[j],t):
                    seq_choices[common_anc].append(choices[j])
                    #print choices[j]

    #remove sequences of choices that are subsets of other sequences
    to_be_removed = []
    to_be_adapted = []
    for seq_1,choices_1 in seq_choices.iteritems():
        for seq_2,choices_2 in seq_choices.iteritems():
            set_1 = set(choices_1)
            set_2 = set(choices_2)
            if seq_1 != seq_2 and set_1.issubset(set_2):
                to_be_removed.append(seq_1)
                to_be_adapted.append(seq_2)

    for seq in to_be_removed:
        del seq_choices[seq]

    #restore the order of the choices in supersets
    for seq in to_be_adapted:
        seq_choices[seq] = _restore_order(seq_choices[seq],choices)

    #make candidates: (ante_1,...,ante_n,conse) from grouped choices
    for seq, grouped_choices in seq_choices.items():
        candidate_tree = TreeNode("root;",format=1)
        for i in range(1,len(grouped_choices)):
            body = grouped_choices[i]
            head = grouped_choices[:i]
            candidate = tuple(head) + (body,)
            #new part to include dependency metric
            dec_table,row_headers,column_headers = create_decision_table(head,
                                                        body, choice_leaves)
            #add candidate to tree structure(sequence)
            last_node = candidate_tree.get_leaves()[0]
            last_node.add_child(name=candidate)
            for leaf in candidate_tree:
                leaf.add_features(table=dec_table,rows=row_headers,columns=column_headers)

            seq_candidates[seq] = seq_candidates.setdefault(seq,[])
            seq_candidates[seq].append(candidate)
            seq_candidate_tree[seq] = candidate_tree

    return seq_choices, seq_candidates, seq_candidate_tree


def add_to_rule_tree(rule_tree,choices,choice_leaves,pointers,pointer_id):
    leaves = rule_tree.get_leaves()
    #get the first leaf of each child in the choice for building the tree
    first_leaves, node_names_parent = get_first_leaves2(choices[0])
    for leaf in leaves:
        for child in first_leaves:
            if child not in pointers:
                pointer_id = pointer_id + 1
                pointers[child] = pointer_id
                child.support = pointer_id
            leaf.add_child(name=child.name, dist=pointers[child])
            #add parent feature to ensure it can be found later on
            for x in leaf.search_nodes(dist=pointers[child]):
                x.add_features(parent=child.parent)

    del choices[0]
    if len(choices) > 0:
        add_to_rule_tree(rule_tree,choices,choice_leaves,pointers,pointer_id)
    return rule_tree, pointers, node_names_parent

def _search_nodes(node, lookup_node):
    ok_nodes = node.search_nodes(dist=lookup_node)
    return ok_nodes

def consequent_not_valid(rule_base, node, lookup_node, conse, pointers):
    #check if only child
    if len(node.get_children()) < 2:
        #print "only child"
        return True
    #check if no dead activity = conse would never appears in rule base tree
    else:
        rb_nodes = _search_nodes(rule_base, lookup_node)
        if len(rb_nodes) < 2:
            return True
        else:
            dead_act = False
            if not conse.is_leaf():
                for descendant in conse.iter_descendants():
                    if len(rule_base.search_nodes(dist = descendant.dist)) < 2:
                        dead_act = True
                        break
            return dead_act


def no_valid_rule(rule_base, pointers, ante, conse):
    start_node = rule_base
    not_valid = False
    for i in range(len(ante)+1):
        #first look for the node in the rule base tree
        if i == len(ante):
            rb_node = _search_nodes(start_node, pointers[conse])
        else:
            rb_node = _search_nodes(start_node, pointers[ante[i]])
        #if there is no node, it is unreachable and the pair is not valid!
        if len(rb_node) < 1:
            not_valid = True
            break
        #if reachable
        else:
            #and if consequent
            if i == len(ante):
                #check if consequent is valid
                not_valid = consequent_not_valid(rule_base,start_node,
                                             pointers[conse],rb_node[0],pointers)
            else:
                start_node = rb_node[0]
    return not_valid

def find_cell_dec_table(node,pair):
    ante = pair[:-1]
    conse = pair[-1]

    row_headers = node.rows
    column_headers = node.columns

    index_row = row_headers.index(ante)
    index_column = column_headers.index(conse)

    return index_row,index_column

def adapt_decision_table(node,pair):
    index_row,index_column = find_cell_dec_table(node,pair)
    dec_table = node.table

    dec_table[index_row][index_column] = 1

def get_candidate_children(candidate_tree, candidate):
    match = candidate_tree.search_nodes(name=candidate)
    if match[0].is_leaf():
        candidate_children = []
    else:
        candidate_children = match[0].get_children()

    return candidate_children

def find_rows_to_prune(node,pair):
    ante = pair
    row_headers = node.rows
    row_indices = []
    for header in row_headers:
        if set(ante).issubset(set(header)):
            row_index = row_headers.index(header)
            row_indices.append(row_index)

    return row_indices

def prune_dec_table(node,pair):
    row_headers = node.rows
    dec_table = node.table
    row_indices = find_rows_to_prune(node,pair)
    removed_rows = []
    for i in row_indices:
        removed_rows.append(row_headers[i])
        del row_headers[i]
        del dec_table[i]

    node.rows = row_headers
    node.table = dec_table
    return removed_rows


def prune_tree(seq_dict,sequence,pair):
    rule_base = seq_dict[sequence][0]
    pointers = seq_dict[sequence][1]
    ante = pair[:-1]
    conse = pair[-1]

    start_node = rule_base
    for i in range(len(ante)+1):
        #first look for the node in the rule base tree
        if i == len(ante):
            rb_node = _search_nodes(start_node, pointers[conse])
        else:
            rb_node = _search_nodes(start_node, pointers[ante[i]])
            start_node = rb_node[0]

    rb_node[0].detach()


def same_children(node, sister, check):
    children_node = []
    children_sister = []

    if check == None:
        check = True

    for child_n in node.get_children():
        children_node.append(child_n.name)

    for child_s in sister.get_children():
        children_sister.append(child_s.name)

    if set(children_node) != set(children_sister):
        check = False
        return check
    else:
        for child_n in node.get_children():
            for child_s in sister.get_children():
                if child_n.is_leaf():
                    continue
                else:
                    check = same_children(child_n,child_s,check)



def find_cuts(rule_base):
    splits = []
    grouped = []

    for node in rule_base.traverse(strategy="levelorder"):
        if node.is_leaf():
            break

        else:
            sisters = node.get_sisters()
            if len(sisters) < 1:
                continue
            else:
                for sister in sisters:
                    if same_children(node, sister,True):
                        if (sister,node) not in grouped:
                            grouped.append((node,sister))
                    else:
                        if (sister,node) not in splits:
                            splits.append((node,sister))

    return grouped,splits

def cluster_splits(grouped,splits):
    clusters = []
    to_delete = []
    remaining_clusters = []

    if len(grouped) > 1:
        for i in range(len(grouped)):
            for j in range(i+1,len(grouped)):
                a = set(grouped[i])
                b = set(grouped[j])
                if len(a.intersection(b)) > 0:
                    l = list(a.union(b))
                    l.sort()
                    cluster = tuple(l)
                    if cluster not in clusters:
                        clusters.append(cluster)

                    if grouped[i] not in to_delete:
                        to_delete.append(grouped[i])
                    if grouped[j] not in to_delete:
                        to_delete.append(grouped[j])

        for el in to_delete:
            grouped.remove(el)

        clusters.extend(grouped)


        new_splits = []

        for split in splits:
            set_split = set(split)
            for cluster in clusters:
                set_cluster = set(cluster)
                intersect = set_split.intersection(set_cluster)
                if len(intersect) > 0:
                    if split in new_splits:
                        new_splits.remove(split)
                    new_split = list(set_split.difference(intersect))
                    cluster = tuple(list(set_cluster))
                    new_split = tuple(new_split) + (cluster,)
                    if tuple(new_split) not in new_splits:
                        new_splits.append(tuple(new_split))

                else:
                    if split not in new_splits:
                        new_splits.append(split)

    elif len(grouped) == 1:
        clusters.extend(grouped)


        new_splits = []

        for split in splits:
            set_split = set(split)
            for cluster in clusters:
                set_cluster = set(cluster)
                intersect = set_split.intersection(set_cluster)
                if len(intersect) > 0:
                    if split in new_splits:
                        new_splits.remove(split)
                    new_split = list(set_split.difference(intersect))
                    cluster = tuple(list(set_cluster))
                    new_split = tuple(new_split) + (cluster,)
                    if tuple(new_split) not in new_splits:
                        new_splits.append(tuple(new_split))

                else:
                    remaining_clusters.append(cluster)
                    if split not in new_splits:
                        new_splits.append(split)

    else:
        new_splits = []
        new_splits = splits

    return new_splits,remaining_clusters


def prune_duplicate(duplicate, rb_node, branch, pointers, node_names_parent):
    sisters_rb = rb_node.get_sisters()
    sisters_rb_names = []
    for s_rb in sisters_rb:
        #use distance instead of node names in case there are duplicate labels
        if len(branch.search_nodes(dist=s_rb.dist)) > 0:
            sisters_rb_names.append(s_rb.name)
    """dangerous solution!!!!
        first with only part within try
        now possibly problems in case of duplicate act!
    """
    try:
        matches = duplicate.search_nodes(parent=rb_node.parent)
        match = matches[0]
    except:
        for node_name, parent_id in node_names_parent.iteritems():
            if parent_id == rb_node.parent:
                matches = duplicate.search_nodes(name=node_name)
                match = matches[0]
    dupl_node = match

    sisters_dupl = dupl_node.get_sisters()
    for sister_d in sisters_dupl:
        #if the sister is not a leaf, get the first child instead!
        if not sister_d.is_leaf():
            sister_d_leaf = _get_leaf(sister_d)
            if sister_d_leaf.name not in sisters_rb_names:
                sister_d.detach()
        # else apply normal rule
        if sister_d.is_leaf():
            if sister_d.name not in sisters_rb_names:
                sister_d.detach()

def _get_clusters(splits):
    clusters = []
    for split in splits:
        for el in split:
            if isinstance(el,tuple):
                clusters.append(el)
                break
    return clusters

def remove_not_in_cluster(not_in_cluster, duplicate):
    match = duplicate.search_nodes(parent=not_in_cluster.parent)
    match[0].detach()


def unfold_sequence(sequence,rule_base,new_splits,pointers,clusters, node_names_parent):
    previous_duplicates = []
    parent_duplicates = {}
    cluster_duplicates = {}
    duplicate = None
    previous_node = sequence.get_tree_root()
    clusters.extend(_get_clusters(new_splits))
    part_of_split = False
    part_of_cluster = False

    for node in rule_base.iter_descendants(strategy="preorder"):

        in_split = False
        in_cluster = False
        #check if node in a split
        for new_split in new_splits:
            if node in new_split:
                in_split = True
                #split = new_split
                break

        for cluster in clusters:
            if node in cluster:
                in_cluster = True
                nodes_not_in_cluster = []
                for new_split in new_splits:
                    if cluster in new_split:
                        i = 1 - new_split.index(cluster)
                        nodes_not_in_cluster.append(new_split[i])
                #cluster_n = cluster
                break

        if in_split and not in_cluster:
            part_of_split = True
            if duplicate != None and previous_node.is_leaf() and not part_of_cluster:
                previous_duplicates.append(duplicate)

            part_of_cluster = False
            parent = node.get_ancestors()[0]
            if parent in parent_duplicates.keys():
                duplicate = parent_duplicates[parent].copy()
            else:
                duplicate = sequence.copy()
            parent_duplicates[node] = duplicate
            branch = node
            prune_duplicate(duplicate,node,branch,pointers, node_names_parent)
            previous_node = node

        elif in_cluster:
            part_of_cluster = True
            if duplicate != None and previous_node.is_leaf() and part_of_split:
                previous_duplicates.append(duplicate)
                part_of_split = False
            else:
                pass

            if cluster not in cluster_duplicates.keys():
                parent = node.get_ancestors()[0]
                if parent in parent_duplicates.keys():
                    duplicate = parent_duplicates[parent].copy()
                else:
                    duplicate = sequence.copy()
                cluster_duplicates[cluster] = duplicate
                parent_duplicates[node] = duplicate
                previous_duplicates.append(duplicate)
                #remove node not in cluster
                for node_not_in_cluster in nodes_not_in_cluster:
                    remove_not_in_cluster(node_not_in_cluster,duplicate)
                branch = node
                previous_node = node
            else:
                duplicate = cluster_duplicates[cluster]
                branch = node
                previous_node = node
                continue


        else:
            prune_duplicate(duplicate,node,branch,pointers, node_names_parent)
            previous_node = node

    if not part_of_cluster:
        previous_duplicates.append(duplicate)

    for child in sequence.get_children():
        child.detach()
    sequence.name = "choice"

    for duplicate in previous_duplicates:
        sequence.add_child(duplicate)



def simplify_sequence(sequence):
    for node in sequence.iter_search_nodes(name="choice"):
        children = node.get_children()
        if len(children) < 2:
            node.name = children[0].name
            if children[0].name == "sequence":
                node.node_id = children[0].node_id
            children[0].delete(prevent_nondicotomic=False)


def create_all_rules(seq_candidates,choice_leaves):
    rules_list = []
    rules_dictionary = {}
    for sequence,candidates in seq_candidates.iteritems():
        for candidate in candidates:
            #get choices antecedent and consequent
            ante_choices = candidate[:-1]
            conse_choice = candidate[-1]
            headers = []
            antecedents = []
            for choice in ante_choices:
                headers.append(choice_leaves[choice])

            #makes cartesian product of all choice leaves in the antecedent
            for pair in itertools.product(*headers):
                antecedents.append(pair)

            #create a rule for each combination of antecedent and leaf in
            #the consequent choice
            for antecedent in antecedents:
                for leaf in choice_leaves[conse_choice]:
                    rule = antecedent + (leaf,)
                    #add rule to list of rules
                    rules_list.append(rule)
                    #link rule to candidate and sequence for pruning later on
                    rules_dictionary[rule] = [candidate,sequence]

    return rules_list,rules_dictionary

def prune_dependent_rules(removed_rows, rules_list):
    #only removes rules that have subset of current rule in their antecedent
    rules_to_remove = []
    for row in removed_rows:
        for rule in rules_list:
            if set(row).issubset(set(rule)):
                rules_to_remove.append(rule)

    return rules_to_remove


def prune_rules_list(rule, rules_list, rules_dictionary, candidate_tree):
    eliminated_rules = [rule]
    candidate = rules_dictionary[rule][0]

    #adapt decision table rule
    candidate_node = candidate_tree.search_nodes(name=candidate)[0]
    adapt_decision_table(candidate_node,rule)

    #adapt decision tables dependent rules and prunt them
    children_candidate = get_candidate_children(candidate_tree,candidate)
    for child_c in children_candidate:
        removed_rows = prune_dec_table(child_c,rule)
        eliminated_rules.extend(prune_dependent_rules(removed_rows, rules_list))

    return eliminated_rules

def printable_rule(rule):
    output = ""
    for el in rule:
        if el == rule[-1]:
            output += " -> (not)" + el.name
        else:
            output += el.name

    return output


class Lt_dependency():
    def __init__(self,random_tree,rule_probability):
        self.t = random_tree
        self.possible = True
        self.rule_probability = rule_probability

        #STEP 0: search choices in the tree
        choices = search_choices(self.t)
        #get the first leaf of each path in choice and add to dictionary
        choice_leaves = {}
        for choice in choices:
            if choice not in choice_leaves:
                choice_leaves[choice] = choice_leaves.setdefault(choice,[])
                choice_leaves[choice].extend(get_first_leaves(choice))

        #STEP 1: create candidates
        seq_choices, seq_candidates, seq_candidate_tree = search_candidates(self.t,choices,choice_leaves)
        if len(seq_candidates) < 1 :
            #print "NO LT-DEPENDENCIES POSSIBLE --> STOP!"
            self.possible = False
        else:
            #STEP 2:
            #create a rule base tree for every sequence
            seq_dict = {}
            for seq,choices in seq_choices.items():
                rule_tree = TreeNode("root;",format=1)
                pointers = dict()
                pointer_id = 1
                rule_tree, pointers, node_names_parent = add_to_rule_tree(rule_tree, choices, choice_leaves, pointers, pointer_id)
                seq_dict[seq] = (rule_tree, pointers, seq_candidate_tree[seq],[], node_names_parent)

            #STEP 3:
            #create a set containing all possible rules and a dictionary linking each rule
            #as a key to the candidate and sequence
            for sequence in seq_dict:
                #print sequence
                rules_list, rules_dictionary = create_all_rules(seq_candidates,choice_leaves)
                #print rules_list

            #STEP 4:
            #iterate over rules: if random number is lower than the treshold, apply the rule
            #if a rule is applied, we need to eliminate dependend and other rules that would
            #introduce deadlocks or dead activities
            eliminated_rules = []

            #first shuffle the list of rules
            random.shuffle(rules_list)

            #go through the list of rules
            for rule in rules_list:
                ##print "rule:", [x.name for x in rule]
                sequence = rules_dictionary[rule][1]
                #do not consider eliminated rules
                if rule in eliminated_rules:
                    ##print "already eliminated"
                    continue
                #do not consider non-valid rules (should be eliminated too)
                elif no_valid_rule(seq_dict[sequence][0], seq_dict[sequence][1], rule[:-1], rule[-1]):
                    ##print "not a valid rule"
                    eliminated_rules.append(rule)
                    continue
                else:
                    x = random.random()
                    if x < self.rule_probability:
                        print(printable_rule(rule))
                        ##print "INSERTED RULE!"
                        seq_dict[sequence][3].append(rule)
                        candidate_tree = seq_dict[sequence][2]
                        #search for dependent rules to add to eliminated list
                        eliminated_rules.extend(prune_rules_list(rule, rules_list,
                                                                 rules_dictionary, candidate_tree))
                        #prune the rule base tree (needed for identifying non valid rules)
                        prune_tree(seq_dict,sequence,rule)
                    else:
                        pass
                        ##print "not inserted probability"

            ##print "\neliminated_rules:", eliminated_rules

            #STEP 5:
            #find splits in the rule base:
            #each split will determine which part of the process tree will be duplicated

            for sequence in seq_dict:
                rule_base = seq_dict[sequence][0]
                pointers = seq_dict[sequence][1]
                grouped, splits = find_cuts(rule_base)
                new_splits,remaining_clusters = cluster_splits(grouped, splits)
                seq_dict[sequence] = seq_dict[sequence] + (new_splits,remaining_clusters,)

            #STEP 6:
            #prep the tree:
                sequence_id_dict = {}
            for node in self.t.traverse(strategy="preorder"):
                new_id = str(uuid.uuid4())
                node.add_features(node_id = new_id)
                if node in seq_dict.keys():
                    sequence_id_dict[new_id] = node

            #duplicating parts of the process tree
            for node in self.t.traverse(strategy="preorder"):
                if node.name == "sequence" and node.node_id in sequence_id_dict.keys():
                    old_node = sequence_id_dict[node.node_id]
                    rule_base = seq_dict[old_node][0]
                    pointers = seq_dict[old_node][1]
                    splits = seq_dict[old_node][5]
                    remaining_clusters = seq_dict[old_node][6]
                    rules = seq_dict[old_node][3]
                    node_names_parent = seq_dict[old_node][4]

                    del sequence_id_dict[node.node_id]

                    if len(rules) > 0:
                        unfold_sequence(node, rule_base, splits, pointers, remaining_clusters, node_names_parent)
                        simplify_sequence(node)
                    else:
                        pass
