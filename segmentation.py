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

        
                
        
        if video_ptr == len(video_stcz) and audio_ptr == [len(stcz) for stcz in audio_stcz]:
            flag = False

arr1 = np.array(byteOffset)
arr2 = np.array(byteRange)
end_arr = np.add(arr1, arr2)

tuple = np.array((byteOffset,end_arr)).T
print("Succeed in get video offsets tuple")


####### record the IDR info 

cut_cmd = 'ffmpeg -skip_frame nokey -i {} -vf showinfo -vsync 0 -f null - > {} 2>&1'.format(
    input_file, os.path.join(output_dir, 'IDRinfo.csv')
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Succeed in getting IDR info')

IDRInfoPath = os.path.join(output_dir, 'IDRinfo.csv')


######### IDR start time, offset position, timerange的code
start_time = [] #start_time = [0]+IDR+[whole video length]
range = []
offset= []
with open(IDRInfoPath, 'r') as file:
    csvreader = csv.reader(file)
    for row in csvreader:
        #print("pts_time" in row[0])

        if "pts_time" in row[0]:
            result = row[0].split(':')[3].split(' ', 1)[0]
            start_time.append(float(result))
            result2 = row[0].split(':')[4]
            
            s = ''.join(x for x in result2 if x.isdigit())
            offset.append(int(s))

            
        if "Lsize" in row[0]:
            result1 = row[0].split('=')[5].split(' ', 1)[0]
            total = int(result1.split(':')[0])*3600 + int(result1.split(':')[1])*60 + float(result1.split(':')[2])
            sum = total
            start_time.append(total) # this is the whole video length


file.close()

# print(range)
if(start_time[0] != 0):
    start_time=[0]+start_time

i = 1
while i < len(start_time):
    range.append(start_time[i] - start_time[i - 1])
    i+=1


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
    if (IDR[IDRIndex] < smallest or IDR[IDRIndex] > largest): 
        IDRIndex = IDRIndex + 1
    else: 
        #第一个IDR
        if (firstToken == True):
            #如果在tuple里，那就直接计算，不在的话就看下一个tuple
            if (IDR[IDRIndex] >= tuple[tupleIndex][0] and IDR[IDRIndex] <= tuple[tupleIndex][1]):
                appendValue = IDR[IDRIndex] - tuple[tupleIndex][0] + sum
                # print("currIDR: " + str(IDR[IDRIndex]) + " Value: " + str(appendValue))
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
                # print("currIDR: " + str(IDR[IDRIndex]) + " Value: " + str(appendValue))
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

while(tupleIndex < len(tuple)):
    if (last >= tuple[tupleIndex][0] and last <= tuple[tupleIndex][1]):
        sum = tuple[tupleIndex][1] - last
    else:
        sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
    tupleIndex = tupleIndex + 1
# print("Last Value: " + str(sum)) 
size.append(sum)
print(size)
print("Succeed in getting video size between IDRs ")
####### make them into tuples
newIDR = [0] + IDR
IDRSize = [(newIDR[i], size[i]) for i in range(0, len(newIDR))]
print(IDRSize)

### Find the mean value without outliers

q_2 = np.quantile(size, .50)
q_1 = np.quantile(size, .25)
q_3 = np.quantile(size, .75)
print(q_1)
print(q_3)
iqr = q_3-q_1
upper_fence = q_3 + (1.5*iqr)
lower_fence = q_1 - (1.5*iqr)

clean_data = []
outlier = []
outlier_count = 0
for i in size:
    if i < lower_fence or i > upper_fence:
        outlier_count += 1
        outlier.append(i)
    else:
        clean_data.append(i)
        

final_mean = np.mean(np.array(clean_data))  ## final_mean is what we what 

