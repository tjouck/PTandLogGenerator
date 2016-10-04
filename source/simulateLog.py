# -*- coding: utf-8 -*-
"""
Created on Tue Mar 08 20:55:25 2016

@author: lucp8356

Simulates a log given a newick tree

INPUT:
    newick tree string
    number of cases to simulate

OUTPUT:
    log as a list of traces
"""

import sys
sys.path.insert(0, '../newick')
sys.path.insert(0, '../simpy')
from tree import TreeNode
import random
import datetime
from core import Environment
from events import AllOf, AnyOf, NOf, Zombie


class Case():
    def __init__(self):
        self.trace = []

class Log():
    def __init__(self):
        self.traces = []

    def add_trace(self, trace):
        self.traces.append(trace)

class LogSimulator():

    def __init__(self,newick_tree,no_cases,record_timestamps):
        self.t = TreeNode(newick_tree, format = 1)
        self.record_timestamps = record_timestamps
        self.log = Log()
        self.env = Environment()
        self.start_date = datetime.datetime.today()
        self.create_bpsim()

        for i in range(no_cases):
            self.eid = 1
            self.case = Case()

            #creates one instance or case of the tree
            self.create_case()
            #run the instance
            self.run()
            self.log.add_trace(self.returnTrace())


    def create_bpsim(self):

        self.bpsim_sequence = []
        self.join_endpoints = dict()

        #make a dictionary to save all needed activity generators
        self.act_generators = dict()
        leaves = self.t.get_leaves()
        for leaf in leaves:
            self.act_generators[leaf] = self.act_generator(leaf.name)

        #save the required number of arcs
        #by default 1 for the startevent and 1 for each act
        self.arcs = 1 + len(self.act_generators)

        ####################################################################################
        #traverse tree and deduce the sequence of the process tree operators and activities#
        ####################################################################################
        for node in self.t.traverse(strategy="preorder"):
            if node.is_leaf():
                startevent = self.determine_startevent(node)
                endevent = self.determine_endevent(node)
                #print "act: %s, gen: %s, end: %s" % (node.name, act_generators[node],
                                                                #endevent)

                self.bpsim_sequence.append((node, "" , "", startevent, endevent))
                for ancestor in node.get_ancestors():
                    if node in ancestor.endpoints:
                        ancestor.to_reach_endpoints -= 1
                        if ancestor.to_reach_endpoints == 0 and ancestor.name not in ["sequence", "loop"]:
                            self.arcs += 1
                            #print ancestor.name + "_join_generator", ancestor.endpoints
                            self.bpsim_sequence.append((ancestor, "join", "", ancestor.endpoints))
                        elif ancestor.to_reach_endpoints == 0 and ancestor.name == "loop":
                            endevents = []
                            children = ancestor.get_children()
                            endevents.append(self.determine_start_middle(children[1]))
                            endevents.append(self.determine_start_middle(children[2]))
                            start = self.loop_end_left(children[0])
                            #print ancestor.name, "xor-split", start, endevents
                            self.bpsim_sequence.append((ancestor,"split","",start, endevents))
            else:
                endpoints = []
                real_endpoints = []
                children = node.get_children()
                for child in children:
                    self.determine_endpoints(node, child, endpoints)
                    if node.name != "sequence":
                        self.arcs += 1
                if not node.is_root():
                    startevent = self.determine_startevent(node)
                else:
                    startevent = None
                node.add_feature("endpoints", endpoints)
                node.add_feature("to_reach_endpoints", len(endpoints))
                if node.name not in ["sequence", "loop"]:
                    for child in children:
                        self.return_real_endpoints(child, real_endpoints)
                    self.join_endpoints[node] = real_endpoints
                    #print node.name + "_split_generator", [endpoint.name for endpoint in endpoints]
                    self.bpsim_sequence.append((node, "split", children, startevent))
                elif node.name == "loop":
                    endpoints_middle = []
                    if children[1].is_leaf():
                        endpoints_middle.append(children[1])
                    else:
                        if children[1].name in ["sequence", "loop"]:
                            endpoints_middle.append(self.endpoint_loop_in_sequence(children[1]))
                        else:
                            endpoints_middle.append(children[1])
                        self.join_endpoints[node] = endpoints_middle
                    #print node.name, "xor-join", [startevent, endpoints_middle], children[0]
                    self.bpsim_sequence.append((node,"join", [startevent, endpoints_middle], children[0]))


    def create_case(self):

        ##############################################################
        #translate bpsim sequence to bpsim simulation building blocks#
        ##############################################################

        e = []
        joins = dict()
        or_dict = dict()
        loops_joins= dict()
        loops_splits = dict()
        for i in range(self.arcs):
            e.append(Zombie(self.env))
        out_arc = 1
        self.node_outgoing_arcs = dict()


        for element in self.bpsim_sequence:
            outgoing_arcs = []
            incoming_arcs = []

            #determining incoming events
            if element[0].name == "loop" and element[1] == "join":
                if element != self.bpsim_sequence[0]:
                    try:
                        if element[2][0][1] == "xor-split":
                            in_arc = out_arc
                            out_arc = out_arc + 1
                            loops_splits[element[0]] = in_arc
                        else:
                            startevent = element[2][0][0]
                            in_arc, self.node_outgoing_arcs = self.return_incoming_arc(startevent, self.node_outgoing_arcs)
                    except:
                        startevent = element[2][0]
                        in_arc, self.node_outgoing_arcs = self.return_incoming_arc(startevent, self.node_outgoing_arcs)
                    incoming_arcs.append(in_arc)

                    incoming_arcs.append(out_arc)
                    loops_joins[element[0]] = out_arc
                else:
                    incoming_arcs.append(0)

                    incoming_arcs.append(out_arc)
                    loops_joins[element[0]] = out_arc
                out_arc += 1
            elif element != self.bpsim_sequence[0] and element[1] != "join":
                try:
                    if element[3][1] == "xor-join":
                        startevent = element[3][0]
                        in_arc, self.node_outgoing_arcs = self.return_incoming_arc(startevent, self.node_outgoing_arcs)
                    elif element[3][1] == "xor-split":
                        in_arc = out_arc
                        loops_splits[element[0]] = in_arc
                        #in case xor-split outgoing arc heads towards an operator
                        if not element[0].is_leaf():
                            out_arc += 1
                except:
                    startevent = element[3]
                    in_arc, self.node_outgoing_arcs = self.return_incoming_arc(startevent, self.node_outgoing_arcs)
            elif element != self.bpsim_sequence[0] and element[1] == "join":
                startevents = self.join_endpoints[element[0]]
                for startevent in startevents:
                    if startevent.is_leaf():
                        incoming_arcs.append(self.node_outgoing_arcs[startevent][0])
                    else:
                        incoming_arcs.append(joins[startevent])
            else:
                in_arc = 0


            #determining outgoing events
            if element[1] == "split":
                if element[0].name == "loop":
                    for in_event in element[4]:
                        try:
                            in_event = in_event[0]
                        except:
                            pass
                        outgoing_arcs.append(loops_splits[in_event])
                    self.node_outgoing_arcs[element[0]] = outgoing_arcs
                    split, routing = self.produce_split_generator(element[0], self.env, self.eid, outgoing_arcs, e, or_dict)
                    self.env.process(split(e[in_arc], self.eid, routing))
                else:
                    for i in range(len(element[2])):
                        outgoing_arcs.append(out_arc + i)
                    self.node_outgoing_arcs[element[0]] = outgoing_arcs
                    split, routing = self.produce_split_generator(element[0], self.env, self.eid, outgoing_arcs, e, or_dict)
                    self.env.process(split(e[in_arc], self.eid, routing))
                    out_arc = out_arc + i + 1

            elif element[1] == "join":
                new_out_arc = out_arc
                for key, value in self.join_endpoints.items():
                    if key.name == "loop" and value[0] == element[0]:
                        new_out_arc = loops_joins[key]
                        out_arc = out_arc - 1
                        break
                joins[element[0]] = new_out_arc
                self.node_outgoing_arcs[element[0]] = [new_out_arc]
                join = self.produce_join_generator(element[0])
                incoming_events = []
                for i in incoming_arcs:
                    incoming_events.append(e[i])

                if element[0].name == "or":
                    self.env.process(join(incoming_events, e[new_out_arc], or_dict, element[0], self.eid))
                else:
                    self.env.process(join(incoming_events, e[new_out_arc], self.eid))
                out_arc = out_arc + 1
            else:
                try:
                    #special case when outgoing event is loop xor-join (b)
                    if element[4][1] == "xor-join":
                        out2_arc = loops_joins[element[4][0]]
                        act_gen = self.act_generators[element[0]]
                        self.node_outgoing_arcs[element[0]] = [out2_arc]
                        self.env.process(act_gen(self.env, e[in_arc], e[out2_arc], self.dur_a(), self.eid, self.case))
                        if out_arc > in_arc:
                            out_arc -= 1

                    #case when outgoing event is loop xor-split (a)
                    else:
                        #activity between two loop xor-splits
                        if in_arc == out_arc:
                            out_arc += 1
                        act_gen = self.act_generators[element[0]]
                        self.node_outgoing_arcs[element[0]] = [out_arc]
                        self.env.process(act_gen(self.env, e[in_arc], e[out_arc], self.dur_a(), self.eid, self.case))
                except:
                    #incoming event is loop xor-split
                    if in_arc == out_arc:
                        out_arc += 1
                    act_gen = self.act_generators[element[0]]
                    self.node_outgoing_arcs[element[0]] = [out_arc]
                    self.env.process(act_gen(self.env, e[in_arc], e[out_arc], self.dur_a(), self.eid, self.case))
                out_arc = out_arc + 1

        e[0].succeed()


    def act_generator(self,act_name, res_name=""):
        def act(env, start, end, fdur, eid, case, res=None):
            #print("%d: initialize activity '%s'" % (eid, act_name))
            while True:
                yield start

                if res is not None:
                    req = res.request()
                    print("%d: request resource '%s' @%s" % (eid, res_name, env.now))
                    yield req
                start_time = self.add_sec(self.start_date,env.now)
                #print("%d: start activity '%s' @%s" % (eid, act_name, env.now))
                yield env.timeout(fdur())
                end_time = self.add_sec(self.start_date,env.now)
                #print("%d: end activity '%s' @%s" % (eid, act_name, env.now))
                if act_name != "tau":
                    if self.record_timestamps:
                        case.trace.append((act_name, start_time.isoformat(), end_time.isoformat()))
                    else:
                        case.trace.append(act_name)
                    #+ "," + str(start_time) + "," + str(end_time) + "\n")
                if res is not None:
                    res.release(req)

                end.succeed()
                start.reset()

        return act

    #determine startevent of activity
    def determine_startevent(self,node):
        ancestors = node.get_ancestors()
        if ancestors[0].name in ["choice", "parallel", "or"]:
            return ancestors[0]
        elif ancestors[0].name == "sequence":
            children = ancestors[0].get_children()
            index = children.index(node)
            if index == 0:
                if ancestors[0].is_root():
                    return None
                else:
                    return self.determine_startevent(ancestors[0])
            else:
                if children[index-1].name == "loop":
                    return self.endpoint_loop_in_sequence(children[index-1])
                elif children[index-1].name == "sequence":
                    return self.endpoint_loop_in_sequence(children[index-1])
                else:
                    return children[index-1]
        else:
            children = ancestors[0].get_children()
            index = children.index(node)
            if index == 0:
                return [ancestors[0],"xor-join"]
            else:
                return [ancestors[0],"xor-split"]

    def determine_endevent(self,node):
        ancestors = node.get_ancestors()
        if ancestors[0].name in ["choice", "parallel", "or"]:
            return ancestors[0]
        elif ancestors[0].name == "sequence":
            children = ancestors[0].get_children()
            index = children.index(node)
            if index == (len(children) - 1):
                if ancestors[0].is_root():
                    return None
                else:
                    return self.determine_endevent(ancestors[0])
            else:
                return children[index+1]
        else:
            children = ancestors[0].get_children()
            index = children.index(node)
            if index == 0:
                return [ancestors[0],"xor-split"]
            elif index == 1:
                return [ancestors[0],"xor-join"]
            else:
                if ancestors[0].is_root():
                    return None
                else:
                    return self.determine_endevent(ancestors[0])

    #startevent middle child in loop
    def determine_start_middle(self, node):
        if node.name == "loop":
            return [node,"xor-join"]
        elif node.name == "sequence":
            children = node.get_children()
            return self.determine_start_middle(children[0])
        else:
            return node

    #function to determine endpoint left child in loop
    def loop_end_left(self, node):
        if node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            return self.loop_end_left(last_child)
        else:
            return node

    #recursive function to determine endpoints
    def determine_endpoints(self, node, child, endpoints):
        if node.name in ["choice", "parallel", "or"]:
            if child.is_leaf():
                endpoints.append(child)

            else:
                for grandchild in child.get_children():
                    self.determine_endpoints(child, grandchild, endpoints)

        elif node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            if child == last_child:
                if last_child.is_leaf():
                    endpoints.append(last_child)

                else:
                    for grandchild in last_child.get_children():
                        self.determine_endpoints(last_child, grandchild, endpoints)
            else:
                pass
        return endpoints

    #determine real endpoints node
    def return_real_endpoints(self, node, real_endpoints):

        if node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            self.return_real_endpoints(last_child,real_endpoints)
        else:
            real_endpoints.append(node)
        return real_endpoints

    #special function to determine endpoint of loop for loops in first part of a sequence
    def endpoint_loop_in_sequence(self, node):
        last_child = node.get_children()[-1]
        if last_child.name in ["sequence", "loop"]:
            return self.endpoint_loop_in_sequence(last_child)
        else:
            return last_child

    #determine right incoming arc
    def return_incoming_arc(self, startevent, node_outgoing_arcs):

        if len(node_outgoing_arcs[startevent]) > 1:
            incoming_arc = node_outgoing_arcs[startevent][0]
            del node_outgoing_arcs[startevent][0]
            return incoming_arc, node_outgoing_arcs
        else:
            incoming_arc = node_outgoing_arcs[startevent][0]
            return incoming_arc, node_outgoing_arcs


    #produce the correct generator function for each split
    def produce_split_generator(self, node, env, eid, outgoing_indices, e, or_dict):
        outgoing_arcs = []
        for i in outgoing_indices:
                outgoing_arcs.append(e[i])
        if node.name == "parallel":
            and_split = self.and_split_generator('and')
            path_probabilities = []
            for child in node.get_children(): path_probabilities.append(child.dist)
            and_routing = self.and_routing_generator(env, outgoing_arcs, path_probabilities)
            return and_split, and_routing

        elif node.name in ["choice", "loop"]:
            xor_split = self.xor_split_generator("xor")
            if node.name == "choice":
                path_probabilities = []
                for child in node.get_children(): path_probabilities.append(child.dist)
                xor_routing = self.xor_routing_generator(env, outgoing_arcs, path_probabilities)
            else:
                xor_routing = self.xor_routing_generator2(env, outgoing_arcs)
            return xor_split, xor_routing

        else:
            or_split = self.or_split_generator("or")
            path_probabilities = []
            for child in node.get_children(): path_probabilities.append(child.dist)
            or_routing = self.or_routing_generator(env, outgoing_arcs, or_dict, node, path_probabilities)
            return or_split, or_routing


    def and_split_generator(self, and_name):
        def and_split(start, eid, routing_func):
            #print("%d: initialize and_split '%s'" % (eid, and_name))
            while True:
                yield start
                #print("%d: and routing at '%s'" % (eid, and_name))
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return and_split

    def and_routing_generator(self, env, events, path_probabilities):
        def and_routing():

            n = len(events)
            chosen_events = []
            random_event = random.choice(events)
            for i in range (n):
                while random_event in chosen_events:
                    random_event = random.choice(events)
                random_event.succeed()
                chosen_events.append(random_event)
        return and_routing


    def and_join_generator(self, and_name):
        def and_join(start_events, end, eid):
            #print("%d: initialize and_join '%s'" % (eid, and_name))
            while True:
                join = AllOf(self.env, start_events)
                yield join
                #print("%d: and join activated at '%s'" % (eid, and_name))
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return and_join

    def xor_split_generator(self, xor_name):
        def xor_split(start, eid, routing_func):
            #print("%d: initialize xor_split '%s'" % (eid, xor_name))
            while True:
                yield start
                #print("%d: xor routing at '%s'" % (eid, xor_name))
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return xor_split

    def xor_join_generator(self, xor_name):
        def xor_join(start_events, end, eid):
            #print("%d: initialize xor_join '%s'" % (eid, xor_name))
            while True:
                join = AnyOf(self.env, start_events)
                yield join
                #print("%d: xor join activated at '%s'" % (eid, xor_name))
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return xor_join

    def xor_routing_generator(self, env, events, path_probabilities):
        def xor_routing():
            x = random.random()
            cutoffs = []
            previous_cutoff = 0

            for i in range(len(path_probabilities) - 1):
                cutoffs.append(previous_cutoff + path_probabilities[i])
                previous_cutoff = previous_cutoff + path_probabilities[i]
            #print "cutoffs" , cutoffs

            j = len(cutoffs)
            for i in range(len(cutoffs)):
                if x < cutoffs[i]:
                    j = i
                    break
            random_event = events[j]
            random_event.succeed()
        return xor_routing

    #old routing generator, now used only for loops
    def xor_routing_generator2(self, env, events):
        def xor_routing():
            random_event = random.choice(events)
            random_event.succeed()
        return xor_routing

    def or_split_generator(self, or_name):
        def or_split(start, eid, routing_func):
            #print("%d: initialize or_split '%s'" % (eid, or_name))
            while True:
                yield start
                #print("%d: or routing at '%s'" % (eid, or_name))
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return or_split

    def or_join_generator(self, or_name):
        def or_join(start_events, end, or_dict, or_, eid):
            #print("%d: initialize or_join '%s'" % (eid, or_name))
            while True:
                join = NOf(self.env, start_events, or_dict, or_)
                yield join
                #print("%d: or join activated at '%s'" % (eid, or_name))
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return or_join

    def or_routing_generator(self, env, events, or_dict, or_, path_probabilities):
        def or_routing():
            x = int(round(random.uniform(1,len(events))))
            n=0
            chosen_events = []
            random_event = random.choice(events)
            for i in range (x):
                while random_event in chosen_events:
                    random_event = random.choice(events)
                random_event.succeed()
                chosen_events.append(random_event)
                n += 1
            or_dict[or_] = n
        return or_routing

    #produce the correct generator function for each join
    def produce_join_generator(self, node):
        if node.name == "parallel":
            and_join = self.and_join_generator("and")
            return and_join

        elif node.name in ["choice", "loop"]:
            xor_join = self.xor_join_generator("xor")
            return xor_join

        else:
            or_join = self.or_join_generator("or")
            return or_join

    def dur_a(self):
        def fdur():
            return random.randint(1,10000)
        return fdur
        
    def add_sec(self,time,secs):
        time = time + datetime.timedelta(seconds=secs)
        return time

    def run(self):
        global env
        env = self.env
        env.run()

    def returnTrace(self):
        return self.case.trace

    def returnLog(self):
        return self.log.traces
