import binascii
import re


def parsing_atoms(data, atom_name):

    offsets = []
    atom_exist = []

    if data[8:16] == atom_name['ftyp']:
        offsets.append(8)
        atom_exist.append('ftyp')
        size_ftyp = int(data[: 8], 16)
        new_start_offset = size_ftyp*2 
    else:
        raise ValueError('There is no Atom \'ftyp\' at the beginnin of this mp4...')

    while new_start_offset < len(data):
        if data[new_start_offset+8: new_start_offset+16] == atom_name['moov']:
            if data[new_start_offset: new_start_offset+8] == b'00000008':
                atom_exist.append('moov(empty)')
            else:
                atom_exist.append('moov')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*int(data[new_start_offset: new_start_offset+8], 16)
        
        elif data[new_start_offset+8: new_start_offset+16] == atom_name['mdat']:
            if data[new_start_offset: new_start_offset+8] == b'00000008':
                atom_exist.append('mdat(empty)')
            else:
                atom_exist.append('mdat')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*int(data[new_start_offset: new_start_offset+8], 16)
            
        elif data[new_start_offset+8: new_start_offset+16] == atom_name['free']:
            atom_exist.append('free')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*int(data[new_start_offset: new_start_offset+8], 16)

        else:
            raise ValueError('The hierarchy of this mp4 is not valid...')

    # check the validity
    check_list = ['moov', 'mdat']
    for i in check_list:
        if len([idx for idx, atom in enumerate(atom_exist) if atom == i]) > 1:
            raise ValueError('There exist more than one valid Atom \'{}\'...'.format(i))
        if len([idx for idx, atom in enumerate(atom_exist) if atom == i]) < 1:
            raise ValueError('At least one valid Atom \'{}\' is required...'.format(i))
   
    return offsets, atom_exist


def parsing_meta_atoms(data, atom_name):

    offsets = []
    atom_exist = []

    if data[8:16] == atom_name['ftyp']:
        offsets.append(8)
        atom_exist.append('ftyp')
        size_ftyp = int(data[: 8], 16)
        new_start_offset = size_ftyp*2 
    else:
        raise ValueError('There is no Atom \'ftyp\' at the beginnin of this mp4...')

    while new_start_offset < len(data):
        if data[new_start_offset+8: new_start_offset+16] == atom_name['moov']:
            if data[new_start_offset: new_start_offset+8] == b'00000008':
                atom_exist.append('moov(empty)')
            else:
                atom_exist.append('moov')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*int(data[new_start_offset: new_start_offset+8], 16)
        
        elif data[new_start_offset+8: new_start_offset+16] == atom_name['mdat']:
            if data[new_start_offset: new_start_offset+8] == b'00000008':
                atom_exist.append('mdat(empty)')
            else:
                atom_exist.append('mdat')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*8
            
        elif data[new_start_offset+8: new_start_offset+16] == atom_name['free']:
            atom_exist.append('free')
            offsets.append(new_start_offset+8)
            new_start_offset += 2*int(data[new_start_offset: new_start_offset+8], 16)

        else:
            raise ValueError('The hierarchy of this mp4 is not valid...')

    # check the validity
    check_list = ['moov', 'mdat']
    for i in check_list:
        if len([idx for idx, atom in enumerate(atom_exist) if atom == i]) > 1:
            raise ValueError('There exist more than one valid Atom \'{}\'...'.format(i))
        if len([idx for idx, atom in enumerate(atom_exist) if atom == i]) < 1:
            raise ValueError('At least one valid Atom \'{}\' is required...'.format(i))
   
    return offsets, atom_exist


def finding_traks(data, st_name):

    if data[24:32] == st_name['mvhd']:
        mvhd_size = int(data[16:24], 16)
        num_trak = int(data[8+mvhd_size*2: 16+mvhd_size*2], 16)-1
    else:
        raise ValueError('Box \'mvhd\' is missing in Atom \'moov\'...')

    trak_start_offset = 16+mvhd_size*2
    trak_byte_range = []

    while trak_start_offset < len(data):  
        trak_size = int(data[trak_start_offset: trak_start_offset+8], 16)
        if data[trak_start_offset+8: trak_start_offset+16] == st_name['trak']:
            trak_byte_range.append([trak_start_offset, trak_start_offset+trak_size*2])
        trak_start_offset += trak_size*2

    assert len(trak_byte_range) == num_trak
    
    video_idx = []
    audio_idx = []
    audio_name = []
    for byte_range in trak_byte_range:

        trak_data = data[int(byte_range[0]): int(byte_range[1])]
        if trak_data[24:32] == st_name['tkhd']:
            trak_id = int(trak_data[56: 64], 16)-1
        else:
            raise ValueError('Box \'tkhd\' is missing in Box \'trak\'...')

        match = re.finditer(st_name['hdlr'], trak_data)
        for m in match:
            if m.start() % 2 == 0:
                pos_track_type = m.start()+24
                raw = binascii.unhexlify(trak_data[pos_track_type: pos_track_type+8])
                if raw == b'vide':
                    video_idx.append(trak_id)
                elif raw == b'soun':
                    audio_idx.append(trak_id)
                    audio_name.append('audio')
                elif raw == b'sbtl':
                    audio_idx.append(trak_id)
                    audio_name.append('subtitle')
    if len(video_idx) > 1:
        raise ValueError('There exist more than one video stream... ')
    if len(video_idx) < 1:
        raise ValueError('There is no video stream... ')
    
    return trak_byte_range, video_idx, audio_idx, audio_name


def get_bytes_of_chunks(chunk_sample_table, sample_len, num_of_chunk):

    flat_list = [item for sublist in sample_len for item in sublist]
    num_of_samples_in_each_chunk = []
    size_of_chunk = []
    for i in range(len(chunk_sample_table)):
        n = chunk_sample_table[i][0]
        if i+1 < len(chunk_sample_table):
            nxt = chunk_sample_table[i+1][0] 
        else:
            nxt = num_of_chunk+1
        for j in range(nxt-n):
            chunk_sample_table[i][1]
            num_of_samples_in_each_chunk.append(chunk_sample_table[i][1])
    start_idx = 0
    end_idx = 0
    for i in num_of_samples_in_each_chunk:
        size = sum(flat_list[start_idx:end_idx+i])
        size_of_chunk.append(size)
        start_idx += i
        end_idx += i

    return size_of_chunk


def get_length_of_chunks(chunk_sample_table, num_of_chunk):

    sample_list_in_each_chunk = []
    start_ptr = 0
    for i in range(len(chunk_sample_table)):
        n = chunk_sample_table[i][0]-1
        if i+1 < len(chunk_sample_table):
            nxt = chunk_sample_table[i+1][0]-1
        else:
            nxt = num_of_chunk
        for _ in range(nxt-n):
            sample_list_in_each_chunk.append(
                [sample_idx+start_ptr for sample_idx in range(chunk_sample_table[i][1])])
            start_ptr += chunk_sample_table[i][1]

    return sample_list_in_each_chunk


def argsort(seq):
    return sorted(range(len(seq)), key=seq.__getitem__)


def sort_key(file_name):
    return int(file_name.split('.')[0].split('_')[-1])


# def get_sample_table(trak_data, st_name):

#     hierarchy_name = {
#         'mdia':b'6d646961',
#         'minf':b'6d696e66',
#         'stbl':b'7374626c'
#     }
#     #going down the hierarchy to stbl
#     hierarchy = ['mdia', 'minf','stbl']
#     for h in hierarchy:
#         match = re.finditer(hierarchy_name[h], trak_data)
#         all_appearance = [m.start() for m in match if m.start() % 2 == 0]
#         trak_data = trak_data[all_appearance[0]-8:]
#     original_trak_data = trak_data[:]

#     #determine which ele is first
#     table_list = ['stsc', 'stsz', 'stco']
#     table_dict = {}
#     who_is_first = []
#     for i in range(len(table_list)):
#         match = re.finditer(st_name[table_list[i]], trak_data)
#         first_match_pos = [m.start() for m in match if m.start() % 2 == 0][0]
#         who_is_first.append({ "name" : table_list[i], "pos" : first_match_pos})
#     sorted_dic = sorted(who_is_first, key = lambda i: i['pos'])

#     # order_dic tells the ranking of the elements based on who occurs first.Element with 0 occurs first, then 1, then 2
#     order_dic = {'stsc': -1, 'stsz': -1, 'stco': -1}
#     for i in range(len(sorted_dic)):
#         order_dic[sorted_dic[i]['name']] = i

#     for keyword in table_list:
#         if order_dic[keyword] == 1:
#             size_of_first = int(trak_data[sorted_dic[0]['pos']-8: sorted_dic[0]['pos']], 16)
#             trak_data = trak_data[sorted_dic[0]['pos']-8+size_of_first*2:]
#         if order_dic[keyword] == 2:
#             size_of_first = int(trak_data[sorted_dic[0]['pos']-8: sorted_dic[0]['pos']], 16)
#             trak_data = trak_data[sorted_dic[0]['pos']-8+size_of_first*2:]
#             match = re.finditer(st_name[sorted_dic[1]['name']], trak_data)
#             first_match_pos = [m.start() for m in match if m.start() % 2 == 0][0]
#             size_of_second = int(trak_data[first_match_pos-8: first_match_pos], 16)
#             trak_data = trak_data[first_match_pos-8+size_of_second*2:]
#         match = re.finditer(st_name[keyword], trak_data)
#         for m in match:
#             if m.start() % 2 == 0:
#                 position = m.start()
#         if keyword == 'stsc':
#             loop_num = 3
#         elif keyword == 'stsz':
#             loop_num = 1
#         elif keyword == 'stco':
#             loop_num = 1
#         position_of_video = position + 8*2
#         if keyword == 'stsz':
#             if int(trak_data[position_of_video:position_of_video+8], 16) == 0:
#                 num_of_entries = int(trak_data[position_of_video+8:position_of_video+16], 16)
#                 starting_offset = position_of_video + 16
#             else:
#                 num_of_entries = 1
#                 starting_offset = position_of_video
#         else:
#             num_of_entries = int(trak_data[position_of_video: position_of_video+8], 16)
#             starting_offset = position_of_video + 8
#         chunk_sample_table = []
#         for i in range(num_of_entries):
#             entry = []
#             for j in range(loop_num):
#                 num = int(trak_data[starting_offset:starting_offset+8], 16)
#                 entry.append(num)
#                 starting_offset += 8
#             chunk_sample_table.append(entry)
#         table_dict[keyword] = chunk_sample_table
#         trak_data = original_trak_data

#     return table_dict['stsc'], table_dict['stsz'], table_dict['stco']


# def get_sample_table_old(trak_data, st_name):
    
#     table_list = ['stsc', 'stsz', 'stco']
#     table_dict = {}

#     for keyword in table_list:
#         match = re.finditer(st_name[keyword], trak_data)
#         for m in match:
#             if m.start() % 2 == 0:
#                 position = m.start()

#         if keyword == 'stsc':
#             loop_num = 3
#         elif keyword == 'stsz':
#             loop_num = 1
#         elif keyword == 'stco':
#             loop_num = 1

#         position_of_video = position + 8*2
#         if keyword == 'stsz':
#             if int(trak_data[position_of_video:position_of_video+8], 16) == 0:
#                 num_of_entries = int(trak_data[position_of_video+8:position_of_video+16], 16)
#                 starting_offset = position_of_video + 16
#             else:
#                 num_of_entries = 1
#                 starting_offset = position_of_video
#         else:   
#             num_of_entries = int(trak_data[position_of_video: position_of_video+8], 16)
#             starting_offset = position_of_video + 8

#         chunk_sample_table = []
#         for i in range(num_of_entries):
#             entry = []
#             for j in range(loop_num):
#                 num = int(trak_data[starting_offset:starting_offset+8], 16)
#                 entry.append(num)
#                 starting_offset += 8
#             chunk_sample_table.append(entry)

#         table_dict[keyword] = chunk_sample_table

#     return table_dict['stsc'], table_dict['stsz'], table_dict['stco']


def get_sample_table(trak_data, st_name):
    hierarchy_name = {
        'mdia':b'6d646961',
        'minf':b'6d696e66',
        'stbl':b'7374626c'
    }
    
    #going down the hierarchy to stbl
    hierarchy = ['mdia', 'minf','stbl']
    for h in hierarchy:
        match = re.finditer(hierarchy_name[h], trak_data)
        all_appearance = [m.start() for m in match if m.start() % 2 == 0]
        trak_data = trak_data[all_appearance[0]-8:]
        
        if h == 'mdia':
            match = re.finditer(st_name['mdhd'], trak_data)
            all_appearance = [m.start() for m in match if m.start() % 2 == 0]
            pos_of_time_scale = all_appearance[0]+16*2
            mdhd_time_scale = int(trak_data[pos_of_time_scale: pos_of_time_scale+8], 16)
            # print("mdhd_time_scale: ", mdhd_time_scale)
            
            #audio or video track
            match = re.finditer(st_name['hdlr'], trak_data)
            all_appearance = [m.start() for m in match if m.start() % 2 == 0]
            pos_of_type = all_appearance[0]+12*2
            is_audio = False
            if binascii.unhexlify(trak_data[pos_of_type: pos_of_type+8]) == b'soun' or binascii.unhexlify(trak_data[pos_of_type: pos_of_type+8]) == b'sbtl':
                is_audio = True
            # print(is_audio)
            
    original_trak_data = trak_data[:]
    #determine which ele is first
    if is_audio:
        # print("This is an audio track! So there is no stss.")
        table_list = ['stsc', 'stsz', 'stco', 'stts']
    else:  
        table_list = ['stsc', 'stsz', 'stco', 'stts','stss']
        
    table_dict = {}
    who_is_first = []
    for i in range(len(table_list)):
        match = re.finditer(st_name[table_list[i]], trak_data)
        first_match_pos = [m.start() for m in match if m.start() % 2 == 0][0]
        who_is_first.append({ "name" : table_list[i], "pos" : first_match_pos})
    print("##################### who_is_first ########################")
    print(who_is_first)
    sorted_dic = sorted(who_is_first, key = lambda i: i['pos'])
    print("##################### sorted_dic ########################")
    print(sorted_dic)
    # order_dic tells the ranking of the elements based on who occurs first.Element with 0 occurs first, then 1, then 2
    order_dic = {'stsc': -1, 'stsz': -1, 'stco': -1, 'stts': -1, 'stss': -1}
    for i in range(len(sorted_dic)):
        order_dic[sorted_dic[i]['name']] = i
    print("order dic:", order_dic)
    
    #store the corresponding trak data for each element in order dic
    corresponding_track = []
    ele_trak_data = trak_data[:]
    for i in range(len(sorted_dic)-1):
        match = re.finditer(st_name[sorted_dic[i]['name']], ele_trak_data)
        first_match_pos = [m.start() for m in match if m.start() % 2 == 0][0]
        size_of_ele = int(ele_trak_data[first_match_pos-8: first_match_pos], 16)
        ele_trak_data = ele_trak_data[first_match_pos-8+size_of_ele*2:]
        corresponding_track.append(ele_trak_data)
    
    for keyword in table_list:
        if order_dic[keyword] != 0:
            trak_data = corresponding_track[order_dic[keyword]-1]
        match = re.finditer(st_name[keyword], trak_data)
        for m in match:
            if m.start() % 2 == 0:
                position = m.start()
        if keyword == 'stsc':
            loop_num = 3
        elif keyword == 'stts':
            loop_num = 2
        else:
            loop_num = 1
        position_of_video = position + 8*2
        if keyword == 'stsz':
            if int(trak_data[position_of_video:position_of_video+8], 16) == 0:
                num_of_entries = int(trak_data[position_of_video+8:position_of_video+16], 16)
                starting_offset = position_of_video + 16
            else:
                num_of_entries = 1
                starting_offset = position_of_video
        else:
            num_of_entries = int(trak_data[position_of_video: position_of_video+8], 16)
            starting_offset = position_of_video + 8

        chunk_sample_table = []     
        if keyword == 'stts':
            # print('stts #entry:', num_of_entries)
            for i in range(num_of_entries):
                entry = []
                num = int(trak_data[starting_offset:starting_offset+8], 16)
                entry.append(num)
                num = int(trak_data[starting_offset+8:starting_offset+16], 16)
                entry.append(num)
                # entry.append(mdhd_time_scale)
                starting_offset += 16
                chunk_sample_table.append(entry)
        else:
            for i in range(num_of_entries):
                entry = []
                for j in range(loop_num):
                    num = int(trak_data[starting_offset:starting_offset+8], 16)
                    if keyword == 'stss':
                        entry.append(num-1)
                    else:
                        entry.append(num)
                    starting_offset += 8
                chunk_sample_table.append(entry)
                
        table_dict[keyword] = chunk_sample_table
        trak_data = original_trak_data
    
    if is_audio:
        return table_dict['stsc'], table_dict['stsz'], table_dict['stco'], table_dict['stts'], -1, mdhd_time_scale
    return table_dict['stsc'], table_dict['stsz'], table_dict['stco'], table_dict['stts'], table_dict['stss'], mdhd_time_scale


def trans_stts_to_flat(stts):

    flatten_stts = []
    for aa in stts:
        for i in range(aa[0]):
            flatten_stts.append(aa[1])
    return flatten_stts