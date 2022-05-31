import csv
import pandas as pd
from statistics import mean, median
import binascii
from utils import *

#start time和timerange的code
start_time = []
range = []
offset= []
with open("logfile2.csv", 'r') as file:
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
            start_time.append(total)


file.close()

# print(range)
if(start_time[0] != 0):
    start_time=[0]+start_time

i = 1
while i < len(start_time):
    range.append(start_time[i] - start_time[i - 1])
    i+=1

#需要添加：寻找offset和IDR的code





#通过byteoffset和IDR来找IDR之间的size:
size = []
tuple = [(3,7), (9,13), (15,19), (20, 25), (30,31)]
smallest = tuple[0][0]
largest = tuple[-1][1]
IDR = [4,10,31]
last = IDR[-1]
print(tuple)
print(IDR)
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

while(tupleIndex < len(tuple)):
    if (last >= tuple[tupleIndex][0] and last <= tuple[tupleIndex][1]):
        sum = tuple[tupleIndex][1] - last
    else:
        sum = sum + tuple[tupleIndex][1] - tuple[tupleIndex][0]
    tupleIndex = tupleIndex + 1
print("Last Value: " + str(sum)) 
size.append(sum)
                
                
print(size)

#之后是outlier和grouping

