import sys
sys.path.insert(0, '../')
sys.path.insert(0, '../source')
sys.path.insert(0, '../newick/')
import glob
import argparse
from tree import TreeNode
from tree_with_data_dependencies import TreeWithDataDependencies
from simulate_tree_with_rules import LogSimulator as LogSimulatorData
from simulateLog import LogSimulator
from xes_writer import write_as_xes
import xml.etree.ElementTree as xmltree

def write_as_xes_cf(traces, index):
    '''writes log to xes-formatted file'''
    xes_file = open("../data/logs/log" + index + ".xes", 'w')
    xes_file.write('<?xml version="1.0" encoding="UTF-8" ?>\n')

    root = xmltree.Element('log')
    root.attrib['xes.version'] = "1.0"
    root.attrib['xes.features'] = "nested-attributes"
    root.attrib['openxes.version'] = "1.0RC7"
    root.attrib['xmlns'] = "http://www.xes-standard.org/"
    concept = xmltree.SubElement(root, 'extension')
    concept.attrib['name'] = "Concept"
    concept.attrib['prefix'] = "concept"
    concept.attrib['uri'] = "http://www.xes-standard.org/concept.xesext"
    life = xmltree.SubElement(root, 'extension')
    life.attrib['name'] = "Lifecycle"
    life.attrib['prefix'] = "lifecycle"
    life.attrib['uri'] = "http://www.xes-standard.org/lifecycle.xesext"
    lname = xmltree.SubElement(root, 'string')
    lname.attrib['key'] = "concept:name"
    lname.attrib['value'] = "log" + index

    i = 1

    for t in traces:
        trace = xmltree.SubElement(root, 'trace')
        tname = xmltree.SubElement(trace, 'string')
        tname.attrib['key'] = "concept:name"
        tname.attrib['value'] = str(i)
        for act in t:
            event = xmltree.SubElement(trace, 'event')
            ename = xmltree.SubElement(event, 'string')
            ename.attrib['key'] = "concept:name"
            ename.attrib['value'] = act
            elf = xmltree.SubElement(event, 'string')
            elf.attrib['key'] = "lifecycle:transition"
            elf.attrib['value'] = 'complete'
        i += 1
    xes_file.write(xmltree.tostring(root))
    xes_file.close()

def write_decision_tables(tree_w_data, index):
    '''write final decision tables of each decision with dependencies'''
    print index
    for d in tree_w_data.D:
        tree_w_data.Delta[d].print_decision_table(tree_w_data.choice_labels, d, tree_w_data.tree_index)
        print 'determinism:', str(tree_w_data._calculate_determinism_decision_table(tree_w_data.Delta[d]))
    print 'overall determinism level:', str(tree_w_data.calculate_mean_determinism_level())

parser = argparse.ArgumentParser(description='Generate data dependencies and simulate event logs from process trees.')
parser.add_argument('--i', nargs='?', default='../data/trees/',
                    help='specify the relative address to the trees folder' \
                    ', default=../data/trees/', metavar='input_folder')
parser.add_argument('--p', nargs='?', default=False, type=bool,
                    help='print decision tables in separate files, '\
                    'default=False', metavar='print_decision_tables', choices=[False,True])
parser.add_argument('size', type=int, help='number of cases to simulate')
parser.add_argument('noise_size', type=int, help='number of noisy cases to simulate')
parser.add_argument('nodes', type=int, help='maximum input variables of each decision')
parser.add_argument('cutoff', type=int, help='maximum cutoff values for numerical variable')
parser.add_argument('determinism', type=float, help='target determinism level')

args = parser.parse_args()

if args.determinism < 0.0 or args.determinism > 1.0:
    print "ERROR: specify target determinism level in range [0,1]"
    sys.exit()

print "start of plugin with arguments: ", args

#read the input parameters
number_of_cases = args.size
no_noisy_cases = args.noise_size
target_determinism_level = args.determinism
max_input_nodes = args.nodes
max_cutoff_values = args.cutoff
tree_folder = args.i
print_decision_tables = args.p

#specify the folder with the trees
tree_files = glob.glob(tree_folder + "*.nw")

# for each tree
for filepath in tree_files:
    # get tree index
    i = filepath[filepath.find('_'):filepath.rfind('.nw')]

    # generate traces
    tree = TreeNode(filepath, format=1)
    tree_w_data = TreeWithDataDependencies(tree.write(format=1, format_root_node=True),
                                           str(i), target_dl=target_determinism_level)
    if (not tree_w_data.data_dependencies_possible):
        simulator = LogSimulator(tree.write(format=1, format_root_node=True), 1000, record_timestamps=False)
        traces = simulator.returnLog()
        write_as_xes_cf(traces, i)
        dl = ''
    else:
        tree_w_data.extend_tree_with_data_dependencies(max_input_nodes, max_cutoff_values)
        # write decision tables
        if args.p:
            write_decision_tables(tree_w_data,i)
        # simulate tree with data dependencies
        # all cases are fitting to the tree with data dependencies
        simulator = LogSimulatorData(tree_w_data.t,
                                     tree_w_data.input_choice_dictionary,
                                     tree_w_data.rules_simulation,
                                     tree_w_data.case_attr,
                                     False)
        simulator.simulate(number_of_cases)
        # simulate noisy cases based on removed rules
        simulator.simulate_noise(number_of_cases, no_noisy_cases, tree_w_data.removed_rules_simulation)
        # write the simulated log to a xes file
        write_as_xes(simulator.log.cases, i)
        # write determinism level
        dl = tree_w_data.final_average_determinism_level
        # print "determinism level:", dl
