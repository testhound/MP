import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import datetime
import time
import dateutil.relativedelta
import BaseClasses as bcs

Exclusion_list = ['QQQ','SPY']

def cal_market_proflie(df,openRangeSize,initialBalDelta,mode):
    factor = 100.0
    r_min = df.Close.min()
    r_max =  df.Close.max()
    tickSize =  (r_max - r_min+1)/factor
    #tickSize = 0.01
    tickSize = math.floor(tickSize) if tickSize>1 else round(tickSize,2)
    print(f'tickSize = {tickSize}')
    mp = bcs.MarketProfile(df, tick_size = tickSize,
                       open_range_size = openRangeSize,
                       initial_balance_delta = initialBalDelta,
                       mode=mode)

    mp_slice = mp[0:len(df.index)]

    #val=mp_slice.value_area[0]
    #vah=mp_slice.value_area[1]
    #poc=mp_slice.poc_price
    
    return mp_slice

def r_tp(tup,x=2):
        return round(tup[0],x),round(tup[1],x)

def get_from_to_pair(sym):
    if sym in Exclusion_list:
        return '00:01','23:59'
    else:
        return '9:30','16:00'

def get_adjusted_dt(s_dt,month,year):
    flag = True 
    day = s_dt.day
    while(flag):
        try:       
            #dt = datetime.datetime.now()
            dt2 = s_dt.replace(day = day,month = month, year = year)
            flag = False
            #print(dt2)
        except Exception as e:
            day-=1
            #print(e)
    return dt2

def df_null_check(df):
    if len(df)==0:
        print('No data available for the requested period')
        return True
    else:
        return False

def save_chart(fname,data,val,vah,poc):
    plt.figure()
    plt.plot(data)
    g_line = plt.axhline(y=vah,linewidth=2, color='green', label ='vah')
    r_line = plt.axhline(y=val,linewidth=2, color='red',label ='val')
    y_line = plt.axhline(y=poc,linewidth=2, color='yellow',label ='poc')
    plt.legend(handles=[g_line,r_line,y_line])
    diff = (data.max()-data.min()+1)/30
    yAxStep = round(diff) if (diff)>1 else round(diff,2)
    plt.yticks(np.arange(math.floor(min(data)), math.ceil(max(data))+yAxStep,yAxStep))
    fig = plt.gcf()
    fig.set_size_inches(22, 11)
    fig.savefig(fname, dpi=98, bbox_inches='tight', pad_inches=0.1)
    
def save_profile(fname,profile):
    plt.figure() 
    cName = 'Close'
    df_bars =  pd.DataFrame(columns=[cName,'freq'])
    df_bars[cName] = profile.index
    df_bars['freq'] = profile.values
    df_bars[cName] = df_bars[cName].round(2)
    data = df_bars.groupby(cName)['freq'].sum()
    img1 = data.plot(kind='barh')
    #img1.figure.set_size_inches(22, 10.5)
    img1.figure.set_size_inches(44, 22)

    plt.grid(b = True, color ='grey', 
        linestyle ='-.', linewidth = 0.5, 
        alpha = 0.2)

    # for i in img1.patches: 
    #     plt.text(i.get_width()+0.2, i.get_y()+0.25,  
    #         str(round((i.get_width()), 2)), 
    #         fontsize = 15, fontweight ='bold', 
    #         color ='grey')

    img1.figure.savefig(fname, dpi=98, bbox_inches='tight', pad_inches=0.1)
