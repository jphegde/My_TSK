import datetime
import struct


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
        
        print('ms_nibble', ms_nibble, 'ls_nibble', ls_nibble)
        
        runlength = as_signed_le(runlist_arr[i : i+ls_nibble])
        i += ls_nibble
        print('run offset ', runlist_arr[i : i+ms_nibble])
        runoffset += as_signed_le(runlist_arr[i : i+ms_nibble])
        i += ms_nibble
        
        
        print('runlength', runlength, 'runoffset', runoffset, '\n')
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

def parse_content(attrib, attrib_type, content_offset, content_size):
    content = attrib[content_offset : content_offset + content_size]
    res = []
    #print(content[0 : 10])
    file_types = {0x0001: 'Read Only', 0x0002: 'Hidden', 0x0004: 'System', 0x0020: 'Archive', 0x0040: 'Device', 0x0080: '#Normal', 0x0100: 'Temporary', 0x0200: 'Sparse file ', 0x0400: 'Reparse point', 0x0800: 'Compressed', 0x1000: 'Offline', 0x2000: 'Content is not being indexed for faster searches', 0x4000: 'Encrypted'}
    
    if attrib_type == 0x10:
        #print('$STD_INFO')
        creation_time = into_localtime_string(as_signed_le(content[0x0 : 0x8]))
        modification_time = into_localtime_string(as_signed_le(content[0x8 : 0x10]))
        mft_modified_time = into_localtime_string(as_signed_le(content[0x10 : 0x18]))
        file_accessed_time = into_localtime_string(as_signed_le(content[0x18 : 0x20]))
        flags = as_signed_le(content[0x20 : 0x24])
        #print(creation_time, modification_time, content[0x30 : 0x34])
        owner_id_bytes = content[0x30 : 0x34]
        owner_id = 0
        if owner_id_bytes:
            owner_id = as_signed_le(owner_id_bytes)
            
        filetype = file_types[flags]
        
        res.append('$STANDARD_INFORMATION Attribute Values:')
        res.append('Flags: '+filetype)
        res.append('Owner ID: '+str(owner_id))
        res.append('Created:	'+creation_time)
        res.append('File Modified:	'+modification_time)
        res.append('MFT Modified:	'+mft_modified_time)
        res.append('Accessed:	'+file_accessed_time)
        
        
        
    elif attrib_type == 0x30:
        #print('$FILENAME')
        file_ref = content[0x0 : 0x8]
        seq_num = as_signed_le(content[0x6 : 0x8])
        mft_entry = as_signed_le(content[0x0 : 0x6])
        #print('Trying creation time', content[0x8 : 0x10])
        creation_time = into_localtime_string(as_signed_le(content[0x8 : 0x10]))
        modification_time = into_localtime_string(as_signed_le(content[0x10 : 0x18]))
        mft_modified_time = into_localtime_string(as_signed_le(content[0x18 : 0x20]))
        file_accessed_time = into_localtime_string(as_signed_le(content[0x20 : 0x28]))
        allocated_filesize = as_signed_le(content[0x28 : 0x30])
        real_filesize = as_signed_le(content[0x30 : 0x38])
        flags = as_signed_le(content[0x38 : 0x3c])
        filename_length = content[0x40]
        #print(filename_length, content_offset)
        filename_bytes = content[0x42 : 0x42 + filename_length*2]
        filename = filename_bytes.decode()
        filename = filename.replace('\0', '')
        
        filetype = file_types[flags]
        
        res.append('$FILE_NAME Attribute Values:')
        res.append('Flags: '+filetype)
        res.append('Name: '+filename)
        res.append('Parent MFT Entry: '+str(mft_entry)+' 	Sequence: '+str(seq_num))
        res.append('Allocated Size: '+str(allocated_filesize)+'   	Actual Size: '+str(real_filesize))
        res.append('Created:	'+creation_time)
        res.append('File Modified:	'+modification_time)
        res.append('MFT Modified:	'+mft_modified_time)
        res.append('Accessed:	'+file_accessed_time)
        
    else:
        res.append('$DATA_SIZE:'+str(len(content)))
        
    return res

def parse_attrib(mft_entry, attrib_offset, attrib_length):
    res = []
    attrib = []
    attrib_str = ''
    
    attrib_types = {0x10:'$STANDARD_INFORMATION', 0x30:'$FILE_NAME', 0x80:'$DATA'}
    std_ids = {'$STANDARD_INFORMATION': 16, '$FILE_NAME': 48, '$DATA': 128}
    attrib = mft_entry[attrib_offset : attrib_offset + attrib_length]
    
    attrib_type_id = as_signed_le(attrib[0 : 0x4])
    nonresident_flag = attrib[0x8]
    name_length = attrib[0x9]
    name_offset = attrib[0xa]
    flags = attrib[0xc : 0xe]
    
    #print('attrib id',attrib_type_id, 'name length', name_length)
    attr_name = ''
    if name_length == 0:
        attr_name = 'N/A'
        
    else:
        attr_name = attrib[name_offset : name_offset + name_length].decode()
    
    
    next_offset = 0
    
    if attrib_type_id not in attrib_types:
        return res, '', []
    
    attrib_type =  attrib_types[attrib_type_id]
    attrib_str += 'Type: '+ attrib_type+' ('+ str(std_ids[attrib_type])+'-'+str(as_signed_le(attrib[0xe : 0x10]))+')   Name: '+attr_name
    runlists = []
    if nonresident_flag == 1:
        start_cluster = as_signed_le(attrib[0x10 : 0x18])
        end_cluster = as_signed_le(attrib[0x18 : 0x20])
        runlist_offset = as_signed_le(attrib[0x20 : 0x22])
        
        runlist = get_runlist(mft_entry[attrib_offset + runlist_offset :], start_cluster, end_cluster)
       
        if runlist:
            runlists = runlists + runlist
        
        #print(runlists)
        alloc_content_size = as_signed_le(attrib[0x28 : 0x30])
        actual_content_size = as_signed_le(attrib[0x30 : 0x38])
        init_content_size = as_signed_le(attrib[0x28 : 0x30])
        
        attrib_str += '   Non-Resident   size: '+str(actual_content_size)+'  init_size: '+str(actual_content_size)
        
    else:
        content_size = as_signed_le(attrib[0x10 : 0x14])
        content_offset = as_signed_le(attrib[0x14 : 0x16])
        #print('+++++++++',content_size, attrib_offset + content_offset + 0x42, attrib[0x14 : 0x16])
        content = parse_content(mft_entry[attrib_offset :], attrib_type_id, content_offset, content_size)
        
        attrib_str += '   Resident   size: '+str(content_size)
        
        if content and attrib_type != '$DATA':
            res = res + content
        
    #print('\n')
    
    
    return res, attrib_str, runlists

def parse_mft_entry(mft_entry, address):
    res = []
    
    #n_fixup_entries = as_signed_le(mft_entry[0x6:0x8])
    lsn = as_signed_le(mft_entry[0x8:0x10])
    seq_num = as_signed_le(mft_entry[0x10:0x12])
    n_links = as_signed_le(mft_entry[0x12:0x14])
    attr_offset = as_signed_le(mft_entry[0x14:0x16])
    flags = mft_entry[0x16:0x18]
    fixup_array = mft_entry[0x30:attr_offset]
    
    res.append('MFT Entry Header Values:')
    res.append('Entry: '+str(address)+'        Sequence: '+str(seq_num))
    res.append('$LogFile Sequence Number: '+str(lsn))
    if seq_num == 1:
        res.append('Allocated File')
    elif seq_num == 2:
        res.append('Directory')
    
    res.append('Links: '+str(n_links))
    res.append('\n') 
    attribs = []
    
    mft_end = len(mft_entry)
    iteration = 1
    runlists = []
    while attr_offset < mft_end:
        start_bytes = as_signed_le(mft_entry[attr_offset : attr_offset + 5])
        
        if start_bytes == 0xffffffff:
            break
        
        attrib_length = as_signed_le(mft_entry[attr_offset + 0x04 : attr_offset + 0x08])
        next_attrib_offset = attr_offset + attrib_length
        attrib = mft_entry[attr_offset : next_attrib_offset]
        
        #print('Iteration number:', iteration, 'attr offset', attr_offset, 'mft end', mft_end, 'attrib length', attrib_length)
        #print(mft_entry[attr_offset : attr_offset+10])
        iteration += 1
        attrib_contents, attrib_str, runlist = parse_attrib(mft_entry, attr_offset, attrib_length)
        
        if attrib_contents:
            res = res + attrib_contents
            res.append('\n')
            
        if attrib_str != '':
            attribs.append(attrib_str)
        
        if runlist:
            runlists = runlists + runlist
        
        #print(attrib_contents, '\n', attrib_str, '\n\n')
        attr_offset = next_attrib_offset
        
    
    res.append('Attributes:')    
    res = res + attribs + runlists
    
    return res


def istat_ntfs(f, address, sector_size=512, offset=0):
    starting_address = offset
    ntfs = f.read()
    ntfs[starting_address:]
    boot_sector = ntfs[0 : sector_size]
    
    sector_size = struct.unpack('<H', boot_sector[0xb : 0xd])[0]
    sectors_per_cluster = boot_sector[0xd]
    mft_logical_cluster = struct.unpack('<Q', boot_sector[0x30 : 0x38])[0]
    clusters_per_mft = boot_sector[0x40]
    mft_size = 0
    
    if clusters_per_mft >= 0x7f:
        mft_size = 2**(256 - clusters_per_mft)
        
    else:
        mft_size = sectors_per_cluster*sector_size*clusters_per_mft
        
    
    mft_address = sectors_per_cluster * mft_logical_cluster * sector_size
    print('Cluster size etc.', sector_size, sectors_per_cluster, mft_logical_cluster, mft_address, clusters_per_mft)
    
    required_entry_address = address*mft_size + mft_address
    
    #print('**', required_entry_address, mft_size, clusters_per_mft)
    
    mft_entry = ntfs[required_entry_address : required_entry_address + clusters_per_mft*sectors_per_cluster*sector_size]
    
    res = parse_mft_entry(mft_entry, address)
    #print(res)
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
    parser.add_argument('address', type=int, help='Meta-data number to display stats on')
    args = parser.parse_args()
    with open(args.image, 'rb') as f:
        result = istat_ntfs(f, args.address, args.b, args.o)
        for line in result:
            print(line.strip())