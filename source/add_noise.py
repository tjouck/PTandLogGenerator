# -*- coding: utf-8 -*-
"""
Created on Mon Aug 17 14:40:24 2015

@author: lucp8356
"""
import random

#adds noise to a log-file. This implements a mix all noise type (ranadomly adds
#all types of noise)

class NoiseGenerator():

    def __init__(self,traces,noise_percentage):
        self.resulting_traces = []
        self.resulting_traces = self.add_noise(noise_percentage,traces)

    #read csv log-file
    def get_traces(self,fname):
        log = open(fname)
        traces = dict()
        for line in log:
            if line.startswith("case_id"):
                #print line
                continue
            line = line.strip()
            contents = line.split(",")
            traces.setdefault(contents[0],[]).append(contents[1])
        return traces

    #work with traces as lists: <y,z,aa> => ["y","z","aa"]!

    def remove_task(self,trace):
        #print "remove task"
        #print "old trace:", trace
        act = random.choice(trace)
        trace.remove(act)
        #print "new trace:", trace
        return trace

    def swap_tasks(self,trace):
        #print "swap tasks"
        #print "old trace:", trace
        act_1 = random.choice(trace)
        act_2 = act_1
        while act_2 == act_1:
            act_2 = random.choice(trace)
        a, b = trace.index(act_1), trace.index(act_2)
        trace[a], trace[b] = trace[b], trace[a]
        #print "new trace:", trace
        return trace

    def remove_head(self,trace):
        #print "remove head"
        #print "old trace:", trace
        end_index = len(trace)/3
        trace = trace[end_index:]
        #print "new trace:", trace
        return trace

    def remove_body(self,trace):
        #print "remove body"
        #print "old trace:", trace
        start_index = len(trace)/3
        end_index = (2*len(trace))/3
        trace = trace[:start_index] + trace[end_index:]
        #print "new trace:", trace
        return trace

    def remove_tail(self,trace):
        #print "remove tail"
        #print "old trace:", trace
        start_index = (2*len(trace))/3
        trace = trace[:start_index]
        #print "new trace:", trace
        return trace

    def add_noise(self,noise_prob, traces):
        for i in range(len(traces)):
            #draw a random number x
            x = random.random()
            #if x is smaller than the noise_prob, add noise
            if x < noise_prob:
                #use x to select a random trace
                key = int(x * len(traces))
                trace = traces[key]
                #if the trace contains only one activity, select another trace
                while len(trace) <= 1:
                    x = random.random()
                    key = int(x * len(traces))
                    trace = traces[key]
                #print key
                #to implement a mix all noise, randomly choose a noise type
                noise_type = random.choice(["swap","remove","head","body","tail"])
                if noise_type == "swap":
                    traces[key] = self.swap_tasks(trace)
                elif noise_type == "remove":
                    traces[key] = self.remove_task(trace)
                elif noise_type == "head":
                    traces[key] = self.remove_head(trace)
                elif noise_type == "body":
                    traces[key] = self.remove_body(trace)
                elif noise_type == "tail":
                    traces[key] = self.remove_tail(trace)
        return traces

    def noisy_traces_to_csv(self,fname, traces):
        output = open(fname + "_noise.csv", 'w')
        output.write("case_id,act_name\n")
        for eid,trace in traces.iteritems():
            for activity in trace:
                output.write(str(eid) + "," + activity + "\n")

        output.close()

"""
#################################################################
#ask user to provide the name of the log input file
fname = "plugins/Logs/_10_1.csv"

def get_traces(fname):
        log = open(fname)
        traces = dict()
        for line in log:
            if line.startswith("case_id"):
                print line
                continue
            line = line.strip()
            contents = line.split(",")
            traces.setdefault(contents[0],[]).append(contents[1])
        return traces

#ask user for percentage of noise in log
noise_percentage = 0.1

#insert noise into traces
dict_traces = get_traces(fname)
traces = []
for eid,trace in dict_traces.iteritems():
    traces.append(trace)
generator = NoiseGenerator(traces, noise_percentage)
noisy_traces = generator.resulting_traces

#print noisy traces

for trace in noisy_traces:
    print trace
"""
