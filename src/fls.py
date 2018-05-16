import datetime
import struct


attrib_types = {0x10:'$STANDARD_INFORMATION', 0x30:'$FILE_NAME', 0x80:'$DATA',  0xa0: '$INDEX_ALLOCATION', 0x90: '$INDEX_ROOT'}#, 0xb0: '$BITMAP'}

def as_signed_le(bs):
    if len(bs) <= 0 or len(bs) > 8:
        raise ValueError()

    signed_format = {1: 'b', 2: 'h', 4: 'l', 8: 'q'}

    fill = b'\xFF' if ((bs[-1] & 0x80) >> 7) == 1 else b'\x00'

    while len(bs) not in signed_format:
        bs = bs + fill

    return struct.unpack('<' + signed_format[len(bs)], bs)[0]

def get_runlist(runlist_arr, start_cluster, end_cluster):
    #print('$DATA')
    res = []
    i = 0
    runoffset = 0
    while True:
        header = runlist_arr[i]
        i += 1
        if header == 0:
            #print('runlist end')
            break
            
        ms_nibble = header>>4
        ls_nibble = (header & 0x0f)
        
        #print('ms_nibble', ms_nibble, 'ls_nibble', ls_nibble)
        
        runlength = as_signed_le(runlist_arr[i : i+ls_nibble])
        i += ls_nibble
        runoffset += as_signed_le(runlist_arr[i : i+ms_nibble])
        i += ms_nibble
        
        
        #print('runlength', runlength, 'runoffset', runoffset, '\n')
        cluster_run = list(range(runoffset, runoffset + runlength))
        #print('Cluster run ...')
        #print(cluster_run)
        
        res = res + cluster_run
    
    cluster_run = []
    
    line = ''
    for i in range(0, len(res)):
        #print(sectors[i])
        if i%8 == 0 and i != 0:
            cluster_run.append(line)#+'\n')
            line = str(res[i])+ ' '
        else:
            line += str(res[i]) + ' '
    
    cluster_run.append(line)
    return cluster_run

def parse_entry(content, content_len):
    res = content.decode(errors = 'ignore')
    #print('RES ', res)
    
    return res

def parse_entry_list(node_header, attrib_type, start, end, alloc_end, dir_flag, del_flag):
    #print('Parsing entrylist ...')
    list_iter = 0
    res = []
    
    #print(start, end, alloc_end)
    while list_iter < end:
        entry_details = node_header[list_iter : list_iter + 16]
        
        #print('Entry details\n', entry_details)
        if not entry_details:
            break
        mft_entry = as_signed_le(entry_details[0:6])
        #print('MFT entry corresponding to index entry: ', mft_entry, entry_details[0:8])
        entry_len = as_signed_le(entry_details[8:10])
        filename_attrib_len = as_signed_le(entry_details[10:12])
        flag = as_signed_le(entry_details[12:15])
        file_attrib = node_header[list_iter + 16 : list_iter + 16 + filename_attrib_len]
        #print('\n')
        
        if filename_attrib_len > 0:
            attrib_content, _ = parse_content(file_attrib, 0x30, 0, filename_attrib_len)
        
            #print('INDEX FILENAME CONTENT\n', attrib_content, '\n\n')
            attrib_content['MFT_num'] = mft_entry
            res.append(attrib_content)
        #child_vcn = as_signed_le(node_header[entry_len - 8 : entry_len])
        #print('My child vcn: ', child_vcn)
        if flag == 0x01:
            child_vcn = as_signed_le(node_header[entry_len - 8 : entry_len])
            #print('My child vcn: ', child_vcn)
            
        elif flag == 0x02:
            #print('list end flag: ', flag)
            break
            
        list_iter += entry_len#(16 + filename_attrib_len)

    return res
    

def parse_node_header(node_header):
    content = dict()
    
    index_entry_list_start = as_signed_le(node_header[0:4])
    index_entry_list_end = as_signed_le(node_header[4:8])
    index_entry_list_alloc_end = as_signed_le(node_header[8:12])
    
    content['index_entry_list_start'] = index_entry_list_start
    content['index_entry_list_end'] = index_entry_list_end
    content['index_entry_list_alloc_end'] = index_entry_list_alloc_end
    
    return content
    

def parse_index_root(attrib, attrib_type_id, content_offset, content_size):
    #print('In parse index root')
    attrib_in_index = as_signed_le(attrib[0:4])
    #print('Attribute type in index ', attrib_in_index)
    sorting_rule = as_signed_le(attrib[4:8])
    
    index_record_size = as_signed_le(attrib[8:12])
    index_record_clusters = attrib[12]
    
    node_header = attrib[16:]
    
    node_header_content = parse_node_header(node_header)
    
    entry_list_start = node_header_content['index_entry_list_start']
    entry_list_end = node_header_content['index_entry_list_end'] #+ entry_list_start
    entry_list_alloc_end = node_header_content['index_entry_list_alloc_end'] #+ entry_list_start
    
    del_file_flag = 1
    dir_flag = 1
    entry_list_content = []
    if attrib_in_index in attrib_types:
        entry_list_content = parse_entry_list(node_header[entry_list_start:], attrib_in_index, entry_list_start, entry_list_end, entry_list_alloc_end, dir_flag, del_file_flag)
    
    return entry_list_content, attrib_in_index
    

def parse_index_allocation(ntfs, runlist, index_size, sectors_per_cluster, sector_size, clusters_per_index, attrib_in_index):
    
    vcn = 0
    entry_list = []
    for i in range(0, len(runlist)):
        clusters = runlist[i].strip().split()
        
        for c in clusters:
            start_cluster = int(c)
            starting_address = start_cluster * sector_size * sectors_per_cluster
            index_alloc = ntfs[starting_address :]
            index_end = len(index_alloc)
            index_record_offset = 0
        
            while index_record_offset < index_end:
                index = index_alloc[index_record_offset : index_record_offset + index_size]
                attrib_data = index[0:24]
            
                sig = attrib_data[0:4].decode(errors='ignore')
            
                if sig != 'INDX':
                    break
                
                vcn = as_signed_le(attrib_data[16:24])
                #print('My vcn', vcn)
                node_header = index[24:]
                node_header_content = parse_node_header(node_header)
        
                entry_list_start = node_header_content['index_entry_list_start']
                entry_list_end = node_header_content['index_entry_list_end'] #+ entry_list_start
                entry_list_alloc_end = node_header_content['index_entry_list_alloc_end'] #+ entry_list_start
                #print('NODE HEADER DATA ', entry_list_start, entry_list_end, entry_list_alloc_end)
                del_file_flag = 1
                dir_flag = 1
                entry_list = parse_entry_list(node_header[entry_list_start:], attrib_in_index, entry_list_start, entry_list_end, entry_list_alloc_end, dir_flag, del_file_flag)
        
                #print('ENTRY LIST')
                #print(entry_list)
            
                index_record_offset += index_size
        
    return entry_list    
    

def parse_bitmap(attrib, attrib_type_id, content_offset, content_size):
    pass

def parse_content(attrib, attrib_type, content_offset, content_size):
    content = attrib[content_offset : content_offset + content_size]
    res = dict()
    #print(content[0 : 10])
    file_types = {0x0001: 'Read Only', 0x0002: 'Hidden', 0x0003: 'Directory', 0x0004: 'System', 0x0020: 'Archive', 0x0040: 'Device', 0x0080: '#Normal', 0x0100: 'Temporary', 0x0200: 'Sparse file ', 0x0400: 'Reparse point', 0x0800: 'Compressed', 0x1000: 'Offline', 0x2000: 'Content is not being indexed for faster searches', 0x4000: 'Encrypted'}
    attrib_in_index = 0
    
    if attrib_type == 0x10:
        #print('$STD_INFO')
        #creation_time = into_localtime_string(as_signed_le(content[0x0 : 0x8]))
        #modification_time = into_localtime_string(as_signed_le(content[0x8 : 0x10]))
        #mft_modified_time = into_localtime_string(as_signed_le(content[0x10 : 0x18]))
        #file_accessed_time = into_localtime_string(as_signed_le(content[0x18 : 0x20]))
        flags = as_signed_le(content[0x20 : 0x24])
        #print(creation_time, modification_time, content[0x30 : 0x34])
        owner_id_bytes = content[0x30 : 0x34]
        owner_id = 0
        if owner_id_bytes:
            owner_id = as_signed_le(owner_id_bytes)
            
        #filetype = file_types[flags]
        
        #res.append('$STANDARD_INFORMATION Attribute Values:')
        #res.append('Flags: '+filetype)
        #res.append('Owner ID: '+str(owner_id))
        #res.append('Created:	'+creation_time)
        #res.append('File Modified:	'+modification_time)
        #res.append('MFT Modified:	'+mft_modified_time)
        #res.append('Accessed:	'+file_accessed_time)
        
        
    elif attrib_type == 0x30:
        #print('$FILENAME')
        file_ref = content[0x0 : 0x8]
        seq_num = as_signed_le(content[0x6 : 0x8])
        mft_entry = as_signed_le(content[0x0 : 0x6])
        #print('Trying creation time', content[0x8 : 0x10])
        #creation_time = into_localtime_string(as_signed_le(content[0x8 : 0x10]))
        #modification_time = into_localtime_string(as_signed_le(content[0x10 : 0x18]))
        #print('MFT modified time: ', content[0x18 : 0x20])
        #mft_modified_time = into_localtime_string(as_signed_le(content[0x18 : 0x20]))
        #file_accessed_time = into_localtime_string(as_signed_le(content[0x20 : 0x28]))
        allocated_filesize = as_signed_le(content[0x28 : 0x30])
        real_filesize = as_signed_le(content[0x30 : 0x38])
        flags = as_signed_le(content[0x38 : 0x3c])
        filename_length = content[0x40]
        #print(filename_length, content_offset)
        filename_bytes = content[0x42 : 0x42 + filename_length*2]
        filename = filename_bytes.decode()
        filename = filename.replace('\0', '')
        
        filetype = ''
        #print('File flags: ', flags, content[0x38 : 0x3c])
        if flags == 0x03:
            filetype = 'Directory'
        
        #res.append('$FILE_NAME Attribute Values:')
        #res.append('Flags: '+filetype)
        res['Name'] = filename
        res['Parent MFT Entry'] = mft_entry
        #res['File Type'] = filetype
        #res.append('Created:	'+creation_time)
        #res.append('File Modified:	'+modification_time)
        #res.append('MFT Modified:	'+mft_modified_time)
        #res.append('Accessed:	'+file_accessed_time)
    
    elif attrib_type == 0x90:
        content, attrib_in_index = parse_index_root(content, attrib_type, content_offset, content_size)
        res['content'] = content
        
    return res, attrib_in_index

def parse_attrib(mft_entry, attrib_offset, attrib_length):
    res = []
    attrib = []
    attrib_str = ''
    
    
    std_ids = {'$STANDARD_INFORMATION': 16, '$FILE_NAME': 48, '$DATA': 128}#, 0x90: '$INDEX_ROOT'}
    attrib = mft_entry[attrib_offset : attrib_offset + attrib_length]
    
    attrib_type_id = as_signed_le(attrib[0 : 0x4])
    nonresident_flag = attrib[0x8]
    name_length = attrib[0x9]
    name_offset = attrib[0xa]
    flags = attrib[0xc : 0xe]
    
    attrib_in_index = 0
    
    #print('attrib id',attrib_type_id, 'name length', name_length)
    attr_name = ''
    if name_length == 0:
        attr_name = 'N/A'
        
    else:
        attr_name = attrib[name_offset : name_offset + name_length*2].decode()
        attr_name = attr_name.replace('\0', '')
    
    next_offset = 0
    
    """if attrib_type_id not in attrib_types:
        return res, '', []"""
    
    #attrib_type =  attrib_types[attrib_type_id]
    #attrib_str += 'Type: '+ attrib_type+' ('+ str(std_ids[attrib_type])+'-'+str(as_signed_le(attrib[0xe : 0x10]))+')   Name: '+attr_name
    runlists = []
    if nonresident_flag == 1 and attrib_type_id != 0x80:
        if attrib_type_id == 0xa0:
            #print('attrib type: ', attrib_type_id)
            start_cluster = as_signed_le(attrib[0x10 : 0x18])
            end_cluster = as_signed_le(attrib[0x18 : 0x20])
            runlist_offset = as_signed_le(attrib[0x20 : 0x22])
        
            runlist = get_runlist(mft_entry[attrib_offset + runlist_offset :], start_cluster, end_cluster)
       
            if runlist:
                runlists = runlists + runlist
            
            #print('Runlists')
            #print(runlists)
            alloc_content_size = as_signed_le(attrib[0x28 : 0x30])
            actual_content_size = as_signed_le(attrib[0x30 : 0x38])
            init_content_size = as_signed_le(attrib[0x28 : 0x30])
        
            attrib_str += '   Non-Resident   size: '+str(actual_content_size)+'  init_size: '+str(actual_content_size)
    
    
        
    elif attrib_type_id in attrib_types:
        #print('**attrib type: ', attrib_type_id)
        content_size = as_signed_le(attrib[0x10 : 0x14])
        content_offset = as_signed_le(attrib[0x14 : 0x16])
        #print('+++++++++',content_size, content_offset, attrib[0x14 : 0x16])
        
        content = []
        #if attrib_type_id == 0x80 or attrib_type_id == 0x90:
        #content = ['$NAME: '+attr_name, 'ATTRIB_ID: '+str(attrib_type_id)]
        
        temp_content, attrib_in_index = parse_content(mft_entry[attrib_offset :], attrib_type_id, content_offset, content_size)
        temp_content['attrib_id'] = attrib_type_id
        temp_content['attrib_name'] = attr_name
        content.append(temp_content)
        #print(content)
        attrib_str += '   Resident   size: '+str(content_size)
        
        res = res + content
            
    
    return res, runlists, attrib_in_index

def parse_mft_entry(mft_entry):
    res = []
    
    #n_fixup_entries = as_signed_le(mft_entry[0x6:0x8])
    lsn = as_signed_le(mft_entry[0x8:0x10])
    seq_num = as_signed_le(mft_entry[0x10:0x12])
    n_links = as_signed_le(mft_entry[0x12:0x14])
    attr_offset = as_signed_le(mft_entry[0x14:0x16])
    flags = mft_entry[0x16:0x18]
    fixup_array = mft_entry[0x30:attr_offset]
    
    """res.append('MFT Entry Header Values:')
    #res.append('Entry: '+str(address)+'        Sequence: '+str(seq_num))
    res.append('$LogFile Sequence Number: '+str(lsn))
    res.append('Links: '+str(n_links))
    res.append('\n')""" 
    attribs = []
    
    mft_end = len(mft_entry)
    iteration = 0
    runlists = []
    index_attrib = 0
    while attr_offset < mft_end:
        start_bytes = as_signed_le(mft_entry[attr_offset : attr_offset + 5])
        
        if start_bytes == 0xffffffff:
            break
        
        attrib_length = as_signed_le(mft_entry[attr_offset + 0x04 : attr_offset + 0x08])
        next_attrib_offset = attr_offset + attrib_length
        attrib = mft_entry[attr_offset : next_attrib_offset]
        
        #print('Iteration number:', iteration, 'attr offset', attr_offset + address, 'mft end', mft_end, 'attrib length', attrib_length)
        #print(mft_entry[attr_offset : attr_offset+10])
        
        attrib_contents, runlist, attrib_in_index = parse_attrib(mft_entry, attr_offset, attrib_length)
        
        if attrib_in_index != 0:
            index_attrib = attrib_in_index
        
        if attrib_contents:
            content = attrib_contents[0]
        
            if content['attrib_id'] == 128 or content['attrib_id'] == 144:
                iteration += 1
            
            attrib_contents[0]['Attrib_index'] = iteration
            #print('ATTRIB CONTENTS: ', attrib_contents)
            res = res + attrib_contents
        
        if runlist:
            runlists = runlists + runlist
        
        #print(attrib_contents, '\n', attrib_str, '\n\n')
        attr_offset = next_attrib_offset
        
    
    #res.append('Attributes:')    
    #res = res + runlists
    #print('\n\n')
    return res, runlists, index_attrib

def list_files(res, mft, mft_size):
    std_files = {'$MFT' : 0, '$MFTMirr':1, '$LogFile': 2, '$Volume': 3, '$AttrDef': 4, '.': 5, '$Bitmap': 6, '$Boot': 7, '$BadClus': 8, '$Secure': 9, '$UpCase': 10, '$Extend': 11}
    
    for d in res:
        output_str = 'r/r '
        
        mft_entry = mft[mft_size*d['MFT_num'] : mft_size*(d['MFT_num'] +1)]
        
        filetype = as_signed_le(mft_entry[0x16 : 0x18])
        if filetype == 0x0003:
            output_str = 'd/d '
        
        if d['MFT_num'] == 8 or d['MFT_num'] == 9:  
            content, _, _ = parse_mft_entry(mft[mft_size*d['MFT_num'] : mft_size*(d['MFT_num'] +1)])
            main_attrib = content[1]
            #print(main_attrib, content)
            main_attrib_name = main_attrib['Name']
            name = main_attrib_name
            
            for i in range(2, len(content)):
                new_dict = content[i]
                attrib_name = new_dict['attrib_name']
                
                if attrib_name != 'N/A':
                    name += ':'+attrib_name
                # print(output_str+" "+str(d['MFT_num'])+':	%15s'%name)
                print("{} {}: \t {}".format(output_str, d['MFT_num'], name))
                name = main_attrib_name
                
            continue
            
        # print(output_str+" "+str(d['MFT_num'])+':	%15s'%d['Name'])
        print("{} {}: \t {}".format(output_str, d['MFT_num'], d['Name']))
        

def fls_ntfs(f, sector_size=512, offset=0):
    starting_address = offset
    ntfs = f.read()
    ntfs = ntfs[starting_address:]
    boot_sector = ntfs[0 : sector_size]
    
    sector_size = struct.unpack('<H', boot_sector[0xb : 0xd])[0]
    sectors_per_cluster = boot_sector[0xd]
    mft_logical_cluster = struct.unpack('<Q', boot_sector[0x30 : 0x38])[0]
    clusters_per_mft = boot_sector[0x40]
    clusters_per_index = boot_sector[0x44]
    mft_size = 0
    index_size = 0
    
    if clusters_per_mft >= 0x7f:
        mft_size = 2**(256 - clusters_per_mft)
        
    else:
        mft_size = sectors_per_cluster*sector_size*clusters_per_mft
        
    
    if clusters_per_index >= 0x7f:
        index_size = 2**(256 - clusters_per_index)
        
    else:
        index_size = sectors_per_cluster*sector_size*clusters_per_index
   
    #print('INDEX SIZE: ', index_size)
    mft_address = sectors_per_cluster * mft_logical_cluster * sector_size
    #print('Cluster size etc.', sector_size, sectors_per_cluster, mft_logical_cluster, mft_address, clusters_per_mft)
    
    required_entry_address = mft_address
    root_dir = mft_address + mft_size*5
    
    mft_entry = ntfs[root_dir : root_dir + clusters_per_mft*sectors_per_cluster*sector_size]
    
    output = []
    mft_index = 0
    
    res, runlists, index_attrib = parse_mft_entry(mft_entry)
    if runlists and index_attrib != 0:
            dir_listing = parse_index_allocation(ntfs, runlists, index_size, sectors_per_cluster, sector_size, clusters_per_index, index_attrib)
            
            list_files(dir_listing, ntfs[required_entry_address:], mft_size)
    
    """while required_entry_address < len(ntfs):
        output_str = 'r/r'
        mft_entry = ntfs[required_entry_address : required_entry_address + clusters_per_mft*sectors_per_cluster*sector_size]
        sig = ''

        sig = mft_entry[0:4].decode(errors="ignore")
        
        if sig != 'FILE':
            required_entry_address += mft_size
            continue
        
        filetype = as_signed_le(mft_entry[0x16 : 0x18])
        if filetype == 0x0003:
            output_str = 'd/d'
            print('Directory')
        
        mft_index = (required_entry_address - mft_address)/mft_size
        print('**', required_entry_address, mft_address, mft_size, mft_index)
        res, runlists, index_attrib = parse_mft_entry(mft_entry, required_entry_address)
        
        
        #print('RES', res)
        if runlists and index_attrib != 0:
            dir_listing = parse_index_allocation(ntfs, runlists, index_size, sectors_per_cluster, sector_size, clusters_per_index, index_attrib)
            print('Directory Listing')
            print(dir_listing)
        required_entry_address += mft_size"""
        
    
    #print('THE END ', required_entry_address, len(ntfs))
    return res


def into_localtime_string(windows_timestamp):
    """
    Convert a windows timestamp into istat-compatible output.

    Assumes your local host is in the EDT timezone.

    :param windows_timestamp: the struct.decoded 8-byte windows timestamp 
    :return: an istat-compatible string representation of this time in EDT
    """
    dt = datetime.datetime.fromtimestamp((windows_timestamp - 116444736000000000) / 10000000)
    hms = dt.strftime('%Y-%m-%d %H:%M:%S')
    fraction = windows_timestamp % 10000000
    return hms + '.' + str(fraction) + '00 (EDT)'


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Display details of a meta-data structure (i.e. inode).')
    parser.add_argument('-o', type=int, default=0, metavar='imgoffset',
                        help='The offset of the file system in the image (in sectors)')
    parser.add_argument('-b', type=int, default=512, metavar='dev_sector_size',
                        help='The size (in bytes) of the device sectors')
    parser.add_argument('image', help='Path to an NTFS raw (dd) image')
    #parser.add_argument('address', type=int, help='Meta-data number to display stats on')
    args = parser.parse_args()
    with open(args.image, 'rb') as f:
        result = fls_ntfs(f, args.b, args.o)
        """for line in result:
            print(line.strip())"""