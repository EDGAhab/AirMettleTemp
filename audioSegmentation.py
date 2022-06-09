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
output_dir = os.path.join(input_dir, input_file.split('/')[-1].split('.')[0], '_audio')
if os.path.isdir(output_dir):
    shutil.rmtree(output_dir)
os.mkdir(output_dir)
os.mkdir(os.path.join(output_dir, 'clips'))
os.mkdir(os.path.join(output_dir, 'other_streams'))


cut_cmd='ffmpeg -i {} -c copy -v -loglevel quiet "{}/Audio.mp4"'.format(
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
        if "stream 1" in row:
            audioSize.append(int(row.split(',')[9].split(' ', 2)[2]))
            #c = int(row.split(',')[6].split(' ', 2)[2])
            #audioSize.append([b, c])


file.close()


############################ Audio Grouping #######################################################
targetSize = 4500000  #4.5MB
overlap = 780         #大约五秒？
cutPlan = []

sum = 0
start = 0
i = 0
while(i < len(audioSize)):
    overlap = 780    #大约五秒？
    sum = sum + audioSize[i]
    if (sum >= targetSize):
        cutPlan.append([start, i])
        sum = 0
        minusOffset = 0
        while(overlap > 0):
            overlap = overlap - audioSize[i + minusOffset]
            minusOffset = minusOffset + 1
        start = i + 1 - minusOffset
        i = start - 1
        print(start)
    i = i + 1
    
if(start != len(audioSize) - 1):
    cutPlan.append([start,len(audioSize) - 1])
print(cutPlan)
#[[0, 5], [4, 9], [8, 13], [12, 17], [16, 18]]
