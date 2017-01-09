# -*- coding: utf-8 -*-
"""
Created on Thu Nov 26 15:09:41 2015

Dependencies: graphviz!

@author: lucp8356
"""

import graphviz
import sys
sys.path.insert(0, '../newick')
from tree import TreeNode
import uuid

class GraphvizTree():
    def __init__(self,tree_string, pop_index, tree_index):
        t = TreeNode(tree_string,format = 1)
        #print t.get_ascii(show_internal=True, compact=False)

        dot = graphviz.Graph(format="png")
        dot.graph_attr.update({'fontname':'sans-serif','ranksep':'0.5','nodesep':'0.1'})
        dot.node_attr.update({'fontname':'sans-serif','fontsize':'20','fixedsize':'True'})
        dot.edge_attr.update({'fontname':'sans-serif'})
        branches = []

        for node in t.traverse("preorder"):
                new_id = str(uuid.uuid4())
                if node.is_root():
                    id_tree = str(uuid.uuid4())
                    node.add_feature("id",new_id)
                    operator_type = node.name
                    if operator_type == "sequence":
                        operator_type = "&#8594;"
                    elif operator_type == "loop":
                        operator_type = "&#x21BA;"
                    elif operator_type == "choice":
                        operator_type = "x"
                    elif operator_type == "parallel":
                        operator_type = "&#8743;"
                    elif operator_type == "or":
                        operator_type = "&#8744;"

                    dot.node(new_id,label=operator_type,shape="circle")


                elif node.is_leaf():
                    if node.name =="tau":
                        dot.node(new_id,label="&#964;",shape="none")
                    else:
                        dot.node(new_id,label=node.name,shape="none")
                    parent = node.get_ancestors()[0]
                    branches.append((parent.id,new_id,node.dist))

                else:
                    parent = node.get_ancestors()[0]
                    branches.append((parent.id,new_id,node.dist))
                    node.add_feature("id",new_id)
                    operator_type = node.name
                    if operator_type == "sequence":
                        operator_type = "&#8594;"
                    elif operator_type == "loop":
                        operator_type = "&#x21BA;"
                    elif operator_type == "choice":
                        operator_type = "x"
                    elif operator_type == "parallel":
                        operator_type = "&#8743;"
                    elif operator_type == "or":
                        operator_type = "&#8744;"

                    dot.node(new_id,label=operator_type,shape="circle")

        for branch in branches:
            if branch[2] != 1.0:
                dot.edge(branch[0],branch[1],label=str(branch[2]))
            else:
                dot.edge(branch[0],branch[1])

        dot.render(filename="../data/trees/tree_" + str(pop_index) + "_" + str(tree_index) , view=False)
