import binascii
import re
import os
import csv
import shutil
import argparse
from utils import *
from utils2 import *
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

meta = input_file.split('/')[-1].split('.')[0]+'.meta'
v_meta = input_file.split('/')[-1].split('.')[0]+'VideoOnly.meta'
a_meta = input_file.split('/')[-1].split('.')[0]+'AudioOnly.meta'
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0])
audio_output_dir = os.path.join(output_dir, 'audio')
intermediate_dir = os.path.join(output_dir, 'intermediate')
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(audio_output_dir)
os.mkdir(intermediate_dir)
os.mkdir(os.path.join(output_dir, 'clips'))  # for video clips
os.mkdir(os.path.join(output_dir, 'other_streams')) # for subtitle


cut_cmdv='ffmpeg -i {} -c copy -an -loglevel quiet "{}/VideoOnly.mp4"'.format(
    input_file, output_dir
)

cut_cmd='ffmpeg -i {} -map 0:a -c:s copy -c:a copy -vn -loglevel quiet "{}/AudioOnly.mp4"'.format(
    input_file, output_dir
)


exit_code = os.system(cut_cmd)
if exit_code != 0:
    print('command failed:', cut_cmd)

exit_code = os.system(cut_cmdv)
if exit_code != 0:
    print('command failed:', cut_cmdv)

print('Succeed in generating VideoOnly.mp4 and AudioOnly.mp4')

VideoOnly =  os.path.join(output_dir, 'VideoOnly.mp4')
Audio =  os.path.join(output_dir, 'AudioOnly.mp4')

# Read VideoOnly.mp4 to get moov_data, track info

######################## generate meta data for videoOnly and AudioOnly  ################################
v_meta_path = os.path.join(intermediate_dir, v_meta)
a_meta_path = os.path.join(intermediate_dir, a_meta)

v_meta = gen_meta_file(VideoOnly, v_meta_path)
a_meta = gen_meta_file(Audio, a_meta_path)







############### meta data for video & audio file and get byte info ###############
meta_path = os.path.join(intermediate_dir, meta)
with open(input_file, 'rb') as f:
    hexdata = binascii.hexlify(f.read())

offsets, atom_exist = parsing_atoms(hexdata, atom_name)

# sort atoms and store their bytes range
sort_idx = argsort([offsets[i] for i in range(len(offsets))])
byte_range = [] # [start_offset, end_offset(not include)]
for i in range(len(atom_exist)):
    if i == len(atom_exist)-1:
        byte_range.append([offsets[sort_idx[i]]-8, len(hexdata)])
    else:
        byte_range.append([offsets[sort_idx[i]]-8, offsets[sort_idx[i+1]]-8])
    # print('Atom {} byte range: {}-{}, total {} bytes'.format(
    #     atom_exist[sort_idx[i]], int(byte_range[i][0]/2), int(byte_range[i][1]/2),
    #     hex(int(byte_range[i][1]/2)-int(byte_range[i][0]/2))))

# write all bytes except for data in valid mdat
with open(meta_path, 'wb') as f:
    for i in range(len(atom_exist)):
        if atom_exist[sort_idx[i]] == 'mdat':
            f.write(binascii.unhexlify(
                hexdata[int(byte_range[i][0]): int(byte_range[i][0]+8*2)]))
        else:
            f.write(binascii.unhexlify(
                hexdata[int(byte_range[i][0]): int(byte_range[i][1])]))
print("Success in generating ", meta_path )

moov_byte_range = byte_range[sort_idx.index(atom_exist.index('moov'))]
moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
trak_byte_range, video_trak_idx, audio_trak_idx, audio_name = finding_traks(
    moov_data, st_name)
if len(audio_trak_idx) == 0:
    # print('There\'s no audio/subtitle stream in this mp4...')
    shutil.rmtree(os.path.join(output_dir, 'other_streams'))

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
tuple = np.array((byteOffset,end_arr)).T  # all video trunck -- (byteOffset, byteOffset+byteRange)
print("Succeed in get video offsets tuple: (byteOffset, byteOffset+byteRange)")

############################ To get IDR info #######################################################
IDRInfoPath =  os.path.join(intermediate_dir, 'IDRinfo.csv')
startTime, IDRoffset = IDR_Info(input_file, IDRInfoPath)

############################ To get Video Frame Sample Number info #################################
FramesInfoPath = os.path.join(intermediate_dir, 'FramesInfo.log')
offset, frame = video_frames_info(input_file, FramesInfoPath)
############################ To get Audio Frame Size info ##########################################
A_FramesInfoPath = os.path.join(intermediate_dir, 'Audio_FramesInfo.log')
audioSize = audio_frames_info(Audio,A_FramesInfoPath)
bigsum = 0   # the whole audio size
for i in audioSize:
    bigsum = bigsum + i
######################### Cut Audio #################################################
start, cutPlan, AudioTarget = audioCutPlan(audioSize, AudioSize2, output_dir)

if bigsum <= 100000:
    cut_cmd='ffmpeg -i {} -c:s copy -c:a copy -vn -loglevel quiet "{}/0audio_0.mp4"'.format(
        input_file, audio_output_dir
    )
    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    print("Audio file less than 4.5 MB. There is no need to cut it")
else:
    print(Audio)
    cut_audio2(start, audioSize, cutPlan, Audio, audio_output_dir)

#################### Video Processing  ##########################################
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


size2 = videoProcessing(tuple, IDR)

videoIDR, newsize2, sample = groupTofindcandidateIDR(size2)
###### Find Video target
if(videoIDR[0] == byteOffset[0]):
    videoIDR.pop(0)

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
video_clips_dir = os.path.join(output_dir, 'clips')
cut_video(sample, input_file, video_clips_dir)
######## generate partition csv################3
import csv
chunk = global_trunck_num
byte_offset =  combineByteOffset #[26235, 279701, 287502, 388389, 396191]
byte_size = combineSize #[253466, 7801, 100887, 7802, 199587]
track_name = trackName #['video_0', 'audio_1', 'video_0', 'audio_1', 'video_0']
allTarget = [] # ['clip_0', 'clip_1', 'clip_2', 'clip_3', 'clip_4']
all = 0
vid = 0
aud = 0
while all < len(track_name):
    if "video" in track_name[all]:
        allTarget.append(target[vid])
        vid +=1
    else:
        allTarget.append(AudioTarget[aud])
        aud +=1

    all+=1


csv_name = os.path.join(output_dir, "partition.csv")
file = open(csv_name, "w")
writer = csv.writer(file)
csv_line = 'chunk, byte_offset, byte_size, track_name, target'
writer.writerows([csv_line.split(',')])

w = 0
while w < len(chunk):
    writer.writerow([chunk[w], byte_offset[w], byte_size[w], track_name[w], allTarget[w]])
    w+=1

file.close()
