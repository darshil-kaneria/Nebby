import bisect
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from sklearn.metrics import mean_squared_error as mse

from globals_lakshay import MAX_DEG
from bif_lakshay import *
from features_lakshay import *

def lower_bound(arr, target):
    index = bisect.bisect_left(arr, target)
    return index

def sample_data_time(time, data, ss, m):
    # Check if we have valid data
    if len(time) == 0 or len(data) == 0:
        return [], []
    
    curr_time, curr_data = adjust(time, data)
    
    # Check again after adjust
    if len(curr_time) == 0 or len(curr_data) == 0:
        return [], []
    tp = curr_time[len(curr_time)-1] - curr_time[0]
    step = tp/m
    samp_time = [curr_time[0] + i*step for i in range(m)]
    x = np.random.uniform(0,math.pi,ss)
    tr_x = np.cos(x)
    tr_x += 1
    tr_x *= (m-1)/2
    ind = [int(round(e, 0)) for e in tr_x]
    sort_ind = sorted(ind)
    tr_time = [samp_time[i] for i in sort_ind]
    new_time = []
    new_data = []
    for t in tr_time :
        i = lower_bound(curr_time, t)
        temp_t = 0
        temp_d = 0
        if round(t,6) == round(curr_time[i],6):
            temp_t = curr_time[i]
            temp_d = curr_data[i]
        else : 
            if i == 0 :
                temp_t = curr_time[i]
                temp_d = curr_data[i]
            elif i == len(curr_time)-1 :
                temp_t = curr_time[i]
                temp_d = curr_data[i]
            else :
                temp_t = (curr_time[i-1] + curr_time[i])/2
                temp_d = (curr_data[i-1] + curr_data[i])/2
        new_time.append(temp_t)
        new_data.append(temp_d)
#     return curr_time, curr_data
    return new_time, new_data

def adjust(time, data):
    # Check if data is empty or too short
    if len(data) < 2:
        return time, data
    
    start = data.index(min(data[:int(len(data)/2)]))
    end = data.index(max(data[int(len(data)/2):]))
    
    if end - start <= 0: 
        return time, data
    new_time = time[start:end+1]
    new_data = data[start:end+1]
    return new_time, new_data


def getRed(files,ss=225,p="y", ft_thresh=3):
    results = []
    for file in files :   
        f_split = file.split("-")
        v = f_split[0] + "-" + f_split[1]
        rtt = float((int(f_split[2]) + int(f_split[3]))*2)/1000
        bdp = float(rtt*1000*int(f_split[4])*int(f_split[5]))/8
        # print(file)
        # print("RTT",rtt,"BDP",bdp)
        time, data, features = get_plot_features(file, p=p)
        count = 1
        for ft in features : 
            if count > ft_thresh:
                break
            curr_time = time[ft[0]:ft[1]+1]
            curr_data = data[ft[0]:ft[1]+1]
            tr_time, tr_data = sample_data_time(curr_time, curr_data, ss, 1000)
            tr_time_pd = pd.DataFrame(tr_time)
            tr_data_pd = pd.DataFrame(tr_data)
            tr_time = list(tr_time_pd.rolling(25, center=True).mean().dropna()[0])
            tr_data = list(tr_data_pd.rolling(25, center=True).mean().dropna()[0])
            # print("Feature Length ", len(tr_data))
            if p == "y" :
                plt.plot(curr_time, curr_data, c='b', alpha = 0.5, lw = 5)
                plt.plot(tr_time, tr_data, c='r', alpha = 1)
                plt.scatter(tr_time, tr_data, c='k')
#                 plt.scatter(tr_time, tr_data, c='r', s=10)
                plt.title(v)
                plt.show()
            results.append(
                {v+"_"+"data"+"_"+str(count):tr_data,
                     v+"_"+"time"+"_"+str(count):tr_time,
                        v+"_"+"rtt"+"_"+str(count):rtt, 
                             v+"_"+"bdp"+"_"+str(count):bdp})
            count+=1
    return results


    
def get_degree(time, data, p="n", max_deg=5):
    # Check for valid input data
    if len(time) < 2 or len(data) < 2 or len(time) != len(data):
        print("Invalid input data for polynomial fitting")
        return 1, [0, 0], [1.0]
    
    # Check for constant data (no variation)
    if max(data) == min(data):
        print("Data has no variation, using constant polynomial")
        return 1, [min(data)], [0.0]
    
    # Check for numerical issues
    if any(not np.isfinite(x) for x in time + data):
        print("Data contains non-finite values")
        return 1, [0, 0], [1.0]
    
    p_net = []
    mse_l = []
    fit_net = []
    
    for d in range(1, max_deg + 1):
        try:
            # Normalize time to avoid numerical issues
            time_norm = np.array(time)
            time_norm = (time_norm - np.min(time_norm)) / (np.max(time_norm) - np.min(time_norm) + 1e-10)
            
            p_temp = np.polyfit(time_norm, data, d)
            p_net.append(p_temp)
            fit_net.append(np.polyval(p_temp, time_norm))
            
            # Calculate MSE
            mse_val = np.mean((np.array(data) - fit_net[-1])**2)
            mse_l.append(mse_val)
            
        except (np.linalg.LinAlgError, np.RankWarning, ValueError) as e:
            print(f"Polynomial fitting failed for degree {d}: {e}")
            # Use previous degree or fallback
            if len(p_net) > 0:
                break
            else:
                # Fallback to linear fit with the mean
                p_net.append([np.mean(data)])
                fit_net.append([np.mean(data)] * len(data))
                mse_l.append(np.var(data))
                break
    
    if len(p_net) == 0:
        # Complete fallback
        return 1, [np.mean(data)], [1.0]
    
    if p == 'y':
        plt.plot(time, data, c='k', label='Truth')
        for d in range(min(len(fit_net), max_deg) - 1, min(len(fit_net), max_deg)):
            if d < len(fit_net):
                plt.plot(time, fit_net[d], label="degree" + str(d + 1))
        plt.legend()
        plt.show()
    
    best_degree = len(p_net)
    return best_degree, p_net[-1], mse_l

def normalize(time, data, rtt, bdp):
    new_time = (time/rtt)
    new_data = (data/bdp)*100
    new_time -=min(new_time)
    new_data -=min(new_data)
    return new_time, new_data


def get_feature_degree(files,ss=225,p='n',ft_thresh=3,max_deg=5):
    results = getRed(files,ss,p=p,ft_thresh=ft_thresh)
    # errors = []
    mp = {}
    cc_mp = {}
    count_features = 0
    for item in results :
        for ele in list(item.keys()):
            name_list = ele.split("_")
            cc = name_list[0]
            name = name_list[0] + name_list[-1]
            if "data" in ele :
                curr_data = np.array(item[ele])
            if "time" in ele :
                curr_time = np.array(item[ele])
            if "rtt" in ele :
                curr_rtt = item[ele]
            if "bdp" in ele :
                curr_bdp = item[ele]
        curr_time, curr_data = normalize(curr_time, curr_data, curr_rtt, curr_bdp)
        count_features += 1
        # print("Name :",name)
        degree, coeff, error_item = get_degree(curr_time, curr_data,p=p,max_deg=max_deg)
        mp[name] = {'d':degree, 'coeff':coeff, 'error':error_item, 'data':curr_data, 'time':curr_time}
        if cc not in cc_mp :
            cc_mp[cc] = []
        cc_mp[cc].append(mp[name])
        # error_item.append(name)
        # error_item.append(degree)
        # errors.append(error_item)
    # return cc_mp, errors
    return cc_mp

def getCC(files,cc_mp, p="n"):
    # experiment change start
    cc_coeff = {}
    for file in files :
#         file = v + "-0-50-1000-2"
        curr_file = file
        f_split = file.split("-") 
        cc = f_split[0]
        version = f_split[1]
        v = cc+"-"+version
        if cc not in cc_coeff:
            cc_coeff[cc] = []
    # experiment change end
        time, data, retrans, rtt = plot_one_bt(curr_file, p)
        count = 0
        temp = []
        if v not in cc_mp.keys():
            continue
        n = math.ceil(float(len(cc_mp[v]))/3)
        for item in cc_mp[v]:
            time = item['time']
            data = item['data']
            deg = item['d']
            temp.append(item['coeff'])    
            xlim = 0
            ylim = 0
            t = 1
            while time[-1] > t:
                t*=2
            xlim = t
            while data[-1] > t:
                t*=2
            ylim = t
            lim = max(xlim, ylim)
            names = []
            bars=[]
            for i in range(1,deg+1):
                bars.append(i)
                names.append(str(i))
            # print(names)
            # print(item['error'])
            count+=1
            if p == 'y':
                plt.plot(time,data)
                plt.plot(time, np.polyval(item['coeff'],time))
                plt.xlim(0,lim)
                plt.ylim(0,lim)
                plt.title(str(count)+" " + names[deg-1])
                plt.show()
#---              Showing the coefficient magnitude on a bar plot
#                 plt.figure().set_figwidth(4)
#                 plt.figure().set_figheight(2)
#                 plt.bar([i for i in range(1,deg+2)], item['coeff'])
#                 plt.show()
#---              Showing the change in error magnitute on a bar plot
                plt.figure().set_figwidth(4)
                plt.figure().set_figheight(2)
                plt.bar(bars, item['error'][0:deg], tick_label=names)
                plt.show()
        cc_coeff[cc].append(temp)
    return cc_coeff 

def showCC(files,ss=225,p='y',ft_thresh=1,max_deg=5):
    # cc_mp, errors = get_feature_degree(files,ss=ss,p="n",ft_thresh=ft_thresh,max_deg=max_deg)
    cc_mp = get_feature_degree(files,ss=ss,p="n",ft_thresh=ft_thresh,max_deg=max_deg)
    cc_coeff = getCC(files,cc_mp, p=p)
    return cc_coeff