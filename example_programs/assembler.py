import re
import pathlib
import argparse

def check_mov(args):
    r = re.match(r'([abc]) ([abc])', args)
    if (r is not None):
        return r.group(1) != r.group(2)

def check_load(args):
    r = re.match(r'ram\[[abc]\] [abc]', args)
    if (r is not None):
        return True
    r = re.match(r'ram\[[0-9]+\] [abc]', args)
    if (r is not None):
        return True
    r = re.match(r'rom [abc] [0-9]+', args)
    return r is not None

def check_save(args):
    r = re.match(r'[abc] ram', args)
    if (r is not None):
        return True
    r = re.match(r'[abc] ram\[[abc]\]', args)
    if (r is not None):
        return True
    r = re.match(r'[abc] ram\[[0-9]+\]', args)
    if (r is not None):
        return True
    r = re.match(r'[abc] mar', args)
    return r is not None

operations = {
    'nop': lambda x: x == '',
    'mov': check_mov,
    'cmp': re.compile(r'([abc]) ([abc])').match,
    'jmp': re.compile(r'(\.?(<=|<|=|>|>=) [abc])|(.+)').match,
    'jmpr': re.compile(r'(\.?(<=|<|=|>|>=) [abc])|(.+)').match,
    'opp': re.compile(r'').match,
    'load': check_load,
    'save': check_save,
    'in': re.compile(r'[abc]').match,
    'out': re.compile(r'[abc]').match,
    'pause': lambda x: x == ''
}

translation = {
    'nop': 0x0,

    'mov a b': 0x10,
    'mov a c': 0x11,
    'mov b a': 0x12,
    'mov b c': 0x13,
    'mov c a': 0x14,
    'mov c b': 0x15,

    'cmp a a': 0x20,
    'cmp a b': 0x21,
    'cmp a c': 0x22,
    'cmp b b': 0x23,
    'cmp b a': 0x24,
    #'cmp c d': 0x25,
    'cmp c c': 0x26,
    'cmp c a': 0x27,
    #'cmp c b': 0x28,

    'jmp {label}':     0x30, 
    'jmp = {label}':   0x31, 
    'jmp != {label}':  0x32, 
    'jmp <= {label}':  0x33, 
    'jmp < {label}':   0x34, 
    'jmp > {label}':   0x35, 
    'jmp >= {label}':  0x36, 
    'jmp .<= {label}': 0x37, 
    'jmp .< {label}':  0x38, 
    'jmp .> {label}':  0x39, 
    'jmp .>= {label}': 0x3a,  
    
    'jmpr {number}':     0x40, 
    'jmpr = {number}':   0x41, 
    'jmpr != {number}':  0x42, 
    'jmpr < {number}':   0x43, 
    'jmpr <= {number}':  0x44, 
    'jmpr > {number}':   0x45, 
    'jmpr >= {number}':  0x46, 
    'jmpr .< {number}':  0x47, 
    'jmpr .<= {number}': 0x48, 
    'jmpr .> {number}':  0x49, 
    'jmpr .>= {number}': 0x4a, 

    'opp 0':   0x50,
    'opp 1':   0x51,
    'opp -1':  0x52,
    'opp a':   0x53,
    'opp b':   0x54,
    'opp !a':  0x55,
    'opp !b':  0x56,
    'opp -a':  0x57,
    'opp -b':  0x58,
    'opp a+1': 0x59,
    'opp b+1': 0x5a,
    'opp a-1': 0x5b,
    'opp b-1': 0x5c,
    'opp a+b': 0x5d,
    'opp a-b': 0x5e,
    'opp b-a': 0x5f,

    'opp a&b':  0x60,
    'opp a|b':  0x61,
    'opp a.+b': 0x62,
    'opp a>>b': 0x63,
    'opp a<<b': 0x64,

    'load rom a {number}': 0x70,
    'load rom b {number}': 0x71,
    'load rom c {number}': 0x72,
    
    'load ram[a] a': 0x80,
    'load ram[a] b': 0x81,
    'load ram[a] c': 0x82,
    'load ram[b] a': 0x83,
    'load ram[b] b': 0x84,
    'load ram[b] c': 0x85,
    'load ram[c] a': 0x86,
    'load ram[c] b': 0x87,
    'load ram[c] c': 0x88,
    'load ram[{number}] a': 0x89,
    'load ram[{number}] b': 0x8a,
    'load ram[{number}] c': 0x8b,
    
    'save a ram': 0x90,
    'save b ram': 0x91,
    'save c ram': 0x92,
    'save a ram[a]': 0x93,
    'save b ram[c]': 0x94,
    'save c ram[d]': 0x95,
    'save a ram[{number}]': 0x96,
    'save b ram[{number}]': 0x97,
    'save c ram[{number}]': 0x98,
    'save a mar': 0x99,
    'save b mar': 0x9a,
    'save c mar': 0x9b,

    'in a': 0xa0,
    'in b': 0xa1,
    'in c': 0xa2,

    'out a':  0xb0,
    'out b':  0xb1,
    'out c':  0xb2,
    #'out 0':  0xb3, #TODO: Implement this
    #'out 1':  0xb4,
    #'out -1': 0xb5,

    'pause': 0xf0
}

translation_stage_two = list(filter(lambda x: '{label}' in x or
                                    '{number}' in x, 
                                    translation))

def opp_to_hex(line):
    global offset

    if line in translation:
        offset += 1
        return [translation[line]]

    for instruction in translation_stage_two:
        match_whole_ins = '^'+re.escape(instruction)+'$'
        
        ins_temp = match_whole_ins.replace('\{label\}','([^ ]+)')
        match = re.match(ins_temp, line)
        if match is not None:
            #Instructions with labels are 3 bytes
            offset += 3
            return [translation[instruction], *match.groups()]

        ins_temp = match_whole_ins.replace('\{number\}','(?:(0x([0-9a-fA-F]+))|(0b([01]+))|([0-9]+))')
        match = re.match(ins_temp, line)
        if match is not None:
            #Instructions with numbers are 2 bytes
            offset += 2

            #TODO: Only supports one number per instruction
            if match.group(1):
                number = int(match.group(2),16)
            elif match.group(3):            
                number = int(match.group(4),2)
            elif match.group(5):
                number = int(match.group(5))
                
            if number > 0xff:
                print(line)
                print("Number larger than can fit in register")
                return None
            		
            return [translation[instruction], number]
    return None 

def parse(input_file, output_file):
    final = []
    labels = {}
    global offset
    offset = 0

    for ln,line in enumerate(input_file):
        line = re.sub(r'//.*',r'',line)
        line = line.strip()
        if not line:
            continue
        
        variables = line.split()
        opp = variables[0]
        opp_args = ' '.join(variables[1:])

        label_match = re.match(':(.+)', opp)
        if label_match is not None:
            #print(line, offset)
            label_match = label_match.group(1)
            if label_match not in labels:
                labels[label_match] = offset
            else:
                print(line)
                print("Line %d duplicate label detected" % (ln+1))
        elif opp in operations:
            if not operations[opp](opp_args):
                print(line)
                print("Line %d is not valid" % (ln+1))
                return

            hex_op = opp_to_hex(line)
            if hex_op is None:
                print(line)
                print("Line %d couldn't find translation for instruction" % (ln+1))
                return
            final.extend(hex_op)
        else:
            print(line)
            print("Line %d couldn't find matching instruction" % (ln+1))
            return


    #for x in final:
    #    if isinstance(x, int):
    #        print(hex(int(x)), end=' ')
    #    else:
    #        print(x, end=' ')
    #print()
            
    #print(final)
    file_output = []
    for ins in final:
        if isinstance(ins, str):
            if ins not in labels:
                print("Label %s has not been defined" % (ins))
                return

            ins = labels[ins]
            file_output.append('%02x' % (ins >> 4*2))
            file_output.append('%02x' % (ins & 0xFF))
        else:
            file_output.append('%02x' % ins)
    #print(file_output)

    if output_file is None:
        output_file = open(pathlib.Path(input_file.name).stem+'.o','w')

    output_file.write("v2.0 raw\n")
    output_file.write(' '.join(file_output))
    output_file.write("\n")
    output_file.close()

    print("Successfully compiled")
    print("File written to %s" % output_file.name)

parser = argparse.ArgumentParser(description='Process some integers.')
parser.add_argument('input', 
                    type=argparse.FileType('r'), 
                    help='The assembly file to compile to machine level code')
parser.add_argument('--output', '-o',
                    type=argparse.FileType('w'),
                    help='The machine level filename to write')
import sys
if len(sys.argv) > 1:
    args = parser.parse_args()
    input_file = args.input
    output_file = args.output
else:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()

    filename = filedialog.askopenfilename()
    input_file = open(filename, 'r')
    output_file = None

parse(input_file, output_file)
