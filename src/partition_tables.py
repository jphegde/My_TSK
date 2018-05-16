import struct
import uuid

def get_details(partition_details, partition_num):
    partition_type = hex(partition_details[4])
    start = partition_details[8:12]
    end = partition_details[12:16]
    
    start_offset = struct.unpack('<I', start)[0]
    end_offset = struct.unpack('<I', end)[0] + start_offset -1
    
    if start_offset <= 0 or end_offset <= start_offset:
        return None
    
    dictionary = {'type': partition_type, 'end': end_offset, 'start': start_offset, 'number': partition_num }
    
    return dictionary

def parse_mbr(mbr_bytes):
    #print(mbr_bytes, mbr_bytes[-1])
    end_bytes = mbr_bytes[-2:]

    if end_bytes[0] != 0x55 and end_bytes[1] != 0xaa:
        return []
    
    partition_table = mbr_bytes[-66:-2]
    
    #print(partition_table)
    i = 0
    res = []
    
    for j in range(1, 5):
        partition_details = partition_table[i:16*j]
        details = get_details(partition_details, j-1)
        if details != None:
            res.append(details)
            
        i += 16
    
    return res

def get_gpt_details(partition_details, partition_num):
    partition_type = partition_details[0:16]
    #print('partition type:', partition_type)
    #partition_type = partition_type.decode('utf-8')
    partition_type = uuid.UUID(bytes_le = partition_type)
    
    start = partition_details[32:40]
    end = partition_details[40:48]
    
    start_offset = struct.unpack('<Q', start)[0]
    end_offset = struct.unpack('<Q', end)[0]
    #print('start offset', start_offset)
    #print('***', struct.unpack('<Q', end)[0])
    #print('end offset', end_offset)
    if start_offset <= 0 or end_offset <= start_offset:
        return None
    
    partition_name = partition_details[56:]
    
    p_name = partition_name.decode('utf-16-le')       
    #print('partition name1:', p_name)
    
    name = ''
    
    for c in p_name:
        if ord(c) == 0x00:
            break
        
        name += c
    
    dictionary = {'start': start_offset, 'end': end_offset, 'number': partition_num, 'name': name,
                               'type': partition_type}
    
    return dictionary


def parse_gpt(gpt_file, sector_size=512):
    mbr_bytes = gpt_file.read(sector_size)
    end_bytes = mbr_bytes[-2:]

    if end_bytes[0] != 0x55 and end_bytes[1] != 0xaa:
        return []
    
    lba1 = gpt_file.read(sector_size)
    flag = 0
    
    signature = lba1[:8]
    #signature = signature[::-1]
    signature = signature.decode('utf-8')
    #print(signature)
    if signature != 'EFI PART':
        return []
    num_partitions = struct.unpack('<I', lba1[80:84])[0]
    #num_partitions2 = struct.unpack('>I', lba1[80:84])[0]
    #print(num_partitions1, num_partitions2)
    #print(signature)
    
    entry_size = 128
    entry_table_size = num_partitions * entry_size
    
    entry_table = gpt_file.read(entry_table_size)
    
    res = []
    p_num = 0
    for i in range(0, 128):
        entry = entry_table[i*128 : i*128 + 128]
        details = get_gpt_details(entry, p_num)
        
        if details != None:
            res.append(details)
            p_num += 1
    #print(res)
    return res