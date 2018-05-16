import sys

def print_hex(f):
    byte_offset = 0
    perusal_output = []
    hex_output = []
    
    while True:
        input_bytes = f.read(16)
        
        if not input_bytes:
            break
        
        perusal_line = '|'
        hex_line = ' '*2
        byte_counter = 0
        
        for byte in input_bytes:
            #print(byte)
            ascii_val = byte
            #print(hex(ascii_val))
            hex_val = hex(ascii_val)[2:].zfill(2)
            #print(hex_val)
            hex_line = hex_line + str(hex_val)+' '
            
            if 0x20 <= int('0x'+ hex_val, 16) <= 0x7e:
                perusal_line = perusal_line + chr(byte)
                
            else:
                perusal_line = perusal_line + '.'
            
            if byte_counter == 7:
                hex_line = hex_line +' '
                
            byte_counter = byte_counter + 1
                
        perusal_line = perusal_line + '|'
        #print('*** ',byte_counter)
        if byte_counter < 8:
            hex_line = hex_line + ' '*(26+ (8 - byte_counter)*3)
        elif byte_counter < 16:
            hex_line = hex_line + ' '*(1 + (16 - byte_counter)*3)
            
        else:
            hex_line = hex_line + ' '
            
        perusal_output.append(perusal_line)
        hex_output.append(hex_line)
    
    if hex_output:
        for i in range(len(hex_output)):
            print('%08x'%(byte_offset)+hex_output[i]+perusal_output[i])
            byte_offset = byte_offset + (len(perusal_output[i]) - 2)
            
        print('%08x'%(byte_offset))

if __name__=="__main__":
    filename = sys.argv[1]
    with open(filename, 'rb') as f_ptr:
        print_hex(f_ptr)
