import binascii
import re
import os
import csv
import shutil
import argparse
from utils import *
import numpy as np
import pandas as pd


############################ To get All  Video Trunck info #######################################################
# Read info from cmd, and create relative folder
parser = argparse.ArgumentParser()
parser.add_argument('--input_file', type=str)
parser.add_argument('--save_tape', action='store_true')
args = parser.parse_args()


input_file = args.input_file
input_dir = os.path.dirname(input_file)

output_name = input_file.split('/')[-1].split('.')[0]+'.meta'
voutput_name = input_file.split('/')[-1].split('.')[0]+'noAudio.meta'
aoutput_name = input_file.split('/')[-1].split('.')[0]+'noVideo.meta'
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0])
audio_output_dir = os.path.join(output_dir, 'audio')
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(audio_output_dir)
os.mkdir(os.path.join(output_dir, 'clips'))
os.mkdir(os.path.join(output_dir, 'other_streams'))


cut_cmdv='ffmpeg -i {} -c copy -an -loglevel quiet "{}/noAudio.mp4"'.format(
    input_file, output_dir
)

cut_cmd='ffmpeg -i {} -c copy -vn -loglevel quiet "{}/Audio.mp4"'.format(
    input_file, output_dir
)


exit_code = os.system(cut_cmd)
if exit_code != 0:
    print('command failed:', cut_cmd)

exit_code = os.system(cut_cmdv)
if exit_code != 0:
    print('command failed:', cut_cmdv)
print('Succeed in generating none audio video')

noAudio =  os.path.join(output_dir, 'noAudio.mp4')
Audio =  os.path.join(output_dir, 'Audio.mp4')

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



######################## meta data for video only ################################

with open(noAudio, 'rb') as f:
    vhexdata = binascii.hexlify(f.read())

print('Searching Atoms in input mp4...')
voffsets, vatom_exist = parsing_atoms(vhexdata, atom_name)

# sort atoms and store their bytes range
sort_idx = argsort([voffsets[i] for i in range(len(voffsets))])
vbyte_range = [] # [start_offset, end_offset(not include)]
for i in range(len(vatom_exist)):
    if i == len(vatom_exist)-1:
        vbyte_range.append([voffsets[sort_idx[i]]-8, len(vhexdata)])
    else:
        vbyte_range.append([voffsets[sort_idx[i]]-8, voffsets[sort_idx[i+1]]-8])
    print('Atom {} byte range: {}-{}, total {} bytes'.format(
        vatom_exist[sort_idx[i]], int(vbyte_range[i][0]/2), int(vbyte_range[i][1]/2),
        hex(int(vbyte_range[i][1]/2)-int(vbyte_range[i][0]/2))))

# write all bytes except for data in valid mdat
with open(os.path.join(output_dir, voutput_name), 'wb') as f:
    for i in range(len(vatom_exist)):
        if vatom_exist[sort_idx[i]] == 'mdat':
            f.write(binascii.unhexlify(
                vhexdata[int(vbyte_range[i][0]): int(vbyte_range[i][0]+8*2)]))
        else:
            f.write(binascii.unhexlify(
                vhexdata[int(vbyte_range[i][0]): int(vbyte_range[i][1])]))
print('-'*30)
print('Finish writing mata-data into {}'.format(os.path.join(output_dir, voutput_name)))

######################## meta data for audio only ################################

with open(Audio, 'rb') as f:
    ahexdata = binascii.hexlify(f.read())

print('Searching Atoms in input mp4...')
aoffsets, aatom_exist = parsing_atoms(ahexdata, atom_name)

# sort atoms and store their bytes range
sort_idx = argsort([aoffsets[i] for i in range(len(aoffsets))])
abyte_range = [] # [start_offset, end_offset(not include)]
for i in range(len(aatom_exist)):
    if i == len(aatom_exist)-1:
        abyte_range.append([aoffsets[sort_idx[i]]-8, len(ahexdata)])
    else:
        abyte_range.append([aoffsets[sort_idx[i]]-8, aoffsets[sort_idx[i+1]]-8])
    print('Atom {} byte range: {}-{}, total {} bytes'.format(
        aatom_exist[sort_idx[i]], int(abyte_range[i][0]/2), int(abyte_range[i][1]/2),
        hex(int(abyte_range[i][1]/2)-int(abyte_range[i][0]/2))))

# write all bytes except for data in valid mdat
with open(os.path.join(output_dir, aoutput_name), 'wb') as f:
    for i in range(len(aatom_exist)):
        if aatom_exist[sort_idx[i]] == 'mdat':
            f.write(binascii.unhexlify(
                ahexdata[int(abyte_range[i][0]): int(abyte_range[i][0]+8*2)]))
        else:
            f.write(binascii.unhexlify(
                ahexdata[int(abyte_range[i][0]): int(abyte_range[i][1])]))
print('-'*30)
print('Finish writing mata-data into {}'.format(os.path.join(output_dir, aoutput_name)))


############### meta data for video & audio file ###############
with open(input_file, 'rb') as f:
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
################################# something next ###################################

moov_byte_range = byte_range[sort_idx.index(atom_exist.index('moov'))]
moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
trak_byte_range, video_trak_idx, audio_trak_idx, audio_name = finding_traks(
    moov_data, st_name)
if len(audio_trak_idx) == 0:
    # print('There\'s no audio/subtitle stream in this mp4...')
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
    byteOffset = [] #only for video 
    byteRange = []  #only for video
    trackName = []  # for all video and audio
    AudioSize2 = [] # only for audio 
    combineByteOffset = [] # for all video and audio
    combineSize = []
    global_trunck_num = []

    max_video_stco = max([video_table[2][i][0] for i in range(len(video_stcz))])
    max_audio_stco = []
    for i in range(len(audio_stcz)):
        max_audio_stco.append(max([audio_table[i][2][j][0] for j in range(len(audio_stcz[i]))]))
    max_stco = max(max_audio_stco+[max_video_stco])+1

    j = 0
    while flag:
        cuurent_chunk_offset = []
        for i in range(len(audio_trak_idx)):
            current_ptr = audio_ptr[i]
            cuurent_chunk_offset.append(audio_table[i][2][current_ptr][0])
        cuurent_chunk_offset.append(video_table[2][video_ptr][0])
        chunk_offset_argsort = argsort(cuurent_chunk_offset)
        select_trakid = chunk_offset_argsort[0]
        j += 1
        global_trunck_num.append(j)
        if select_trakid == len(audio_trak_idx):
            combineByteOffset.append(video_table[2][video_ptr][0])
            combineSize.append(video_stcz[video_ptr])
            byteOffset.append(video_table[2][video_ptr][0])
            byteRange.append(video_stcz[video_ptr])
            # print('video format')

            trackName.append('video_{}'.format(video_trak_idx[0]))
            # print('video_{}'.format(video_trak_idx[0]))
            video_ptr += 1
            if video_ptr == len(video_stcz):
                video_table[2].append([max_stco])
        else :
            combineByteOffset.append(audio_table[select_trakid][2][audio_ptr[select_trakid]][0])
            combineSize.append(audio_stcz[select_trakid][audio_ptr[select_trakid]])
            trackName.append('{}_{}'.format(audio_name[select_trakid], audio_trak_idx[select_trakid]))

            AudioSize2.append(audio_stcz[select_trakid][audio_ptr[select_trakid]])

            audio_ptr[select_trakid] +=1

            if audio_ptr[select_trakid] == len(audio_stcz[select_trakid]):


                audio_table[select_trakid][2].append([max_stco])


        if video_ptr == len(video_stcz) and audio_ptr == [len(stcz) for stcz in audio_stcz]:
            flag = False

arr1 = np.array(byteOffset)
arr2 = np.array(byteRange)
end_arr = np.add(arr1, arr2)
# print('########print byteOffset')
# print(byteOffset)

tuple = np.array((byteOffset,end_arr)).T  # all video trunck -- (byteOffset, byteOffset+byteRange)
print("Succeed in get video offsets tuple: (byteOffset, byteOffset+byteRange)")


###############################################################

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
IDRoffset= []
with open(IDRInfoPath, 'r') as file:
    csvreader = csv.reader(file)
    for row in csvreader:
        #print("pts_time" in row[0])

        if "pts_time" in row[0]:
            result = row[0].split(':')[3].split(' ', 1)[0]
            startTime.append(float(result))
            result2 = row[0].split(':')[4]

            s = ''.join(x for x in result2 if x.isdigit())
            IDRoffset.append(int(s))

file.close()

print("The total IDR number is : ", len(startTime))

############################ To get All Frames info #######################################################

# record the All Frames info, including I, B,P frames ...
cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
    os.path.join(output_dir, 'allFramesInfo.log'), input_file
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Faild in getting Frames info')
print('Success in getting allFramesInfo.log')

allFramesInfoPath = os.path.join(output_dir, 'allFramesInfo.log')


# To get IDR info by reading the log file, that the corresponding IDR sample number, IDR byteoffset
offset= [] # All frames byteoffset
frame = [] #  All frames Sample number

# To get IDR info by reading the log file, that the audio size

with open(allFramesInfoPath, 'r') as file:
    lines = file.read().splitlines()
    for row in lines:
        if "stream 0" in row and "keyframe 1" in row:
            frame.append(int(row.split(',')[6].split(' ', 2)[2]))
            offset.append(int(row.split(',')[7].split(' ', 2)[2], 16))

file.close()
print('Success in getting frame, offset of All Frames')

############################ To get Audio info #######################################################

# record the All Frames info, including I, B,P frames ...
cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
    os.path.join(output_dir, 'allFramesInfoa.log'), Audio
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Faild in getting Frames info')
print('Success in getting allFramesInfo.log')

allFramesInfoPatha = os.path.join(output_dir, 'allFramesInfoa.log')


# To get IDR info by reading the log file, that the corresponding IDR sample number, IDR byteoffset

# To get IDR info by reading the log file, that the audio size
audioSize = [] #[size]

with open(allFramesInfoPatha, 'r') as file:
    lines = file.read().splitlines()
    for row in lines:
        if "AVIndex stream 0" in row:
            audioSize.append(int(row.split(',')[9].split(' ', 2)[2]))

file.close()
print('Success in getting frame, offset of All Frames')

bigsum = 0
for i in audioSize:
    bigsum = bigsum + i
# print(bigsum)




########### Audio Processing #############################
# AudioSize2 = []  ###假设我已经有了  I will get the size
AudioTarget = [] ###输出分类// for reconstruction audio "0clip_0.mp4"
AudioIndex = 0

targetSize = 4500000  #4.5MB
overlap = 80000         #大约五秒？
cutPlan = []
overall = []
sum = 0
start = 0
i = 0
remaining = 0
while(i < len(audioSize)):
    overlap = 80000     #大约五秒？
    sum = sum + audioSize[i]
    if (sum >= targetSize):
        tempMinus = 0
        if (AudioIndex != 0):
            tempMinus = overlap
        tempSum = remaining
        while (tempSum < sum and len(AudioSize2) > 0):
            tempSum = tempSum + AudioSize2.pop(0)
            tempStr = 1
            if(AudioIndex == 0):
                tempStr = 0
            AudioTarget.append(str(AudioIndex)+ "audio_" + str(tempStr) + ".mp4")
            if(tempSum >= sum):
                remaining = tempSum - sum - tempMinus
                if(remaining > 0):
                    lastIndex = len(AudioTarget) - 1
                    temp = AudioTarget[lastIndex]
                    AudioTarget[lastIndex] = temp + ", "+ str(AudioIndex + 1)+ "audio_1.mp4"
        AudioIndex = AudioIndex + 1


        overall.append(sum)
        cutPlan.append([start, i+1])
        sum = 0
        minusOffset = 0
        while(overlap > 0):
            overlap = overlap - audioSize[i + minusOffset]
            minusOffset = minusOffset + 1
        start = i + 1 - minusOffset
        i = start - 1
        # print(start)
    i = i + 1
if(sum > 0 and len(AudioSize2) > 0):
    i = 0
    while(i < len(AudioSize2)):
        tempStr = 1
        if(AudioIndex == 0):
            tempStr = 0
        AudioTarget.append(str(AudioIndex)+ "audio_" + str(tempStr) + ".mp4")
        i = i + 1

# print(AudioTarget)  ###csv的audio
#############################################################################################


if bigsum <= 4500000:
    cut_cmd='ffmpeg -i {} -c copy -vn -loglevel quiet "{}/0audio_0.mp4"'.format(
        input_file, audio_output_dir
    )


    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    print("Audio file less than 4.5 MB. There is no need to cut it")
else:
    if(start != len(audioSize) - 1):
        cutPlan.append([start])
    cutPlan[0] = [cutPlan[0][1]]
    # print('##### cut plan ######')
    # print(cutPlan)
    #[[0, 5], [4, 9], [8, 13], [12, 17], [16, 18]]
    i = 0
    while i < len(cutPlan):
        string = ",".join(str(x) for x in cutPlan[i])
        cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -loglevel quiet "{}/{}audio_%d.mp4"'.format(
                Audio, string, os.path.join(audio_output_dir), i
            )
        exit_code = os.system(cut_cmd)
        if exit_code != 0:
            print('command failed:', cut_cmd)


        # for the middle
        if (i == 0) :
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 1)
            cut_cmd_1 = 'rm -f {}'.format(clip_path1)
            exit_code = os.system(cut_cmd_1)
            if exit_code != 0:
                print('command failed:', cut_cmd_1)

        elif (i > 0  and i < len(cutPlan)-1 ):
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 0)
            clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),i, 2)
            cut_cmd_1 = 'rm -f {}'.format(clip_path1)
            cut_cmd_2 = 'rm -f {}'.format(clip_path2)
            exit_code = os.system(cut_cmd_1)
            if exit_code != 0:
                print('command failed:', cut_cmd_1)
            exit_code = os.system(cut_cmd_2)
            if exit_code != 0:
                print('command failed:', cut_cmd_2)
        else:
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),i, 0)
            cut_cmd_1 = 'rm -f {}'.format(clip_path1)
            exit_code = os.system(cut_cmd_1)
            if exit_code != 0:
                print('command failed:', cut_cmd_1)


        i += 1

    print('Succeed in partition audio around 4.5 mb')



#################### Create IDR tuple (frame, offset, startTime) ##############
left_df = pd.DataFrame({'start_time': startTime,
                       'byteoffset': IDRoffset,
                      })
# users
right_df = pd.DataFrame({'sample_id': frame,
                        'byteoffset': offset,
                       })

# joint_table = left_df.merge(right_df, on='byteoffset', how='left')  we can use both left join or inner join
joint_table = pd.merge(left_df, right_df, on='byteoffset', how='inner')
IDR = []
for i in joint_table.index:
    IDR.append((joint_table['sample_id'].iloc[i], joint_table['byteoffset'].iloc[i], joint_table['start_time'].iloc[i] ))


#find the size between IDR frames through the byteoffset information
size = [] # to store the size between IDRs
smallest = tuple[0][0]
largest = tuple[-1][1]


last = IDR[-1][1]
tupleIndex = 0
IDRIndex = 0


firstToken = True
sameTuple = True

previous = 0
sum = 0  #cumulated offset

# print('Success in getting all IDR: [frame, offset] *********')
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
# print("*************** size2 *************")
# print(size2)
# print('######size2 byteoffset')
output = []
for i in size2:
    output.append(i[1])

# print(output)



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
videoIDR = []

for a in size2:
    sample.append(a[0])
    finalStartTime.append(a[2])
    videoIDR.append(a[1])

print('Success in get the list: (sample_number, IDR_offset, startTime, byte_range)')
# print(size2)
print("Total Candidate partition IDR number: ", len(sample))
############################ save tape csv file generation #######################################################

###########################################################################################
if(videoIDR[0] == byteOffset[0]):
    videoIDR.pop(0)
# print(videoIDR)
# print(byteOffset)
chunk = []
num = 1
target = []
videosum = 0
offsetIndex = 0


IDRIndex = 0
while offsetIndex < len(byteOffset):
    chunk.append(num)
    if(IDRIndex == len(videoIDR)):
        target.append("clip_" + str(IDRIndex) + ".mp4")
        offsetIndex = offsetIndex + 1
    else:
        if(videoIDR[IDRIndex] <= byteOffset[offsetIndex]):
            IDRIndex = IDRIndex + 1
            if (videoIDR[IDRIndex - 1] < byteOffset[offsetIndex]):
                temp = target[offsetIndex - 1]
                target[offsetIndex - 1] = temp + ", clip_" + str(IDRIndex)+".mp4"
        else:
            target.append("clip_" + str(IDRIndex) + ".mp4")
            offsetIndex = offsetIndex + 1
    num = num + 1

# print(target)  #####csv的video



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
    csv_line = '#clip, sample_number, bytes_offset, clip_size, clip_start_time'
    writer.writerows([csv_line.split(',')])
    writer.writerows(data_rows)

print("fished partition.csv")

# print('########test tape##########3')
#######################write tape###############
# write csv header
# csv_file = os.path.join(output_dir, 'test_tape.csv')
# with open(csv_file, 'w') as f:
#     writer = csv.writer(f)
#     csv_line = '#chunk, bytes_offset, bytes_size, track_name'
#     ####csv_line = '#chunk, bytes_offset, bytes_size, track_name, #delta_start, #delta_end, timescale, time range(s), tgt_file_name, tgt_bytes_offset, tgt_bytes_size'
#     writer.writerows([csv_line.split(',')])
# # write csv data
# with open(csv_file, 'a') as f:
#     writer = csv.writer(f)
#     video_ptr = 0
#     video_clip = 0

#     audio_ptr = [0]   ####要改回来
#     video_start_offset = 48
#     audio_start_offset = [44] #####改[44 for _ in range(len(audio_trak_idx))]

#     global_chunk_num = 0
#     flag = True
#     inner_lst = []
#     i=0
#     while i < len(video_stcz):
#         inner_lst.append(video_table[2][i][0])
#         i += 1
#     max_video_stco = max(inner_lst)


#     # for i in range(len(video_stcz)):
#     #     inner_lst.append(video_table[2][i][0])
#     # max_video_stco = max(inner_lst)


#     #max_video_stco = max([video_table[2][i][0] for i in range(len(video_stcz))])

#     max_audio_stco = []
#     tempAudio = []
#     idx = 0
#     while idx < len(audio_stcz):
#         jdx = 0
#         while jdx < len(audio_stcz[idx]):
#             tempAudio.append(audio_table[idx][2][jdx][0])
#             jdx = jdx + 1
#         max_audio_stco.append(max(tempAudio))
#         tempAudio = []
#         idx = idx + 1

#     # for i in range(len(audio_stcz)):
#     #     max_audio_stco.append(max([audio_table[i][2][j][0] for j in range(len(audio_stcz[i]))]))
#     max_stco = max(max_audio_stco+[max_video_stco])+1

#     while flag:
#         csv_line = '{}/'.format(global_chunk_num+1)
#         global_chunk_num += 1
#         cuurent_chunk_offset = []

#         idx = 0
#         while(idx < len(audio_trak_idx)):
#             current_ptr = audio_ptr[idx]
#             cuurent_chunk_offset.append(audio_table[idx][2][current_ptr][0])
#             idx = idx + 1
#         # for i in range(len(audio_trak_idx)):
#         #     current_ptr = audio_ptr[i]
#         #     cuurent_chunk_offset.append(audio_table[i][2][current_ptr][0])

#         cuurent_chunk_offset.append(video_table[2][video_ptr][0])
#         chunk_offset_argsort = argsort(cuurent_chunk_offset)
#         select_trakid = chunk_offset_argsort[0]
#         if select_trakid == len(audio_trak_idx):
#             #delta_start = sum(video_stts_flat[:video_stcl[video_ptr][0]])
#             #delta_end = sum(video_stts_flat[:video_stcl[video_ptr][-1]+1])
#             #####byteOffset = video_table[2][video_ptr][0] byteRange = video_stcz[video_ptr]

#             csv_line += '{}/{}/{}/'.format(
#                 video_table[2][video_ptr][0], video_stcz[video_ptr], \
#                 'video_{}'.format(video_trak_idx[0])
#             )




#             video_ptr += 1
#             if video_ptr == len(video_stcz):
#                 video_table[2].append([max_stco])

#         else:

#             csv_line += '{}/{}/{}/'.format(
#                 audio_table[select_trakid][2][audio_ptr[select_trakid]][0], \
#                 audio_stcz[select_trakid][audio_ptr[select_trakid]], \
#                 '{}_{}'.format(audio_name[select_trakid], audio_trak_idx[select_trakid])
#             )

#             #audio_start_offset[select_trakid] += audio_stcz[select_trakid][audio_ptr[select_trakid]]
#             audio_ptr[select_trakid] += 1
#             if audio_ptr[select_trakid] == len(audio_stcz[select_trakid]):
#                 audio_table[select_trakid][2].append([max_stco])

#         writer.writerows([csv_line.split('/')])
#         if video_ptr == len(video_stcz) and audio_ptr == [len(stcz) for stcz in audio_stcz]:
#             flag = False

# print('Succeed in testing tape #############test tape ########3')



###### The following segement by frame ffmpeg command line need postive integer to partition.

if len(sample) == 1 and sample[0] == 0 :
    print("The partition video is identical to the noAudio.mp4")
else:
    if 0 in sample:
        sample.remove(0)
    string = ",".join(str(x) for x in sample)
    #The command line to partition video based on candidate IDRs in sample
    cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -an -loglevel quiet "{}/clip_%d.mp4"'.format(
        input_file, string, os.path.join(output_dir, 'clips')
    )
    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    print('Succeed in partition videos base on IDR')






########添加online editor code 生成csv################3
import csv
chunk = global_trunck_num
byte_offset =  combineByteOffset #[26235, 279701, 287502, 388389, 396191]
byte_size = combineSize #[253466, 7801, 100887, 7802, 199587]
track_name = trackName #['video_0', 'audio_1', 'video_0', 'audio_1', 'video_0']
allTarget = [] # ['clip_0', 'clip_1', 'clip_2', 'clip_3', 'clip_4']
all = 0
vid = 0
aud = 0
# print("all target name num: ", len(track_name))
# print("all audio trunck: ", len(AudioTarget))
# print("all video trunck num: ", len(target))
while all < len(track_name):
    if "video" in track_name[all]:
        allTarget.append(target[vid])
        vid +=1
    else: 
        allTarget.append(AudioTarget[aud])
        aud +=1 
        
    all+=1


csv_name = os.path.join(output_dir, "columns.csv")
file = open(csv_name, "w")
writer = csv.writer(file)
csv_line = 'chunk, byte_offset, byte_size, track_name, target'
writer.writerows([csv_line.split(',')])

w = 0
while w < len(chunk):
    writer.writerow([chunk[w], byte_offset[w], byte_size[w], track_name[w], allTarget[w]])
    w+=1

file.close()

