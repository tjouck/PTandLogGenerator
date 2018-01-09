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
        self.no_noisy_traces = 0
        self.resulting_traces = self.add_noise(noise_percentage,traces)

    #read csv log-file
    def get_traces(self,fname):
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

    #work with traces as lists: <y,z,aa> => ["y","z","aa"]!

    #not used in mixed noise type
    def remove_task(self,trace):
        act = random.choice(trace)
        trace.remove(act)
        return trace

    def duplicate_task(self,trace):
        random_index = random.randrange(0,len(trace))
        trace.insert(random_index+1,trace[random_index])
        return trace

    def swap_tasks(self,trace):
        act_1 = random.choice(trace)
        act_2 = act_1
        count = 0
        while act_2 == act_1 and count <10:
            act_2 = random.choice(trace)
            count += 1
        if count < 10:
            a, b = trace.index(act_1), trace.index(act_2)
            trace[a], trace[b] = trace[b], trace[a]
            return trace,True
        else:
            return trace,False

    def remove_head(self,trace):
        end_index = len(trace)/3
        trace = trace[end_index:]
        return trace

    def remove_body(self,trace):
        start_index = len(trace)/3
        end_index = (2*len(trace))/3
        trace = trace[:start_index] + trace[end_index:]
        return trace

    def remove_tail(self,trace):
        start_index = (2*len(trace))/3
        trace = trace[:start_index]
        return trace

    def add_noise(self,noise_prob, traces):
        new_traces = []
        for trace in traces:
            #if the trace contains only one activity, continue
            if len(trace) <= 1:
                new_traces.append(trace)
                continue
            #draw a random number x
            x = random.random()
            #if x is smaller than the noise_prob, add noise
            if x < noise_prob:
                self.no_noisy_traces += 1
                #to implement a mix all noise, randomly choose a noise type
                noise_type = random.choice(["swap","duplicate","head","body","tail"])
                if noise_type == "swap":
                    trace, added = self.swap_tasks(trace)
                    if added == True:
                        new_traces.append(trace)
                    else:
                        noise_type = random.choice(["duplicate","head","body","tail"])
                        if noise_type == "duplicate":
                            new_traces.append(self.duplicate_task(trace))
                        elif noise_type == "head":
                            new_traces.append(self.remove_head(trace))
                        elif noise_type == "body":
                            new_traces.append(self.remove_body(trace))
                        elif noise_type == "tail":
                            new_traces.append(self.remove_tail(trace))
                elif noise_type == "duplicate":
                    new_traces.append(self.duplicate_task(trace))
                elif noise_type == "head":
                    new_traces.append(self.remove_head(trace))
                elif noise_type == "body":
                    new_traces.append(self.remove_body(trace))
                elif noise_type == "tail":
                    new_traces.append(self.remove_tail(trace))
            else:
                new_traces.append(trace)
        return new_traces

    def noisy_traces_to_csv(self,fname, traces):
        output = open(fname + "_noise.csv", 'w')
        output.write("case_id,act_name\n")
        for eid,trace in traces.iteritems():
            for activity in trace:
                output.write(str(eid) + "," + activity + "\n")

        output.close()