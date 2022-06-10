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
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0] +  '_audio')
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(os.path.join(output_dir, 'clips'))
os.mkdir(os.path.join(output_dir, 'other_streams'))


cut_cmd='ffmpeg -i {} -c copy -vn -loglevel quiet "{}/Audio.mp4"'.format(
    input_file, output_dir
)
exit_code = os.system(cut_cmd)
if exit_code != 0:
    print('command failed:', cut_cmd)

print('Succeed in generating audio')  

Audio =  os.path.join(output_dir, 'Audio.mp4')
# record the All Frames info, including I, B,P frames ...
cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
    os.path.join(output_dir, 'allFramesInfo.log'), Audio
    )
exit_code = os.system(cut_cmd)
if exit_code == 0:
    print('Faild in getting Frames info')
print('Success in getting allFramesInfo.log')

allFramesInfoPath = os.path.join(output_dir, 'allFramesInfo.log')


# To get IDR info by reading the log file, that the corresponding IDR sample number, IDR byteoffset

audioSize = [] #[size]

with open(allFramesInfoPath, 'r') as file:
    lines = file.read().splitlines()
    for row in lines:
        if "AVIndex stream 0" in row:
            # print(row)
            audioSize.append(int(row.split(',')[9].split(' ', 2)[2]))
            #c = int(row.split(',')[6].split(' ', 2)[2])
            #audioSize.append([b, c])


file.close()
print(audioSize)
print("****** auido size  overall") 
x = 0
for i in  audioSize:
    x+=i
print(x)

############################ Audio Grouping #######################################################
targetSize = 4500000  #4.5MB
overlap = 780         #大约五秒？
cutPlan = []
overall = []
sum = 0
start = 0
i = 0
while(i < len(audioSize)):
    overlap = 80000    #大约五秒？
    sum = sum + audioSize[i]
    if (sum >= targetSize):
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


if(start != len(audioSize) - 1):
    cutPlan.append([start])
cutPlan[0] = [cutPlan[0][1]]
print('##### cut plan ######')
print(cutPlan)
#[[0, 5], [4, 9], [8, 13], [12, 17], [16, 18]]
i = 0
while i < len(cutPlan):
    string = ",".join(str(x) for x in cutPlan[i])
    cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -loglevel quiet "{}/{}clip_%d.mp4"'.format(
            Audio, string, os.path.join(output_dir, 'clips'), i
        )
    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    

    # for the middle
    if (i == 0) :
        clip_path1 = "{}/{}clip_{}.mp4".format(os.path.join(output_dir, 'clips'), i, 1)
        cut_cmd_1 = 'rm -f {}'.format(clip_path1)
        exit_code = os.system(cut_cmd_1)
        if exit_code != 0:
            print('command failed:', cut_cmd_1)

    elif (i > 0  and i < len(cutPlan)-1 ): 
        clip_path1 = "{}/{}clip_{}.mp4".format(os.path.join(output_dir, 'clips'), i, 0)
        clip_path2 = "{}/{}clip_{}.mp4".format(os.path.join(output_dir, 'clips'),i, 2)
        cut_cmd_1 = 'rm -f {}'.format(clip_path1)
        cut_cmd_2 = 'rm -f {}'.format(clip_path2)
        exit_code = os.system(cut_cmd_1)
        if exit_code != 0:
            print('command failed:', cut_cmd_1)
        exit_code = os.system(cut_cmd_2)
        if exit_code != 0:
            print('command failed:', cut_cmd_2)
    else:
        clip_path1 = "{}/{}clip_{}.mp4".format(os.path.join(output_dir, 'clips'),i, 0)
        cut_cmd_1 = 'rm -f {}'.format(clip_path1)
        exit_code = os.system(cut_cmd_1)
        if exit_code != 0:
            print('command failed:', cut_cmd_1)


    i += 1

print('Succeed in partition videos base on IDR')
