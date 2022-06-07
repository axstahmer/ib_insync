from copy import copy
import pandas as pd
from ib_insync import *
#util.startLoop()

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=20)
util.logToConsole()
ib.isConnected()
#ib.disconnect()

isin_init_dt = pd.read_csv('ISIN_CAC_IB.csv')

isin_init_dt = isin_init_dt.loc[ isin_init_dt["EQY_PRIM_EXCH_SHRT"] == "FP" ]
isin_init_dt.reset_index(drop=True, inplace=True)

isin_init_dt["contracts"] = [ Contract(secIdType='ISIN', secId=isin_input, exchange='SBF', currency='EUR') for isin_input in isin_init_dt["ISIN"] ]
ib.qualifyContracts(*isin_init_dt["contracts"])


isin_init_dt['conId'] = 0

for i in range( isin_init_dt.shape[0] ):
    isin_init_dt['conId'][i] = isin_init_dt['contracts'][i].conId


#import time
#while True: #Infinite loop
#    f() #Execute the function
#    time.sleep(600) #Wait 600s (10 min) before re-entering the cycle


isin_dt = copy( isin_init_dt )

market_data_dt = util.df( ib.reqHistoricalData(
                contract = isin_dt["contracts"][0],
                endDateTime='', #'20220207 00:00:00',
                durationStr=  '2 D',# '3600 S', #'2 D', #600 S',
                barSizeSetting= '1 day', #'1 hour', #10 mins',# '1 day',
                whatToShow='MIDPOINT',
                useRTH=False,
                formatDate=1,
                keepUpToDate=False) )

market_data_dt['close'].pct_change(1).tail(1)[1]

isin_dt['Return'] = 0.0
isin_dt['Return'][0]

isin_dt['PX_LAST'] = 0.0
isin_dt['PX_LAST'][0]

for i in range( isin_dt.shape[0]):
    market_data_tmp_dt = util.df( ib.reqHistoricalData(
                contract = isin_dt["contracts"][i],
                endDateTime='', #'20220207 00:00:00',
                durationStr= '2 D', #600 S',
                barSizeSetting='1 day', #10 mins',# '1 day',
                whatToShow='MIDPOINT',
                useRTH=False,
                formatDate=1,
                keepUpToDate=False)) 
    isin_dt['PX_LAST'][i] = market_data_tmp_dt['close'].tail(1)[1]            
    isin_dt['Return'][i] = market_data_tmp_dt['close'].pct_change(1).tail(1)[1]
    print( isin_dt['ISIN'][i], isin_dt['PX_LAST'][i] , isin_dt['Return'][i] )

isin_dt['quantile'] = pd.qcut(isin_dt['Return'], q=5, labels=False)
isin_dt.sort_values('quantile', inplace=True)


isin_dt['DIRECTION'] = 'NONE'
isin_dt.loc[ isin_dt['quantile'] == 4 , 'DIRECTION' ] = 'SHORT'
isin_dt.loc[ isin_dt['quantile'] == 0 , 'DIRECTION' ] = 'LONG'

isin_dt['Notional_Total'] = 1000000
# Maybe replace with portfolio value instead of fixed number


isin_dt['Notional_Target_Pos'] = 0
isin_dt.loc[ isin_dt['DIRECTION'] == 'SHORT' , 'Notional_Target_Pos' ] =  - isin_dt['Notional_Total'] / isin_dt.groupby(['DIRECTION']).size()['SHORT']
isin_dt.loc[ isin_dt['DIRECTION'] == 'LONG' , 'Notional_Target_Pos' ] =  isin_dt['Notional_Total'] / isin_dt.groupby(['DIRECTION']).size()['LONG']

isin_dt["Target_Stk"] = round( isin_dt["Notional_Target_Pos"] /  isin_dt["PX_LAST"] )


positions_initial_dt = util.df( ib.positions() )
positions_initial_dt['conId'] = 0

for i in range( positions_initial_dt.shape[0] ):
    positions_initial_dt['conId'][i] = positions_initial_dt['contract'][i].conId


isin_dt = pd.merge( isin_dt, positions_initial_dt[['conId', 'position']], on='conId', how='left')

isin_dt.loc[ isin_dt['position'].isna() , 'position' ] = 0

isin_dt['Trade_Stk_Signed'] = round( isin_dt["Target_Stk"] - isin_dt["position"] )

isin_dt['Trade'] = 'NONE'
isin_dt.loc[ isin_dt['Trade_Stk_Signed'] < 0 , 'Trade' ] = 'SELL'
isin_dt.loc[ isin_dt['Trade_Stk_Signed'] > 0 , 'Trade' ] = 'BUY'

isin_dt['Trade_Stk'] = abs( isin_dt['Trade_Stk_Signed'] )

isin_orders_dt = isin_dt.loc[ isin_dt['Trade'] != 'NONE'].reset_index(drop=True)


isin_orders_dt['orders'] = ''
for i in range( isin_orders_dt.shape[0]):
    isin_orders_dt['orders'][i] = Order(orderType='MKT', action= isin_orders_dt['Trade'][i], totalQuantity = isin_orders_dt['Trade_Stk'][i] , transmit=False) 
    #isin_orders_dt['orders'][i] = Order(orderType='MKT', tif='OPG', action= isin_orders_dt['Trade'][i], totalQuantity = isin_orders_dt['Trade_Stk'][i] , transmit=False) 



for i in range( isin_orders_dt.shape[0]):
    _placeorder =  ib.placeOrder( isin_orders_dt["contracts"][i], isin_orders_dt["orders"][i] )
    del _placeorder

_placeorder

#for i in range( isin_orders_dt.shape[0]):
#    _cancelorder =  ib.cancelOrder(  isin_orders_dt["orders"][i] )


positions_dt = util.df( ib.positions() )
positions_dt['conId'] = 0

for i in range( positions_dt.shape[0] ):
    positions_dt['conId'][i] = positions_dt['contract'][i].conId

positions_dt = pd.merge( positions_dt, isin_dt[['conId', 'ISIN', 'LONG_COMP_NAME', 'PX_LAST' ]], on='conId', how='left')

positions_dt['Notional_Position'] = positions_dt['position'] * positions_dt['PX_LAST']

positions_dt

#util.df( ib.fills() )


