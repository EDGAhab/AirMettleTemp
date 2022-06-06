import binascii
import re
import os
import shutil
import argparse
import csv
from utils import *
import numpy as np
import pandas as pd
from statistics import mean, median


####### find the tuple (start offset, end offset)
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str)
parser.add_argument('--save_tape', action='store_true')
args = parser.parse_args()
input_file = args.input_file
input_dir = os.path.dirname(input_file)
# output_name = input_file.split('/')[-1].split('.')[0]+'.meta'
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0])
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(os.path.join(output_dir, 'clips'))
# read mp4
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

with open(input_file, 'rb') as f:
    hexdata = binascii.hexlify(f.read())

# search for atom names
print('Searching Atoms in input mp4...')
offsets, atom_exist = parsing_atoms(hexdata, atom_name)

# sort atoms and store their bytes range
sort_idx = argsort([offsets[i] for i in range(len(offsets))])
byte_range = [] # [start_offset, end_offset(not include)]
for i in range(len(atom_exist)):
    if i == len(atom_exist)-1:
        byte_range.append([offsets[sort_idx[i]]-8, len(hexdata)])
    else:
        byte_range.append([offsets[sort_idx[i]]-8, offsets[sort_idx[i+1]]-8])
    print('Atom {} byte range: {}-{}, total {} bytes'.format(
        atom_exist[sort_idx[i]], int(byte_range[i][0]/2), int(byte_range[i][1]/2), 
        hex(int(byte_range[i][1]/2)-int(byte_range[i][0]/2))))

# write all bytes except for data in valid mdat
# with open(os.path.join(output_dir, output_name), 'wb') as f:
#     for i in range(len(atom_exist)):
#         if atom_exist[sort_idx[i]] == 'mdat':
#             f.write(binascii.unhexlify(
#                 hexdata[int(byte_range[i][0]): int(byte_range[i][0]+8*2)]))
#         else:
#             f.write(binascii.unhexlify(
#                 hexdata[int(byte_range[i][0]): int(byte_range[i][1])]))
# print('-'*30)
# print('Finish writing mata-data into {}'.format(os.path.join(output_dir, output_name)))

moov_byte_range = byte_range[sort_idx.index(atom_exist.index('moov'))]
moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
trak_byte_range, video_trak_idx, audio_trak_idx, audio_name = finding_traks(
    moov_data, st_name)
if len(audio_trak_idx) == 0:
    print('There\'s no audio/subtitle stream in this mp4...')
    shutil.rmtree(os.path.join(output_dir, 'other_streams'))

if args.save_tape:

    audio_table = []
    audio_stcz = []
    audio_stcl = []
    audio_timescale = []
    audio_stts_flat = []
    for i, byte_range in enumerate(trak_byte_range):
        if i in video_trak_idx:
            # table = (stsc, stsz, stco, stts, stss, trak_timescale)
            video_table = get_sample_table(
                moov_data[int(byte_range[0]): int(byte_range[1])], st_name)
            video_stcz = get_bytes_of_chunks(
                video_table[0], video_table[1], len(video_table[2]))
            video_stcl = get_length_of_chunks(video_table[0], len(video_table[2]))
            video_timescale = video_table[-1]
            video_stss = video_table[4]
            video_stss.append([len(video_table[1])])
            video_stts_flat = trans_stts_to_flat(video_table[3])
        else:
            audio_table.append(get_sample_table(
                moov_data[int(byte_range[0]): int(byte_range[1])], st_name))
            audio_stcz.append(get_bytes_of_chunks(
                audio_table[-1][0], audio_table[-1][1], len(audio_table[-1][2])))
            audio_stcl.append(get_length_of_chunks(audio_table[-1][0], len(audio_table[-1][2])))
            audio_timescale.append(audio_table[-1][-1])
            audio_stts_flat.append(trans_stts_to_flat(audio_table[-1][3]))



    video_ptr = 0
    video_clip = 0
    audio_ptr = [0 for _ in range(len(audio_trak_idx))]
    flag = True
    byteOffset = []
    byteRange = []

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
            byteOffset.append(video_table[2][video_ptr][0])
            byteRange.append(video_stcz[video_ptr])
            video_ptr += 1
            if video_ptr == len(video_stcz):
                video_table[2].append([max_stco])
        else : 
            audio_ptr[select_trakid] +=1
            if audio_ptr[select_trakid] == len(audio_stcz[select_trakid]):
                    audio_table[select_trakid][2].append([max_stco])
                             

        if video_ptr == len(video_stcz) and audio_ptr == [len(stcz) for stcz in audio_stcz]:
            flag = False

arr1 = np.array(byteOffset)
arr2 = np.array(byteRange)
end_arr = np.add(arr1, arr2)

tuple = np.array((byteOffset,end_arr)).T
print("Succeed in get video offsets tuple")


####### record the IDR info 

cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
    os.path.join(output_dir, 'IDRinfo.log'), input_file
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Succeed in getting IDR info')

IDRInfoPath = os.path.join(output_dir, 'IDRinfo.log')


######### IDR start time, offset position, timerange的code
offset= []

frame = []
with open(IDRInfoPath, 'r') as file:
    lines = file.read().splitlines()
    for row in lines:
        if "stream 0" in row and "keyframe 1" in row:
            #  s = ''.join(x for x in result2 if x.isdigit())
            frame.append(row.split(',')[6].split(' ', 2)[2])
            offset.append(int(row.split(',')[7].split(' ', 2)[2], 16))


file.close()




#tuple: [(2,5), (6,9)]
#IDR: [3,7,8]

#通过byteoffset和IDR来找IDR之间的size:
size = []
smallest = tuple[0][0]
largest = tuple[-1][1]
IDR = offset
last = IDR[-1]
tupleIndex = 0
IDRIndex = 0


firstToken = True
sameTuple = True

previous = 0
sum = 0  #累计

while(IDRIndex < len(IDR)):
    #不可能的情况：IDR不在video里，直接跳过
    if (IDR[IDRIndex] < smallest or last > largest): 
        IDRIndex = IDRIndex + 1
    elif(IDR[IDRIndex] >= previous): 
        #第一个IDR
        if (firstToken == True):
            #如果在tuple里，那就直接计算，不在的话就看下一个tuple
            if (IDR[IDRIndex] >= tuple[tupleIndex][0] and IDR[IDRIndex] <= tuple[tupleIndex][1]):
                appendValue = IDR[IDRIndex] - tuple[tupleIndex][0] + sum
                print("currIDR: " + str(IDR[IDRIndex]) + " Value: " + str(appendValue))
                size.append(appendValue)
                previous = IDR[IDRIndex]
                IDRIndex = IDRIndex + 1
                sum = 0
                firstToken = False
            else:
                sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
                tupleIndex = tupleIndex + 1
        #之后的IDR
        else:
            if (IDR[IDRIndex] >= tuple[tupleIndex][0] and IDR[IDRIndex] <= tuple[tupleIndex][1]):
                appendValue = 0
                if (sameTuple == True):
                    appendValue = IDR[IDRIndex] - previous
                else:
                    appendValue = IDR[IDRIndex] - tuple[tupleIndex][0] + sum
                print("currIDR: " + str(IDR[IDRIndex]) + " Value: " + str(appendValue))
                size.append(appendValue)
                previous = IDR[IDRIndex]
                IDRIndex = IDRIndex + 1
                sum = 0
                sameTuple = True
            else:
                if (previous >= tuple[tupleIndex][0] and previous <= tuple[tupleIndex][1]):
                    sum = sum + tuple[tupleIndex][1] - previous
                else:
                    sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
                sameTuple = False
                tupleIndex = tupleIndex + 1
    else:
        IDR.pop(IDRIndex)
        frame.pop(IDRIndex)  ###修改

while(tupleIndex < len(tuple)):
    if (last >= tuple[tupleIndex][0] and last <= tuple[tupleIndex][1]):
        sum = tuple[tupleIndex][1] - last
    else:
        sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
    tupleIndex = tupleIndex + 1
# print("Last Value: " + str(sum)) 
size.append(sum)
print("Succeed in getting video size between IDRs ")
newIDR = [0] + IDR
size2 = []
i = 0
while i < len(newIDR):
    lst = [newIDR[i], size[i]]
    if(lst != [0,0]):
        size2.append((newIDR[i], size[i]))
    else:
        frame.pop(0) ###修改
    i+=1




## Grouping input=size2, output=[start_offset]  =>
#grouping
tot_len = 0
arbitraryNumber = 4500000
i = 0

tempSize = 0
while i < len(size2):
    if(len(size2) != 1):
        if(size2[i][1] < arbitraryNumber and i != len(size2) - 1):
            temp = size2[i][1] + size2[i + 1][1]
            diff1 = abs(temp - arbitraryNumber)
            diff2 = abs(size2[i][1] - arbitraryNumber)
            if(diff1 <= diff2 or size2[i][1] <= 0.1*arbitraryNumber):
                size2[i] = (size2[i][0], temp)
                size2.pop(i+1)
                frame.pop(i+1) #####修改
            else:
                i = i + 1
        else:
            i = i + 1
    else:
        i = i + 1
        
start_offset = []
for a in size2:
    start_offset.append(a[0])

print('******** (IDR,size) *******')
print(size2)

print("***** Candidate IDR*******")
print(len(start_offset))

print("***** Candidate sample*******")
print(frame)

## find the corresponding partition time based on position

# dct = dict((x,y) for x,y in offset_time)
# partition_time = []
# for i in start_offset:
#     partition_time.append(dct[i])

# partition_time.append(start_time[-1])
# print(partition_time)

## video cut
# cut video

# end_idx=1
# while end_idx < len(partition_time):
#     cut_cmd='ffmpeg  -ss {} -i {} -to {} -c:v copy -avoid_negative_ts 1 -loglevel quiet {}/clip_{}.mp4'.format(
#     partition_time[end_idx-1], input_file, partition_time[end_idx]-partition_time[end_idx-1], 
#     os.path.join(output_dir, 'clips'), end_idx-1)
#     end_idx +=1
#     exit_code = os.system(cut_cmd)
#     if exit_code != 0:
#         print('command failed:', cut_cmd)

string = ",".join(str(x) for x in frame)
cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy "%03d_clip.mp4"'.format(
    input_file, string
)
    
print('Succeed in partition videos base on IDR')




