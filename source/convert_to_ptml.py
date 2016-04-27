# -*- coding: utf-8 -*-
"""
Created on Tue Apr 07 16:25:36 2015

@author: lucp8356
"""
import uuid
import sys
sys.path.insert(0, '../newick')
from tree import TreeNode

#create a ptml file from process tree in newick format

class PtmlConverter():
    def __init__(self,tree_name, tree_string):
        ptml_file = open(tree_name + ".ptml", 'w')

        #start the new ptml file with the correct tags
        ptml_file.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        ptml_file.write('<ptml>\n')

        #read tree in newick format
        t = TreeNode(tree_string,format=1)

        #initialize the branches array
        branches = []

        #traverse tree. If node = root then start building the tree
        #by initializing with the process tree tag. If node = leaf,
        #then distinguish between invisble and visible tasks. If the
        #node is an operator, then replace with correct operator tags
        #in ptml. Each time a node is visited, the branch with its
        #parent is saved in an array (added later on to the ptml file).

        for node in t.traverse("preorder"):
            new_id = str(uuid.uuid4())
            if node.is_root():
                id_tree = str(uuid.uuid4())
                node.add_feature("id",new_id)
                ptml_file.write('<processTree id="' + id_tree + '" name="tree1" root="' + new_id + '">\n')
                operator_type = node.name
                if operator_type == "loop":
                    operator_type = "xorLoop"
                elif operator_type == "choice":
                    operator_type = "xor"
                elif operator_type == "parallel":
                    operator_type = "and"
                elif operator_type == "or":
                    operator_type = "or"
                ptml_file.write('<' + operator_type + ' id="' + new_id + '" name="">\n')
                ptml_file.write('</' + operator_type + '>\n')

            elif node.is_leaf():
                if node.name =="tau":
                    ptml_file.write('<automaticTask id="' + new_id + '" name="' + node.name + '">\n')
                    ptml_file.write('</automaticTask>\n')
                else:
                    ptml_file.write('<manualTask id="' + new_id + '" name="' + node.name + '">\n')
                    ptml_file.write('</manualTask>\n')
                parent = node.get_ancestors()[0]
                branches.append((parent.id,new_id))

            else:
                parent = node.get_ancestors()[0]
                branches.append((parent.id,new_id))
                node.add_feature("id",new_id)
                operator_type = node.name
                if operator_type == "loop":
                    operator_type = "xorLoop"
                elif operator_type == "choice":
                    operator_type = "xor"
                elif operator_type == "parallel":
                    operator_type = "and"
                elif operator_type == "or":
                    operator_type = "or"
                ptml_file.write('<' + operator_type + ' id="' + new_id + '" name="">\n')
                ptml_file.write('</' + operator_type + '>\n')

        #write all branches to ptml file

        for branch in branches:
            new_id = str(uuid.uuid4())
            ptml_file.write('<parentsNode id="' + new_id + '" sourceId="' + branch[0] +
            '" targetId="' + branch[1] + '"/>\n')

        #close with correct tags

        ptml_file.write('</processTree>\n')
        ptml_file.write('</ptml>\n')

        ptml_file.close()


"""
for i in range(1,11):
    for j in range(1,11):
        #open a new file the ptml tree is outputted to
        #ptml_file = open("0_tree" + str(i) + ".ptml", 'w')
        ptml_file = open("systemen_gert/systemen_2_1/system_" + str(i) + "_" + str(j) + ".ptml", 'w')
        #start the new ptml file with the correct tags
        ptml_file.write('<?xml version="1.0" encoding="ISO-8859-1"?>\n')
        ptml_file.write('<ptml>\n')

        #read tree in newick format

        t = Tree("systemen_gert/systemen_2_1/system_" + str(i) + "_" + str(j) + ".nw",format=1)
        print t.get_ascii(show_internal=True, compact=False)

        #initialize the branches array
        branches = []

        #traverse tree. If node = root then start building the tree
        #by initializing with the process tree tag. If node = leaf,
        #then distinguish between invisble and visible tasks. If the
        #node is an operator, then replace with correct operator tags
        #in ptml. Each time a node is visited, the branch with its
        #parent is saved in an array (added later on to the ptml file).

        for node in t.traverse("preorder"):
            new_id = str(uuid.uuid4())
            if node.is_root():
                id_tree = str(uuid.uuid4())
                node.add_feature("id",new_id)
                ptml_file.write('<processTree id="' + id_tree + '" name="tree1" root="' + new_id + '">\n')
                operator_type = node.name
                if operator_type == "loop":
                    operator_type = "xorLoop"
                elif operator_type == "choice":
                    operator_type = "xor"
                elif operator_type == "parallel":
                    operator_type = "and"
                elif operator_type == "or":
                    operator_type = "or"
                ptml_file.write('<' + operator_type + ' id="' + new_id + '" name="">\n')
                ptml_file.write('</' + operator_type + '>\n')

            elif node.is_leaf():
                if node.name =="tau":
                    ptml_file.write('<automaticTask id="' + new_id + '" name="' + node.name + '">\n')
                    ptml_file.write('</automaticTask>\n')
                else:
                    ptml_file.write('<manualTask id="' + new_id + '" name="' + node.name + '">\n')
                    ptml_file.write('</manualTask>\n')
                parent = node.get_ancestors()[0]
                branches.append((parent.id,new_id))

            else:
                parent = node.get_ancestors()[0]
                branches.append((parent.id,new_id))
                node.add_feature("id",new_id)
                operator_type = node.name
                if operator_type == "loop":
                    operator_type = "xorLoop"
                elif operator_type == "choice":
                    operator_type = "xor"
                elif operator_type == "parallel":
                    operator_type = "and"
                elif operator_type == "or":
                    operator_type = "or"
                ptml_file.write('<' + operator_type + ' id="' + new_id + '" name="">\n')
                ptml_file.write('</' + operator_type + '>\n')

        #write all branches to ptml file

        for branch in branches:
            new_id = str(uuid.uuid4())
            ptml_file.write('<parentsNode id="' + new_id + '" sourceId="' + branch[0] +
            '" targetId="' + branch[1] + '"/>\n')

        #close with correct tags

        ptml_file.write('</processTree>\n')
        ptml_file.write('</ptml>\n')

        ptml_file.close()
"""
