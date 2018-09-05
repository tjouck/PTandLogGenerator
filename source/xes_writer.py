import xml.etree.ElementTree as xmltree
import datetime

def write_as_xes(cases,index,test=False):
    '''
    Write log to xes-formatted file

    @type cases: Case object
    @param cases: case in a log (with trace and case attributes)

    @type tree_index: int
    @param tree_index: specifies the number of the tree used to name the log file

    '''
    if test:
        xes_file = open("../data/logs/log" + str(index) + "_test.xes", 'w')
    else:
        xes_file = open("../data/logs/log" + str(index) + ".xes", 'w')
    xes_file.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
    
    root = xmltree.Element('log')
    root.attrib['xes.version']="1.0" 
    root.attrib['xes.features']="nested-attributes"
    root.attrib['openxes.version']="1.0RC7" 
    root.attrib['xmlns']="http://www.xes-standard.org/"
    concept = xmltree.SubElement(root,'extension')
    concept.attrib['name']="Concept" 
    concept.attrib['prefix']="concept" 
    concept.attrib['uri']="http://www.xes-standard.org/concept.xesext"
    life = xmltree.SubElement(root,'extension')
    life.attrib['name']="Lifecycle" 
    life.attrib['prefix']="lifecycle"
    life.attrib['uri']="http://www.xes-standard.org/lifecycle.xesext"
    time = xmltree.SubElement(root, 'extension')
    time.attrib['name'] = "Time"
    time.attrib['prefix'] = "time"
    time.attrib['uri'] = "http://www.xes-standard.org/time.xesext"
    lname = xmltree.SubElement(root,'string')
    lname.attrib['key'] = "concept:name"
    if test:
        lname.attrib['value'] = "test_log" + str(index)
    else:
        lname.attrib['value'] = "log" + str(index)

    timestamp = 1
    for c_id,case in enumerate(cases):
        case_trace = case.trace
        c_attributes = case.case_attrs
        trace = xmltree.SubElement(root,'trace')
        tname = xmltree.SubElement(trace,'string')
        tname.attrib['key'] = "concept:name"
        tname.attrib['value'] = str(c_id)

        for act in case_trace:
            event = xmltree.SubElement(trace,'event')
            ename = xmltree.SubElement(event,'string')
            ename.attrib['key'] = "concept:name"
            ename.attrib['value'] = act
            elf = xmltree.SubElement(event,'string')
            elf.attrib['key'] = "lifecycle:transition"
            elf.attrib['value'] = 'complete'
            etime = xmltree.SubElement(event, 'date')
            etime.attrib['key'] = "time:timestamp"
            etime.attrib['value'] = add_sec(datetime.datetime.today(),timestamp).isoformat()
            timestamp += 1
            for attr in c_attributes:
                if attr.type == 'bool':
                    eattr = xmltree.SubElement(event, 'string')
                else:
                    eattr = xmltree.SubElement(event, 'float')
                eattr.attrib['key'] = attr.name
                eattr.attrib['value'] = str(attr.value)
    xes_file.write(xmltree.tostring(root))
    xes_file.close()

def add_sec(time, secs):
    time = time + datetime.timedelta(seconds=secs)
    return time