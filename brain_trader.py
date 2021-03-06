# -*- coding: utf-8 -*-
"""
Created on Sun Aug 13 08:07:30 2017

@author: nick
"""
import pickle
import time
import pandas as pd
import numpy as np
from poloniex import Poloniex
from datetime import date, timedelta, datetime 
from hist_service import HistWorker
from crypto_evolution import CryptoFolio
from random import randint, shuffle
import requests
# Local
import neat.nn
import _pickle as pickle
from pureples.shared.substrate import Substrate
from pureples.shared.visualize import draw_net
from pureples.es_hyperneat.es_hyperneat import ESNetwork
#polo = Poloniex('key', 'secret')

key = ""
secret = ""
class LiveTrader:
    params = {"initial_depth": 0, 
            "max_depth": 4, 
            "variance_threshold": 0.03, 
            "band_threshold": 0.3, 
            "iteration_level": 1,
            "division_threshold": 0.3, 
            "max_weight": 5.0, 
            "activation": "tanh"}


    # Config for CPPN.
    config = neat.config.Config(neat.genome.DefaultGenome, neat.reproduction.DefaultReproduction,
                                neat.species.DefaultSpeciesSet, neat.stagnation.DefaultStagnation,
                                'config_trader')
    def __init__(self, ticker_len, target_percent):
        self.polo = Poloniex(key, secret)
        self.currentHists = {}
        self.hist_shaped = {}
        self.coin_dict = {}
        self.ticker_len = ticker_len
        self.end_ts = datetime.now()+timedelta(seconds=(ticker_len*55))
        file = open("es_trade_god_cppn.pkl",'rb')
        self.cppn = pickle.load(file)
        file.close()
        self.tickers = self.polo.returnTicker()
        self.bal = self.polo.returnBalances()
        self.target = self.bal['BTC']*target_percent
        self.pull_polo()
        self.inputs = self.hist_shaped.shape[0]*(self.hist_shaped[0].shape[1]-1)
        self.outputs = self.hist_shaped.shape[0]
        self.multiplier = self.inputs/self.outputs
        
    def make_shapes(self):
        self.in_shapes = []
        self.out_shapes = []
        sign = 1
        for ix in range(self.outputs):
            sign = sign *-1
            self.out_shapes.append((sign*ix, 1))
            for ix2 in range(len(self.hist_shaped[0][0])-1):
                self.in_shapes.append((sign*ix, (1+ix2)*.1))
        
    def pull_polo(self):
        tickLen = '7200'
        start = datetime.today() - timedelta(1) 
        start = str(int(start.timestamp()))
        ix = 0
        for coin in self.tickers:
            if coin[:3] == 'BTC':
                hist = requests.get('https://poloniex.com/public?command=returnChartData&currencyPair='+coin+'&start='+start+'&end=9999999999&period='+tickLen)
                try:
                    df = pd.DataFrame(hist.json())
                    #df.rename(columns = lambda x: col_prefix+'_'+x, inplace=True)
                    as_array = np.array(df)
                    #print(len(as_array))
                    self.currentHists[coin] = df
                    self.hist_shaped[ix] = as_array
                    self.coin_dict[ix] = coin
                    ix += 1
                except:
                    print("error reading json")
        self.hist_shaped = pd.Series(self.hist_shaped)
        self.end_idx = len(self.hist_shaped[0])-1


    def get_one_bar_input_2d(self):
        active = []
        misses = 0
        for x in range(0, self.outputs):
            try:
                sym_data = self.hist_shaped[x][self.end_idx] 
                for i in range(len(sym_data)):
                    if (i != 1):
                        active.append(sym_data[i].tolist())
            except:
                self.outputs -= 1
                self.inputs -= self.multiplier
                print('error')
        #print(active)
        self.make_shapes()
        return active


    def closeOrders(self):
        orders = self.polo.returnOpenOrders()
        for o in orders:
            if orders[o] != []:
                try:
                    ordnum = orders[o][0]['orderNumber']
                    self.polo.cancelOrder(ordnum)
                except:
                    print('error closing')
                    
                    
                    
    def sellCoins(self, coinlist, currency):
        balances = self.polo.returnBalances()
        for b in balances:
            bal = balances[b]*.99

    def buy_coin(self, coin, price):
        amt = self.target
        if(self.bal['BTC'] > self.target):
            try:
                self.polo.buy(coin, price, amt, fillOrKill=1)
                print("buying: ", coin)
            except:
                print('error buying', coin)
        return 

    def sell_coin(self, coin, price):
        amt = self.bal[coin[4:]]
        try:
            self.polo.sell(coin, price, amt, fillOrKill=1)
        except:
            print('error selling: ', coin)
        return 

    def reset_tickers(self):
        self.tickers = self.polo.returnTicker()
        return 
    def get_price(self, coin):
        return self.tickers[coin]['last']

    def poloTrader(self):
        end_prices = {}
        active = self.get_one_bar_input_2d()
        sub = Substrate(self.in_shapes, self.out_shapes)
        network = ESNetwork(sub, self.cppn, self.params)
        net = network.create_phenotype_network()
        net.reset()
        for n in range(network.activations):
            out = net.activate(active)
        #print(len(out))
        rng = len(out)
        #rng = iter(shuffle(rng))
        for x in np.random.permutation(rng):
            sym = self.coin_dict[x]
            #print(out[x])
            try:
                if(out[x] < -.5):
                    print("selling: ", sym)
                    self.sell_coin(sym, self.get_price(sym), )
                elif(out[x] > .5):
                    print("buying: ", sym)
                    self.buy_coin(sym, self.get_price(sym))
            except:
                print('error', sym)
            #skip the hold case because we just dont buy or sell hehe
            end_prices[sym] = self.get_price(sym)
        
        if datetime.now() >= self.end_ts:
            return
        else:
            time.sleep(self.ticker_len)
        self.reset_tickers
        self.pull_polo()
        self.poloTrader()
class PaperTrader:
    params = {"initial_depth": 0, 
            "max_depth": 4, 
            "variance_threshold": 0.03, 
            "band_threshold": 0.3, 
            "iteration_level": 1,
            "division_threshold": 0.3, 
            "max_weight": 5.0, 
            "activation": "tanh"}


    # Config for CPPN.
    config = neat.config.Config(neat.genome.DefaultGenome, neat.reproduction.DefaultReproduction,
                                neat.species.DefaultSpeciesSet, neat.stagnation.DefaultStagnation,
                                'config_trader')
    def __init__(self, ticker_len, start_amount):
        self.polo = Poloniex()
        self.currentHists = {}
        self.hist_shaped = {}
        self.coin_dict = {}
        self.ticker_len = ticker_len
        self.end_ts = datetime.now()+timedelta(seconds=(ticker_len*24))
        self.start_amount = start_amount
        file = open("es_trade_god_cppn.pkl",'rb')
        self.cppn = pickle.load(file)
        file.close()
        self.pull_polo()
        self.inputs = self.hist_shaped.shape[0]*(self.hist_shaped[0].shape[1]-1)
        self.outputs = self.hist_shaped.shape[0]
        self.multiplier = self.inputs/self.outputs
        self.folio = CryptoFolio(start_amount, self.coin_dict)
        
    def make_shapes(self):
        self.in_shapes = []
        self.out_shapes = []
        sign = 1
        for ix in range(self.outputs):
            sign = sign *-1
            self.out_shapes.append((sign*ix, 1))
            for ix2 in range(len(self.hist_shaped[0][0])-1):
                self.in_shapes.append((sign*ix, (1+ix2)*.1))
        
    def pull_polo(self):
        try:
            self.coins = self.polo.returnTicker()
        except:
            time.sleep(10)
            self.pull_polo()
        tickLen = '7200'
        start = datetime.today() - timedelta(1) 
        start = str(int(start.timestamp()))
        ix = 0
        for coin in self.coins:
            if coin[:3] == 'BTC':
                hist = requests.get('https://poloniex.com/public?command=returnChartData&currencyPair='+coin+'&start='+start+'&end=9999999999&period='+tickLen)
                try:
                    df = pd.DataFrame(hist.json())
                    #df.rename(columns = lambda x: col_prefix+'_'+x, inplace=True)
                    as_array = np.array(df)
                    #print(len(as_array))
                    self.currentHists[coin] = df
                    self.hist_shaped[ix] = as_array
                    self.coin_dict[ix] = coin
                    ix += 1
                except:
                    print("error reading json")
        self.hist_shaped = pd.Series(self.hist_shaped)
        self.end_idx = len(self.hist_shaped[0])-1

    def get_current_balance(self):
        self.pull_polo()
        c_prices = {}
        for s in self.folio.ledger.keys():
            if s != 'BTC':
                c_prices[s] = self.currentHists[s]['close'][len(self.currentHists[s]['close'])-1]
        return self.folio.get_total_btc_value_no_sell(c_prices)
        
    def get_one_bar_input_2d(self):
        active = []
        misses = 0
        for x in range(0, self.outputs):
            try:
                sym_data = self.hist_shaped[x][self.end_idx] 
                for i in range(len(sym_data)):
                    if (i != 1):
                        active.append(sym_data[i].tolist())
            except:
                self.outputs -= 1
                self.inputs -= self.multiplier
                print('error')
        #print(active)
        self.make_shapes()
        return active
        
    def poloTrader(self):
        end_prices = {}
        active = self.get_one_bar_input_2d()
        sub = Substrate(self.in_shapes, self.out_shapes)
        network = ESNetwork(sub, self.cppn, self.params)
        net = network.create_phenotype_network()
        net.reset()
        for n in range(network.activations):
            out = net.activate(active)
        #print(len(out))
        rng = len(out)
        #rng = iter(shuffle(rng))
        for x in np.random.permutation(rng):
            sym = self.coin_dict[x]
            #print(out[x])
            try:
                if(out[x] < -.5):
                    print("selling: ", sym)
                    self.folio.sell_coin(sym, self.currentHists[sym]['close'][self.end_idx])
                elif(out[x] > .5):
                    print("buying: ", sym)
                    self.folio.buy_coin(sym, self.currentHists[sym]['close'][self.end_idx])
            except:
                print('error', sym)
            #skip the hold case because we just dont buy or sell hehe
            end_prices[sym] = self.hist_shaped[x][len(self.hist_shaped[x])-1][2]
        
        if datetime.now() >= self.end_ts:
            port_info = self.folio.get_total_btc_value(end_prices)
            print("total val: ", port_info[0], "btc balance: ", port_info[1])
            return
        else:
            print(self.get_current_balance())
            for t in range(3):
                time.sleep(self.ticker_len/4)
                p_vals = self.get_current_balance()
                print("current value: ", p_vals[0], "current btc holdings: ", p_vals[1])
                #print(self.folio.ledger)
        time.sleep(self.ticker_len/4)
        self.pull_polo()
        self.poloTrader()
                        


live = LiveTrader(7200, .1)

live.poloTrader()
