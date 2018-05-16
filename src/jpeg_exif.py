import tags
import struct

class ExifParseError(Exception):
    def init(__self__):
        pass


def carve(f, start, end):
    # return the bytes

    # here is an example that just returns the entire range of bytes:
    
    num_bytes = end - start +1
    
    f.seek(start)
    return f.read(num_bytes)


def purge_jfif_list(chunk, pairs):
    size = len(chunk)
    res = []
    #print('PAIRS\n\n',pairs, '\n\n')
    for pair in pairs:
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&& ', pair)
        start, end = pair
        #print('START  ', chunk[start:start+10])
        #print('END chunk  ', chunk[end-10:end+1])
        state = 1
        i = start+2
        while i < end:
            tag = chunk[i : i + 2]
            
            if tag[0] == 0xff and (tag[1] != 0xff or tag[1] != 0x00 or tag[1] != 0xd8) and state == 1:
                #print('******SEG TAGS*****',tag)
                seg_size = struct.unpack('>H', chunk[i + 2: i + 4])[0]
                i += (seg_size + 2)
            
                if tag[0] == 0xff and tag[1] == 0xda and state == 1:
                    print(i, end)
                    if i+3 == end:
                        print('********',i, end,'**************')
                        state = 2
                    break
                
            else:
                #print('!!!!!!!!!!!!!!!!!', tag, end, i)
                state = 0
                break
                
            
        #print('STATE  ', state, 'END  ', chunk[i:i+2])    
        if state == 2:
            print('%%%%%%%%%%%%%%%%%%%', pair)
            res.append(pair)
            
            
    #print('RES\n\n',res, '\n\n')    
    return sorted(res)
            


def find_jfif(f, max_length=None, parse=False):
    # do some stuff
    # then return a possibly-empty sequence of pairs
    # here's an example that just returns the start and end of the file without parsing
    soi_list = []
    eoi_list = []
    
    i = 0
    chunk = f.read()
    size = len(chunk)
    while i < size:
        c = chunk[i:i+2]
        
        if c[0] == 0xff and c[1] == 0xd8:
            soi_list.append(i)
            i += 2
            
        elif c[0] == 0xff and c[1] == 0xd9:
            eoi_list.append(i)
            i += 2
            
        else:
            i += 1
            
        
    
    pairs = []
    for i in soi_list:
        for j in eoi_list:
            if i < j:
                if max_length != None:
                    if ((j+1)-i)+1 > max_length:
                        continue
                pairs.append((i, j+1))
                #print('(',i,',',j+1,')')
                
    if parse == True:
        pairs = purge_jfif_list(chunk, pairs)
        
    #print(pairs)
    return pairs


def get_data(data_content, total_size, data_type, data_format, num_comp):
    
    if data_type == 1:
        return struct.unpack(data_format+'B', data_content[0:1])[0]
    
    elif data_type == 2:
        return bytes.decode(data_content[0:-1])
    
    elif data_type == 3:
        #print(data_content)
        l = list()
        j = 0
        if num_comp > 1:
            for i in range(0, num_comp):
                num = struct.unpack(data_format+'H', data_content[j:j+2])[0]
                l.append(num)
                j += 2
            return l
        
        val = struct.unpack(data_format+'H', data_content[j:j+2])
        #print('VAL', val)
        return val[0]
    
    elif data_type == 4:
        return struct.unpack(data_format+'L', data_content[0:4])[0]
                    
    elif data_type == 5:
        (numerator, denominator) = struct.unpack(data_format+'LL', data_content[0:8]) 
        return str(numerator)+'/'+str( denominator)
                    
    elif data_type == 7:
        val = struct.unpack(data_format+'%dB' % total_size, data_content)
        return "".join("%.2x" % x for x in val)

def parse_exif(f):
    # do it!

    # ...

    # Don't hardcode the answer! Return your computed dictionary.
    res = dict()
    image_bytes = f.read()
    flag = 0
    soi = image_bytes[0:2]
    
    big_endian = '>'
    little_endian = '<'
    data_format = None
    app_flag = 1
    data_sizes = {1:1, 2:1, 3:2, 4:4, 5:8, 7:1}
    
    if soi[0] == 0xff and soi[1] == 0xd8:
        app0 = image_bytes[2:4]
        #print('1')
        if app0[0] == 0xff and (0xe0 <= app0[1]<= 0xef) :
            if app0[1] == 0xe0:     
                app0_size = struct.unpack('>H', image_bytes[4:6])[0]
                #print('2')
                app1 = image_bytes[4 + app0_size:4 + app0_size + 2]
                app_flag = 0
            
            else:
                app0_size = -2
                app1 = image_bytes[2:4]
            
            if app1[0] == 0xff and (0xe0 <= app1[1]<= 0xef):#app1[1] == 0xe1:
                #print('3', app0_size)
                exif_bytes = image_bytes[4 + app0_size:]
                
                app1_size = struct.unpack('>H', exif_bytes[2:4])[0]
                
                exif_tag = exif_bytes[4:10]
                #print('EXif tag', exif_tag)
                endianness = exif_bytes[10:12]
                
                
                if endianness[0] == 0x4d and endianness[1] == 0x4d:
                    data_format = big_endian
                    
                elif endianness[0] == 0x49 and endianness[1] == 0x49:
                    data_format = little_endian
                #print('ENDIANNESS', data_format)
                bom_bytes = exif_bytes[10:]
                #print(bom_bytes[0:30])
                ifd_begin = struct.unpack(data_format+'I', exif_bytes[14:18])[0]
                #print('IFD begin', ifd_begin)
                num_entries = struct.unpack(data_format+'H', bom_bytes[8:10])[0]
                #print('Num entries', num_entries)
                
                next_offset = 10
                
                
                while True:
                    i = 0
                
                    for entry in range(0, num_entries):
                        ifd_entry = bom_bytes[next_offset + i : next_offset + i + 12]
                        #print('IFD entry\n\n', ifd_entry, '\n\n', bom_bytes[next_offset + i*entry + 12: next_offset + i*entry + 16])
                        tag_num = struct.unpack(data_format+'H', ifd_entry[0:2])[0]
                        tag_name = None
                        #print('TAG NUM', tag_num)
                        if tag_num in tags.TAGS.keys():
                            tag_name = tags.TAGS[tag_num]
                            #print('TAG NAME', tag_name)
                        
                        else:
                            i += 12
                            continue
                    
                        data_type = struct.unpack(data_format+'H', ifd_entry[2:4])[0]
                        #print('DATA TYPE', data_type)
                        num_comp = struct.unpack(data_format+'I', ifd_entry[4:8])[0]
                        total_size = num_comp * data_sizes[data_type]
                    
                        #data = struct.unpack(data_format+'I', ifd_entry[8:12])[0]
                        data_content = None
                        data_offset = ifd_entry[8:12]
                    
                        if total_size > 4:
                            data_offset = struct.unpack(data_format+'I', ifd_entry[8:12])[0]
                            data_content =  bom_bytes[data_offset : data_offset + total_size]
                        else:
                            data_content = data_offset
                        
                        data_content = get_data(data_content, total_size, data_type, data_format, num_comp)
                        
                        data = data_content
                    
                        if tag_name not in res:
                            res[tag_name] = []
                    
                        res[tag_name].append(data)
                    
                        i += 12
                
                    #i -= 12
                    #print('i', i, 'entry', entry)
                    next_offset = struct.unpack(data_format+'I', bom_bytes[next_offset + i : next_offset + i + 4])[0]
                    
                    if next_offset == 0:
                        break
                    
                    #print('buffer', bom_bytes[next_offset:next_offset+2])
                    num_entries = struct.unpack(data_format+'H', bom_bytes[next_offset:next_offset+2])[0]
                    next_offset += 2
                
                flag = 1
                    
    if flag == 0:
        raise Exception()
                        
    #print('RES\n', res)
    
    return res#{'Make':['Apple']}