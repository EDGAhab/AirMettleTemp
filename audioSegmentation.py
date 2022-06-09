
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
