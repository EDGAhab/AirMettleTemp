import binascii
import re
import os
import csv
import shutil
import argparse
from utils import *
import numpy as np
import csv


############################ To get All  Video Trunck info #######################################################
# Read info from cmd, and create relative folder
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str)
parser.add_argument('--save_tape', action='store_true')
args = parser.parse_args()


input_file = args.input_file
input_dir = os.path.dirname(input_file)

output_name = input_file.split('/')[-1].split('.')[0]+'.meta'
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0])
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(os.path.join(output_dir, 'clips'))
os.mkdir(os.path.join(output_dir, 'other_streams'))


cut_cmd='ffmpeg -i {} -c copy -an -loglevel quiet "{}/noAudio.mp4"'.format(
    input_file, output_dir
)
exit_code = os.system(cut_cmd)
if exit_code != 0:
    print('command failed:', cut_cmd)

print('Succeed in generating none audio video')   

noAudio =  os.path.join(output_dir, 'noAudio.mp4')


# Read noAudio.mp4 to get moov_data, track info
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

with open(noAudio, 'rb') as f:
    hexdata = binascii.hexlify(f.read())

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
with open(os.path.join(output_dir, output_name), 'wb') as f:
    for i in range(len(atom_exist)):
        if atom_exist[sort_idx[i]] == 'mdat':
            f.write(binascii.unhexlify(
                hexdata[int(byte_range[i][0]): int(byte_range[i][0]+8*2)]))
        else:
            f.write(binascii.unhexlify(
                hexdata[int(byte_range[i][0]): int(byte_range[i][1])]))
print('-'*30)
print('Finish writing mata-data into {}'.format(os.path.join(output_dir, output_name)))

moov_byte_range = byte_range[sort_idx.index(atom_exist.index('moov'))]
moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
trak_byte_range, video_trak_idx, audio_trak_idx, audio_name = finding_traks(
    moov_data, st_name)
if len(audio_trak_idx) == 0:
    print('There\'s no audio/subtitle stream in this mp4...')
    shutil.rmtree(os.path.join(output_dir, 'other_streams'))





# To get video trunk byteOffset, byteRange
 
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

tuple = np.array((byteOffset,end_arr)).T  # all video trunck -- (byteOffset, byteOffset+byteRange)
print("Succeed in get video offsets tuple: (byteOffset, byteOffset+byteRange)")

############################ To get All IDR info #######################################################

cut_cmd = 'ffmpeg -skip_frame nokey -i {} -vf showinfo -vsync 0 -f null - > {} 2>&1'.format(
    input_file, os.path.join(output_dir, 'IDRinfo.csv')
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Succeed in getting IDR info')

IDRInfoPath = os.path.join(output_dir, 'IDRinfo.csv')



#start time和timerange的code
startTime = []
range = []
offset= []
with open("logfile2.csv", 'r') as file:
    csvreader = csv.reader(file)
    for row in csvreader:
        #print("pts_time" in row[0])

        if "pts_time" in row[0]:
            result = row[0].split(':')[3].split(' ', 1)[0]
            startTime.append(float(result))
            result2 = row[0].split(':')[4]
            
            s = ''.join(x for x in result2 if x.isdigit())
            offset.append(int(s))

            
        if "Lsize" in row[0]:
            result1 = row[0].split('=')[5].split(' ', 1)[0]
            total = int(result1.split(':')[0])*3600 + int(result1.split(':')[1])*60 + float(result1.split(':')[2])
            sum = total
            startTime.append(total)
file.close()
        

############################ To get All Frames info #######################################################

# record the All Frames info, including I, B,P frames ...
cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
    os.path.join(output_dir, 'allFramesInfo.log'), noAudio
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Faild in getting Frames info')
print('Success in getting allFramesInfo.log')

allFramesInfoPath = os.path.join(output_dir, 'allFramesInfo.log')


# To get IDR info by reading the log file, that the corresponding IDR sample number, IDR byteoffset
offset= [] # IDR byteoffset
frame = [] # IDR Sample number 

with open(allFramesInfoPath, 'r') as file:
    lines = file.read().splitlines()
    for row in lines:
        if "stream 0" in row and "keyframe 1" in row:
            frame.append(int(row.split(',')[6].split(' ', 2)[2]))
            offset.append(int(row.split(',')[7].split(' ', 2)[2], 16))

file.close()

print('Success in getting frame, offset of IDR')





#find the size between IDR frames through the byteoffset information
size = [] # to store the size between IDRs
smallest = tuple[0][0]
largest = tuple[-1][1]
IDR = [] #the IDR list stores [frame, offset, startTime]
print("len(frame)   ", len(frame) )
print("len(offset)   ", len(offset) )
print("len(startTime)   ", len(startTime) )
while i < len(offset):
    temp5 = [frame[i], offset[i], startTime[i]]
    IDR.append(temp5)
    i+=1

last = IDR[-1][1]
tupleIndex = 0
IDRIndex = 0


firstToken = True
sameTuple = True

previous = 0
sum = 0  #cumulated offset

print('Success in getting all IDR: [frame, offset] *********')
# print(IDR)

while(IDRIndex < len(IDR)):
    #the condition where IDR is not in the video (actually this situation doesn't exists )
    if (IDR[IDRIndex][1] < smallest or last > largest): 
        IDRIndex = IDRIndex + 1
    # We only consider that all IDR byteoffset are increasing, otherwise we drop the wired IDR
    elif(IDR[IDRIndex][1] >= previous): 
        #the condition in the first IDR
        if (firstToken == True):
            #if IDR is inside the tuple, then we calculate offset directly, otherwise we jump to the next tuple
            if (IDR[IDRIndex][1] >= tuple[tupleIndex][0] and IDR[IDRIndex][1] <= tuple[tupleIndex][1]):
                appendValue = IDR[IDRIndex][1] - tuple[tupleIndex][0] + sum
                # print("currIDR: " + str(IDR[IDRIndex][1]) + " Value: " + str(appendValue))
                size.append(appendValue)
                previous = IDR[IDRIndex][1]
                IDRIndex = IDRIndex + 1
                sum = 0
                firstToken = False
            else:
                sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
                tupleIndex = tupleIndex + 1
        #To calculate IDR offsets after the first tuple
        else:
            if (IDR[IDRIndex][1] >= tuple[tupleIndex][0] and IDR[IDRIndex][1] <= tuple[tupleIndex][1]):
                appendValue = 0
                if (sameTuple == True):
                    appendValue = IDR[IDRIndex][1] - previous
                else:
                    appendValue = IDR[IDRIndex][1] - tuple[tupleIndex][0] + sum
                # print("currIDR: " + str(IDR[IDRIndex][1]) + " Value: " + str(appendValue))
                size.append(appendValue)
                previous = IDR[IDRIndex][1]
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
        #There exists some weird IDR frames which is not monotnously increading, so we pop those IDRs which are suddenly decreasing
        IDR.pop(IDRIndex)

while(tupleIndex < len(tuple)):
    if (last >= tuple[tupleIndex][0] and last <= tuple[tupleIndex][1]):
        sum = tuple[tupleIndex][1] - last
    else:
        sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
    tupleIndex = tupleIndex + 1
# print("Last Value: " + str(sum)) 
size.append(sum)
newIDR = []
print("Succeed in getting video size between IDRs ")
if size[0] == 0 :
    size.pop(0)
    newIDR=IDR
else:
    newIDR = [[0,smallest,0]] + IDR  #[frame, offset, startTime]
size2 = [] # size2 is the tupple (frame, byte_offset, startTime, size)
i = 0
while i < len(newIDR):
    lst = [newIDR[i][0], newIDR[i][1],newIDR[i][2], size[i]]
    if(lst[1] != 0 and lst[3] != 0 ):
        size2.append((newIDR[i][0], newIDR[i][1], newIDR[i][2], size[i]))
    i+=1
print("*************** size2 *************")
print(size2)


############################ To Grouping Video and find candidate IDRs #######################################################
# Grouping the videos to approximately 4.5 mb.
tot_len = 0
arbitraryNumber = 4500000    #4.5 mb
i = 0

tempSize = 0
while i < len(size2):
    if(len(size2) != 1):
        if(size2[i][3] < arbitraryNumber and i != len(size2) - 1):
            temp = size2[i][3] + size2[i + 1][3]
            diff1 = abs(temp - arbitraryNumber)
            diff2 = abs(size2[i][3] - arbitraryNumber)
            if(diff1 <= diff2 or size2[i][3] <= 0.1*arbitraryNumber):
                size2[i] = (size2[i][0], size2[i][1], size2[i][2], temp)
                size2.pop(i+1)
            else:
                i = i + 1
        else:
            i = i + 1
    else:
        i = i + 1
        
sample = []  # the sample number of candidate IDRs
finalStartTime = []
for a in size2:
    sample.append(a[0])
    finalStartTime.append(a[2])

print('Success in get the list: (sample_number, IDR_offset, startTime, byte_range)')
print(size2)
print("Total Candidate partition IDR number: ", len(sample))



############################ To Cut Video #######################################################
####write sample_number, IDR_offset, byte_range,
data_rows = []
inner_row = []
clip_count = 0
for ele in size2:
    inner_row = [clip_count, ele[0], ele[1], ele[3], ele[2]]
    clip_count += 1
    data_rows.append(inner_row)

csv_file = os.path.join(output_dir, 'partition_mdat_dstrbt1.csv')
with open(csv_file, 'w') as f:
    writer = csv.writer(f)
    csv_line = '#clip, sample_number, bytes_offset, clip_size, clip_time_range'
    writer.writerows([csv_line.split(',')])
    writer.writerows(data_rows)

print("fished partition.csv")




###### The following segement by frame ffmpeg command line need postive integer to partition.
if 0 in sample:
    sample.remove(0)
if len(sample) == 1 and sample[0] == 0 :
    print("The partition video is identical to the noAudio.mp4")  
else:
    string = ",".join(str(x) for x in sample)
    #The command line to partition video based on candidate IDRs in sample
    cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -an -loglevel quiet "{}/clip_%d.mp4"'.format(
        input_file, string, os.path.join(output_dir, 'clips')
    )
    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    print('Succeed in partition videos base on IDR')



