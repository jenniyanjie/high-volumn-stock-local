# -*- coding: utf-8 -*-
"""
Created on Sun May 29 17:19:35 2016

@author: Jennifer

pre-requisite:
    
1. install pattern library: 
    https://www.clips.uantwerpen.be/pages/pattern-web
2. install simplejson library:
    https://pypi.python.org/pypi/simplejson/
    
"""
from __future__ import division, print_function
import sys, os, errno, urllib2, pdb
from re import sub
from datetime import datetime, timedelta
from datetime import date as dtlib
from time import time
from google_screener_data_extract import GoogleStockDataExtract
import pandas_datareader as pdr
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.finance import candlestick_ohlc
import pylab
matplotlib.rcParams.update({'font.size': 9})


def screen_stock(exchange='SGX', ratio_threshold=2, op_all=False, op_sele=True, workDir=os.getcwd()):
    """
    exchange: 'SGX' or 'HKG'
    return: a list of stock symbols
    :param exchange:
    :param ratio_threshold:
    :param op_all:
    :param op_sele:
    :param workDir:
    :return:
    """
    suffix = {'SGX':'.SI', 'HKG': '.HK'}

    h = GoogleStockDataExtract(exchange)
    h.retrieve_all_stock_data()
    h_df = h.result_google_ext_df

    if op_all:
        op_f_all = os.path.join(workDir, datetime.now().strftime('%Y%m%d'),
                            'checkHighVolume_all' + \
                            datetime.now().strftime('%Y%m%d-%H%M') + \
                            '_all_' + exchange + '.csv')
        if not os.path.exists(os.path.dirname(op_f_all)):
            try:
                os.makedirs(os.path.dirname(op_f_all))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        h_df.to_csv(op_f_all, index = False)

    # selection:
    h_df['ratio'] = h_df['Volume'] / h_df['AverageVolume']

    sele = h_df.loc[((h_df['ratio'] >= ratio_threshold) & (h_df['QuotePercChange'] > 0) & \
                    (h_df['QuoteLast'] > h_df['PriceAverage_50Day']) & \
                    (h_df['TotalDebtToEquityQuarter'] < 100)), ]

    if op_sele:
        op_f_sele = os.path.join(workDir, datetime.now().strftime('%Y%m%d'),
        			'checkHighVolume_sele' + \
                    datetime.now().strftime('%Y%m%d-%H%M') + \
                    '_select_' + exchange + '.csv')
        if not os.path.exists(os.path.dirname(op_f_sele)):
            try:
                os.makedirs(os.path.dirname(op_f_sele))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        sele.to_csv(op_f_sele, index = False)
    symbols = [symb + suffix[exchange] for symb in sele['SYMBOL'].tolist()]
    return symbols


#%% for ploting
def rsiFunc(prices, n=14):
    deltas = np.diff(prices)
    seed = deltas[:n+1]
    up = seed[seed>=0].sum()/n
    down = -seed[seed<0].sum()/n
    rs = up/down
    rsi = np.zeros_like(prices)
    rsi[:n] = 100. - 100./(1.+rs)

    for i in range(n, len(prices)):
        delta = deltas[i-1] # cause the diff is 1 shorter

        if delta>0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up*(n-1) + upval)/n
        down = (down*(n-1) + downval)/n

        rs = up/down
        rsi[i] = 100. - 100./(1.+rs)

    return rsi


def movingaverage(values,window):
    weigths = np.repeat(1.0, window)/window
    smas = np.convolve(values, weigths, 'valid')
    return smas # as a numpy array


def ExpMovingAverage(values, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a


def computeMACD(x, slow=26, fast=12):
    """
    compute the MACD (Moving Average Convergence/Divergence) using a fast and slow exponential moving avg'
    return value is emaslow, emafast, macd which are len(x) arrays
    """
    emaslow = ExpMovingAverage(x, slow)
    emafast = ExpMovingAverage(x, fast)
    return emaslow, emafast, emafast - emaslow


def graphStock(stock, MA1, MA2, writeDir = os.getcwd()):
    '''
        Use this to dynamically pull a stock:
    '''
    # pulling data
    try:
        print('Currently Pulling', stock, '...')
        start = (datetime.now() - timedelta(days=2*365)).date()
        end = dtlib.today()
        data = pdr.get_data_yahoo(stock, start, end)

    except Exception,e:
        print(str(e), 'failed to pull pricing data')
    # plot
    try:
        # date, openp, highp, lowp, closep, closeadjp, volume = np.loadtxt(stockFile,delimiter=',',
        #                                                                  unpack=True,
        #                                                                  converters={ 0: mdates.strpdate2num('%Y-%m-%d')})
        data['Date'] = data.index
        data['Date'] = mdates.date2num(data['Date'].dt.to_pydatetime())
        date = np.array(data['Date'])
        closep = np.array(data['Close'])
        volume = np.array(data['Volume'])
        openp = np.array(data['Open'])
        highp = np.array(data['High'])
        lowp = np.array(data['Low'])


        x = 0
        y = len(date)
        newAr = []
        while x < y:
            appendLine = date[x],openp[x],highp[x],lowp[x],closep[x],volume[x]
            newAr.append(appendLine)
            x+=1

        Av1 = movingaverage(closep, MA1)
        Av2 = movingaverage(closep, MA2)

        SP = len(date[MA2-1:])

        fig = plt.figure(facecolor='#07000d')

        ax1 = plt.subplot2grid((6,4), (1,0), rowspan=4, colspan=4, axisbg='#07000d')
        candlestick_ohlc(ax1, newAr[-SP:], width=.6, colorup='#53c156', colordown='#ff1717')

        Label1 = str(MA1)+' SMA'
        Label2 = str(MA2)+' SMA'

        ax1.plot(date[-SP:],Av1[-SP:],'#e1edf9',label=Label1, linewidth=1.5)
        ax1.plot(date[-SP:],Av2[-SP:],'#4ee6fd',label=Label2, linewidth=1.5)

        ax1.grid(True, color='w')
        ax1.xaxis.set_major_locator(mticker.MaxNLocator(10))
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.yaxis.label.set_color("w")
        ax1.spines['bottom'].set_color("#5998ff")
        ax1.spines['top'].set_color("#5998ff")
        ax1.spines['left'].set_color("#5998ff")
        ax1.spines['right'].set_color("#5998ff")
        ax1.tick_params(axis='y', colors='w')
        plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
        ax1.tick_params(axis='x', colors='w')
        plt.ylabel('Stock price and Volume')

        maLeg = plt.legend(loc=9, ncol=2, prop={'size':7},
                   fancybox=True, borderaxespad=0.)
#        maLeg.get_frame().set_alpha(0.4)
#        textEd = pylab.gca().get_legend().get_texts()
#        pylab.setp(textEd[0:5], color = 'w')

        volumeMin = 0

        ax0 = plt.subplot2grid((6,4), (0,0), sharex=ax1, rowspan=1, colspan=4, axisbg='#07000d')
        rsi = rsiFunc(closep)
        rsiCol = '#c1f9f7'
        posCol = '#386d13'
        negCol = '#8f2020'

        ax0.plot(date[-SP:], rsi[-SP:], rsiCol, linewidth=1.5)
        ax0.axhline(70, color=negCol)
        ax0.axhline(30, color=posCol)
        ax0.fill_between(date[-SP:], rsi[-SP:], 70, where=(rsi[-SP:]>=70), facecolor=negCol, edgecolor=negCol, alpha=0.5)
        ax0.fill_between(date[-SP:], rsi[-SP:], 30, where=(rsi[-SP:]<=30), facecolor=posCol, edgecolor=posCol, alpha=0.5)
        ax0.set_yticks([30,70])
        ax0.yaxis.label.set_color("w")
        ax0.spines['bottom'].set_color("#5998ff")
        ax0.spines['top'].set_color("#5998ff")
        ax0.spines['left'].set_color("#5998ff")
        ax0.spines['right'].set_color("#5998ff")
        ax0.tick_params(axis='y', colors='w')
        ax0.tick_params(axis='x', colors='w')
        plt.ylabel('RSI')

        ax1v = ax1.twinx()
        ax1v.fill_between(date[-SP:],volumeMin, volume[-SP:], facecolor='#00ffe8', alpha=.4)
        ax1v.axes.yaxis.set_ticklabels([])
        ax1v.grid(False)
        ###Edit this to 3, so it's a bit larger
        ax1v.set_ylim(0, 3*volume.max())
        ax1v.spines['bottom'].set_color("#5998ff")
        ax1v.spines['top'].set_color("#5998ff")
        ax1v.spines['left'].set_color("#5998ff")
        ax1v.spines['right'].set_color("#5998ff")
        ax1v.tick_params(axis='x', colors='w')
        ax1v.tick_params(axis='y', colors='w')
        ax2 = plt.subplot2grid((6,4), (5,0), sharex=ax1, rowspan=1, colspan=4, axisbg='#07000d')
        fillcolor = '#00ffe8'
        nslow = 26
        nfast = 12
        nema = 9
        emaslow, emafast, macd = computeMACD(closep)
        ema9 = ExpMovingAverage(macd, nema)
        ax2.plot(date[-SP:], macd[-SP:], color='#4ee6fd', lw=2)
        ax2.plot(date[-SP:], ema9[-SP:], color='#e1edf9', lw=1)
        ax2.fill_between(date[-SP:], macd[-SP:]-ema9[-SP:], 0, alpha=0.5, facecolor=fillcolor, edgecolor=fillcolor)

        plt.gca().yaxis.set_major_locator(mticker.MaxNLocator(prune='upper'))
        ax2.spines['bottom'].set_color("#5998ff")
        ax2.spines['top'].set_color("#5998ff")
        ax2.spines['left'].set_color("#5998ff")
        ax2.spines['right'].set_color("#5998ff")
        ax2.tick_params(axis='x', colors='w')
        ax2.tick_params(axis='y', colors='w')
        plt.ylabel('MACD', color='w')
        ax2.yaxis.set_major_locator(mticker.MaxNLocator(nbins=5, prune='upper'))
        for label in ax2.xaxis.get_ticklabels():
            label.set_rotation(45)

        plt.suptitle(stock.upper(),color='w')

        plt.setp(ax0.get_xticklabels(), visible=False)
        plt.setp(ax1.get_xticklabels(), visible=False)

        plt.subplots_adjust(left=.09, bottom=.14, right=.94, top=.95, wspace=.20, hspace=0)
#        plt.show()
        # save the figure
        figNm = writeDir + '/' + datetime.now().strftime('%Y%m%d') + '/' + stock +'.jpg'
        if not os.path.exists(os.path.dirname(figNm)):
            try:
                os.makedirs(os.path.dirname(figNm))
            except OSError as exc: # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
        fig.savefig(figNm, dpi=900, facecolor=fig.get_facecolor())
        plt.close('all')
    except Exception, e:
        print('main loop:', str(e))

    return

#%% main
if __name__ == "__main__":

    currentPath = os.path.abspath(os.path.dirname(sys.argv[0])) # the path of current file
    writeDir = os.path.abspath(os.path.join(currentPath, '..')) # the parent directory
    # print(currentPath)
    # print(writeDir)

    #SGX --------------------------------------------------------------------#
    sgx_symb = screen_stock(exchange='SGX', ratio_threshold=2, workDir=writeDir, op_all=True)

    #HKG --------------------------------------------------------------------#
    hkg_symb = screen_stock(exchange='HKG', ratio_threshold=3, workDir=writeDir, op_all=True)

    symbols = sgx_symb + hkg_symb
    print('selected result: ', symbols)
    # plot the result -------------------------------------------------------#
    for symb in symbols:
        graphStock(symb, 50, 100, writeDir)


