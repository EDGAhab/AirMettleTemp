import binascii
import re
import os
import argparse
from utils import *
import numpy as np
import csv

parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str)
parser.add_argument('--mute', action='store_true')
args = parser.parse_args()


input_dir = args.input_dir
original_file = input_dir + '.mp4'
noAudio_file = os.path.join(input_dir, 'noAudio.mp4')
meta_file = os.path.join(input_dir, "intermediate",input_dir.split('/')[-1]+'.meta')
recon_file = os.path.join(input_dir, input_dir.split('/')[-1]+'_recon.mp4')
audio_dir = os.path.join(input_dir, 'audio')
tmp_file = os.path.join(input_dir, 'tmp_file')
clip_dir = os.path.join(input_dir, 'clips')
overlap_path = os.path.join(input_dir, 'recon_overlap.csv')
overlap = [0]
with open(overlap_path) as f:
    reader = csv.reader(f)
    for row in reader:
        print("******** overlap *********")
        overlap+=row
        print(overlap)

# print("******** overlap *********")
# print(overlap)
if not os.path.isdir(clip_dir):
    raise ValueError('Video clips do not exist ...')
if not os.path.isfile(meta_file):
    raise ValueError('Meta-data does not exist ...')


atom_name = {
    'ftyp': b'66747970', 
    'moov': b'6d6f6f76', 
    'free': b'66726565', 
    'mdat': b'6d646174'}
st_name = {    
    'stsc': b'73747363', 
    'stsz': b'7374737a', 
    'stco': b'7374636f', 
    'stts': b'73747473', 
    'stss': b'73747373', 
    'hdlr': b'68646c72',
    'mvhd': b'6d766864',
    'trak': b'7472616b',
    'tkhd': b'746b6864',
    'mdhd': b'6d646864'}

# read stored metadata
with open(meta_file, 'rb') as f:
    hexdata = binascii.hexlify(f.read())

print('Searching Atoms in .meta file...')
offsets, atom_exist = parsing_meta_atoms(hexdata, atom_name)
print('offsets')
print(offsets)
# extract valid moov byte range for future use
sort_idx = argsort([offsets[i] for i in range(len(offsets))])
moov_idx = atom_exist.index('moov')
if sort_idx.index(moov_idx) == len(atom_exist)-1:
    moov_byte_range = [offsets[moov_idx]-8, len(hexdata)]
else:  
    moov_byte_range = [offsets[moov_idx]-8, offsets[sort_idx[sort_idx.index(moov_idx)+1]]-8]
    
# write 'head' metadata into recon file
insert_offsets = offsets[atom_exist.index('mdat')]+8  
with open(recon_file, 'wb') as fout:
    fout.write(binascii.unhexlify(hexdata[:insert_offsets]))

# stack mdats of video clips
with open(tmp_file, 'wb') as fin:
    pass
print('Extracting video mdat from ./clips...')
for path, dirs, files in os.walk(clip_dir):
    for f in sorted(files, key=sort_key):
        if 'clip' in f:
            if not args.mute:
                print('Extracting {}...'.format(f))
            with open(os.path.join(path, f), 'rb') as fin:
                mdat = binascii.hexlify(fin.read())

            offsets, atom_exist = parsing_atoms(mdat, atom_name)
            sort_idx = argsort([offsets[i] for i in range(len(offsets))])
            start_idx = offsets[atom_exist.index('mdat')]+8
            if atom_exist[sort_idx[-1]] == 'mdat':
                contents = mdat[start_idx:]
            else:
                sort_atom_exist = [atom_exist[i] for i in sort_idx]
                sort_offsets = [offsets[i] for i in sort_idx]
                end_idx = sort_offsets[sort_atom_exist.index('mdat')+1]-8
                contents = mdat[start_idx:end_idx]
            with open(tmp_file, 'ab') as fin:
                fin.write(binascii.unhexlify(contents))

with open(tmp_file, 'rb') as fin:
    print("*********** vidoe **********" )
    print(tmp_file)
    video_mdat = binascii.hexlify(fin.read())
os.remove(tmp_file)
tmp_file = os.path.join(input_dir, 'tmp_file')

if not os.path.isdir(audio_dir):
    # video only mode
    with open(recon_file, 'ab') as fout:
        fout.write(binascii.unhexlify(video_mdat))
else:
    # video with audio(s)
    print('Extracting audio&subtitle mdat from ./audio...')
    audio_mdat = []
    i = 0
    for path, dirs, files in os.walk(audio_dir):
        for f in sorted(files, key=sort_key):
            if 'audio' in f or 'subtitle' in f:
                if not args.mute:
                    print('Extracting {}...'.format(f))
                with open(os.path.join(path, f), 'rb') as fin:
                    audio_mdat = binascii.hexlify(fin.read())
                    # audio_data = binascii.hexlify(fin.read())

                # offsets, atom_exist = parsing_atoms(audio_data, atom_name)
                # sort_idx = argsort([offsets[i] for i in range(len(offsets))])
                # start_idx = offsets[atom_exist.index('mdat')]+8
                # start_idx1 = offsets[atom_exist.index('mdat')]+8+int(overlap[i])
                # print("on overlap start index   "+ str(start_idx) + " vs overlap: " + str(start_idx1))

                # if sort_idx[-1] == len(offsets) - 1:
                #     audio_mdat.append(audio_data[start_idx:])
                # else:   
                #     end_idx = offsets[sort_idx.index(sort_idx[-1]+1)]-8
                #     audio_mdat.append(audio_data[start_idx:end_idx])
                offsets, atom_exist = parsing_atoms(audio_mdat, atom_name)
                sort_idx = argsort([offsets[i] for i in range(len(offsets))])
                start_idx = offsets[atom_exist.index('mdat')]+8
                if atom_exist[sort_idx[-1]] == 'mdat':
                    contents = audio_mdat[start_idx:]
                else:
                    sort_atom_exist = [atom_exist[i] for i in sort_idx]
                    sort_offsets = [offsets[i] for i in sort_idx]
                    end_idx = sort_offsets[sort_atom_exist.index('mdat')+1]-8
                    contents = audio_mdat[start_idx:end_idx]
                with open(tmp_file, 'ab') as fin:
                    fin.write(binascii.unhexlify(contents))

            i+=1
    with open(tmp_file, 'rb') as fin:
        print("*********** audio **********" )
        print(tmp_file)
        audio_mdat = binascii.hexlify(fin.read())
    os.remove(tmp_file)

    # get sample tables
    moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
    trak_byte_range, video_trak_idx, audio_trak_idx, _ = finding_traks(
        moov_data, st_name)
    audio_table = []
    audio_stcz = []
    for i, byte_range in enumerate(trak_byte_range):
        if i in video_trak_idx:
            # (stsc, stsz, stco)
            video_table = get_sample_table(
                moov_data[int(byte_range[0]): int(byte_range[1])], st_name)
            video_stcz = get_bytes_of_chunks(
                video_table[0], video_table[1], len(video_table[2]))
        else:
            audio_table.append(get_sample_table(
                moov_data[int(byte_range[0]): int(byte_range[1])], st_name))
            audio_stcz.append(get_bytes_of_chunks(
                audio_table[-1][0], audio_table[-1][1], len(audio_table[-1][2])))  

    # merge mdat of video and audio(s)
    video_ptr = 0
    audio_ptr = [0 for _ in range(len(audio_trak_idx))]
    video_mdat_offset = 0
    audio_mdat_offset = [0 for _ in range(len(audio_trak_idx))]
    flag = True

    max_video_stco = max([video_table[2][i][0] for i in range(len(video_stcz))])
    max_audio_stco = []
    for i in range(len(audio_stcz)):
        max_audio_stco.append(max([audio_table[i][2][j][0] for j in range(len(audio_stcz[i]))]))   
    max_stco = max(max_audio_stco+[max_video_stco])+1

    while flag:
        cuurent_chunk_offset = []
        for i in range(len(audio_trak_idx)):
            current_ptr = audio_ptr[i]
            cuurent_chunk_offset.append(audio_table[i][2][current_ptr][0])
        cuurent_chunk_offset.append(video_table[2][video_ptr][0])
        chunk_offset_argsort = argsort(cuurent_chunk_offset)
        select_trakid = chunk_offset_argsort[0]
        if select_trakid == len(audio_trak_idx):
            with open(recon_file, 'ab') as fout:
                fout.write(binascii.unhexlify(
                    video_mdat[video_mdat_offset: video_mdat_offset+video_stcz[video_ptr]*2]))
            video_mdat_offset += video_stcz[video_ptr]*2
            video_ptr += 1
            if video_ptr == len(video_stcz):
                video_table[2].append([max_stco])
        else:
            with open(recon_file, 'ab') as fout:
                    # fout.write(binascii.unhexlify(
                    #     audio_mdat[select_trakid][
                    #         audio_mdat_offset[select_trakid]: audio_mdat_offset[select_trakid]+audio_stcz[select_trakid][audio_ptr[select_trakid]]*2]
                    #         ))
                    fout.write(binascii.unhexlify(
                        audio_mdat[audio_mdat_offset: audio_mdat_offset+audio_stcz[audio_ptr]*2]))
            audio_mdat_offset += audio_stcz[audio_ptr]*2
            audio_ptr += 1
            if audio_ptr == len(audio_stcz):
                audio_table[2].append([max_stco])
            # audio_mdat_offset[select_trakid] += audio_stcz[select_trakid][audio_ptr[select_trakid]]*2
            # audio_ptr[select_trakid] += 1
            # if audio_ptr[select_trakid] == len(audio_stcz[select_trakid]):
            #     audio_table[select_trakid][2].append([max_stco])

        if video_ptr == len(video_stcz) and audio_ptr == [len(stcz) for stcz in audio_stcz]:
            flag = False

# write 'tail' metadata into recon file
with open(recon_file, 'ab') as fout:
    fout.write(binascii.unhexlify(hexdata[insert_offsets:]))
print('Succeed in reconstructing file: {}'.format(recon_file))
exit = os.system('diff {} {} -s'.format(recon_file, original_file))