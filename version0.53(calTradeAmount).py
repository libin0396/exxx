# botvs@043465b2ba1c5689ca3f5faec1d4ba4f
# -*- coding: utf-8 -*-
import math
import sqlite3
import time
import json
import os
import numpy as np
import pandas as pd
import urllib2
import random
import uuid

_CDelay(500)
dbname = ''
currentState = []
pricemeanList = []
initState = []
tStart = time.time()
tradeOrdersNP = np.array([])
depthsCache = {}
depths = {}
accounts = {}
accountsCache = {}
priceMatrix = {}
feeInfo = {}
checkProfit = False
currentProfit = 0
lastProfit = 0
currentRatio = 0
balanceTime = 0
checkCancelOrderTime = 0
readDBTime = 0
cleanDBTime = 0
realProfitTime = time.time()
allTradeTimes = 0
needBalance = False
insertTradeHistoryDbValues =np.array([])
waitingOrders = np.array([])
tradehistoryDF = pd.DataFrame()
currentTradeDF = pd.DataFrame()
exInfoDF = pd.DataFrame()
gp = pd.DataFrame()
calProfit = 0
realProfit = 0
isTimeToGetProfit = False
allProfit = 0
cancelTimes = np.array([])
_currentBitcoin = 0
'''[switch]
v = 'ten'
for case in switch(v):
	if case('ten'):
		break
	if case():
		print ''
[switch]
'''
class switch(object):
	def __init__(self, value):
		self.value = value
		self.fall = False

	def __iter__(self):
		yield self.match
		raise StopIteration

	def match(self, *args):
		if self.fall or not args:
			return True
		elif self.value in args:
			self.fall = True
			return True
		else:
			return False

def cancelAll():
	ret = False
	for e in exchanges:
		while True:
			n = 0
			for order in _C(e.GetOrders):
				ret = True
				e.CancelOrder(order.Id)
				n+=1
			if n == 0:
				break
	return ret

def create_table(dbname):
	conn = sqlite3.connect(dbname)
	try:
		create_cancelorders_cmd='''
		CREATE TABLE IF NOT EXISTS cancelorders
		(orderid INTEGER,
		exname text,
		price real,
		commission real,
		amount real,
		orderidinfo real UNIQUE,
		type int,
		dealed int,
		canceltime real,
		tradeid real,
		PRIMARY KEY (orderid));
		'''

		create_exchanges_cmd = '''
		CREATE TABLE IF NOT EXISTS exchanges
		(exname text,
		buyfee real NOT NULL,
		sellfee real NOT NULL,
		initprice real DEFAULT 0,
		avgprice real DEFAULT 0,
		PRIMARY KEY (exname));
		'''

		create_tradehistory_cmd = '''
		CREATE TABLE IF NOT EXISTS tradehistory
		(id INTEGER,
		exbuyname text NOT NULL,
		exsellname text NOT NULL,
		buyprice real NOT NULL,
		sellprice real NOT NULL,
		diffprice real NOT NULL,
		commission real NOT NULL,
		istraded real NOT NULL,
		buydepth real NOT NULL,
		selldepth real NOT NULL,
		tradeamount real NOT NULL,
		tradetime text NOT NULL,
		PRIMARY KEY (id));
		'''

		create_exchangeticker_cmd = '''
		CREATE TABLE IF NOT EXISTS exchangeticker
		(id INTEGER,
		exname text NOT NULL,
		buyprice real NOT NULL,
		sellprice real NOT NULL,
		tickertime text NOT NULL,
		PRIMARY KEY (id));
		'''

		conn.execute(create_cancelorders_cmd)
		conn.execute(create_tradehistory_cmd)
		conn.execute(create_exchanges_cmd)
		conn.execute(create_exchangeticker_cmd)
	except:
		Log("Create table failed")
		return False

	insert_ex_cmd='''
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('HitBTC',0.001,0.001);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Poloniex',0.001,0.001);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Huobi',0.002,0.002);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Bitfinex',0.002,0.002);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Bittrex',0.0025,0.0025);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Bitstamp',0.0025,0.0025);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('Binance',0.001,0.001);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('OKEX',0.001,0.001);
		REPLACE INTO exchanges (exname,buyfee,sellfee) VALUES ('ZB',0.001,0.001);
		'''
	conn.executescript(insert_ex_cmd)
	conn.commit()
	conn.close()

def onerror(a):
	Log(a)

def cleanDBEveryDay():
	global dbname
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	delts = time.time() - 24*1*3600
	c.execute("DELETE FROM tradehistory WHERE tradetime < ?",(delts,))
	conn.commit()
	conn.execute("VACUUM")
	c.close()
	conn.close()

def initDatabase():
	global tradehistoryDF,gp,exInfoDF,currentTradeDF,dbname,allTradeTimes
	conn = sqlite3.connect(dbname)
	#一天内的数据区间.
	#删除10天前的数据。
	timeZone = time.time()-24*3600
	#应该收集最近4个小时甚至最近2个小时的交易信息。
	df = pd.read_sql_query("select * from tradehistory where tradetime > " + str(timeZone),conn)

	cursor = conn.cursor()
	cursor.execute('select count(*) from tradehistory')
	allTradeTimes = cursor.fetchone()[0]
	cursor.close()
	conn.close()

	df['profit'] = df['diffprice'] - df['commission']
	thirtyMinutes = time.time() - 1200
	for i in range(len(exchanges)):
		exBuyName = exchanges[i].GetName()

		new1 = pd.DataFrame({
							'name':exBuyName,
							'allbuytimes':df[df.exbuyname == exBuyName].id.count(),
							'allselltimes':df[df.exsellname == exBuyName].id.count(),
							'allavgprofit':df[df.exbuyname == exBuyName].profit.mean(),
							'allstd':df[df.exbuyname == exBuyName].profit.std()
							}, index=[i])

		new2 = pd.DataFrame({
									'name':exBuyName,
									'buytimes':df[(df.exbuyname == exBuyName) & (df.tradetime >= thirtyMinutes) & (df.istraded == True)].id.count(),
									'selltimes':df[(df.exsellname == exBuyName) & (df.tradetime >= thirtyMinutes) & (df.istraded == True)].id.count(),
									'allcanbuytimes':df[(df.exbuyname == exBuyName) & (df.tradetime >= thirtyMinutes)].id.count(),
									'allcanselltimes':df[(df.exsellname == exBuyName) & (df.tradetime >= thirtyMinutes)].id.count()
									},index=[i])

		exInfoDF = exInfoDF.append(new1,ignore_index=True)
		currentTradeDF = currentTradeDF.append(new2,ignore_index=True)

	for i in range(len(exchanges)):
		for j in range(len(exchanges)):
			if i == j:
				continue
			else:
				exBuyName = exchanges[i].GetName()
				exSellName = exchanges[j].GetName()

				new3 = pd.DataFrame({
									'name':exBuyName + ':' + exSellName,
									'tradetimes':df[(df.exbuyname == exBuyName) & (df.exsellname == exSellName)].id.count(),
									'avgprofit':df[(df.exbuyname == exBuyName) & (df.exsellname == exSellName)].profit.mean(),
									'std':df[(df.exbuyname == exBuyName) & (df.exsellname == exSellName)].profit.std()
									},index=[i])

				tradehistoryDF = tradehistoryDF.append(new3,ignore_index=True)

def retDepth():
	global depths
	depths.clear()
	while True:
		for ex in exchanges:
			if depths.has_key(ex.GetName()) == False:
				depths[ex.GetName()] = ex.Go("GetDepth")

		failed = 0

		for k,v in depths.items():
			try:
				ret,ok = depths[k].wait()
				if ok == True and ret is not None and type(ret.Bids) == list:
					depths[k] = ret
			except:
				failed += 1

		if failed == 0:
			break
		else:
			Sleep(10)
	return depths

def retAccount():
	global accounts
	accounts.clear()
	while True:
		for ex in exchanges:
			if accounts.has_key(ex.GetName()) == False:
				accounts[ex.GetName()] = ex.Go("GetAccount")

		failed = 0

		for k,v in accounts.items():
			try:
				ret,ok = accounts[k].wait()
				if ok == True and ret is not None and type(ret.Balance) == float:
					accounts[k] = ret
			except:
				failed += 1

		if failed == 0:
			break
		else:
			Sleep(10)
	return accounts

def getProfit():
	#需要优化，耗时4s
	global checkProfit,currentState,accounts,accountsCache
	if(checkProfit):
		retAccount()
		for i,detail in enumerate(currentState.details):
			try:
				if type(accounts[detail['name']].Balance) is not None:
					currentState.details[i]['account'] = accounts[detail['name']]
				accountsCache[detail['name']] = accounts[detail['name']]
			except:
				currentState.details[i]['account'] = accountsCache[detail['name']]

		checkProfit = False

def insertDataToDB():
	global insertTradeHistoryDbValues
	if len(insertTradeHistoryDbValues) != 0:
		try:
			conn = sqlite3.connect(dbname)
			insertTradeHistoryDb = 'insert into tradehistory (exbuyname,exsellname,buyprice,sellprice,diffprice,commission,istraded,buydepth,selldepth,tradeamount,tradetime) values (?,?,?,?,?,?,?,?,?,?,?)'
			conn.executemany(insertTradeHistoryDb, insertTradeHistoryDbValues)
			conn.commit()
			conn.close()
		except:
			Log("写入买卖单数据时出错.")
			return
	insertTradeHistoryDbValues = np.array([])

def calTradeAmount(buyExname,sellExname,buyExBalance,buyExStock,sellExBalance,sellExStock,buyExCanBuyAmount,sellExCanBuyAmount,diffPrice,commission,bDepth,sDepth):
	global tradehistoryDF,gp,exInfoDF,currentTradeDF

	#成交之前对比当前钱币比，按照50：50分配.
	'''[summary]
	1.下一步检测价格突然变化，决定买卖方向
	2.如果买方交易所很活跃，那么钱币比应该是都是钱，如果钱比值小于2：8，则大量出售。如果当前出现信号是买方很活跃，又是买方在大量出售，查看钱币比，如果已经满足2：8，则查看当前利润。而不是大量购买。
	[description]
	'''
	#tradeamountSeries[tradeamountSeries.ratio < 0.84].amount[0:1].item()
	tradeProfit = diffPrice - commission
	#深度如果小于1，处理一下。TODO
	#MaxTradeAmount这里可以选择让程序自动控制，或者自己给定一个数量。

	maxCanTradeAmount = min(buyExCanBuyAmount,sellExStock,bDepth,sDepth)
	minCanTradeAmount = 0.1
	if (buyExname == 'Binance' or sellExname == 'Binance') : minCanTradeAmount = 0.2

	if tradeProfit > 0 :
		if sellExStock < minCanTradeAmount :
			return True,False,0,'break'
		if maxCanTradeAmount < minCanTradeAmount:
			return True,False,0,'continue'
	elif tradeProfit < 0:
		if sellExStock < minCanTradeAmount :
			return False,False,0,'break'
		if maxCanTradeAmount < minCanTradeAmount:
			return False,False,0,'continue'
	# Log(buyExname,'->',sellExname)
	#买卖交易所当前时间周期内的交易信息.
	currentBuyExBuyTimes = currentTradeDF[currentTradeDF.name == buyExname].buytimes.item()
	currentBuyExSellTimes = currentTradeDF[currentTradeDF.name == buyExname].selltimes.item()
	currentBuyExAllCanBuyTimes = currentTradeDF[currentTradeDF.name == buyExname].allcanbuytimes.item()
	currentBuyExAllCanSellTimes = currentTradeDF[currentTradeDF.name == buyExname].allcanselltimes.item()
	# Log(' currentBuyExBuyTimes ',currentBuyExBuyTimes,' currentBuyExSellTimes ',currentBuyExSellTimes,' currentBuyExAllCanBuyTimes ',currentBuyExAllCanBuyTimes,'currentBuyExAllCanSellTimes',currentBuyExAllCanSellTimes)
	currentSellExBuyTimes = currentTradeDF[currentTradeDF.name == sellExname].buytimes.item()
	currentSellExSellTimes = currentTradeDF[currentTradeDF.name == sellExname].selltimes.item()
	currentSellExAllCanBuyTimes = currentTradeDF[currentTradeDF.name == sellExname].allcanbuytimes.item()
	currentSellExAllCanSellTimes = currentTradeDF[currentTradeDF.name == sellExname].allcanselltimes.item()
	# Log(' currentSellExBuyTimes ',currentSellExBuyTimes,' currentSellExSellTimes ',currentSellExSellTimes,' currentSellExAllCanBuyTimes ',currentSellExAllCanBuyTimes,' currentSellExAllCanSellTimes ',currentSellExAllCanSellTimes)
	#买卖交易所所有时间内的交易信息.
	buyExAllBuyTimes = exInfoDF[exInfoDF.name == buyExname].allbuytimes.item()
	buyExAllSellTimes = exInfoDF[exInfoDF.name == buyExname].allselltimes.item()
	buyExAllAvgProfit = exInfoDF[exInfoDF.name == buyExname].allavgprofit.item()
	# buyExAllStd = exInfoDF[exInfoDF.name == buyExname].allstd
	# Log(' buyExAllBuyTimes ',buyExAllBuyTimes,' buyExAllSellTimes ',buyExAllSellTimes,' buyExAllAvgProfit ',buyExAllAvgProfit)
	sellExAllBuyTimes = exInfoDF[exInfoDF.name == sellExname].allbuytimes.item()
	sellExAllSellTimes = exInfoDF[exInfoDF.name == sellExname].allselltimes.item()
	sellExAllAvgProfit = exInfoDF[exInfoDF.name == sellExname].allavgprofit.item()
	# sellExAllStd = exInfoDF[exInfoDF.name == sellExname].allstd
	# Log(' sellExAllBuyTimes ',sellExAllBuyTimes,' sellExAllSellTimes ',sellExAllSellTimes,' sellExAllAvgProfit ',sellExAllAvgProfit)
	#买卖双方所有时间内相互的交易信息.
	buyToSellTradeTimes = tradehistoryDF[tradehistoryDF.name == (buyExname +':'+ sellExname)].tradetimes.item()
	sellToBuyTradeTimes = tradehistoryDF[tradehistoryDF.name == (sellExname +':'+ buyExname)].tradetimes.item()
	buyToSellAvgProfit = tradehistoryDF[tradehistoryDF.name == (buyExname +':'+ sellExname)].avgprofit.item()
	sellToBuyAvgProfit = tradehistoryDF[tradehistoryDF.name == (sellExname +':'+ buyExname)].avgprofit.item()
	# buyToSellStd = tradehistoryDF[tradehistoryDF.name == (buyExname +':'+ sellExname)].std
	# sellToBuyStd = tradehistoryDF[tradehistoryDF.name == (sellExname +':'+ buyExname)].std
	#计算当前利润在利润区间出现的几率.
	# Log('buyToSellTradeTimes ',buyToSellTradeTimes,' sellToBuyTradeTimes',sellToBuyTradeTimes,' buyToSellAvgProfit ',buyToSellAvgProfit,' sellToBuyAvgProfit ',sellToBuyAvgProfit)
	# currentProfitProb = 1 - scipy.stats.norm(buyToSellAvgProfit,buyToSellStd).cdf(tradeProfit)

	#买卖双方现金货币比。2:8警戒线.
	buyExBalanceCoinRatio = float(buyExCanBuyAmount) / (float(buyExCanBuyAmount) + float(buyExStock))
	sellExBalanceCoinRatio = float(sellExCanBuyAmount) / (float(sellExCanBuyAmount) + float(sellExStock))

	tradeamountSeries = pd.DataFrame({
									'amount':np.linspace(minCanTradeAmount,maxCanTradeAmount,41),
									'ratio':np.linspace(1,0,41)
									})


	if tradeProfit >= MaxCoinDiff:

		#根据双方交易数据查出应该交易的个数.
		buyExRatio = 1.0*buyExAllBuyTimes / allTradeTimes
		sellExRatio = 1.0*sellExAllSellTimes / allTradeTimes

		buyToSellRatio = buyExRatio / (buyExRatio + sellExRatio)
		sellToBuyRatio = sellExRatio / (buyExRatio + sellExRatio)

		buyExOwnRatio = 1.0*currentBuyExAllCanBuyTimes / (currentBuyExAllCanBuyTimes + currentBuyExAllCanSellTimes)
		sellExOwnRatio = 1.0*currentSellExAllCanBuyTimes / (currentSellExAllCanBuyTimes + currentSellExAllCanSellTimes)

		buyToSellOwnRatio = buyExOwnRatio / (buyExOwnRatio + sellExOwnRatio)
		sellToBuyOwnRatio = sellExOwnRatio / (buyExOwnRatio + sellExOwnRatio)
		# Log(tradeamountSeries)
		# Log(buyToSellOwnRatio,sellToBuyOwnRatio)
		buyExNeedAmount = tradeamountSeries[tradeamountSeries.ratio <= buyExOwnRatio].amount[:1].item()
		sellExNeedAmount = tradeamountSeries[tradeamountSeries.ratio <= sellExOwnRatio].amount[:1].item()

		agreementAmount = buyExNeedAmount * buyToSellOwnRatio + sellExNeedAmount * sellToBuyOwnRatio

		agreementAmount = _N(agreementAmount,2)

		return True,True,agreementAmount,'ok'
	else:
		return False,False,0,'test'

def buyOrSell():
	return True

def isGotRealProfitTime():
	global realProfitTime
	ts = time.time()
	if ts >= realProfitTime:
		realProfitTime = time.mktime(time.strptime(time.strftime('%Y-%m-%d 00:00:00', time.localtime(ts+25*3600)),'%Y-%m-%d %H:%M:%S'))
		return True
	else:
		return False

def findByRow(mat, row):
	if len(mat) == 1:
		idx = np.where((mat == row).all())[0]
		return len(idx)
	else:
		idx = np.where((mat == row).all(1))[0]
		return len(idx)

def coinToCoinTrade():
	global currentState, tradeInfo, dbname,insertTradeHistoryDbValues,calProfit,tradeOrdersNP,waitingOrders,checkProfit,depthsCache,pricemeanList
	#画矩阵，把所有信息一起查看，包括能卖，能买，深度，买一，卖一，然后并发处理。
	minExTradeAmount = 0.2
	listArrs = []
	tradeArrs = []
	tradetime = time.time()
	canbeTrade = False
	isTraded = False
	fixnum = 0
	for i,sellDetail in enumerate(currentState.details):

		for j,buyDetail in enumerate(currentState.details):

			exchangeBuyName = buyDetail['name']
			exchangeSellName = sellDetail['name']

			if exchangeSellName == exchangeBuyName : continue

			if exchangeSellName == 'Binance' or exchangeBuyName == 'Binance':
				minExTradeAmount = 0.2
			else:
				minExTradeAmount = 0.1
			if exchangeSellName == 'Huobi'  or exchangeSellName == 'Binance' : sellLen = 6
			else: sellLen = 8

			# if (exchangeBuyName == 'Bittrex' or exchangeSellName == 'Bittrex'):
			# 	SlidePrice = 0.0000005
			# else:
			# 	SlidePrice = 0
			if ( exchangeBuyName == 'Huobi' or exchangeSellName == 'Huobi'):
				buyLen = 7
				fixnum = 0.000000001
				SlidePrice = 0.000001

			else:
				buyLen = 9
				fixnum = 0.00000000001
				# SlidePrice = 0.0000005
			SlidePrice = 0
			buyPriceWithSlidePrice = round(buyDetail['ticker']['Sell'] + SlidePrice + fixnum, buyLen)
			sellPriceWithSlidePrice = _N(sellDetail['ticker']['Buy'] - SlidePrice, sellLen)
			sellExStocks = _N(sellDetail['account'].Stocks, 4)

			buyExBalance = _N(buyDetail['account'].Balance,8)
			buyExStock = _N(buyDetail['account'].Stocks,4)
			sellExBalance = _N(sellDetail['account'].Balance,8)

			S_depth = _N(sellDetail['ticker']['BuyAmount']*0.5, 2)
			B_depth = _N(buyDetail['ticker']['SellAmount']*0.5, 2)

			buyExCanBuyAmount = _N(buyDetail['account'].Balance * (1 - buyDetail['fee']['Buy']) / buyPriceWithSlidePrice, 2)
			sellExCanBuyAmount = _N(sellDetail['account'].Balance * (1 - sellDetail['fee']['Buy']) / sellPriceWithSlidePrice, 2)

			tradeAmount = min(MaxTradeAmount, B_depth, S_depth,sellExStocks,buyExCanBuyAmount)
			_maxCanTradeAmount = min(B_depth, S_depth,sellExStocks,buyExCanBuyAmount)
			tradeDepth = min(B_depth,S_depth)
			diffPrice = sellPriceWithSlidePrice - buyPriceWithSlidePrice
			buyCommision = buyPriceWithSlidePrice * buyDetail['fee']['Buy']
			sellCommision = sellPriceWithSlidePrice * sellDetail['fee']['Sell']
			commission = buyCommision + sellCommision
			tradeprofit = diffPrice - commission

			canbeTrade,isTraded,suggestAmount,control = calTradeAmount(exchangeBuyName,exchangeSellName,buyExBalance,buyExStock,sellExBalance,sellExStocks,buyExCanBuyAmount,sellExCanBuyAmount,diffPrice,commission,B_depth,S_depth)

			if canbeTrade == False:
				if control == 'break':
					break
				if control == 'continue':
					continue
			elif canbeTrade == True and isTraded == False:
				if exchangeBuyName != 'Binance' or exchangeSellName != 'Binance':
					readyToInsertList = [exchangeBuyName, exchangeSellName, buyPriceWithSlidePrice, sellPriceWithSlidePrice, diffPrice, commission, isTraded, B_depth, S_depth, tradeAmount, tradetime]
					listArrs.append(readyToInsertList)
				if control == 'break':
					break
				if control == 'continue':
					continue
			elif canbeTrade == True and isTraded == True:
				readyToInsertList = [exchangeBuyName, exchangeSellName, buyPriceWithSlidePrice, sellPriceWithSlidePrice, diffPrice, commission, isTraded, B_depth, S_depth, tradeAmount, tradetime]
				listArrs.append(readyToInsertList)

				tradeAmount = _N(tradeAmount,2)
				###########开始交易################
				#######比较买卖之间的差价，决定先买后卖还是先卖后买。这个没做
				#搞清楚交易的时候价格趋势,优先处理同趋势的单子，逆趋势的单好下
				#这样逆趋势的单能剩滑点甚至下单就小赚了,砸盘的时候先把卖单下出去
				#不成交不下买单,拉伸的时候反过来
				#价格预测？？？？？？？
				#上涨的时候先买，后卖，
				#下跌的时候先卖，后买
				#################################
				# tradeid = random.randint(1,10000)
				# tradeTime = time.time()
				# Log(exchangeBuyName, ' -> ', exchangeSellName, ' 存在套利机会，开始交易。买可买数量：',buyExCanBuyAmount,'卖可卖数量：',sellExStocks,'买现金:',buyDetail['account'].Balance,'买深度：',B_depth,'卖深度：',S_depth)
				npmeanarray = np.array(pricemeanList)
				buymeanprice = np.mean(npmeanarray,axis=0)[1]
				sellmeanprice = np.mean(npmeanarray,axis=0)[0]
				tradeList = []
				minTradeStep = 0.5
				buyOrSellLists = []
				buyOrSellOrderLists = []
				maxTradeRange = _maxCanTradeAmount

				if maxTradeRange <= minTradeStep:
					minTradeStep = minExTradeAmount
					while maxTradeRange >= minTradeStep:
						maxTradeRange = maxTradeRange - minTradeStep
						tradeList.append(minTradeStep)
					leftamount= _maxCanTradeAmount - len(tradeList)*minTradeStep
					if leftamount >= minExTradeAmount:
						tradeList.append(leftamount)
				else:
					minTradeStep = 0.5
					while maxTradeRange >= minTradeStep:
						maxTradeRange = maxTradeRange - minTradeStep
						tradeList.append(minTradeStep)
					leftamount= _maxCanTradeAmount - len(tradeList)*minTradeStep
					if leftamount >= 0.2:
						tradeList.append(leftamount)

				for ix in tradeList:
					tradeid = int(round(time.time())) + random.randint(1,10000)
					ix = _N(ix,2)
					buyOrSellLists.append([buyDetail['exchange'].Go('Buy',buyPriceWithSlidePrice,ix,buymeanprice),ix,buyPriceWithSlidePrice,'buy',tradeid,exchangeBuyName,buyDetail['exchange']])
					buyOrSellLists.append([sellDetail['exchange'].Go('Sell',sellPriceWithSlidePrice,ix,sellmeanprice),ix,sellPriceWithSlidePrice,'sell',tradeid,exchangeSellName,sellDetail['exchange']])

				for ixx, trade in enumerate(buyOrSellLists):
					ret,ok = trade[0].wait()
					if ok == True and ret is not None:
						insertTradeList = [ret,trade[5],trade[1],tradeprofit,trade[3],'query',time.time(),trade[6],trade[2],trade[4]]
						tradeArrs.append(insertTradeList)
					elif trade[3] == 'buy':
						insertTradeList = [int(round(time.time())),trade[5],trade[1],tradeprofit,'buy','error',time.time(),trade[6],trade[2],0]
						tradeArrs.append(insertTradeList)
					elif trade[3] == 'sell':
						insertTradeList = [int(round(time.time())),trade[5],trade[1],tradeprofit,'sell','error',time.time(),trade[6],trade[2],0]
						tradeArrs.append(insertTradeList)
					else:
						pass
				# calProfit -= _maxCanTradeAmount * ( buyCommision + sellCommision )
				# calProfit += _maxCanTradeAmount * sellPriceWithSlidePrice - _maxCanTradeAmount * buyPriceWithSlidePrice



				calBuyExBalance = buyDetail['account'].Balance - _N(tradeAmount * buyPriceWithSlidePrice * (1 + buyDetail['fee']['Buy']), buyLen)
				calBuyExStock = buyDetail['account'].Stocks + tradeAmount
				calSellExBalance = sellDetail['account'].Balance + _N(tradeAmount * sellPriceWithSlidePrice * (1 - sellDetail['fee']['Sell']), sellLen)
				calSellExStock = sellExStocks - tradeAmount
				Sleep(100)
				try:
					#或者在这里判断是否有冻单？？
					currentState.details[j]['account'] = _C(currentState.details[j]['exchange'].GetAccount)
					currentState.details[i]['account'] = _C(currentState.details[i]['exchange'].GetAccount)
					# Log('网站获取的买方现金:',currentState.details[j]['account'].Balance,'卖方币数：',currentState.details[i]['account'].Stocks,'计算得出的买方现金：',calBuyExBalance,'卖方币数：',calSellExStock)
					currentState.details[j]['account'].Balance = min(currentState.details[j]['account'].Balance, calBuyExBalance)
					currentState.details[j]['account'].Stocks = min(currentState.details[j]['account'].Stocks, calBuyExStock)
					currentState.details[i]['account'].Balance = min(currentState.details[i]['account'].Balance, calSellExBalance)
					currentState.details[i]['account'].Stocks = min (currentState.details[i]['account'].Stocks, calSellExStock)
					# Log('取最小值的买方现金：',currentState.details[j]['account'].Balance,'卖方币数:',currentState.details[i]['account'].Stocks)
				except Exception as e:
					Log('578',e)
					currentState.details[j]['account'].Balance = calBuyExBalance
					currentState.details[j]['account'].Stocks = calBuyExStock
					currentState.details[i]['account'].Balance = calSellExBalance
					currentState.details[i]['account'].Stocks = calSellExStock
			else:
				pass

	if len(insertTradeHistoryDbValues) == 0:
		insertTradeHistoryDbValues = np.array(listArrs)
	else:
		for listArr in listArrs:
			_arr = [listArr]
			idx = findByRow(insertTradeHistoryDbValues, np.array(_arr))
			if idx == 0:
				insertTradeHistoryDbValues = np.row_stack((insertTradeHistoryDbValues, np.array(_arr)))
	_G("dbValuesHistory",insertTradeHistoryDbValues)

	if len(tradeOrdersNP) == 0:
		tradeOrdersNP = np.array(tradeArrs)
	else:
		checkProfit = True
		for tradeArr in tradeArrs:
			_arr = [tradeArr]
			tradeOrdersNP = np.row_stack((tradeOrdersNP,np.array(_arr)))
	_G("tradesHistory",tradeOrdersNP)

def coinToCoinBalanceAccounts():
	global checkProfit,balanceTime,tradeOrdersNP,waitingOrders,checkCancelOrderTime,calProfit,needBalance,cancelTimes,currentState,dbname,isTimeToGetProfit,readDBTime,cleanDBTime
	global tradehistoryDF,exInfoDF,currentTradeDF
	ts = time.time()
	arrs = []
	delidx = []
	queryOrderList = []
	dealOrderList = []
	cancelOrderList = []
	needGetAccount = 0
	needdealedAmount = 0
	orderlists = []
	strlog = ''
	#5分钟写一次数据库.
	if (ts - balanceTime) > 5*60:
		try:
			conn = sqlite3.connect(dbname)
			c = conn.cursor()
			c.execute("SELECT * FROM cancelorders WHERE dealed = 0")
			orderlists = c.fetchall()
			if len(orderlists) == 0:
				pass
			else:
				for order in orderlists:
					if order[6] == 0:
						needdealedAmount += float(order[4])
					elif order[6] == 1:
						needdealedAmount -= float(order[4])

			if needdealedAmount > 0:
				strlog = '需要处理的冻单个数为' + str(len(orderlists)) + ' 个,共需要购买：' + str(abs(needdealedAmount)) + '个'
			elif needdealedAmount < 0:
				strlog = '需要处理的冻单个数为' + str(len(orderlists)) + ' 个,共需要出售：' + str(abs(needdealedAmount)) + '个'
			elif needdealedAmount == 0 and len(orderlists) != 0:
				strlog = '需要处理的冻单个数为' + str(len(orderlists)) + ' 个,但刚好一买一卖抵平.'
			else:
				strlog = '没有需要处理的冻单'
		except:
			Log('读取数据库出错.')
		finally:
			c.close()
			conn.close()

		Log('5分钟内所有可交易次数为:',len(insertTradeHistoryDbValues),'次. ',strlog)
		insertDataToDB()
		isTimeToGetProfit = True
		checkProfit = True
		balanceTime = ts
	#5秒钟处理一次订单。
	if (ts - checkCancelOrderTime >= 5):
		failed = 1
		for i,trade in enumerate(tradeOrdersNP):
			if trade[5] == 'error' and trade[4] == 'sell':
				#ex,buy or sell Type,amount,price
				# dealOrderList.append([trade[7],1,trade[2],trade[8],'not',trade[1]])
				# exname,price,commission,amount,dealamount,type,dealed,time
				dealOrderList.append([trade[1],trade[8],trade[3],trade[2],time.time(),1,0,time.time()])
				delidx.append(i)
			elif trade[5] == 'error' and trade[4] == 'buy':
				dealOrderList.append([trade[1],trade[8],trade[3],trade[2],time.time(),0,0,time.time()])
				delidx.append(i)
			elif ts - float(trade[6]) >= 15 and trade[5] == 'query':
				#ex,exaction,buy or sell id
				queryOrderList.append([trade[7],trade[7].Go('GetOrder',trade[0]),trade[0],trade[9],trade[8],trade[3]])
				delidx.append(i)
			elif trade[5] == 'checknow':
				queryOrderList.append([trade[7],trade[7].Go('GetOrder',trade[0]),trade[0],trade[9],trade[8],trade[3]])
				delidx.append(i)
			else:
				pass
		if len(delidx) != 0:
			tradeOrdersNP = np.delete(tradeOrdersNP,delidx,0)
		# Log(queryOrderList)
		for query in queryOrderList:
			ret,ok = query[1].wait()
			if ok == True and ret is not None:
				if ret.Amount - ret.DealAmount == 0:
					# Log('订单为',query[2],'的已经处理完毕.')
					pass
				elif ret.Amount - ret.DealAmount > 0:
					#ex,exaction,buy or sell Type,dealamount
					_type = ret.Type
					if query[0].GetName() == 'Bittrex':
						if ret.Info.Type == 'LIMIT_BUY':
							_type = 0
						else:
							_type = 1
					cancelOrderList.append([query[0],query[0].Go('CancelOrder',query[2]),_type,float(ret.Amount-ret.DealAmount),query[4],query[3],query[2],query[5]])
			else:
				# Log('query is error',query[2],ret)
				pass

		for cancelorder in cancelOrderList:
			try:
				ret,ok = cancelorder[1].wait()
				if ok == True and ret is not None:
					#ex,buy or sell Type,amount,price
					# dealOrderList.append([cancelorder[0],cancelorder[2],cancelorder[3],cancelorder[4],'not',cancelorder[0].GetName()])
					#exname,price,amount,dealamount,type,canceled,dealed,time
					#cancelorder[5] is tradeid
					dealOrderList.append([cancelorder[0].GetName(),cancelorder[4],cancelorder[7],cancelorder[3],cancelorder[6],cancelorder[2],0,time.time(),cancelorder[5]])
						# Log("订单号为 %s 加入处理订单数组." % (str(cancelorder[6])))
				else:
					pass
			except Exception as e:
				Log('710',e)

		if len(dealOrderList) != 0:
			checkProfit = True
			# dealOrderList = map(lambda x:x[:8],dealOrderList)
			ret = insertDealCancelOrderList(dealOrderList)
			if ret:
				dealOrderList = []

		checkCancelOrderTime = ts

	#1小时读取一次数据库.
	if (ts - readDBTime >= 3605):
		tradehistoryDF = tradehistoryDF.iloc[0:0]
		exInfoDF = exInfoDF.iloc[0:0]
		currentTradeDF = currentTradeDF.iloc[0:0]
		initDatabase()
		# Log('readDBTime..')
		readDBTime = ts

	#24小时清理一次数据库.
	if (ts - cleanDBTime >= 86410):
		cleanDBEveryDay()
		cleanDBTime = ts


	if needBalance == True:
		pass

def insertDealCancelOrderList(dealOrderList):
	global dbname
	try:
		conn = sqlite3.connect(dbname)
		c = conn.cursor()
		for item in dealOrderList:
			c.execute("SELECT * FROM cancelorders WHERE tradeid = ?",(item[8],))
			existTrade = c.fetchone()
			if existTrade is not None:
				c.execute("DELETE FROM cancelorders WHERE orderid = ?",(existTrade[0],))
				conn.commit()
			else:
				insertCancelDB = "insert or IGNORE into cancelorders (exname,price,commission,amount,orderidinfo,type,dealed,canceltime,tradeid) values (?,?,?,?,?,?,?,?,?)"
				conn.execute(insertCancelDB,item)
				conn.commit()

		#先查找所有小于0.1的,替换到相同类型的订单上
		c.execute("SELECT * FROM cancelorders WHERE dealed = 0 and amount < 0.1")
		littleAmountLists = c.fetchall()
		for littleAmountlist in littleAmountLists:
			_littleAmount = float(littleAmountlist[4])
			_littlePrice = float(littleAmountlist[2])
			_littleType = littleAmountlist[6]
			_littleId = littleAmountlist[0]
			c.execute("SELECT * FROM cancelorders WHERE dealed = 0 and type = ?",(_littleType,))
			badLuckOrder = c.fetchone()
			if badLuckOrder is not None:
				badLuckPrice = float(badLuckOrder[2])
				badLuckAmount = float(badLuckOrder[4])
				badLuckId = badLuckOrder[0]
				_allAmount = _N(_littleAmount + badLuckAmount,2)
				_avgPrice = (_littleAmount * _littlePrice + badLuckPrice * badLuckAmount) / (_littleAmount + badLuckAmount)
				_avgPrice = _N(_avgPrice,6)
				c.execute("UPDATE cancelorders SET price = ? , amount = ? WHERE orderid = ?",(_avgPrice,_allAmount,badLuckId))
				c.execute("DELETE FROM cancelorders WHERE orderid = ?",(_littleId,))
				conn.commit()
			else:
				c.execute("DELETE FROM cancelorders WHERE orderid = ?",(_littleId,))
				Log('因为单量太小，价格为：',_littlePrice,'的冻单被删除了.')
				conn.commit()
			#替换订单结束.
			#

		#把买单，卖单的最小值跟最大值中和一下，以便可以及时买入卖出。
		#先处理买单：

		c.close()
		conn.close()
		return True
	except Exception as e:
		Log('789',e)
		exit()
		return False

def dealCancelOrder():
	global feeInfo,dbname,currentState,tradeOrdersNP,checkProfit
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	c.execute("SELECT count(*) FROM cancelorders WHERE dealed = 0")
	value = c.fetchall()
	if value == 0:
		c.close()
		conn.close()
		return

	tradeArrs = []
	conn = sqlite3.connect(dbname)
	c = conn.cursor()
	for i,detail in enumerate(currentState.details):
		gotoTop = False
		while 1:
			exname = detail['name']
			if exname == 'Binance' or exname == 'Binance':
				_minTradeAmount = 0.2
			else:
				_minTradeAmount = 0.1

			if exname == 'Huobi'  or exname == 'Binance' : Len = 6
			else: Len = 8

			_bPrice = round(detail['ticker']['Sell'], Len)
			_sPrice = _N(detail['ticker']['Buy'], Len)

			_stock = _N(detail['account'].Stocks, 4)
			_balance = _N(detail['account'].Balance,8)
			_canbuyamount = _N(_balance * (1 - detail['fee']['Buy']) / _bPrice,2)

			#这就是正确的买卖单深度，s_depth就是卖的数量，b_depth 就是买的数量。
			S_depth = _N(detail['ticker']['BuyAmount']*0.8, 2)
			B_depth = _N(detail['ticker']['SellAmount']*0.8, 2)

			# _profitPrice = _N(_bPrice*1.001,6)
			_profitPrice = _N(_bPrice,Len)
			# c.execute("SELECT * FROM cancelorders WHERE price + commission >= ? and type = ? and dealed = 0",(_profitPrice,0))
			c.execute("SELECT * FROM cancelorders WHERE price >= ? and type = ? and dealed = 0",(_profitPrice,0))
			blists = c.fetchall()
			if len(blists) == 0:
				break
			else:
				for blist in blists:
					tradeid = int(round(time.time())) + random.randint(1,10000)
					_needbuyamount = _N(float(blist[4]),2)
					if _needbuyamount < min(B_depth, _canbuyamount) and _needbuyamount >= _minTradeAmount:
						bid = detail['exchange'].Buy(_bPrice, _needbuyamount, '处理之前的买单。价格为：',blist[2])
						if type(bid) is not None and bid is not None:
							c.execute("UPDATE cancelorders SET dealed = 1 WHERE orderid = ?",(blist[0],))
							conn.commit()
							insertTradeList = [bid,exname,_needbuyamount,blist[3],'buy','checknow',time.time(),detail['exchange'],blist[2],tradeid]
							tradeArrs.append(insertTradeList)
							currentState.details[i]['account'] = _C(currentState.details[i]['exchange'].GetAccount)
							currentState.details[i]['depth'] = _C(currentState.details[i]['exchange'].GetDepth)
							currentState.details[i]['ticker'] = {
												'Buy':currentState.details[i]['depth'].Bids[0].Price,
												'Sell':currentState.details[i]['depth'].Asks[0].Price,
												'BuyAmount':currentState.details[i]['depth'].Bids[0].Amount,
												'SellAmount':currentState.details[i]['depth'].Asks[0].Amount
												}
							break
						else:
							currentState.details[i]['account'] = _C(currentState.details[i]['exchange'].GetAccount)
							currentState.details[i]['depth'] = _C(currentState.details[i]['exchange'].GetDepth)
							break
					else:
						gotoTop = True
						break
			if gotoTop == True:
				break

	for i,detail in enumerate(currentState.details):
		gotoTop = False
		while 1:
			exname = detail['name']

			if exname == 'Binance' or exname == 'Binance':
				_minTradeAmount = 0.2
			else:
				_minTradeAmount = 0.1

			if exname == 'Huobi'  or exname == 'Binance' : Len = 6
			else: Len = 8

			_sPrice = _N(detail['ticker']['Buy'], Len)

			_stock = _N(detail['account'].Stocks, 4)

			#这就是正确的买卖单深度，卖多少就看s_depth的数量，买多少就看b_depth的数量。
			S_depth = _N(detail['ticker']['BuyAmount']*0.8, 2)
			B_depth = _N(detail['ticker']['SellAmount']*0.8, 2)
			# _profitPrice = _N(_sPrice*0.999,6)
			_profitPrice = _N(_sPrice,Len)
			# c.execute("SELECT * FROM cancelorders WHERE price - commission <= ? and type = ? and dealed = 0",(_profitPrice,1))
			c.execute("SELECT * FROM cancelorders WHERE price <= ? and type = ? and dealed = 0",(_profitPrice,1))
			slists = c.fetchall()
			if len(slists) == 0:
				break
			else:
				for slist in slists:
					tradeid = int(round(time.time())) + random.randint(1,10000)
					_needsellamount = _N(float(slist[4]),2)
					if _needsellamount < min(S_depth, _stock) and _needsellamount >= _minTradeAmount:
						sid = detail['exchange'].Sell(_sPrice, _needsellamount, '处理之前的卖单。价格为：',slist[2])
						if type(sid) is not None and sid is not None:
							c.execute("UPDATE cancelorders SET dealed = 1 WHERE orderid = ?",(slist[0],))
							conn.commit()
							insertTradeList = [sid,exname,_needsellamount,slist[3],'sell','checknow',time.time(),detail['exchange'],slist[2],tradeid]
							tradeArrs.append(insertTradeList)
							currentState.details[i]['account'] = _C(currentState.details[i]['exchange'].GetAccount)
							currentState.details[i]['depth'] = _C(currentState.details[i]['exchange'].GetDepth)
							currentState.details[i]['ticker'] = {
												'Buy':currentState.details[i]['depth'].Bids[0].Price,
												'Sell':currentState.details[i]['depth'].Asks[0].Price,
												'BuyAmount':currentState.details[i]['depth'].Bids[0].Amount,
												'SellAmount':currentState.details[i]['depth'].Asks[0].Amount
												}
							break
						else:
							currentState.details[i]['account'] = _C(currentState.details[i]['exchange'].GetAccount)
							currentState.details[i]['depth'] = _C(currentState.details[i]['exchange'].GetDepth)
							break
					else:
						gotoTop = True
						break
			if gotoTop == True:
				break

	c.close()
	conn.close()

	if len(tradeArrs) != 0:
		checkProfit = True
		if len(tradeOrdersNP) == 0:
			tradeOrdersNP = np.array(tradeArrs)
		else:
			for tradeArr in tradeArrs:
				_arr = [tradeArr]
				tradeOrdersNP = np.row_stack((tradeOrdersNP,np.array(_arr)))
	_G("tradesHistory",tradeOrdersNP)

def generateLogStatus():
	global tStart,currentState,needBalance,realProfit,allProfit,isTimeToGetProfit,_currentBitcoin
	strHead = '{'
	strEnd = '}'
	strTable_type = ' "type": "table",'
	strTable_title = ' "title": "运行信息",'
	strTable_cols_begin = ' "cols" : ['

	strTable_cols_text = '"交易所","币种","当前买1价","当前卖1价","余钱","余币","冻结钱","冻结币"'
	strTable_cols_end = '],'
	strTable_rows_begin = ' "rows" : ['
	strTable_rows_text = ""
	strTable_rows_end = ']'
	strRow = ""
	i = 0
	_allCoin = 0
	_allCurrency = 0
	_allFrozenBalance = 0
	_allFrozenStocks = 0
	for detail in currentState.details:
		strTable_rows_text += '["' + str(detail['name']) + '",'
		strTable_rows_text += '"' + str(detail['currency']) + '",'
		strTable_rows_text += '"' + str(detail['ticker']['Buy']) + '",'
		strTable_rows_text += '"' + str(detail['ticker']['Sell']) + '",'
		strTable_rows_text += '"' + str(detail['account'].Balance) + '",'
		strTable_rows_text += '"' + str(detail['account'].Stocks) + '",'
		strTable_rows_text += '"' + str(detail['account'].FrozenBalance) + '",'
		if i == len(currentState.details) - 1:
			strTable_rows_text += '"' + str(detail['account'].FrozenStocks) + '"]'
		else:
			strTable_rows_text += '"' + str(detail['account'].FrozenStocks) + '"],'
		_allFrozenBalance += detail['account'].FrozenBalance
		_allFrozenStocks += detail['account'].FrozenStocks
		_allCurrency += detail['account'].Balance + detail['account'].FrozenBalance
		_allCoin += detail['account'].Stocks + detail['account'].FrozenStocks
		i += 1

	if abs(_allCoin - BaseCoin) >= BalanceCoinDiff and _allFrozenBalance == 0 and _allFrozenStocks == 0:
		needBalance = True
	oldrealProfit = realProfit
	oldallProfit = allProfit
	_initPrice = 0.01680
	if isGotRealProfitTime() == True or isTimeToGetProfit == True:
		try:
			hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
					'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
					'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
					'Accept-Encoding': 'none',
					'Accept-Language': 'en-US,en;q=0.8',
					'Connection': 'keep-alive'}
			usdtcny = float(exchange.GetUSDCNY())
			url = 'https://www.okex.com/api/v1/ticker.do?symbol=BTC_USDT'
			req = urllib2.Request(url, headers=hdr)
			res = urllib2.urlopen(req,timeout=5)
			res_data = res.read()
			d = json.loads(res_data)
			basebtcprice = BaseCurrency*float(d['ticker']['last'])*usdtcny
			nowbtcprice = _allCurrency*float(d['ticker']['last'])*usdtcny

			url = 'https://www.okex.com/api/v1/ticker.do?symbol=LTC_USDT'
			req = urllib2.Request(url, headers=hdr)
			res = urllib2.urlopen(req,timeout=5)
			res_data = res.read()
			d = json.loads(res_data)
			baseltcprice = BaseCoin*float(d['ticker']['last'])*usdtcny
			nowltcprice = _allCoin*float(d['ticker']['last'])*usdtcny
			realProfit= nowbtcprice - basebtcprice + nowltcprice - baseltcprice
			allProfit = nowbtcprice + nowltcprice
			_currentBitcoin = _N(( _allCoin - BaseCoin ) * _initPrice + (_allCurrency - BaseCurrency ),6)
			calProfit = realProfit
			LogProfit(calProfit,'当前总市值为: ', _N(allProfit,2))
			_G("calProfitHistory",calProfit)
		except Exception as e:
			Log(e)

		isTimeToGetProfit = False


	strTable = strHead + strTable_type + strTable_title + strTable_cols_begin + strTable_cols_text + strTable_cols_end + strTable_rows_begin + strTable_rows_text + strTable_rows_end + strEnd
	tEnd = time.time() - tStart
	btmTableStr = "当前轮询共耗时：" + str(_N(currentState.allPing,2)) + "s"
	LogStatus("初始资金为: " + str(_N(BaseCurrency, 6)) + ", 初始总币为: " + str(_N(BaseCoin, 6)) + ", 当前资金为: " + str(_N(_allCurrency, 6)) + ", 当前总币为: " + str(_N(_allCoin, 6)) + ", 现金收益为:" + str(_N(realProfit,5))  + ", BitCoin收益为: " + str(_currentBitcoin) + ", 当前市值为: " + str(_N(allProfit,2)) + "\n" + '`' + strTable + '`' + "\n" + btmTableStr)

def updateStatePrice():
	global depthsCache,currentState,depths,dbname,pricemeanList
	priceMatrix = []
	pricemeanList = []
	t1 = time.time()
	retDepth()
	currentState.allPing = time.time() - t1
	conn = sqlite3.connect(dbname)
	for detail in currentState.details:

		try:
			detail['depth'] = depths[detail['name']]
			detail['ticker'] = {
				'Buy':depths[detail['name']].Bids[0].Price,
				'Sell':depths[detail['name']].Asks[0].Price,
				'BuyAmount':depths[detail['name']].Bids[0].Amount,
				'SellAmount':depths[detail['name']].Asks[0].Amount
				}
			depthsCache[detail['name']] = depths[detail['name']]
			priceMatrix.append([detail['name'],depths[detail['name']].Bids[0].Price,depths[detail['name']].Asks[0].Price,t1])
			pricemeanList.append([depths[detail['name']].Bids[0].Price,depths[detail['name']].Asks[0].Price])
		except Exception as e:
			# Log(e)
			detail['ticker'] = {
				'Buy':depthsCache[detail['name']].Bids[0].Price,
				'Sell':depthsCache[detail['name']].Asks[0].Price,
				'BuyAmount':0.0001,
				'SellAmount':0.0001
				}
			priceMatrix.append([detail['name'],depthsCache[detail['name']].Bids[0].Price,depthsCache[detail['name']].Asks[0].Price,t1])

	insertCancelDB = "insert into exchangeticker (exname,buyprice,sellprice,tickertime) values (?,?,?,?)"
	conn.executemany(insertCancelDB,priceMatrix)
	conn.commit()
	conn.close()

class getExchangeState(object):
	global cancelTimes,accountsCache,feeInfo
	allCoin = 0
	allCurrency = 0
	details = []
	allPing = 0
	accountsCache.clear()

	def __init__(self):
		conn = sqlite3.connect(dbname)
		cursor = conn.cursor()
		for ex in exchanges:
			account = _C(ex.GetAccount)
			name = _C(ex.GetName)
			accountsCache[name] = account
			currency = _C(ex.GetCurrency)
			cursor.execute( 'select * from exchanges where exname=?',(name,))
			values = cursor.fetchall()
			self.allCoin += account.Stocks + account.FrozenStocks
			self.allCurrency += account.Balance + account.FrozenBalance
			self.details.append({
				'exchange': ex,
				'account': account,
				'name': name,
				'currency': currency,
				'ticker':[],
				'fee':{
					'Buy':values[0][1],
					'Sell':values[0][2]
				},
				'depth':[],
				'depthCache':[]
			})
			feeInfo[name] = values[0][1]
			allCoin = self.allCoin
			allCurrency = self.allCurrency
			details = self.details
		cursor.close()
		conn.close()

def onTick():

	updateStatePrice()

	dealCancelOrder()

	coinToCoinTrade()

	coinToCoinBalanceAccounts()

	getProfit()

	generateLogStatus()

def main():
	global TickInterval, initPrice, cancelOrdersBook, diffHistory, initState, currentState, balanceTime,dbname,calProfit,checkCancelOrderTime,realProfitTime,checkProfit,readDBTime
	#LogReset()
	TickInterval = max(TickInterval,500)
	# cancelAll()
	Log("读取历史交易文件........")

	if ResetLog == True:
		LogReset()

	if ResetProfit == True:
		LogProfitReset()
		_G("calProfitHistory",0)
	else:
		calProfit = _G("calProfitHistory")

	t1 = time.time()
	try:
		if _G("waitingOrdersHistory") is not None and ResetWaitingOrders == False:
			waitingOrders = _G("waitingOrdersHistory")
			# Log(waitingOrders)
		if _G("tradesHistory") is not None:
			tradeOrdersNP = _G("tradesHistory")
			# Log(tradeOrdersNP)
		if _G("dbValuesHistory") is not None:
			insertTradeHistoryDbValues = _G("dbValuesHistory")

		dbname = exchanges[0].GetCurrency() + '.db'
		#os.remove(dbname)
		if os.path.exists(dbname):
			# Log('当前python工作目录是:',os.getcwd(),'数据库已经存在..正在读取...')
			Log('数据库已经存在,正在读取...')
			initDatabase()
		else:
			Log('数据库不存在，正在创建....')
			create_table(dbname)
	except:
		Log('获取历史交易文件有错误发生，请检查.')

	Log("读取历史交易文件结束,共耗时:",_N((time.time()-t1),2),'s')
	Log("获取账户信息开始..........")
	t1 = time.time()
	initState = getExchangeState()
	currentState = initState
	# checkProfit = True
	Log("当前所有现金为：", initState.allCurrency, "所有币为：", initState.allCoin)
	Log("获取账户信息结束,共耗时:",_N((time.time()-t1),2),'s')
	Log("程序即将开始运行........")

	SetErrorFilter("502:|503:|404:|504:|403:|S_U_001|unexpected|network|timeout|WSARecv|Connect|GetAddr|no such|reset|http|received|refused|EOF|When|GetOrder|CancelOrder|GetAccount:|GetDepth:")

	balanceTime = time.time()
	checkCancelOrderTime = time.time()
	readDBTime = time.time()
	cleanDBTime = time.time()
	realProfitTime = time.mktime(time.strptime(time.strftime('%Y-%m-%d 00:00:00', time.localtime(time.time())),'%Y-%m-%d %H:%M:%S'))
	while(true):
		tStart = time.time()
		onTick()
		Sleep(TickInterval)
