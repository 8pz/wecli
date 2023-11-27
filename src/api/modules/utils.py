import collections, requests, time

from datetime import datetime, timedelta
from pandas import DataFrame, to_datetime
from pytz import timezone

from ..utils.endpoints import urls

endpoint= urls()

class utils:
    def login(self, wb):
        self.wb = wb

    def get_ticker(self, stock=''):
        '''
        Lookup ticker_id
        Ticker issue, will attempt to find an exact match, if none is found, match the first one
        '''
        headers = self.wb.build_req_headers()
        ticker_id = 0
        if stock and isinstance(stock, str):
            response = requests.get(endpoint.stock_id(stock, self.wb._region_code), headers=headers, timeout=self.wb.timeout)
            result = response.json()
            if result.get('data') :
                for item in result['data'] : # implies multiple tickers, but only assigns last one?
                    if 'symbol' in item and item['symbol'] == stock :
                        ticker_id = item['tickerId']
                        break
                    elif 'disSymbol' in item and item['disSymbol'] == stock :
                        ticker_id = item['tickerId']
                        break
                if ticker_id == 0 :
                    ticker_id = result['data'][0]['tickerId']
            else:
                raise ValueError('TickerId could not be found for stock {}'.format(stock))
        else:
            raise ValueError('Stock symbol is required')
        return ticker_id

    def get_ticker_info(self, stock=None, tId=None):
        '''
        Get stock public info
        get price quote
        tId: ticker ID str
        '''
        headers = self.wb.build_req_headers()
        if not stock and not tId:
            raise ValueError('Must provide a stock symbol or a stock id')

        if stock :
            try:
                tId = str(self.get_ticker(stock))
            except ValueError as _e:
                raise ValueError("Could not find ticker for stock {}".format(stock))
        response = requests.get(endpoint.stock_detail(tId), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result

    def get_all_tickers(self, region_code=None):
        '''
        Get all tickers from a region
        region id: https://github.com/tedchou12/webull/wiki/What-is-the-region_id%3F
        '''
        headers = self.wb.build_req_headers()

        if not region_code :
            region_code = self.wb._region_code

        response = requests.get(endpoint.get_all_tickers(region_code, region_code), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result

    def get_quote(self, stock=None, tId=None):
        '''
        get price quote
        tId: ticker ID str
        '''
        headers = self.wb.build_req_headers()
        if not stock and not tId:
            raise ValueError('Must provide a stock symbol or a stock id')

        if stock:
            try:
                tId = str(self.get_ticker(stock))
            except ValueError as _e:
                raise ValueError("Could not find ticker for stock {}".format(stock))
        response = requests.get(endpoint.quotes(tId), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result
    
    # request options quotes

    def get_option_quote(self, stock=None, tId=None, optionId=None):
        '''
        get option quote
        '''
        if not stock and not tId:
            raise ValueError('Must provide a stock symbol or a stock id')

        if stock:
            try:
                tId = str(self.get_ticker(stock))
            except ValueError as _e:
                raise ValueError("Could not find ticker for stock {}".format(stock))
        headers = self.wb.build_req_headers()
        params = {'tickerId': tId, 'derivativeIds': optionId}
        return requests.get(endpoint.option_quotes(), params=params, headers=headers, timeout=self.wb.timeout).json()

    def get_options_expiration_dates(self, stock=None, count=-1):
        '''
        returns a list of options expiration dates
        '''
        headers = self.wb.build_req_headers()
        data = {'count': count,
                'direction': 'all',
                'tickerId': self.get_ticker(stock)}

        res = requests.post(endpoint.options_exp_dat_new(), json=data, headers=headers, timeout=self.wb.timeout).json()
        r_data = []
        for entry in res['expireDateList'] :
            r_data.append(entry['from'])

        return r_data

    def get_options(self, stock=None, count=-1, includeWeekly=1, direction='all', expireDate=None, queryAll=0):
        '''
        get options and returns a dict of options contracts
        params:
            stock: symbol
            count: -1
            includeWeekly: 0 or 1 (deprecated)
            direction: all, call, put
            expireDate: contract expire date
            queryAll: 0 (deprecated)
        '''
        headers = self.wb.build_req_headers()
        # get next closet expiredate if none is provided
        if not expireDate:
            dates = self.get_options_expiration_dates(stock)
            for d in dates:
                expireDate = d['date']
                break

        data = {'count': count,
                'direction': direction,
                'tickerId': self.get_ticker(stock)}

        res = requests.post(endpoint.options_exp_dat_new(), json=data, headers=headers, timeout=self.wb.timeout).json()
        t_data = []
        for entry in res['expireDateList'] :
            if str(entry['from']['date']) == expireDate :
                t_data = entry['data']

        r_data = {}
        for entry in t_data :
            if entry['strikePrice'] not in r_data :
                r_data[entry['strikePrice']] = {}
            r_data[entry['strikePrice']][entry['direction']] = entry

        r_data = dict(sorted(r_data.items()))

        rr_data = []
        for s_price in r_data :
            rr_entry = {'strikePrice': s_price}
            if 'call' in r_data[s_price] :
                rr_entry['call'] = r_data[s_price]['call']
            if 'put' in r_data[s_price] :
                rr_entry['put'] = r_data[s_price]['put']
            rr_data.append(rr_entry)

        return rr_data

    def get_options_by_strike_and_expire_date(self, stock=None, expireDate=None, strike=None, direction='all'):
        '''
        get a list of options contracts by expire date and strike price
        strike: string
        '''
        opts = self.get_options(stock=stock, expireDate=expireDate, direction=direction)
        return [c for c in opts if c['strikePrice'] == strike]

    # others

    def get_tradable(self, stock='') :
        '''
        get if stock is tradable
        '''
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.is_tradable(self.get_ticker(stock)), headers=headers, timeout=self.wb.timeout)

        return response.json()

    def alerts_list(self) :
        '''
        Get alerts
        '''
        headers = self.wb.build_req_headers()

        response = requests.get(endpoint.list_alerts(), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        if 'data' in result:
            return result.get('data', [])
        else:
            return None

    def alerts_remove(self, alert=None, priceAlert=True, smartAlert=True):
        '''
        remove alert
        alert is retrieved from alert_list
        '''
        headers = self.wb.build_req_headers()

        if alert.get('tickerWarning') and priceAlert:
            alert['tickerWarning']['remove'] = True
            alert['warningInput'] = alert['tickerWarning']

        if alert.get('eventWarning') and smartAlert:
            alert['eventWarning']['remove'] = True
            for rule in alert['eventWarning']['rules']:
                rule['active'] = 'off'
            alert['eventWarningInput'] = alert['eventWarning']

        response = requests.post(endpoint.remove_alert(), json=alert, headers=headers, timeout=self.wb.timeout)
        if response.status_code != 200:
            raise Exception('alerts_remove failed', response.status_code, response.reason)
        return True

    def alerts_add(self, stock=None, frequency=1, interval=1, priceRules=[], smartRules=[]):
        '''
        add price/percent/volume alert
        frequency: 1 is once a day, 2 is once a minute
        interval: 1 is once, 0 is repeating
        priceRules: list of dicts with below attributes per alert
            field: price , percent , volume
            type: price (above/below), percent (above/below), volume (vol in thousands)
            value: price, percent, volume amount
            remark: comment
        rules example:
        priceRules = [{'field': 'price', 'type': 'above', 'value': '900.00', 'remark': 'above'}, {'field': 'price', 'type': 'below',
             'value': '900.00', 'remark': 'below'}]
        smartRules = [{'type':'earnPre','active':'on'},{'type':'fastUp','active':'on'},{'type':'fastDown','active':'on'},
            {'type':'week52Up','active':'on'},{'type':'week52Down','active':'on'},{'type':'day5Down','active':'on'}]
        '''
        headers = self.wb.build_req_headers()

        rule_keys = ['value', 'field', 'remark', 'type', 'active']
        for line, rule in enumerate(priceRules, start=1):
            for key in rule:
                if key not in rule_keys:
                    raise Exception('malformed price alert priceRules found.')
            rule['alertRuleKey'] = line
            rule['active'] = 'on'

        alert_keys = ['earnPre', 'fastUp', 'fastDown', 'week52Up', 'week52Down', 'day5Up', 'day10Up', 'day20Up', 'day5Down', 'day10Down', 'day20Down']
        for rule in smartRules:
            if rule['type'] not in alert_keys:
                raise Exception('malformed smart alert smartRules found.')

        try:
            stock_data = self.get_tradable(stock)['data'][0]
            data = {
                'regionId': stock_data['regionId'],
                'tickerType': stock_data['type'],
                'tickerId': stock_data['tickerId'],
                'tickerSymbol': stock,
                'disSymbol': stock,
                'tinyName': stock_data['name'],
                'tickerName': stock_data['name'],
                'exchangeCode': stock_data['exchangeCode'],
                'showCode': stock_data['disExchangeCode'],
                'disExchangeCode': stock_data['disExchangeCode'],
                'eventWarningInput': {
                    'tickerId': stock_data['tickerId'],
                    'rules': smartRules,
                    'remove': False,
                    'del': False
                },
                'warningInput': {
                    'warningFrequency': frequency,
                    'warningInterval': interval,
                    'rules': priceRules,
                    'tickerId': stock_data['tickerId']
                }
            }
        except Exception as e:
            print(f'failed to build alerts_add payload data. error: {e}')

        response = requests.post(endpoint.add_alert(), json=data, headers=headers, timeout=self.wb.timeout)
        if response.status_code != 200:
            raise Exception('alerts_add failed', response.status_code, response.reason)
        return True

    def active_gainer_loser(self, direction='gainer', rank_type='afterMarket', count=50) :
        '''
        gets gainer / loser / active stocks sorted by change
        direction: gainer / loser / active
        rank_type: preMarket / afterMarket / 5min / 1d / 5d / 1m / 3m / 52w (gainer/loser)
                   volume / turnoverRatio / range (active)
        '''
        headers = self.wb.build_req_headers()

        response = requests.get(endpoint.active_gainers_losers(direction, self.wb._region_code, rank_type, count), headers=headers, timeout=self.wb.timeout)
        result = response.json()

        return result

    def run_screener(self, region=None, price_lte=None, price_gte=None, pct_chg_gte=None, pct_chg_lte=None, sort=None,
                     sort_dir=None, vol_lte=None, vol_gte=None):
        '''
        Notice the fact that endpoints are reversed on lte and gte, but this function makes it work correctly
        Also screeners are not sent by name, just the parameters are sent
        example: run_screener( price_lte=.10, price_gte=5, pct_chg_lte=.035, pct_chg_gte=.51)
        just a start, add more as you need it
        '''

        jdict = collections.defaultdict(dict)
        jdict['fetch'] = 200
        jdict['rules'] = collections.defaultdict(str)
        jdict['sort'] = collections.defaultdict(str)
        jdict['attach'] = {'hkexPrivilege': 'true'}  #unknown meaning, was in network trace

        jdict['rules']['wlas.screener.rule.region'] = 'securities.region.name.6'
        if not price_lte is None and not price_gte is None:
            # lte and gte are backwards
            jdict['rules']['wlas.screener.rule.price'] = 'gte=' + str(price_lte) + '&lte=' + str(price_gte)

        if not vol_lte is None and not vol_gte is None:
            # lte and gte are backwards
            jdict['rules']['wlas.screener.rule.volume'] = 'gte=' + str(vol_lte) + '&lte=' + str(vol_gte)

        if not pct_chg_lte is None and not pct_chg_gte is None:
            # lte and gte are backwards
            jdict['rules']['wlas.screener.rule.changeRatio'] = 'gte=' + str(pct_chg_lte) + '&lte=' + str(pct_chg_gte)

        if sort is None:
            jdict['sort']['rule'] = 'wlas.screener.rule.price'
        if sort_dir is None:
            jdict['sort']['desc'] = 'true'

        # jdict = self._ddict2dict(jdict)
        response = requests.post(endpoint.screener(), json=jdict, timeout=self.wb.timeout)
        result = response.json()
        return result

    def get_analysis(self, stock=None):
        '''
        get analysis info and returns a dict of analysis ratings
        '''
        headers = self.wb.build_req_headers()
        return requests.get(endpoint.analysis(self.get_ticker(stock)), headers=headers, timeout=self.wb.timeout).json()

    def get_capital_flow(self, stock=None, tId=None, show_hist=True):
        '''
        get capital flow
        :param stock:
        :param tId:
        :param show_hist:
        :return: list of capital flow
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        return requests.get(endpoint.analysis_capital_flow(tId, show_hist), headers=headers, timeout=self.wb.timeout).json()

    def get_etf_holding(self, stock=None, tId=None, has_num=0, count=50):
        '''
        get ETF holdings by stock
        :param stock:
        :param tId:
        :param has_num:
        :param count:
        :return: list of ETF holdings
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        return requests.get(endpoint.analysis_etf_holding(tId, has_num, count), headers=headers, timeout=self.wb.timeout).json()

    def get_institutional_holding(self, stock=None, tId=None):
        '''
        get institutional holdings
        :param stock:
        :param tId:
        :return: list of institutional holdings
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        return requests.get(endpoint.analysis_institutional_holding(tId), headers=headers, timeout=self.wb.timeout).json()

    def get_short_interest(self, stock=None, tId=None):
        '''
        get short interest
        :param stock:
        :param tId:
        :return: list of short interest
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        return requests.get(endpoint.analysis_shortinterest(tId), headers=headers, timeout=self.wb.timeout).json()

    def get_financials(self, stock=None):
        '''
        get financials info and returns a dict of financial info
        '''
        headers = self.wb.build_req_headers()
        return requests.get(endpoint.fundamentals(self.get_ticker(stock)), headers=headers, timeout=self.wb.timeout).json()

    def get_news(self, stock=None, tId=None, Id=0, items=20):
        '''
        get news and returns a list of articles
        params:
            Id: 0 is latest news article
            items: number of articles to return
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        return requests.get(endpoint.news(tId, Id, items), headers=headers, timeout=self.wb.timeout).json()

    def get_bars(self, stock=None, tId=None, interval='m1', count=1, extendTrading=0, timeStamp=None):
        '''
        get bars returns a pandas dataframe
        params:
            interval: m1, m5, m15, m30, h1, h2, h4, d1, w1
            count: number of bars to return
            extendTrading: change to 1 for pre-market and afterhours bars
            timeStamp: If epoc timestamp is provided, return bar count up to timestamp. If not set default to current time.
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        if timeStamp is None:
            # if not set, default to current time
            timeStamp = int(time.time())

        params = {'extendTrading': extendTrading}
        df = DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'vwap'])
        df.index.name = 'timestamp'
        response = requests.get(
            endpoint.bars(tId, interval, count, timeStamp),
            params=params,
            headers=headers,
            timeout=self.wb.timeout,
        )
        result = response.json()
        time_zone = timezone(result[0]['timeZone'])
        for row in result[0]['data']:
            row = row.split(',')
            row = ['0' if value == 'null' else value for value in row]
            data = {
                'open': float(row[1]),
                'high': float(row[3]),
                'low': float(row[4]),
                'close': float(row[2]),
                'volume': float(row[6]),
                'vwap': float(row[7])
            }
            #convert to a panda datetime64 which has extra features like floor and resample
            df.loc[to_datetime(datetime.fromtimestamp(int(row[0])).astimezone(time_zone))] = data
        return df.iloc[::-1]

    def get_bars_crypto(self, stock=None, tId=None, interval='m1', count=1, extendTrading=0, timeStamp=None):
        '''
        get bars returns a pandas dataframe
        params:
            interval: m1, m5, m15, m30, h1, h2, h4, d1, w1
            count: number of bars to return
            extendTrading: change to 1 for pre-market and afterhours bars
            timeStamp: If epoc timestamp is provided, return bar count up to timestamp. If not set default to current time.
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        params = {'type': interval, 'count': count, 'extendTrading': extendTrading, 'timestamp': timeStamp}
        df = DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'vwap'])
        df.index.name = 'timestamp'
        response = requests.get(endpoint.bars_crypto(tId), params=params, headers=headers, timeout=self.wb.timeout)
        result = response.json()
        time_zone = timezone(result[0]['timeZone'])
        for row in result[0]['data']:
            row = row.split(',')
            row = ['0' if value == 'null' else value for value in row]
            data = {
                'open': float(row[1]),
                'high': float(row[3]),
                'low': float(row[4]),
                'close': float(row[2]),
                'volume': float(row[6]),
                'vwap': float(row[7])
            }
            #convert to a panda datetime64 which has extra features like floor and resample
            df.loc[to_datetime(datetime.fromtimestamp(int(row[0])).astimezone(time_zone))] = data
        return df.iloc[::-1]

    def get_options_bars(self, derivativeId=None, interval='1m', count=1, direction=1, timeStamp=None):
        '''
        get bars returns a pandas dataframe
        params:
            derivativeId: to be obtained from option chain, eg option_chain[0]['call']['tickerId']
            interval: 1m, 5m, 30m, 60m, 1d
            count: number of bars to return
            direction: 1 ignores {count} parameter & returns all bars on and after timestamp
                       setting any other value will ignore timestamp & return latest {count} bars
            timeStamp: If epoc timestamp is provided, return bar count up to timestamp. If not set default to current time.
        '''
        headers = self.wb.build_req_headers()
        if derivativeId is None:
            raise ValueError('Must provide a derivative ID')

        params = {'type': interval, 'count': count, 'direction': direction, 'timestamp': timeStamp}
        df = DataFrame(columns=['open', 'high', 'low', 'close', 'volume', 'vwap'])
        df.index.name = 'timestamp'
        response = requests.get(endpoint.options_bars(derivativeId), params=params, headers=headers, timeout=self.wb.timeout)
        result = response.json()
        time_zone = timezone(result[0]['timeZone'])
        for row in result[0]['data'] :
            row = row.split(',')
            row = ['0' if value == 'null' else value for value in row]
            data = {
                'open': float(row[1]),
                'high': float(row[3]),
                'low': float(row[4]),
                'close': float(row[2]),
                'volume': float(row[6]),
                'vwap': float(row[7])
            }
            #convert to a panda datetime64 which has extra features like floor and resample
            df.loc[to_datetime(datetime.fromtimestamp(int(row[0])).astimezone(time_zone))] = data
        return df.iloc[::-1]

    def get_chart_data(self, stock=None, tId=None, ma=5, timestamp=None):
        bars = self.get_bars(stock=stock, tId=tId, interval='d1', count=1200, timestamp=timestamp)
        ma_data = bars['close'].rolling(ma).mean()
        return ma_data.dropna()

    def get_calendar(self, stock=None, tId=None):
        '''
        There doesn't seem to be a way to get the times the market is open outside of the charts.
        So, best way to tell if the market is open is to pass in a popular stock like AAPL then
        and see the open and close hours as would be marked on the chart
        and see if the last trade date is the same day as today's date
        :param stock:
        :param tId:
        :return: dict of 'market open', 'market close', 'last trade date'
        '''
        headers = self.wb.build_req_headers()
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        params = {'type': 'm1', 'count': 1, 'extendTrading': 0}
        response = requests.get(endpoint.bars(tId), params=params, headers=headers, timeout=self.wb.timeout)
        result = response.json()
        time_zone = timezone(result[0]['timeZone'])
        last_trade_date = datetime.fromtimestamp(int(result[0]['data'][0].split(',')[0])).astimezone(time_zone)
        today = datetime.today().astimezone()  #use no time zone to have it pull in local time zone

        if last_trade_date.date() < today.date():
            # don't know what today's open and close times are, since no trade for today yet
            return {'market open': None, 'market close': None, 'trading day': False}

        for d in result[0]['dates']:
            if d['type'] == 'T':
                market_open = today.replace(
                    hour=int(d['start'].split(':')[0]),
                    minute=int(d['start'].split(':')[1]),
                    second=0)
                market_open -= timedelta(microseconds=market_open.microsecond)
                market_open = market_open.astimezone(time_zone)  #set to market timezone

                market_close = today.replace(
                    hour=int(d['end'].split(':')[0]),
                    minute=int(d['end'].split(':')[1]),
                    second=0)
                market_close -= timedelta(microseconds=market_close.microsecond)
                market_close = market_close.astimezone(time_zone) #set to market timezone

                #this implies that we have waited a few minutes from the open before trading
                return {'market open': market_open ,  'market close':market_close, 'trading day':True}
        #otherwise
        return None

    def get_dividends(self):
        ''' Return account's incoming dividend info '''
        headers = self.wb.build_req_headers()
        data = {}
        response = requests.post(endpoint.dividends(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    def get_five_min_ranking(self, extendTrading=0):
        '''
        get 5 minute trend ranking
        '''
        rank = []
        headers = self.wb.build_req_headers()
        params = {'regionId': self.wb._region_code, 'userRegionId': self.wb._region_code, 'platform': 'pc', 'limitCards': 'latestActivityPc'}
        response = requests.get(endpoint.rankings(), params=params, headers=headers, timeout=self.wb.timeout)
        result = response.json()[0].get('data')
        if extendTrading:
            for data in result:
                if data['id'] == 'latestActivityPc.faList':
                    rank = data['data']
        else:
            for data in result:
                if data['id'] == 'latestActivityPc.5minutes':
                    rank = data['data']
        return rank

    def get_watchlists(self, as_list_symbols=False) :
        """
        get user watchlists
        """
        headers = self.wb.build_req_headers()
        params = {'version': 0}
        response = requests.get(endpoint.portfolio_lists(), params=params, headers=headers, timeout=self.wb.timeout)

        if not as_list_symbols :
            return response.json()['portfolioList']
        else:
            list_ticker = response.json()['portfolioList'][0].get('tickerList')
            return list(map(lambda x: x.get('symbol'), list_ticker))

    def is_logged_in(self):
        '''
        Check if login session is active
        '''
        try:
            self.wb.get_account_id()
        except KeyError:
            return False
        else:
            return True

    def get_press_releases(self, stock=None, tId=None, typeIds=None, num=50):
        '''
        gets press releases, useful for getting past earning reports
        typeIds: None (all) or comma-separated string of the following: '101' (financials) / '104' (insiders)
        it's possible they add more announcment types in the future, so check the 'announcementTypes'
        field on the response to verify you have the typeId you want
        '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = self.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.press_releases(tId, typeIds, num), headers=headers, timeout=self.wb.timeout)
        result = response.json()

        return result

    def get_calendar_events(self, event, start_date=None, page=1, num=50):
        '''
        gets calendar events
        event: 'earnings' / 'dividend' / 'splits'
        start_date: in `YYYY-MM-DD` format, today if None
        '''
        if start_date is None:
            start_date = datetime.today().strftime('%Y-%m-%d')
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.calendar_events(event, self.wb._region_code, start_date, page, num), headers=headers, timeout=self.wb.timeout)
        result = response.json()

        return result

