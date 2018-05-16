import argparse

def print_strings(f, encoding, min_len, x):
    #print(min_len)
    char = ''
    res = ''
    num = min_len
    if min_len%2 == 1:
        num += 1
    i = 0
    while True:
        inp = ''
        if encoding == 's':
            try:
                inp = f.read(1)#.decode('utf-8', 'ignore')#chr(f.read(1)[0])
                #print('****',inp, len(inp))
            except:
                print('exception')
                if len(res) >= min_len:
                    print(res)
                res = ''
                i += 1
                #f.seek(i)
                continue
        
        elif encoding == 'l':
            try:
                inp = f.read(1)#.decode('utf-8', 'ignore')#chr(f.read(1)[0])
                #print('****',inp, len(inp))
            except:
                if len(res) >= min_len:
                    print(res)
                res = ''
                #continue
        
        elif encoding == 'b':
            try:
                inp = f.read(1)#.decode('utf-8', 'ignore')#chr(f.read(1)[0])
                #print('****',inp, len(inp))
            except:
                if len(res) >= min_len:
                    print(res)
                res = ''
                #continue
            
        if not inp:
            if len(res) >= min_len:
                    print(res)
            break
        #print('inp',inp)
        dum = ''
        for c in inp:
            #print(c)
            dum += c
            if x == 1 and (0x0020 <= ord(c) <= 0x007f or 0x00A1 <= ord(c) <= 0xD7FF):
                res += c
            
            elif x == 0 and 0x0020 <= ord(c) <= 0x007f:
                res += c
            
            else:
                #print('***', c)
                if len(res) >= min_len:
                    print(res)
                res = ''
                
def main():
    parser = argparse.ArgumentParser(description='Print the printable strings from a file.')
    parser.add_argument('filename')
    parser.add_argument('-n', metavar='min-len', type=int, default=4,
                        help='Print sequences of characters that are at least min-len characters long')
    parser.add_argument('-e', metavar='encoding', choices=('s', 'l', 'b'), default='s',
                        help='Select the character encoding of the strings that are to be found. ' +
                             'Possible values for encoding are: s = UTF-8, b = big-endian UTF-16, ' +
                             'l = little endian UTF-16.')
    parser.add_argument('-x', action='store_true', help='Print sequences of printable Unicode in the assigned Basic Multilingual Plane.')
    
    args = parser.parse_args()
    
    x = 0
    
    if args.x:
        x = 1

    if args.e == 's':
        with open(args.filename, 'r', encoding ='utf-8', errors='ignore') as f:
            print_strings(f, args.e, args.n, x)
            
    if args.e == 'l':
        with open(args.filename, 'r', encoding ='utf-16-le', errors='ignore') as f:
            print_strings(f, args.e, args.n, x)
            
    if args.e == 'b':
        with open(args.filename, 'r', encoding ='utf-16-be', errors='ignore') as f:
            print_strings(f, args.e, args.n, x)

            
if __name__ == '__main__':
    main()