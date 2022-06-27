from utils import *
import os
import shutil
import csv

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

def gen_meta_file(input_file, output_file):
    with open(input_file, 'rb') as f:
        hexdata = binascii.hexlify(f.read())
    offsets, atom_exist = parsing_atoms(hexdata, atom_name)

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
    with open(output_file, 'wb') as f:
        for i in range(len(atom_exist)):
            if atom_exist[sort_idx[i]] == 'mdat':
                f.write(binascii.unhexlify(
                    hexdata[int(byte_range[i][0]): int(byte_range[i][0]+8*2)]))
            else:
                f.write(binascii.unhexlify(
                    hexdata[int(byte_range[i][0]): int(byte_range[i][1])]))
    print("Success in generating ", output_file )
    return True

def byteInfo1(input_file, output_file):
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
            atom_exist[sort_idx[i]], int(byte_range[i][0]/2), int(byte_range[i][1]/2),
            hex(int(byte_range[i][1]/2)-int(byte_range[i][0]/2))

    # write all bytes except for data in valid mdat
    with open(output_file, 'wb') as f:
        for i in range(len(atom_exist)):
            if atom_exist[sort_idx[i]] == 'mdat':
                f.write(binascii.unhexlify(
                    hexdata[int(byte_range[i][0]): int(byte_range[i][0]+8*2)]))
            else:
                f.write(binascii.unhexlify(
                    hexdata[int(byte_range[i][0]): int(byte_range[i][1])]))

    moov_byte_range = byte_range[sort_idx.index(atom_exist.index('moov'))]
    moov_data = hexdata[int(moov_byte_range[0]): int(moov_byte_range[1])]
    trak_byte_range, video_trak_idx, audio_trak_idx, audio_name = finding_traks(
        moov_data, st_name)




def IDR_Info(input_file, IDRInfoPath):
    cut_cmd = 'ffmpeg -skip_frame nokey -i {} -vf showinfo -vsync 0 -f null - > {} 2>&1'.format(
        input_file, IDRInfoPath
    )
    exit_code = os.system(cut_cmd)
    if exit_code == 0:
        print('Succeed in getting IDR info')

    startTime = []
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
    print('Total IDR number: ', len(IDRoffset))
    return startTime, IDRoffset


def video_frames_info(input_file, FramesInfoPath):
    # record the All Frames info, including I, B,P frames ...
    cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
       FramesInfoPath, input_file
        )
    exit_code = os.system(cut_cmd)
    if exit_code == 0:
        print('Faild in getting Frames info')
    # To get IDR info by reading the log file, that the corresponding IDR sample number, IDR byteoffset
    offset= [] # All frames byteoffset
    frame = [] #  All frames Sample number
    # To get IDR info by reading the log file, that the audio size
    with open(FramesInfoPath, 'r') as file:
        lines = file.read().splitlines()
        for row in lines:
            if "stream 0" in row and "keyframe 1" in row:
                frame.append(int(row.split(',')[6].split(' ', 2)[2]))
                offset.append(int(row.split(',')[7].split(' ', 2)[2], 16))

    file.close()
    return offset, frame

def subtitle_frames_info(input_file, FramesInfoPath):
    # record the All Frames info, including I, B,P frames ...
    cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
       FramesInfoPath, input_file
        )
    exit_code = os.system(cut_cmd)
    if exit_code == 0:
        print('Faild in getting Frames info')

    size = []
    # To get IDR info by reading the log file, that the audio size
    with open(FramesInfoPath, 'r') as file:
        lines = file.read().splitlines()
        for row in lines:
            if "AVIndex stream 0" in row:
                size.append(int(row.split(',')[9].split(' ', 2)[2]))

    file.close()
    return size

def audio_frames_info(Audio,FramesInfoPath):
    cut_cmd = 'FFREPORT=file={}:level=56 ffmpeg -i {}  -f -segment_frames -reset_timestamps 1 -loglevel quiet'.format(
        FramesInfoPath, Audio
        )
    exit_code = os.system(cut_cmd)
    if exit_code == 0:
        print('cmd Failed: ', cut_cmd)

    audioOffset = []
    with open(FramesInfoPath, 'r') as file:
        lines = file.read().splitlines()
        for row in lines:
            if "AVIndex stream 0" in row:
                tempOffset = int(row.split(',')[7].split(' ', 2)[2], 16)
                audioOffset.append(tempOffset)

    file.close()
    audioSize = []
    for i in range(len(audioOffset) - 1):
        audioSize.append(audioOffset[i + 1] - audioOffset[i])

    return audioSize

# def cut_audio(start, audioSize, cutPlan, Audio, audio_output_dir, subtitle_output_dir, token):
#     if(start != len(audioSize) - 1):
#         cutPlan.append([start])
#     cutPlan[0] = [cutPlan[0][1]]


#     i = 0
#     while i < len(cutPlan):




#         string = ",".join(str(x) for x in cutPlan[i])
#         cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -map 0:a -c:s copy -c:a copy -vn -loglevel quiet "{}/%d_audio_{}.mp4"'.format(
#                 Audio, string, audio_output_dir, i
#             )
#         exit_code = os.system(cut_cmd)
#         if exit_code != 0:
#             print('command failed:', cut_cmd)


#         # Remove useless and make subtitles
#         if (i == 0) :
#             clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 1)
#             os.remove(clip_path1)

#             if token == True:
#                 sub_cmds='ffmpeg -i {}/{}audio_0.mp4 -map 0:s {}/subtitle_{}.srt -map 0:a {}/audioclip_{}.mp4'.format(
#                     os.path.join(audio_output_dir), i, subtitle_output_dir, i, audio_output_dir, i
#                 )
#                 exit_code = os.system(sub_cmds)
#                 if exit_code != 0:
#                     print('command failed:', sub_cmds)

#                 clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 0)
#                 os.remove(clip_path2)
#         elif (i > 0  and i < len(cutPlan)-1 ):
#             clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 0)
#             clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),i, 2)
#             os.remove(clip_path1)
#             os.remove(clip_path2)

#             if token == True:
#                 sub_cmds='ffmpeg -i {}/{}audio_1.mp4 -map 0:s:0 {}/subtitle_{}.srt -map 0:a {}/audioclip_{}.mp4'.format(
#                     os.path.join(audio_output_dir), i, subtitle_output_dir, i, audio_output_dir, i
#                 )
#                 exit_code = os.system(sub_cmds)
#                 if exit_code != 0:
#                     print('command failed:', sub_cmds)

#                 clip_path3 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 1)
#                 os.remove(clip_path3)
#         else:
#             clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),i, 0)
#             os.remove(clip_path1)

#             if token == True:
#                 sub_cmds='ffmpeg -i {}/{}audio_1.mp4 -map 0:s:0 {}/subtitle_{}.srt -map 0:a {}/audioclip_{}.mp4'.format(
#                     os.path.join(audio_output_dir), i, subtitle_output_dir, i, audio_output_dir, i
#                 )
#                 exit_code = os.system(sub_cmds)
#                 if exit_code != 0:
#                     print('command failed:', sub_cmds)

#                 clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), i, 1)
#                 os.remove(clip_path2)
#         i += 1

#     print('Succeed in partition audio around 4.5 mb')

def cut_audio2(start, audioSize, cutPlan, Audio, audio_output_dir):
    if(start != len(audioSize) - 1):
        cutPlan.append([start])
    cutPlan[0] = [cutPlan[0][1]]

    print("cut plan: ")
    print(cutPlan)


    i = 0
    while i < len(cutPlan):
        string = ",".join(str(x) for x in cutPlan[i])
        cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -map 0:a -map 0:s -c:s copy -c:a copy -vn -loglevel quiet "{}/%daudio_{}.mp4"'.format(
                Audio, string, audio_output_dir, i
            )
        exit_code = os.system(cut_cmd)
        if exit_code != 0:
            cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -map 0:a -c:s copy -c:a copy -vn -loglevel quiet "{}/%daudio_{}.mp4"'.format(
                    Audio, string, audio_output_dir, i
                )
            exit_code = os.system(cut_cmd)
            if exit_code != 0:
                print('command failed:', cut_cmd)


        # Remove useless and make subtitles
        if (i == 0) :
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), 1, i)
            os.remove(clip_path1)
        elif (i > 0  and i < len(cutPlan)-1 ):
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), 0, i)
            clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),2, i)
            os.remove(clip_path1)
            os.remove(clip_path2)
        else:
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),0, i)
            os.remove(clip_path1)
        i += 1

    print('Succeed in partition audio around 4.5 mb')


def cut_audio3(start, audioSize, cutPlan, Audio, audio_output_dir):
    if(start != len(audioSize) - 1):
        cutPlan.append([start])
    print("cutPlan: ", cutPlan)
    cutPlan[0] = [cutPlan[0][1]]

    print("cut plan: ")
    print(cutPlan)


    i = 0
    while i < len(cutPlan):
        string = ",".join(str(x) for x in cutPlan[i])
        cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -map 0:a -c:a copy -vn -sn -loglevel quiet "{}/%daudio_{}.mp4"'.format(
                Audio, string, audio_output_dir, i
            )
        exit_code = os.system(cut_cmd)
        if exit_code != 0:
            print('command failed:', cut_cmd)


        # Remove useless and make subtitles
        if (i == 0) :
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), 1, i)
            os.remove(clip_path1)
        elif (i > 0  and i < len(cutPlan)-1 ):
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir), 0, i)
            clip_path2 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),2, i)
            os.remove(clip_path1)
            os.remove(clip_path2)
        else:
            clip_path1 = "{}/{}audio_{}.mp4".format(os.path.join(audio_output_dir),0, i)
            os.remove(clip_path1)
        i += 1

    print('Succeed in partition audio around 4.5 mb')

def cut_video(sample, input_file, video_clips_dir):

    if len(sample) == 1 and sample[0] == 0 :
        print("The partition video is identical to the VideoOnly.mp4")

        cut_cmd='ffmpeg -i {} -c copy -an -loglevel quiet "{}/clip_0.mp4"'.format(
            input_file, video_clips_dir
        )
        exit_code = os.system(cut_cmd)
        if exit_code != 0:
            print('command failed:', cut_cmd)
    else:
        if 0 in sample:
            sample.remove(0)
        string = ",".join(str(x) for x in sample)
        #The command line to partition video based on candidate IDRs in sample
        cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -an -loglevel quiet "{}/clip_%d.mp4"'.format(
            input_file, string, video_clips_dir
        )
        exit_code = os.system(cut_cmd)
        if exit_code != 0:
            print('command failed:', cut_cmd)

        print('Succeed in partition videos base on IDR')


def cut_subtitle(input_file, subtitle_clips_dir, subtitleSize):
    targetSize = 4500000
    currSum = 0
    cutPlan = []
    counter = 0
    subtitleTarget = []
    for i in range(len(subtitleSize)):
        currSum = currSum + subtitleSize[i]
        if(currSum >= targetSize):
            cutPlan.append(i)
            currSum = 0
            counter = counter + 1
        subtitleTarget.append("subtitle_" + str(counter) + ".mp4")


    string = ",".join(str(x) for x in cutPlan)
    #The command line to partition video based on candidate IDRs in sample
    cut_cmd='ffmpeg -i {} -f segment -segment_frames {} -reset_timestamps 1 -c copy -an -loglevel quiet "{}/subtitle_%d.mp4"'.format(
        input_file, string, subtitle_clips_dir
    )
    exit_code = os.system(cut_cmd)
    if exit_code != 0:
        print('command failed:', cut_cmd)
    print('Succeed in partition videos base on IDR')

    return subtitleTarget


###########Audio processing function#####################
#input: audioSize, AudioSize2
#output: start, cutPlan, AudioTarget

def audioCutPlan(audioSize, AudioSize2, output_dir):

    AudioTarget = []  ###输出分类// for reconstruction audio "0clip_0.mp4"
    AudioIndex = 80000

    targetSize = 4500000 # 4.5MB
    overlap = 80000 # 大约五秒？
    cutPlan = []
    overall = []
    sum = 0
    start = 0
    i = 0
    remaining = 0
    recon_overlap = []
    while (i < len(audioSize)):
        overlap = 80000 # 大约五秒？
        sum = sum + audioSize[i]
        if (sum >= targetSize):
            tempMinus = 0
            if (AudioIndex != 0):
                tempMinus = overlap
            tempSum = remaining
            while (tempSum < sum and len(AudioSize2) > 0):
                tempSum = tempSum + AudioSize2.pop(0)
                tempStr = 1
                if (AudioIndex == 0):
                    tempStr = 0
                AudioTarget.append(str(AudioIndex) + "audio_" + str(tempStr) + ".mp4")
                if (tempSum >= sum):
                    remaining = tempSum - sum - tempMinus
                    if (remaining > 0):
                        lastIndex = len(AudioTarget) - 1
                        temp = AudioTarget[lastIndex]
                        AudioTarget[lastIndex] = temp + ", " + str(AudioIndex + 1) + "audio_1.mp4"
            AudioIndex = AudioIndex + 1

            overall.append(sum)
            cutPlan.append([start, i + 1])
            sum = 0
            minusOffset = 0
            recon_temp = 0
            while (overlap > 0):
                overlap = overlap - audioSize[i - minusOffset]
                recon_temp = recon_temp + audioSize[i - minusOffset]
                minusOffset = minusOffset + 1
            recon_overlap.append(recon_temp)
            start = i + 1 - minusOffset
            i = start - 1
            # print(start)
        i = i + 1
    csv_name = os.path.join(output_dir, "recon_overlap.csv")
    file = open(csv_name, "w")
    writer = csv.writer(file)
    writer.writerow(recon_overlap)
    file.close()


    if (sum > 0 and len(AudioSize2) > 0):
        i = 0
        while (i < len(AudioSize2)):
            tempStr = 1
            if (AudioIndex == 0):
                tempStr = 0
            AudioTarget.append(str(AudioIndex) + "audio_" + str(tempStr) + ".mp4")
            i = i + 1
    print('succed in getting videoCutPlan info: start, cutPlan, AudioTarget')
    print('AudioTarget: for reconstruction audio "0clip_0.mp4"')
    return start, cutPlan, AudioTarget





#############video processing function ########################
#input: tuple, IDR
#output:  size2

def videoProcessing(tuple, IDR):
    #find the size between IDR frames through the byteoffset information
    size = []  # to store the size between IDRs
    smallest = tuple[0][0]
    largest = tuple[-1][1]

    last = IDR[-1][1]
    tupleIndex = 0
    IDRIndex = 0

    firstToken = True
    sameTuple = True

    previous = 0
    sum = 0  # cumulated offset

    while (IDRIndex < len(IDR)):
        # the condition where IDR is not in the video (actually this situation doesn't exists )
        if (IDR[IDRIndex][1] < smallest or last > largest):
            IDRIndex = IDRIndex + 1
        # We only consider that all IDR byteoffset are increasing, otherwise we drop the wired IDR
        elif (IDR[IDRIndex][1] >= previous):
            # the condition in the first IDR
            if (firstToken == True):
                # if IDR is inside the tuple, then we calculate offset directly, otherwise we jump to the next tuple
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
            # To calculate IDR offsets after the first tuple
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
            # There exists some weird IDR frames which is not monotnously increading, so we pop those IDRs which are suddenly decreasing
            IDR.pop(IDRIndex)

    while (tupleIndex < len(tuple)):
        if (last >= tuple[tupleIndex][0] and last <= tuple[tupleIndex][1]):
            sum = tuple[tupleIndex][1] - last
        else:
            sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
        tupleIndex = tupleIndex + 1
    # print("Last Value: " + str(sum))
    size.append(sum)
    newIDR = []
    print("Succeed in getting video size between IDRs ")


    if size[0] == 0:
        size.pop(0)
        newIDR = IDR
    else:
        newIDR = [[0, smallest, 0]] + IDR  # [frame, offset, startTime]
    size2 = []  # size2 is the tupple (frame, byte_offset, startTime, size)
    i = 0
    while i < len(newIDR):
        lst = [newIDR[i][0], newIDR[i][1], newIDR[i][2], size[i]]
        if (lst[1] != 0 and lst[3] != 0):
            size2.append((newIDR[i][0], newIDR[i][1], newIDR[i][2], size[i]))
        i += 1

    # print('succeed in getting size2: the tupple (frame, byte_offset, startTime, size)')

    return size2


#input: size2

#return videoIDR, newsize2, sample
def groupTofindcandidateIDR(size2):
    # Grouping the videos to approximately 4.5 mb.
    tot_len = 0
    arbitraryNumber = 4500000  # 4.5 mb
    i = 0

    tempSize = 0
    while i < len(size2):
        if (len(size2) != 1):
            if (size2[i][3] < arbitraryNumber and i != len(size2) - 1):
                temp = size2[i][3] + size2[i + 1][3]
                diff1 = abs(temp - arbitraryNumber)
                diff2 = abs(size2[i][3] - arbitraryNumber)
                if (diff1 <= diff2 or size2[i][3] <= 0.1 * arbitraryNumber):
                    size2[i] = (size2[i][0], size2[i][1], size2[i][2], temp)
                    size2.pop(i + 1)
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
    newsize2 = size2
    # print('Success in get the newsize2 list: (sample_number, IDR_offset, startTime, byte_range)')

    #return videoIDR, newsize2, sample
    return videoIDR, newsize2, sample
