import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import datetime
import time
import dateutil.relativedelta
import os
import fire
from Utils import cal_market_proflie
from Utils import save_chart
from Utils import save_profile
from Utils import r_tp
from Utils import get_adjusted_dt
from Utils import df_null_check
from Utils import get_from_to_pair

class MPapp:
    def __init__(self,inputf=''):
        self.API_KEY = 'T133DFH1BDEC1EPU' # replace demo with your api key 
        self.BASE_URL = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY_EXTENDED'
        self.BASE_URL_Rec = 'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY'
        #self.active_monthly_analysis = True
        #self.active_quarterly_analysis = True
        self.display_plots = False
        pdir = "Results/"
        self.dirP = pdir
        self.dirM = f"{pdir}Monthly/"
        self.dirQ = f"{pdir}Quarterly/"
        self.dirG = f"{pdir}Generic/"
        self.dirD = f"{pdir}Daily/"
        self.create_dirs()
        if inputf != '':
            self.s_list = self.read_symbols(inputf)
        self.df_summary = self.create_summary_df()
        
    def create_dirs(self):      
        if not os.path.exists(os.path.dirname(self.dirM)):
            os.makedirs(os.path.dirname(self.dirM))
        if not os.path.exists(os.path.dirname(self.dirQ)):
            os.makedirs(os.path.dirname(self.dirQ))
        if not os.path.exists(os.path.dirname(self.dirG)):
            os.makedirs(os.path.dirname(self.dirG))
        if not os.path.exists(os.path.dirname(self.dirD)):
            os.makedirs(os.path.dirname(self.dirD))
            
    def set_display_plots(self,decision):
        self.display_plots = decision
        if decision:
            plt.ion()
        else:
            plt.ioff()
                
    def get_last_month_data(self,symbol,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'
        dt = datetime.datetime.now()
        dt_to = dt.replace(day=1,hour=0, minute=0, second=0, microsecond=0)
        dt_from = dt_to - dateutil.relativedelta.relativedelta(months=1)

        df_p = pd.DataFrame()
        i=1
        while i<3:
            url = u1+f'slice=year1month{i}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue
            df_p = df_p.append(df_c)
            i+=1

        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p
    
    def get_last_quarter_data(self,symbol,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'
        dt = datetime.datetime.now()
        qtr = (dt.month-1)//3
        dt_to = dt.replace(month=(qtr*3)+1,day=1,hour=0, minute=0, second=0, microsecond=0)
        dt_from = dt_to - dateutil.relativedelta.relativedelta(months=3)

        df_p = pd.DataFrame()
        i=1
        while i<7:
            url = u1+f'slice=year1month{i}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue

            df_p = df_p.append(df_c)
            i+=1

        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p
    
    def get_current_close(self,symbol,barsize):
        url_rec = self.BASE_URL_Rec +  f'&symbol={symbol}&interval={barsize}min&apikey={self.API_KEY}&datatype=csv'
        df_rec = pd.read_csv(url_rec)

        if len(df_rec)<=2:
            a = df_rec.loc[0].to_json()
            print(a)
            if a.count("Thank you") == 1:
                print("------taking a pause for 1 minute-----")
                time.sleep(60)
                return self.get_current_close(symbol,barsize)
            else:
                print(f"Incorrect API Key or Symbol = {symbol} is not compatible")      
                return 0,0
        else:
            return df_rec.loc[0].timestamp, df_rec.loc[0].close
        
    def read_symbols(self,fname):
        df_symbols = pd.read_csv(fname)
        s_list = df_symbols["Symbol"].str.strip()
        return s_list
    
    def create_summary_df(self):
        df_summary = pd.DataFrame(columns=['Symbol','Quarter','Month','Initial_Balance','Opening_Range',
                                  'Profile_Range','POC','Value_Area','Balanced_Target','Last_Refresh_dt',
                                   'Close','Cond_Status'])
        return df_summary
    
    def run_monthly_analysis(self,mode='tpo'):
        ####-------------Monthly Analysis----------------
        #profile cal. parameters
        open_range_size = pd.to_timedelta('30 minutes')
        initial_balance_delta = pd.to_timedelta('3 days')#pd.to_timedelta('120 minutes')
        #mode='tpo' #-- tpo or vol

        #historical data parameters
        interval = 30 # in minutes 
        #from_time = '00:01' 
        #to_time = '23:59'

        for symb in self.s_list:
            ts,close = self.get_current_close(symb,5)
            if ts == 0:
                continue
            from_time, to_time = get_from_to_pair(symb)
            df_m = self.get_last_month_data(symb,interval,from_time,to_time)
            if df_null_check(df_m):
                print(f'Error Symbol {symb}')
                continue
            mnth = df_m.index[0].strftime("%B-%Y")

            mps = cal_market_proflie(df_m,open_range_size,initial_balance_delta,mode)

            condn = 'True' if (close>mps.value_area[0]) and (close<mps.value_area[1]) else 'False'

            self.df_summary.at[len(self.df_summary)] = [symb,'-',mnth,r_tp(mps.initial_balance()),r_tp(mps.open_range()),
                                            r_tp(mps.profile_range),mps.poc_price,r_tp(mps.value_area),mps.balanced_target,
                                            ts,close,condn]

            fname1 = f'{self.dirM}Profile_{symb}_{mnth}.png'
            save_profile(fname1,mps.profile)

            val=mps.value_area[0]
            vah=mps.value_area[1]
            poc=mps.poc_price
            data2 = df_m['Close']
            fname2 = f'{self.dirM}Chart_{symb}_{mnth}.png'
            save_chart(fname2,data2,val,vah,poc)
            
            plt.close('all')

        self.df_summary.to_csv(f'{self.dirP}Summary.csv',index=None)


    def run_quarterly_analysis(self,mode='tpo'):
        ###-----------Quarterly Analysis----------------
        plt.close('all')
        #profile cal. parameters
        open_range_size = pd.to_timedelta('30 minutes')
        initial_balance_delta = pd.to_timedelta('3 days')#pd.to_timedelta('120 minutes')
        #mode='tpo' #-- tpo or vol

        #historical data parameters
        interval = 30 # in minutes 
        #from_time = '00:01' 
        #to_time = '23:59'

        for symb in self.s_list:

            ts,close = self.get_current_close(symb,5)
            if ts == 0:
                continue

            from_time, to_time = get_from_to_pair(symb)
            df_m = self.get_last_quarter_data(symb,interval,from_time,to_time)
            if df_null_check(df_m):
                print(f'Error Symbol {symb}')
                continue
            qrtr = df_m.index[0].strftime("%B-%Y")


            mps = cal_market_proflie(df_m,open_range_size,initial_balance_delta,mode)

            condn = 'True' if (close>mps.value_area[0]) and (close<mps.value_area[1]) else 'False'

            self.df_summary.at[len(self.df_summary)] = [symb,qrtr,'-',r_tp(mps.initial_balance()),r_tp(mps.open_range()),
                                            r_tp(mps.profile_range),mps.poc_price,r_tp(mps.value_area),mps.balanced_target,
                                            ts,close,condn]

            fname1 = f'{self.dirQ}Profile_{symb}_{qrtr}.png'
            save_profile(fname1,mps.profile)

            val=mps.value_area[0]
            vah=mps.value_area[1]
            poc=mps.poc_price 
            fname2 = f'{self.dirQ}Chart_{symb}_{qrtr}.png'
            data2 = df_m['Close']
            save_chart(fname2,data2,val,vah,poc)

            plt.close('all')
        self.df_summary.to_csv(f'{self.dirP}Summary.csv',index=None)

    def get_previous_day_data(self,symbol,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'
        dt = datetime.datetime.now()
        dt_to = dt
        #dt_from = dt_to.replace(day=1,hour=0, minute=0, second=0, microsecond=0)
        
        df_p = pd.DataFrame()
        i=1
        while i<2:
            url = u1+f'slice=year1month{i}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue
            df_p = df_p.append(df_c)
            i+=1
            
        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        dt_from = df_p.index[-1].replace(hour=0, minute=0, second=0, microsecond=0)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p

    def get_current_month_data(self,symbol,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'
        dt = datetime.datetime.now()
        dt_to = dt
        dt_from = dt_to.replace(day=1,hour=0, minute=0, second=0, microsecond=0)
        
        df_p = pd.DataFrame()
        i=1
        while i<3:
            url = u1+f'slice=year1month{i}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue
            df_p = df_p.append(df_c)
            i+=1
            
        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p

    def get_specific_month_data(self,symbol,month,year,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'

        dt = datetime.datetime.now()
        dt2 = get_adjusted_dt(dt,month,year)
        #dt2 = dt.replace(month = month, year = year)
        dt_from = dt2.replace(day=1,hour=0, minute=0, second=0, microsecond=0)
        dt_to = dt_from + dateutil.relativedelta.relativedelta(months=1)

        k = (dt-dt2).days//30
        if k>20 or k<0:
            print("Not data available for given month")
            return -1
        i = k
        df_p = pd.DataFrame()
        while i<k+3 and i<24:
            x = 12 if i%12 == 0 else i%12
            y = (i//13) + 1
            url = u1+f'slice=year{int(y)}month{int(x)}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue
            df_p = df_p.append(df_c)
            df_c['time'] = pd.DatetimeIndex(df_c['time'])
            if df_c.time.iloc[-1] <= dt_from:
                break
            i+=1

        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p
    
    def get_specific_quarter_data(self,symbol,quarter,year,interval,from_time,to_time):
        u1 = self.BASE_URL + f'&symbol={symbol}&interval={interval}min&'
        u3 = f'&adjusted=true&apikey={self.API_KEY}'

        dt = datetime.datetime.now()
        dt2 = get_adjusted_dt(dt,quarter*3,year)
        #dt2 = dt.replace(month = quarter*3, year = year)
        dt_to = dt2.replace(day=1,hour=0, minute=0, second=0, microsecond=0) + dateutil.relativedelta.relativedelta(months=1)
        dt_from = dt_to - dateutil.relativedelta.relativedelta(months=3)

        k = (dt-dt2).days//30
        l = (dt-dt_from).days//30
        m = (dt-dt_to).days
        if l>21 or m<0:
            print("Not data available for given quarter")
            return -1
        i = k
        df_p = pd.DataFrame()
        while i<k+6 and i<24:
            x = 12 if i%12 == 0 else i%12
            y = (i//13) + 1
            url = u1+f'slice=year{int(y)}month{int(x)}'+u3
            df_c = pd.read_csv(url)
            if len(df_c)<=2:
                time.sleep(60)
                continue
            df_p = df_p.append(df_c)
            df_c['time'] = pd.DatetimeIndex(df_c['time'])
            if df_c.time.iloc[-1] <= dt_from:
                break
            i+=1

        df_p.columns = ['datetime','Open','High','Low','Close','Volume']
        df_p['datetime'] = pd.DatetimeIndex(df_p['datetime'])
        df_p.set_index('datetime',inplace = True)
        df_p.sort_index(inplace=True,ascending=True)
        df_p = df_p.between_time(from_time, to_time) 
        mask = (df_p.index > dt_from ) & (df_p.index < dt_to)
        df_p = df_p[mask]
        return df_p
    
    def generic_input_check(self,side,y,m=None,q=None):
        #side = "Quarterly" # "Monthly"
        #m = 1
        #y = 2019
        #q = 1
        dt = datetime.datetime.now()
        if side =="Monthly":
            if dt.month == m: # current month 
                return True 
            dt2 = dt.replace(year=y,month=m,day=1,hour=0, minute=0, second=0, microsecond=0)
            x = (dt-dt2).days//30
            if x>21 or x<1:
                print("Requested month data is out of valid range (only past 20 months will work)")
                return False
            else:
                #print("passed")
                return True
        elif side =="Quarterly":
            dt2 = get_adjusted_dt(dt,q*3,y)
            #dt2 = dt.replace(month = q*3, year = y)
            dt_to = dt2.replace(day=1,hour=0, minute=0, second=0, microsecond=0) + dateutil.relativedelta.relativedelta(months=1)
            dt_from = dt_to - dateutil.relativedelta.relativedelta(months=3)

            k = (dt-dt_from).days//30
            l = (dt-dt_to).days
            if k>21 or l<0:
                print("Requested Quarter data is out of valid range (only past 6 Quarter will work)")
                return False
            else:
                return True
    
    def generate_generic_profile(self,side,symbol,quarter,month,year,interval,from_time,to_time,
                    open_range_size,initial_balance_delta,mode):
        if self.generic_input_check(side,year,month,quarter) == False:
            return -1

        ts,close = self.get_current_close(symbol,5)

        if ts == 0:
            return -1
        df_data = None
        now = datetime.datetime.now()
        if side == 'Monthly':
            if now.month == month:
                df_data = self.get_current_month_data(symbol,interval,from_time,to_time)
            else:
                df_data = self.get_specific_month_data(symbol,month,year,interval,from_time,to_time)
            if df_null_check(df_data):
                return -1
            mmyy = df_data.index[0].strftime("%B-%Y")
            print(f"Monthly analysis (Month: {mmyy}) \nSymbol : {symbol}")
        elif side == 'Quarterly':
            df_data = self.get_specific_quarter_data(symbol,quarter,year,interval,from_time,to_time)
            if df_null_check(df_data):
                return -1
            mmyy = df_data.index[0].strftime("%B-%Y")
            print(f"Quarterly analysis (Quarter: {mmyy}) \nSymbol : {symbol}")

        mps = cal_market_proflie(df_data,open_range_size,initial_balance_delta,mode)

        condn = 'True' if (close>mps.value_area[0]) and (close<mps.value_area[1]) else 'False'

        print( "Initial balance: %f, %f" % r_tp(mps.initial_balance()))
        print( "Opening range: %f, %f" % r_tp(mps.open_range()))
        print( "POC: %f" % mps.poc_price)
        print( "Profile range: %f, %f" % r_tp(mps.profile_range))
        print( "Value area: %f, %f" % r_tp(mps.value_area))
        print( "Balanced Target: %f" % mps.balanced_target)
        print(f"Last available close = {close} at ts = {ts}")
        print(f"Condition Status = {condn}")

        fname1 = f'{self.dirG}Profile_{symbol}_{side}_{mmyy}.png'
        save_profile(fname1,mps.profile)

        val=mps.value_area[0]
        vah=mps.value_area[1]
        poc=mps.poc_price
        fname2 = f'{self.dirG}Chart_{symbol}_{side}_{mmyy}.png'
        data2 = df_data['Close']
        save_chart(fname2,data2,val,vah,poc)
        plt.close('all')
    
    def generate_previous_day_profile(self,symbol,interval,from_time,to_time,
                    open_range_size,initial_balance_delta,mode):

        ts,close = self.get_current_close(symbol,5)

        if ts == 0:
            return -1
        df_data = None
        df_data = self.get_previous_day_data(symbol,interval,from_time,to_time)
        if df_null_check(df_data):
                return -1
        mmyy = df_data.index[0].strftime("%B-%d-%Y")
        print(f"Single day analysis (Month: {mmyy}) \nSymbol : {symbol}")

        mps = cal_market_proflie(df_data,open_range_size,initial_balance_delta,mode)

        condn = 'True' if (close>mps.value_area[0]) and (close<mps.value_area[1]) else 'False'

        print( "Initial balance: %f, %f" % r_tp(mps.initial_balance()))
        print( "Opening range: %f, %f" % r_tp(mps.open_range()))
        print( "POC: %f" % mps.poc_price)
        print( "Profile range: %f, %f" % r_tp(mps.profile_range))
        print( "Value area: %f, %f" % r_tp(mps.value_area))
        print( "Balanced Target: %f" % mps.balanced_target)
        print(f"Last available close = {close} at ts = {ts}")
        print(f"Condition Status = {condn}")

        fname1 = f'{self.dirD}Profile_{symbol}_{mmyy}.png'
        save_profile(fname1,mps.profile)

        val=mps.value_area[0]
        vah=mps.value_area[1]
        poc=mps.poc_price
        fname2 = f'{self.dirD}Chart_{symbol}_{mmyy}.png'
        data2 = df_data['Close']
        save_chart(fname2,data2,val,vah,poc)
        plt.close('all')
    
    def generic_monthly_analysis(self,symbol,month,year,mode):
        #-----------------------------Generic Monthly Analysis -------------------------------------------
        self.set_display_plots(False)
        plt.close('all')

        #profile cal. parameters
        open_range_size = pd.to_timedelta('30 minutes')
        initial_balance_delta = pd.to_timedelta('3 days')#pd.to_timedelta('120 minutes')
        #mode='tpo' #-- tpo or vol

        #historical data parameters
        interval = 30 # in minutes 
        #from_time = '00:01' 
        #to_time = '23:59'
        from_time, to_time = get_from_to_pair(symbol)

        #Monthly Analysis parameters
        side = "Monthly"
        #symbol = "ETG"
        #month = 3 #1 to 12
        #year = 2020
        self.generate_generic_profile(side,symbol,None,month,year,interval,from_time,to_time,
                            open_range_size,initial_balance_delta,mode)
        
    def generic_quarterly_analysis(self,symbol,quarter,year,mode):
        #-----------------------------Generic Quarterly Analysis -------------------------------------------
        self.set_display_plots(False)
        plt.close('all')

        #profile cal. parameters
        open_range_size = pd.to_timedelta('30 minutes')
        initial_balance_delta = pd.to_timedelta('3 days')#pd.to_timedelta('120 minutes')
        #mode='tpo' #-- tpo or vol

        #historical data parameters
        interval = 30 # in minutes 
        #from_time = '00:01' 
        #to_time = '23:59'
        from_time, to_time = get_from_to_pair(symbol)

        #Quarterly Analysis parameters
        side = "Quarterly"
        #symbol = "ADX"
        #quarter = 1 #1 to 4
        #year = 2019
        self.generate_generic_profile(side,symbol,quarter,None,year,interval,from_time,to_time,
                            open_range_size,initial_balance_delta,mode)

    def run_generic_analysis(self,side,symbol,year,p,mode='tpo'):
        if side=="M":
            if p in list(range(1,13)):
                self.generic_monthly_analysis(symbol,p,year,mode)
            else:
                print('Invalid month')
        elif side=="Q":
            if p in list(range(1,5)):
                self.generic_quarterly_analysis(symbol,p,year,mode)
            else:
                print('Invalid quarter value')
        else:
            print('Invalid side specified')
        
    def run_prev_trading_day_analysis(self,symbol,mode):
        #-----------------------------Single Day Analysis -------------------------------------------
        self.set_display_plots(False)
        plt.close('all')

        #profile cal. parameters
        open_range_size = pd.to_timedelta('30 minutes')
        initial_balance_delta = pd.to_timedelta('120 minutes')
        #mode='tpo' #-- tpo or vol

        #historical data parameters
        interval = 30 # in minutes 
        #from_time = '00:01' 
        #to_time = '23:59'
        from_time, to_time = get_from_to_pair(symbol)

        self.generate_previous_day_profile(symbol,interval,from_time,to_time,
                            open_range_size,initial_balance_delta,mode)


if __name__ == '__main__':
  fire.Fire(MPapp)

#### Instructions
##1. run_monthly_analysis(self,mode='tpo')  TO RUN Market Profile ANALYSIS OVER SYMBOL LIST FOR Last Month
#    ### python MktProfApp.py --inputf='sym_small.csv' run_monthly_analysis
# OR ### python MktProfApp.py --inputf='sym_small.csv' run_monthly_analysis 'vol'
# OR ### python MktProfApp.py --inputf='sym_small.csv' run_monthly_analysis --mode='vol'
#    ###
##2. run_quarterly_analysis(self,mode='tpo') TO RUN Market Profile ANALYSIS OVER SYMBOL LIST FOR Last Quarter
#    ### python MktProfApp.py --inputf='sym_small.csv' run_quarterly_analysis
# OR ### python MktProfApp.py --inputf='sym_small.csv' run_quarterly_analysis 'vol'
# OR ### python MktProfApp.py --inputf='sym_small.csv' run_quarterly_analysis --mode='vol'
#    ###
##3. run_generic_analysis(self,side,symbol,year,p,mode='tpo') TO RUN Market Profile ANALYSIS FOR specific symbol over specified quarter or month
#    ### python MktProfApp.py run_generic_analysis
# OR ### python MktProfApp.py run_generic_analysis 'M' 'AMZN' 2020 7 'tpo'
# OR ### python MktProfApp.py run_generic_analysis 'Q' 'MSFT' 2020 1 'tpo'
# OR ### python MktProfApp.py run_generic_analysis --side='M' --symbol='AMZN' --year=2020 --p=7 --mode='tpo'
# OR ### python MktProfApp.py run_generic_analysis --side='Q' --symbol='AMZN' --year=2020 --p=2 --mode='tpo'
#    ###
##4. run_prev_trading_day_analysis(self,symbol,mode) TO RUN Market Profile ANALYSIS FOR specific symbol for previous trading day
## python MktProfApp.py run_prev_trading_day_analysis --symbol='AMZN' --mode='tpo'
