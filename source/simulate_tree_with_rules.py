# -*- coding: utf-8 -*-
"""
Created on Tue Jul 25 15:04:36 2017

This file contains the class LogSimulator that takes a process tree and a set of decision rules
and returns a set of cases with traces and case attributes.

@author: Toon Jouck
"""
import sys
#sys.path.insert(0, 'datasimpy/')
sys.path.insert(0, '../simpy')
import random
from case_attribute import CaseAttribute
from core import Environment
from events import AllOf, AnyOf, NOf, Zombie

class Case():
    '''
    Attributes:
        -trace: list of activity names in order of occurrence
        -case_attrs: list of case attributes (objects)
    '''

    def __init__(self, case_attrs):
        self.trace = []
        self.case_attrs= case_attrs
        self.no_rules_fired = 0

    def initialize_case_attrs(self):
        for attr in self.case_attrs:
            # print attr.name, attr.type
            if attr.type == 'bool':
                attr.assign_value(bool(random.getrandbits(1)))
            else:
                attr.assign_value(random.random())
                # print attr.value

class Log():
    '''
    Attributes:
        -cases: list of cases in the log
    '''

    def __init__(self):
        self.cases = []

    def add_case(self, case):
        '''method to add a case to the list of cases in the log'''
        self.cases.append(case)

class LogSimulator():
    '''
    Attributes:
        -t: the process tree
        -rules: the dependency rules the simulator should take into account dict: {choice:rules}
        -record_timestamps: whether or not timestamps of the activities will be logged (start+complete)
        -log: contains a list of cases (each case has a trace and optionally some case attributes)
        -env: environment needed for the simpy simulation
    '''

    def __init__(self,newick_tree,choice_first_leaves,rules,case_attrs,record_timestamps):
        '''initialize the simulator by building the bpsim model'''
        self.t = newick_tree
        self.choice_first_leaves = choice_first_leaves
        #prepare rules here or beforehand?
        self.rules = rules
        self.case_attributes = case_attrs
        self.record_timestamps = record_timestamps
        self.log = Log()
        self.env = Environment()
        self._create_bpsim()

    def simulate(self,no_cases):
        '''simulates the given bpsim model with rules and adds the generated cases to the log object'''
        for i in range(no_cases):
            eid = i+1
            case = Case([CaseAttribute(attr.name,type=attr.type) for attr in self.case_attributes])
            case.initialize_case_attrs()
            # simulates one instance or case of the tree
            self._create_case(eid,case)
            self._run()
            self.log.add_case(case)
        return self.log

    def simulate_noise(self,no_cases,no_noisy_cases,removed_rules):
        '''simulates the given bpsim model with REMOVED rules to add generated noisy cases to log object'''
        for i in range(no_noisy_cases):
            eid = no_cases + no_noisy_cases + i + 1
            case = Case([CaseAttribute(attr.name,type=attr.type) for attr in self.case_attributes])
            # change the rules of the LogSimulator to the removed rules
            self.rules = removed_rules
            # simulates one instance or case of the tree until data noise is achieved
            while (case.no_rules_fired == 0):
                case.trace = []
                case.initialize_case_attrs()
                self._create_case(eid, case)
                self._run()
            self.log.add_case(case)
        return self.log

    def _run(self):
        global env
        env = self.env
        env.run()

    def _create_bpsim(self):
        '''method derives the sequence of execution between process tree constructs'''

        self.bpsim_sequence = []
        self.join_endpoints = dict()

        #make a dictionary to save all needed activity generators
        self.act_generators = dict()
        leaves = self.t.get_leaves()
        for leaf in leaves:
            self.act_generators[leaf] = self._act_generator(leaf.name,leaf.id)

        #save the required number of arcs
        #by default 1 for the start_node and 1 for each act
        self.arcs = 1 + len(self.act_generators)

        ####################################################################################
        #traverse tree and deduce the sequence of the process tree operators and activities#
        ####################################################################################
        for node in self.t.traverse(strategy="preorder"):
            if node.is_leaf():
                start_node = self._determine_start_node(node)
                end_node = self._determine_end_node(node)
                self.bpsim_sequence.append((node, "act" , "", start_node, end_node))
                for ancestor in node.get_ancestors():
                    if node in ancestor.endpoints:
                        ancestor.to_reach_endpoints -= 1
                        #add join for XOR, AND, OR nodes
                        if ancestor.to_reach_endpoints == 0 and ancestor.name not in ["sequence", "loop"]:
                            self.arcs += 1
                            self.bpsim_sequence.append((ancestor, "join", "", ancestor.endpoints))
                        #add split for LOOP node
                        elif ancestor.to_reach_endpoints == 0 and ancestor.name == "loop":
                            end_nodes = []
                            children = ancestor.get_children()
                            end_nodes.append(self._determine_start_middle(children[1]))
                            end_nodes.append(self._determine_start_middle(children[2]))
                            start = self._loop_end_left(children[0])
                            self.bpsim_sequence.append((ancestor,"split","",start, end_nodes))
            else:
                endpoints = []
                real_endpoints = []
                children = node.get_children()
                for child in children:
                    self._determine_endpoints(node, child, endpoints)
                    if node.name != "sequence":
                        self.arcs += 1
                if not node.is_root():
                    start_node = self._determine_start_node(node)
                else:
                    start_node = None
                node.add_feature("endpoints", endpoints)
                node.add_feature("to_reach_endpoints", len(endpoints))
                if node.name not in ["sequence", "loop"]:
                    for child in children:
                        self._return_real_endpoints(child, real_endpoints)
                    self.join_endpoints[node] = real_endpoints
                    self.bpsim_sequence.append((node, "split", children, start_node))
                elif node.name == "loop":
                    endpoints_middle = []
                    if children[1].is_leaf():
                        endpoints_middle.append(children[1])
                    else:
                        if children[1].name in ["sequence", "loop"]:
                            endpoints_middle.append(self._endpoint_loop_in_sequence(children[1]))
                        else:
                            endpoints_middle.append(children[1])
                        self.join_endpoints[node] = endpoints_middle
                    self.bpsim_sequence.append((node,"join", [start_node, endpoints_middle], children[0]))

    def _create_case(self,eid,case):
        '''translate sequence of execution of process tree to sequence of events with generator functions'''
        e = []
        joins = dict()
        or_dict = dict()
        loops_joins= dict()
        loops_splits = dict()
        for i in range(self.arcs):
            e.append(Zombie(self.env))
        out_arc = 1
        self.map_node_outgoing_arcs = dict()
        map_node_incoming_event = dict()

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
                            in_arc, self.map_node_outgoing_arcs = self._return_incoming_arc(startevent, self.map_node_outgoing_arcs)
                    except:
                        startevent = element[2][0]
                        in_arc, self.map_node_outgoing_arcs = self._return_incoming_arc(startevent, self.map_node_outgoing_arcs)
                    incoming_arcs.append(in_arc)

                    incoming_arcs.append(out_arc)
                    loops_joins[element[0]] = out_arc
                else:
                    incoming_arcs.append(0)
                    #added when loop join is first in bpsim_sequence
                    in_arc = 0
                    incoming_arcs.append(out_arc)
                    loops_joins[element[0]] = out_arc
                out_arc += 1
            elif element != self.bpsim_sequence[0] and element[1] != "join":
                try:
                    if element[3][1] == "xor-join":
                        startevent = element[3][0]
                        in_arc, self.map_node_outgoing_arcs = self._return_incoming_arc(startevent, self.map_node_outgoing_arcs)
                    elif element[3][1] == "xor-split":
                        in_arc = out_arc
                        loops_splits[element[0]] = in_arc
                        #in case xor-split outgoing arc heads towards an operator
                        if not element[0].is_leaf():
                            out_arc += 1
                except:
                    startevent = element[3]
                    in_arc, self.map_node_outgoing_arcs = self._return_incoming_arc(startevent, self.map_node_outgoing_arcs)
            elif element != self.bpsim_sequence[0] and element[1] == "join":
                startevents = self.join_endpoints[element[0]]
                for startevent in startevents:
                    if startevent.is_leaf():
                        incoming_arcs.append(self.map_node_outgoing_arcs[startevent][0])
                    else:
                        incoming_arcs.append(joins[startevent])
            else:
                in_arc = 0

            #use incoming arc as index to map incoming event to tree node
            #print 'element:', element[0].name, element[1]
            if self._add_to_map_node_incoming_event(element[0],element[1],e,in_arc):
                map_node_incoming_event[element[0]] = e[in_arc]

            #determining outgoing events
            if element[1] == "split":
                if element[0].name == "loop":
                    for in_event in element[4]:
                        try:
                            in_event = in_event[0]
                        except:
                            pass
                        outgoing_arcs.append(loops_splits[in_event])
                    self.map_node_outgoing_arcs[element[0]] = outgoing_arcs
                    split, routing = self._produce_split_generator(element[0], self.env, eid,
                                                                  outgoing_arcs, e, or_dict,
                                                                  case, map_node_incoming_event)
                    self.env.process(split(e[in_arc], eid, routing))
                else:
                    for i in range(len(element[2])):
                        outgoing_arcs.append(out_arc + i)
                    self.map_node_outgoing_arcs[element[0]] = outgoing_arcs
                    split, routing = self._produce_split_generator(element[0], self.env, eid,
                                                                  outgoing_arcs, e, or_dict,
                                                                  case, map_node_incoming_event)
                    self.env.process(split(e[in_arc], eid, routing))
                    out_arc = out_arc + i + 1

            elif element[1] == "join":
                new_out_arc = out_arc
                for key, value in self.join_endpoints.items():
                    if key.name == "loop" and value[0] == element[0]:
                        new_out_arc = loops_joins[key]
                        out_arc = out_arc - 1
                        break
                joins[element[0]] = new_out_arc
                self.map_node_outgoing_arcs[element[0]] = [new_out_arc]
                join = self._produce_join_generator(element[0])
                incoming_events = []
                for i in incoming_arcs:
                    incoming_events.append(e[i])
                #for joins we add multiple events to mapping to join node
                #map_node_incoming_event[element[0]] = e[in_arc]

                if element[0].name == "or":
                    self.env.process(join(incoming_events, e[new_out_arc], or_dict, element[0], eid))
                else:
                    self.env.process(join(incoming_events, e[new_out_arc], eid))
                out_arc = out_arc + 1
            else:
                try:
                    #special case when outgoing event is loop xor-join (b)
                    if element[4][1] == "xor-join":
                        out2_arc = loops_joins[element[4][0]]
                        act_gen = self.act_generators[element[0]]
                        self.map_node_outgoing_arcs[element[0]] = [out2_arc]
                        self.env.process(act_gen(self.env, e[in_arc], e[out2_arc], self._dur_a(), eid, case))
                        if out_arc > in_arc:
                            out_arc -= 1

                    #case when outgoing event is loop xor-split (a)
                    else:
                        #activity between two loop xor-splits
                        if in_arc == out_arc:
                            out_arc += 1
                        act_gen = self.act_generators[element[0]]
                        self.map_node_outgoing_arcs[element[0]] = [out_arc]
                        self.env.process(act_gen(self.env, e[in_arc], e[out_arc], self._dur_a(), eid, case))
                except:
                    #incoming event is loop xor-split
                    if in_arc == out_arc:
                        out_arc += 1
                    act_gen = self.act_generators[element[0]]
                    self.map_node_outgoing_arcs[element[0]] = [out_arc]
                    self.env.process(act_gen(self.env, e[in_arc], e[out_arc], self._dur_a(), eid, case))
                out_arc = out_arc + 1

        e[0].succeed()

    def _determine_start_node(self,node):
        '''
        determine node that is executed before node

        @type node: TreeNode
        @param node: node of a newick tree

        @rtype: TreeNode
        @return: node that precedeces given node in execution sequence
        '''
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
                    return self._determine_start_node(ancestors[0])
            else:
                if children[index-1].name == "loop":
                    return self._endpoint_loop_in_sequence(children[index-1])
                elif children[index-1].name == "sequence":
                    return self._endpoint_loop_in_sequence(children[index-1])
                else:
                    return children[index-1]
        else:
            children = ancestors[0].get_children()
            index = children.index(node)
            if index == 0:
                return [ancestors[0],"xor-join"]
            else:
                return [ancestors[0],"xor-split"]

    def _determine_end_node(self,node):
        '''
        determine node that is executed after node

        @type node: TreeNode
        @param node: node of a newick tree

        @rtype: TreeNode
        @return: node that succeeds given node in execution sequence
        '''
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
                    return self._determine_end_node(ancestors[0])
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
                    return self._determine_end_node(ancestors[0])

    def _determine_start_middle(self, node):
        '''start node middle child in loop'''
        if node.name == "loop":
            return [node,"xor-join"]
        elif node.name == "sequence":
            children = node.get_children()
            return self._determine_start_middle(children[0])
        else:
            return node

    def _loop_end_left(self, node):
        '''method to determine end node of left child in loop'''
        if node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            return self._loop_end_left(last_child)
        else:
            return node

    def _determine_endpoints(self, node, child, endpoints):
        '''recursive function to determine endpoints'''
        if node.name in ["choice", "parallel", "or"]:
            if child.is_leaf():
                endpoints.append(child)

            else:
                for grandchild in child.get_children():
                    self._determine_endpoints(child, grandchild, endpoints)

        elif node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            if child == last_child:
                if last_child.is_leaf():
                    endpoints.append(last_child)

                else:
                    for grandchild in last_child.get_children():
                        self._determine_endpoints(last_child, grandchild, endpoints)
            else:
                pass
        return endpoints

    def _return_real_endpoints(self, node, real_endpoints):
        '''determine real endpoints node'''
        if node.name in ["sequence", "loop"]:
            last_child = node.get_children()[-1]
            self._return_real_endpoints(last_child,real_endpoints)
        else:
            real_endpoints.append(node)
        return real_endpoints

    def _endpoint_loop_in_sequence(self, node):
        '''special function to determine endpoint of loop for loops in first part of a sequence'''
        last_child = node.get_children()[-1]
        if last_child.name in ["sequence", "loop"]:
            return self._endpoint_loop_in_sequence(last_child)
        else:
            return last_child

    def _act_generator(self,act_name,act_id,res_name=""):
        '''creates generator function for activity'''
        def act(env, start, end, fdur, eid, case, res=None):
            while True:
                yield start

                if res is not None:
                    req = res.request()
                    print("%d: request resource '%s' @%s" % (eid, res_name, env.now))
                    yield req
                start_time = env.now
                yield env.timeout(fdur())
                end_time = env.now
                if act_name != "tau":
                    case.trace.append(act_name)
                if act_id in self.choice_first_leaves.keys():
                    new_case_attr = CaseAttribute('choice_' + str(self.choice_first_leaves[act_id]))
                    new_case_attr.assign_value(act_name)
                    case.case_attrs.append(new_case_attr)
                if res is not None:
                    res.release(req)

                end.succeed()
                start.reset()

        return act

    def _dur_a(self):
        '''returns a function for picking a (random) duration of an activity'''
        def fdur():
            return random.randint(1,10000)
        return fdur

    def _return_incoming_arc(self,startevent,map_node_outgoing_arcs):
        '''determine the incoming arc (event) of a node'''
        if len(map_node_outgoing_arcs[startevent]) > 1:
            incoming_arc = map_node_outgoing_arcs[startevent][0]
            del map_node_outgoing_arcs[startevent][0]
            return incoming_arc, map_node_outgoing_arcs
        else:
            incoming_arc = map_node_outgoing_arcs[startevent][0]
            return incoming_arc, map_node_outgoing_arcs

    def _add_to_map_node_incoming_event(self,node,node_type,e,in_arc):
        '''return True if node and incoming event should be included in mapping'''
        if node_type == "join" and node.name == "loop":
            return True
        elif node_type == "split" and node.name != "loop":
            return True
        elif node_type == "act":
            return True
        else:
            return False

    def _produce_split_generator(self,node,env,eid,outgoing_indices,e,or_dict,case,map_node_incoming_event):
        '''return the correct generator function for each type of split'''
        outgoing_arcs = []
        for i in outgoing_indices:
                outgoing_arcs.append(e[i])
        if node.name == "parallel":
            and_split = self._and_split_generator('and')
            path_probabilities = []
            for child in node.get_children(): path_probabilities.append(child.dist)
            and_routing = self._and_routing_generator(env, outgoing_arcs, path_probabilities)
            return and_split, and_routing

        elif node.name in ["choice", "loop"]:
            xor_split = self._xor_split_generator("xor")
            if node.name == "choice":
                path_probabilities = dict()
                for i,child in enumerate(node.get_children()):
                    path_probabilities[e[outgoing_indices[i]]] = child.dist
                #xor_routing = self._xor_routing_generator(env,outgoing_arcs,path_probabilities,self.rules[node])
                xor_routing = self._xor_routing_generator(env,outgoing_arcs,
                                                         path_probabilities,
                                                         self.rules.get(node,[]),
                                                         case,map_node_incoming_event)
            else:
                xor_routing = self._xor_routing_generator2(env, outgoing_arcs)
            return xor_split, xor_routing

        else:
            or_split = self._or_split_generator("or")
            path_probabilities = []
            for child in node.get_children(): path_probabilities.append(child.dist)
            or_routing = self._or_routing_generator(env, outgoing_arcs, or_dict, node, path_probabilities)
            return or_split, or_routing

    def _produce_join_generator(self, node):
        '''return the correct generator function for each type of join'''
        if node.name == "parallel":
            and_join = self._and_join_generator("and")
            return and_join

        elif node.name in ["choice", "loop"]:
            xor_join = self._xor_join_generator("xor")
            return xor_join

        else:
            or_join = self._or_join_generator("or")
            return or_join

    def _and_split_generator(self, and_name):
        '''creates AND split generator function'''
        def and_split(start, eid, routing_func):
            while True:
                yield start
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return and_split

    def _and_routing_generator(self, env, events, path_probabilities):
        '''creates AND routing function'''
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


    def _and_join_generator(self, and_name):
        '''creates the AND join generator function'''
        def and_join(start_events, end, eid):
            while True:
                join = AllOf(self.env, start_events)
                yield join
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return and_join

    def _xor_routing_generator2(self, env, events):
        '''creates LOOP routing function'''
        def xor_routing():
            random_event = random.choice(events)
            random_event.succeed()
        return xor_routing

    def _or_split_generator(self, or_name):
        '''creates OR split generator function'''
        def or_split(start, eid, routing_func):
            while True:
                yield start
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return or_split

    def _or_join_generator(self, or_name):
        '''creates the OR join generator function'''
        def or_join(start_events, end, or_dict, or_, eid):
            while True:
                join = NOf(self.env, start_events, or_dict, or_)
                yield join
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return or_join

    def _or_routing_generator(self, env, events, or_dict, or_, path_probabilities):
        '''creates OR routing function'''
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

    def _xor_split_generator(self, xor_name):
        '''creates XOR split generator function'''
        def xor_split(start, eid, routing_func):
            while True:
                yield start
                yield self.env.timeout(0)
                routing_func()
                start.reset()
        return xor_split

    def _xor_join_generator(self, xor_name):
        '''creates the XOR join generator function'''
        def xor_join(start_events, end, eid):
            while True:
                join = AnyOf(self.env, start_events)
                yield join
                yield self.env.timeout(0)
                end.succeed()
                for e in start_events: e.reset()
        return xor_join

    def _xor_routing_generator(self,env,events,path_probabilities,rules,case,map_node_incoming_event):
        '''creates XOR routing function using rules'''
        def xor_routing():
            candidates = self._determine_candidates(events,rules,case,map_node_incoming_event)
            if len(candidates) > 0:
                case.no_rules_fired += 1
                if len(candidates) < 2:
                    candidates[0].succeed()
                else:
                    self._return_random_candidate(path_probabilities,candidates).succeed()
            else:
                x = random.random()
                cutoffs = []
                previous_cutoff = 0

                for val in path_probabilities.values():
                    cutoffs.append(previous_cutoff + val)
                    previous_cutoff = previous_cutoff + val

                j = len(cutoffs)
                for i,value in enumerate(cutoffs):
                    if x < value:
                        j = i
                        break
                random_event = events[j]
                random_event.succeed()

                for event in events:
                    if event != random_event:
                        event.last_chosen = False
                    else:
                        event.last_chosen = True
        return xor_routing

    def _return_random_candidate(self,path_probabilities,candidates):
        '''return a random candidate taking the branch probabilities into account'''
        x = random.random()
        cutoffs = []
        previous_cutoff = 0
        tot_probabilities = 0.0
        for c in candidates:
            tot_probabilities += path_probabilities[c]

        for c in candidates:
            cutoffs.append(previous_cutoff + path_probabilities[c]/tot_probabilities)
            previous_cutoff = previous_cutoff + path_probabilities[c]/tot_probabilities

        j = len(cutoffs)
        for i,value in enumerate(cutoffs):
            if x < value:
                j = i
                break

        return candidates[j]

    def _make_condition(self,case,map_node_incoming_event):
        '''combines all case attributes into condition dictionary:
        {key_1:value_1,key_2:value_2,...}'''
        c =  dict()
        for attr in case.case_attrs:
            c[attr.name] = attr.value
        #print 'events once executed', [node for node,event in map_node_incoming_event.items() if event.once_executed==True]
        for node,event in map_node_incoming_event.items():
            if event.once_executed == True and event.last_chosen:
                #map the node corresponding to the executed event to True
                try:
                    c[node] = True
                except ValueError:
                    print 'missing event', event
        return c

    #@deprecated
    def _consequent_can_fire(self,events,rule):
        '''determine if the choice activates the consequent of the rule'''
        if self.act_startevent_dict[rule[1]] in events:
            return True
        else:
            return False

    def _condition_matches(self,condition,rule):
        '''returns true if the current condition matches the antecedent of the given rule'''
        matches = True
        condition_keys = set(condition.keys())
        rule_keys = set(rule[0].keys())
        absent_keys = rule_keys - condition_keys
        intersect_keys = rule_keys.intersection(condition_keys)
        if len(absent_keys) > 0:
            matches = False
        else:
            for o in intersect_keys:
                if type(condition[o]) == bool:
                    if rule[0][o] != condition[o]:
                        #print 'non-matching condition element:', rule[0][o], condition[o]
                        matches = False
                        break
                else:
                    if (condition[o] < rule[0][o][0] or condition[o] >= rule[0][o][1]):
                        #print 'non-matching condition element:', rule[0][o], condition[o]
                        matches = False
                        break
        #print rule, matches
        return matches

    def _return_incoming_event_child(self,node,map_node_incoming_event):
        '''normally should only occur in case of a sequence node is passed, then return incoming
        event of the first child'''
        return map_node_incoming_event[node.get_children()[0]]

    def _determine_candidates(self,events,rules,case,map_node_incoming_event):
        '''determine all candidates that can be chosen'''
        #print 'mapping', map_node_incoming_event
        candidates = []
        condition = self._make_condition(case,map_node_incoming_event)
        for rule in rules:
            if self._condition_matches(condition,rule):
                try:
                    candidates.append(map_node_incoming_event[rule[1]])
                except KeyError:
                    candidates.append(self._return_incoming_event_child(rule[1],map_node_incoming_event))
        return candidates
