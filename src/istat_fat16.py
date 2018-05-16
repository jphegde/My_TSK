import struct
import math

def parse_boot_block(fat_contents):
    #print(fat_contents)
    res = []
    info = dict()
    boot_sector = 0
    
    sector_size = struct.unpack('H', fat_contents[0x0b:0x0d])[0]
    info['sectorsize'] = sector_size
    
    blocks_per_cluster = fat_contents[0x0d]
    info['blocks_per_cluster'] = blocks_per_cluster
    
    n_reserved_blocks = struct.unpack('H', fat_contents[0x0e:0x10])[0]
    info['n_reserved_blocks'] = n_reserved_blocks
    
    num_of_fats = fat_contents[0x10]
    num_root_dir_entries = struct.unpack('H', fat_contents[0x11:0x13])[0]
    info['n_fats'] = num_of_fats
    info['n_dir_entries'] = num_root_dir_entries
    
    num_blocks_per_fat = struct.unpack('H', fat_contents[0x16:0x18])[0]
    info['blocks_per_fat'] = num_blocks_per_fat
    
    total_num_of_blocks = struct.unpack('I', fat_contents[0x20:0x24])[0] + struct.unpack('H', fat_contents[0x13:0x15])[0] 
    info['total_blocks'] = total_num_of_blocks
    
    """fat0_start = boot_sector*sector_size
    fat0_end = boot_sector*sector_size + num_blocks_per_fat*sector_size
    fat1_start = fat0_end
    fat1_end = fat0_end + num_blocks_per_fat*sector_size"""
    
    root_dir_start = sector_size + num_of_fats * num_blocks_per_fat * sector_size
    root_dir_end = root_dir_start  + num_root_dir_entries*32 
    #print('@@@@',root_dir_start, root_dir_end)
    
    info['root_dir_start'] = root_dir_start
    info['root_dir_end'] = root_dir_end
    
    cluster_range = int((total_num_of_blocks - (root_dir_end +1))/2)
    
    first_cluster_sector = info['n_reserved_blocks'] + info['blocks_per_fat']*info['n_fats'] + int((info['n_dir_entries']*32)/ sector_size)
    info['first_cluster_sector'] = first_cluster_sector
    
    return info

def as_unsigned(bs, endian='<'):
    unsigned_format = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}
    if len(bs) <= 0 or len(bs) > 8:
        raise ValueError()
    fill = '\x00'
    while len(bs) not in unsigned_format:
        bs = bs + fill
    result = struct.unpack(endian + unsigned_format[len(bs)], bs)[0]
    return result


def decode_fat_time(time_bytes, tenths=0, tz='EDT'):
    v = as_unsigned(time_bytes)
    second = int(int(0x1F & v) * 2)
    if tenths > 100:
        second += 1
    minute = (0x7E0 & v) >> 5
    hour = (0xF800 & v) >> 11
    return '{:02}:{:02}:{:02} ({})'.format(hour, minute, second, tz)


def decode_fat_day(date_bytes):
    v = as_unsigned(date_bytes)
    day = 0x1F & v
    month = (0x1E0 & v) >> 5
    year = ((0xFE00 & v) >> 9) + 1980
    return '{}-{:02}-{:02}'.format(year, month, day)

def get_dir_cluster_run(cluster_tables, sector_size, n_fats, blocks_per_fat, blocks_per_cluster, starting_cluster, first_cluster_sector, allocation_status):
    cluster_num = starting_cluster
    sectors = []
    counter = 0
    #print('starting cluster',starting_cluster, file_sectors)
    cluster_chain = dict()
    
    while True:
        index = (cluster_num - 2)*2
        sec1 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector
        sec2 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector + 1
        
        next_cluster = as_unsigned(cluster_tables[index : index + 2])
        #print('next_cluster bytes', next_cluster)   
        if allocation_status == 'Allocated':
            #print('########', sec1, sec2, next_cluster)
            sectors.append(sec1)
            sectors.append(sec2)

            
            if next_cluster in cluster_chain:
                cluster_chain[cluster_num] = next_cluster
                cluster_num += 1
            
            
            else:
                if next_cluster == 0xffff:
                    break
            
                elif next_cluster == 0x0000:
                    if cluster_num not in cluster_chain:
                        cluster_chain[cluster_num] = cluster_num + 2#next_cluster
                    
                    cluster_num += 2
                
                else:
                    if cluster_num not in cluster_chain:
                        cluster_chain[cluster_num] = next_cluster
                        cluster_num = next_cluster
                    
                    else:
                        cluster_num += 1
            
            counter += 2
        
        
        
        else:
            sec1 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector
            sec2 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector + 1
            
            if next_cluster != 0x0000 and next_cluster != 0xffff:
                cluster_num += 1
                continue
            sectors.append(sec1)
            sectors.append(sec2)
            cluster_num += 1
            counter += 2
            
    res = []
    line = ''
    dir_size = sector_size*len(sectors)
    for i in range(0, len(sectors)):
        #print(sectors[i])
        if i%8 == 0:
            res.append(line+'\n')
            line = str(sectors[i])+ ' '
        else:
            line += str(sectors[i]) + ' '
    
    res.append(line+'\n')
    
    return res, dir_size


def get_cluster_run(cluster_tables, sector_size, n_fats, blocks_per_fat, blocks_per_cluster, starting_cluster, first_cluster_sector, file_sectors, allocation_status, filetype):
    cluster_num = starting_cluster
    sectors = []
    counter = 0
    #print('starting cluster',starting_cluster, file_sectors)
    cluster_chain = dict()
    
    while counter < file_sectors:
        index = (cluster_num - 2)*2
        sec1 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector
        sec2 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector + 1
        
        next_cluster = as_unsigned(cluster_tables[index : index + 2])
        #print('next_cluster bytes', next_cluster)   
        if allocation_status == 'Allocated':
            sectors.append(sec1)
            sectors.append(sec2)

            
            if next_cluster == 0xffff:
                #print('***sec2', sec2)
                break

                    
            else:
                cluster_num += 1
            
            counter += 2
        
        
        
        else:
            sec1 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector
            sec2 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector + 1
            
            if next_cluster != 0x0000 and next_cluster != 0xffff:
                cluster_num += 1
                continue
            sectors.append(sec1)
            sectors.append(sec2)
            cluster_num += 1
            counter += 2
            
    res = []
    line = ''
    for i in range(0, len(sectors)):
        #print(sectors[i])
        if i%8 == 0:
            res.append(line+'\n')
            line = str(sectors[i])+ ' '
        else:
            line += str(sectors[i]) + ' '
    
    res.append(line+'\n')
    
    return res

def get_direntry_data(f, metadata_address, info):
    sector_size = info['sectorsize']
    cluster_size = info['blocks_per_cluster']
    root_dir_start = info['root_dir_start']
    root_dir_end = info['root_dir_end']
    last_direntry_address = 2 + info['n_dir_entries']
    
    dir_info = dict()
    filetypes = dict({0x01: 'Read Only', 0x02: 'Hidden', 0x04: 'System', 0x08: 'Volume Label', 0x10: 'Directory', 0x20: 'Archive'})
    
    #print('metadata address', metadata_address)
    
    if metadata_address <= last_direntry_address:
        direntry_address = root_dir_start + (metadata_address - 3)*32
        print(direntry_address)
        direntry = f[direntry_address:direntry_address +32]
        
    else:
        offset = (metadata_address - 515) * 32
        #print('offset ', offset)
        direntry_address = root_dir_end + offset
        print(direntry_address, (info['n_dir_entries']*32 + root_dir_start+offset))
        direntry = f[direntry_address:direntry_address +32]
    
    #print(direntry[:0x0b])
    filename = ''
    if direntry[0] == 0xe5:
        dir_info['allocation_status'] = 'Not Allocated'
        filename = direntry[1:0x0b].decode('utf-8')
        
    else:
        dir_info['allocation_status'] = 'Allocated'
        filename = direntry[0:0x0b].decode('utf-8')
    
    elems = filename.split()
    
    if len(elems) > 1:
        filename = '.'.join(elems)
    #print(filename)
    dir_info['filename'] = 'Name: '+filename
    
    filetype = direntry[0x0b]
    type1 = filetype&0x0f
    type2 = filetype&0xf0
    fileattrib = ''
    
    if filetype == 0x0f:
        n_lfns = 0x0f&direntry[0]
        total = f[direntry_address:direntry_address +32*(n_lfns + 1)]
        lfns = f[direntry_address:direntry_address +32*n_lfns]
        direntry = f[direntry_address +32*n_lfns: direntry_address +32*n_lfns + 32]
        filename = ''
        
        for i in range(0, n_lfns):
            lfn = lfns[i*32:i*32 + 32]
            temp_name = lfn[1:0x0b].decode('utf-8') + lfn[0x0e:0x1a].decode('utf-8') + direntry[0x1b:].decode('utf-8')
            filename = filename + temp_name
            
        if direntry[0] == 0xe5:
            dir_info['allocation_status'] = 'Not Allocated'
            #filename = direntry[1:0x0b].decode('utf-8')
        
        else:
            dir_info['allocation_status'] = 'Allocated'
            #filename = direntry[0:0x0b].decode('utf-8')
        
    
    if filetype == 0x10:
        fileattrib = 'Directory'
    
    else:
        filetype_str = ''
        if type1 != 0:
            filetype_str += filetypes[type1]
        filetype_str += ', '+ filetypes[type2]
        fileattrib = 'File'
        fileattrib += ', '+filetype_str
        #if filetype_str == 'Archive':
            #fileattrib += ', '+filetype_str
        
    fileattrib = 'File Attributes: '+fileattrib  
    dir_info['file_attrib'] = fileattrib
    
    created_date = decode_fat_day(direntry[0x10:0x12])
    created_time = decode_fat_time(direntry[0x0e:0x10])
    
    accessed_time = decode_fat_time(direntry[0x14:0x16])
    accessed_date = decode_fat_day(direntry[0x12:0x14])
    
    written_time = decode_fat_time(direntry[0x16:0x18])
    written_date = decode_fat_day(direntry[0x18:0x1a])
    
    dir_info['written'] = 'Written:\t'+written_date+' '+written_time
    dir_info['accessed'] = 'Accessed:\t'+accessed_date+' '+accessed_time
    dir_info['created'] = 'Created:\t'+created_date+' '+created_time
    
    starting_cluster = as_unsigned(direntry[0x1a:0x1c])
    file_size = as_unsigned(direntry[0x1c:0x20])
    
    file_sectors = math.ceil(file_size/sector_size)
    
    cluster_tables = f[sector_size : sector_size *info['blocks_per_fat']]
    #cluster_tables = f[info['first_cluster_sector']*sector_size:]    
    #print('starting cluster: ',starting_cluster,'\n', 'file size: ', file_size)
    
    sectors = []
    
    if filetype == 0x10:
        sectors, dirsize = get_dir_cluster_run(cluster_tables, sector_size, info['n_fats'], info['blocks_per_fat'], info['blocks_per_cluster'], starting_cluster, info['first_cluster_sector'], dir_info['allocation_status'])
        file_size = dirsize
    
    else:
        sectors = get_cluster_run(cluster_tables, sector_size, info['n_fats'], info['blocks_per_fat'], info['blocks_per_cluster'], starting_cluster, info['first_cluster_sector'], file_sectors, dir_info['allocation_status'], fileattrib)
    
    dir_info['filesize'] = 'Size: '+str(file_size)
    
    
    #print('cluster 5 :',cluster_tables[10:12])
    
    return dir_info, sectors

def istat_fat16(f, address, sector_size=512, offset=0):
    fat_contents = f.read()
    fat_contents = fat_contents[offset*sector_size:]
    boot_info = parse_boot_block(fat_contents)
    sector_size = boot_info['sectorsize']
    print('\n\n\n')
    dir_res, sectors = get_direntry_data(fat_contents, address, boot_info)
    
    res = []
    
    res.append('Directory Entry: '+str(address)+'\n')
    res.append(dir_res['allocation_status']+'\n')
    res.append(dir_res['file_attrib']+'\n')
    res.append(dir_res['filesize']+'\n')
    res.append(dir_res['filename']+'\n')
    res.append('\n')
    res.append('Directory Entry Times:\n')
    res.append(dir_res['written']+'\n')
    res.append(dir_res['accessed']+'\n')
    res.append(dir_res['created']+'\n')
    res.append('\n')
    res.append('Sectors:\n')
    res += sectors
    """for line in sectors:
        print(line)"""
    
    return res
    

if __name__ == '__main__':
    # The code below just exercises the time/date decoder and need not be included
    # in your final submission!
    #
    # values below are from the directory entry in adams.dd that corresponds to the
    # creation date/time of the `IMAGES` directory in the root directory, at
    # metadata address 5; it starts at offset 0x5240 from the start of the image
    print(decode_fat_day(bytes.fromhex('E138')), decode_fat_time(bytes.fromhex('C479'), 0))