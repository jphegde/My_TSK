import struct

def parse_boot_block(fat_contents, offset):
    #print(fat_contents)
    res = []
    info = dict()
    boot_sector = 0
    oem = fat_contents[3:0x0b].decode('utf-8')
    #print(oem)
    info['oem'] = oem
    
    sector_size = struct.unpack('H', fat_contents[0x0b:0x0d])[0]
    info['sectorsize'] = sector_size
    
    blocks_per_cluster = fat_contents[0x0d]
    info['blocks_per_cluster'] = blocks_per_cluster
    
    n_reserved_blocks = struct.unpack('H', fat_contents[0x0e:0x10])[0]
    info['n_reserved_blocks'] = n_reserved_blocks
    
    num_of_fats = fat_contents[0x10]
    #print('No of fats', int(num_of_fats))
    num_root_dir_entries = struct.unpack('H', fat_contents[0x11:0x13])[0]
    info['n_fats'] = num_of_fats
    info['n_dir_entries'] = num_root_dir_entries
    
    num_blocks_per_fat = struct.unpack('H', fat_contents[0x16:0x18])[0]
    info['blocks_per_fat'] = num_blocks_per_fat
    
    total_num_of_blocks = struct.unpack('I', fat_contents[0x20:0x24])[0] + struct.unpack('H', fat_contents[0x13:0x15])[0] 
    #print('total no of blocks', total_num_of_blocks)
    info['total_blocks'] = total_num_of_blocks
    
    volume_id = struct.unpack('I', fat_contents[0x27:0x2b])[0]
    #print('vol id', hex(volume_id))
    info['vol_id'] = hex(volume_id)
    
    volume_label1 = fat_contents[0x2b:0x36].decode('utf-8')
    #print('vol label', volume_label1)
    info['vol_label1'] = volume_label1
    
    fs_id = fat_contents[0x36:0x3e].decode('utf-8')
    #print('fs id', fs_id)
    info['fs_id'] = fs_id
    
    fat0_start = boot_sector + 1
    fat0_end = boot_sector + num_blocks_per_fat
    fat1_start = fat0_end + 1
    fat1_end = fat0_end + num_blocks_per_fat
    
    root_dir_start = fat1_end + 1
    root_dir_end = int((num_root_dir_entries*32)/sector_size) + fat1_end
    
    cluster_range = int((total_num_of_blocks - (root_dir_end +1))/2)
    
    first_cluster_sector = info['n_reserved_blocks'] + info['blocks_per_fat']*info['n_fats'] + int((info['n_dir_entries']*32)/ sector_size)
    cluster_fit = ((total_num_of_blocks-1) - first_cluster_sector + 1)//blocks_per_cluster
    clustered_range = first_cluster_sector + 2*cluster_fit
    non_clustered = total_num_of_blocks - clustered_range
    
    res.append('OEM Name: '+oem+'\n')
    res.append('Volume ID: '+hex(volume_id)+'\n')
    res.append('Volume Label (Boot Sector): '+volume_label1+'\n')
    res.append('File System Type Label: '+fs_id+'\n')
    res.append('\n')
    res.append('Sectors before file system: '+str(offset)+'\n')
    res.append('\n')
    res.append('File System Layout (in sectors)\n')
    res.append('Total Range: 0 - '+str(total_num_of_blocks-1)+'\n')
    res.append('* Reserved: 0 - '+str(n_reserved_blocks-1)+'\n')
    res.append('** Boot Sector: '+str(boot_sector)+'\n')
    res.append('* FAT 0: '+str(fat0_start)+' - '+str(fat0_end)+'\n')
    res.append('* FAT 1: '+str(fat1_start)+' - '+str(fat1_end)+'\n')
    res.append('* Data Area: '+str(fat1_end+1)+' - '+str(total_num_of_blocks-1)+'\n')
    res.append('** Root Directory: '+str(root_dir_start)+' - '+str(root_dir_end)+'\n')
    res.append('** Cluster Area: '+str(root_dir_end + 1)+' - '+str(clustered_range-1)+'\n')
    if non_clustered > 0:
        res.append('** Non-clustered: '+str(clustered_range)+' - '+str(total_num_of_blocks-1)+'\n')
    res.append('\n')
    res.append('CONTENT INFORMATION')
    res.append('--------------------------------------------')
    res.append('Sector Size: '+str(sector_size))
    res.append('Cluster Size: '+str(blocks_per_cluster*sector_size))
    res.append('Total Cluster Range: 2 - '+str(cluster_range+1))
    res.append('\n')
    res.append('FAT CONTENTS (in sectors)')
    res.append('--------------------------------------------')
    
    return res, info

def get_fat_info(fat, sector_size, n_fats, blocks_per_fat, blocks_per_cluster, first_cluster_sector):
    i = 0
    size = len(fat)
    print(size)
    cluster_num = 2
    cluster_list = dict()
    
    while i < size:
        #print(i, i+2, fat[i:i+2])
        next_cluster = struct.unpack('<H', fat[i:i+2])[0]
        #print(i, cluster_num, next_cluster)
        i += 2
        temp = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1
        if temp == 6181:
            print('$$$$$$$$$$$',next_cluster)
        
        if next_cluster != 0:
            #print((cluster_num - 2) * blocks_per_cluster + first_cluster_sector, (next_cluster - 2) * blocks_per_cluster + first_cluster_sector)
            if temp == 6183:
                    print('$$$$$$$$$$$',next_cluster)
            if 0xffff <= next_cluster:
                cluster_list[cluster_num] = -1
                #print(i, cluster_num, next_cluster)
            else:
                cluster_list[cluster_num] = next_cluster
                if temp == 6183:
                    print('$$$$$$$$$$$',next_cluster)
                #print(i, (cluster_num - 2) * blocks_per_cluster + first_cluster_sector, (next_cluster - 2) * blocks_per_cluster + first_cluster_sector)
            
        cluster_num += 1
    
    
    start = 0
    start_sec = 0
    end_sec = 0
    res_list = []
    for cluster_num in sorted(cluster_list.keys()):
        next_cluster = cluster_list[cluster_num]
        #print(cluster_num, (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1, (cluster_list[cluster_num] - 2) * blocks_per_cluster + first_cluster_sector +1)
        temp = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1
        if temp == 6183:
            print('$$$$$$$$$$$',next_cluster)
        if start == 0:
            start = cluster_num
            
            #print('*******start ', (start - 2) * blocks_per_cluster + first_cluster_sector)
            
        if next_cluster == -1:
            start_sec = (start - 2) * blocks_per_cluster + first_cluster_sector
            end_sec = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1
            start = 0
            #print('&&&&&',start, start_sec, end_sec, '&&&&&&&&&') 
            res_list.append((start_sec, end_sec, end_sec-start_sec+1, 0))
            
        if (next_cluster - cluster_num) > 1:
            start_sec = (start - 2) * blocks_per_cluster + first_cluster_sector
            end_sec = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1
            start = 0
            next_cluster_sec = (next_cluster - 2) * blocks_per_cluster + first_cluster_sector
            res_list.append((start_sec, end_sec, end_sec-start_sec+1, next_cluster_sec))
            
        sec1 = (cluster_num - 2) * blocks_per_cluster + first_cluster_sector +1 
        sec2 = (cluster_list[cluster_num] - 2) * blocks_per_cluster + first_cluster_sector +1     
        #print('================= cluster num =====', sec1, sec2)

    """for r in res_list:
        print(r)"""
    
    
    return res_list


    

def fsstat_fat16(fat16_file, sector_size=512, offset=0):
    result = ['FILE SYSTEM INFORMATION',
              '--------------------------------------------',
              'File System Type: FAT16',
              '']
    fat_contents = fat16_file.read()
    # then do a few things, .append()ing to result as needed
    
    #fat_contents, offset = get_boot_sector(fat_contents)
    fat_contents = fat_contents[offset*sector_size:]
    sector_size = struct.unpack('H', fat_contents[0x0b:0x0d])[0]
    boot_res, info = parse_boot_block(fat_contents[:sector_size], offset)
    #result += boot_res
        
    n_fats = info['n_fats']
    blocks_per_fat = info['blocks_per_fat']
    fat_tables = fat_contents[info['n_reserved_blocks']*sector_size : sector_size *blocks_per_fat]
        
    first_cluster_sector = info['n_reserved_blocks'] + info['blocks_per_fat']*info['n_fats'] + int((info['n_dir_entries']*32)/ sector_size)
    print('First cluster sector', first_cluster_sector)
    fat_info = get_fat_info(fat_tables[4:], sector_size, n_fats, blocks_per_fat, info['blocks_per_cluster'], first_cluster_sector) 

    
    for i in fat_info:
        s, t, n, end = i
        if end == 0:
            boot_res.append(str(s)+'-'+str(t)+' ('+str(n)+') -> EOF')
        else:
            boot_res.append(str(s)+'-'+str(t)+' ('+str(n)+') -> '+str(end))
        
    result += boot_res
    #print(result)
    return result