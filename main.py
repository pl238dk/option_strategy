import json
import yfinance as yf
import datetime
import numpy as np

import argparse

p = argparse.ArgumentParser()
p.add_argument('symbol', type=str, help='ticker to retrieve data')
p.add_argument('--exp', type=str, help='expiration to grab option data', required=False)
p.add_argument('--width', type=int, help='width of strikes (default 1)', default=1)
p.add_argument('--credit', type=bool, help='show credit spreads', default=True, action=argparse.BooleanOptionalAction)
p.add_argument('--debit', type=bool, help='show debit spreads', default=False, action=argparse.BooleanOptionalAction)
p.add_argument('--volume', type=int, help='filter above long volume (default 200)', default=200)
p.add_argument('--ratio', type=float, help='filter above long ratio (default .1)', default=0.1)
p.add_argument('--pop', type=int, help='filter above pop (default 60)', default=60)
p.add_argument('--roc', type=float, help='filter above return (default .07)', default=0.07)
p.add_argument('--size', type=int, help='set position size in dollars', default=500)
args = p.parse_args()

class npEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int32):
            return int(obj)
        return json.JSONEncoder.default(self, obj)

def convert_date(d):
    return datetime.datetime.strptime(d, '%Y-%m-%d')

def is_monthly(d):
    today = datetime.datetime.today()
    ptime = convert_date(d)
    if ptime.weekday() == 4:
        if (ptime.day - 1) // 7 == 2:
            return True
    return False

def get_credit_spread_row(chain, long_strike, short_strike):
    # get row and calculate mid price
    long = chain[chain.strike == long_strike].iloc[0]
    long_mid = (long.bid + long.ask) / 2
    long_bid_ask_ratio = 0.0 if long.ask == 0.0 else (long.ask - long.bid) / long.ask
    short = chain[chain.strike == short_strike].iloc[0]
    short_mid = (short.bid + short.ask) / 2
    short_bid_ask_ratio = 0.0 if short.ask == 0.0 else (short.ask - short.bid) / short.ask
    #
    net_credit = (short_mid - long_mid) * 100
    #net_debit = (short_mid - long_mid) * 100
    volume_long = long.volume
    volume_short = short.volume
    margin = abs(short_strike - long_strike) * 100
    # diff between strikes, minus debit
    max_profit = (abs(short_strike - long_strike) * 100) - abs(net_credit)
    max_loss = margin - net_credit
    # prevents divide-by-zero by resetting returns to zero if lower max_profit
    return_on_capital = 0.0 if margin <= 0 else (abs(net_credit) / margin)
    probability_of_profit = (100 - (abs(net_credit) / abs(short_strike - long_strike)))
    # call credits have a lower short strike
    if int(long_strike) > int(short_strike):
        breakeven = short_strike + abs(short_mid - long_mid)
    else:
        breakeven = short_strike - abs(short_mid - long_mid)
    output = {
        'spread_type': 'credit',
        'long': {
            'strike': long_strike,
            'bid': long.bid,
            'mid': long_mid,
            'ask': long.ask,
            'ratio': long_bid_ask_ratio,
            'volume': volume_long,
        },
        'short': {
            'strike': short_strike,
            'bid': short.bid,
            'mid': short_mid,
            'ask': short.ask,
            'ratio': short_bid_ask_ratio,
            'volume': volume_short,
        },
        'net_credit': net_credit,
        #'net_debit': net_debit,
        'margin': margin,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'roc': return_on_capital,
        'pop': probability_of_profit,
        'breakeven': breakeven,
    }
    return output

def get_credit_spread(chain, strike_diff=1):
    output = {
        'calls': [],
        'puts': [],
    }
    calls, puts = chain.calls, chain.puts
    calls = calls[calls['inTheMoney'] == False].copy()
    puts = puts[puts['inTheMoney'] == False].copy()
    # replace volume nan with zero
    calls['volume'] = calls['volume'].fillna(value=0).astype(int)
    puts['volume'] = puts['volume'].fillna(value=0).astype(int)
    call_strikes = list(calls.strike)
    for idx, higher_strike in enumerate(call_strikes[strike_diff:]):
        co = get_credit_spread_row(calls, higher_strike, call_strikes[idx])
        output['calls'].append(co)
    #
    put_strikes = list(puts.strike)
    for idx, higher_strike in enumerate(put_strikes[strike_diff:]):
        po = get_credit_spread_row(puts, put_strikes[idx], higher_strike)
        output['puts'].append(po)
    return output

def get_debit_spread_row(chain, long_strike, short_strike):
    # get row and calculate mid price
    long = chain[chain.strike == long_strike].iloc[0]
    long_mid = (long.bid + long.ask) / 2
    long_bid_ask_ratio = 0.0 if long.ask == 0.0 else (long.ask - long.bid) / long.ask
    short = chain[chain.strike == short_strike].iloc[0]
    short_mid = (short.bid + short.ask) / 2
    short_bid_ask_ratio = 0.0 if short.ask == 0.0 else (short.ask - short.bid) / short.ask
    #
    net_debit = (short_mid - long_mid) * 100
    volume_long = long.volume
    volume_short = short.volume
    # diff between strikes, minus debit
    max_profit = (abs(short_strike - long_strike) * 100) - abs(net_debit)
    max_loss = net_debit
    # prevents divide-by-zero by resetting returns to zero if lower max_profit
    if max_profit < abs(net_debit):
        return_on_capital = 0.0 if max_profit <= 0 else (max_profit / abs(net_debit))
    else:
        return_on_capital = 0.0 if max_profit <= 0 else (abs(net_debit) / max_profit)
    # call debits have a higher short strike
    if int(long_strike) > int(short_strike):
        breakeven = long_strike - abs(short_mid - long_mid)
    else:
        breakeven = long_strike + abs(short_mid - long_mid)
    probability_of_profit = (100 - (abs(max_profit) / abs(short_strike - long_strike)))
    output = {
        'spread_type': 'debit',
        'long': {
            'strike': long_strike,
            'bid': long.bid,
            'mid': long_mid,
            'ask': long.ask,
            'ratio': long_bid_ask_ratio,
            'volume': volume_long,
        },
        'short': {
            'strike': short_strike,
            'bid': short.bid,
            'mid': short_mid,
            'ask': short.ask,
            'ratio': short_bid_ask_ratio,
            'volume': volume_short,
        },
        'net_debit': net_debit,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'roc': return_on_capital,
        'pop': probability_of_profit,
        'breakeven': breakeven,
    }
    return output

def get_debit_spread(chain, strike_diff=1):
    output = {
        'calls': [],
        'puts': [],
    }
    calls, puts = chain.calls, chain.puts
    calls = calls[calls['inTheMoney'] == True].copy()
    puts = puts[puts['inTheMoney'] == True].copy()
    calls['volume'] = calls['volume'].fillna(value=0).astype(int)
    puts['volume'] = puts['volume'].fillna(value=0).astype(int)
    call_strikes = list(calls.strike)
    for idx, higher_strike in enumerate(call_strikes[strike_diff:]):
        co = get_debit_spread_row(calls, call_strikes[idx], higher_strike)
        output['calls'].append(co)
        #'''
    #
    put_strikes = list(puts.strike)
    for idx, higher_strike in enumerate(put_strikes[strike_diff:]):
        po = get_debit_spread_row(puts, higher_strike, put_strikes[idx])
        output['puts'].append(po)
    return output

now = datetime.datetime.now()
symbol = args.symbol.upper()
print(f'-- Symbol : {symbol} --')
t = yf.Ticker(symbol)

if args.exp:
    exp = convert_date(args.exp)
    dte = (exp - now).days
    chain = t.option_chain(args.exp)
    if args.credit:
        print('\n## Credit Spreads ##')
        cs = get_credit_spread(chain, strike_diff=args.width)
        with open(f'{symbol}_{args.exp}_credit.json', 'w') as f:
            f.write(json.dumps(cs, indent=2, cls=npEncoder))
        print('\n-- Bear Call --')
        for x in cs['calls']:
            #print(x)
            if x['long']['volume'] < args.volume: continue
            if x['long']['ratio'] > args.ratio: continue
            if x['pop'] < args.pop: continue
            if x['roc'] < args.roc: continue
            size = int(args.size // x['margin'])
            percent_volume = (size / x['long']['volume'])
            profit_per_day = x['net_credit'] / dte
            msg = (
                f'[[ L {x["long"]["strike"]} / '
                f'S {x["short"]["strike"]} ]]\t'
                f'Margin: {x["margin"]*size:,.02f}\t'
                f'Size: {size}\t'
                f'Credit: {x["net_credit"]*size:,.02f}\t'
                f'Return: {x["roc"]*100:,.02f}%\t'
                f'Probability: {x["pop"]:,.02f}%\t'
                f'Breakeven: <{x["breakeven"]:,.02f}\t'
                f'Per Day: {profit_per_day:,.02f}\t'
                f'Long Volume: {x["long"]["volume"]}\t@ {percent_volume*100:,.02f}%'
            )
            print(msg)
        print('\n-- Bull Put --')
        for x in cs['puts']:
            #print(x)
            if x['long']['volume'] < args.volume: continue
            if x['long']['ratio'] > args.ratio: continue
            if x['pop'] < args.pop: continue
            if x['roc'] < args.roc: continue
            size = int(int(args.size) // x['margin'])
            percent_volume = (size / x['long']['volume'])
            profit_per_day = x['net_credit'] / dte
            msg = (
                f'[[ L {x["long"]["strike"]} / '
                f'S {x["short"]["strike"]} ]]\t'
                f'Margin: {x["margin"]*size:,.02f}\t'
                f'Size: {size}\t'
                f'Credit: {x["net_credit"]*size:,.02f}\t'
                f'Return: {x["roc"]*100:,.02f}%\t'
                f'Probability: {x["pop"]:,.02f}%\t'
                f'Breakeven: >{x["breakeven"]:,.02f}\t'
                f'Per Day: {profit_per_day:,.02f}\t'
                f'Long Volume: {x["long"]["volume"]}\t@ {percent_volume*100:,.02f}%'
            )
            print(msg)
    if args.debit:
        print('\n## Debit Spreads ##')
        ds = get_debit_spread(chain, strike_diff=args.width)
        with open(f'{symbol}_{args.exp}_debit.json', 'w') as f:
            f.write(json.dumps(ds, indent=2, cls=npEncoder))
        print('\n-- Bull Call --')
        for x in ds['calls']:
            #print(x)
            if x['long']['volume'] < args.volume: continue
            if x['long']['ratio'] > args.ratio: continue
            if x['pop'] < args.pop: continue
            if x['roc'] < args.roc: continue
            size = args.size // abs(x['net_debit'])
            percent_volume = (size / x['long']['volume'])
            profit_per_day = x['max_profit'] / dte
            msg = (
                f'[[ L {x["long"]["strike"]} / '
                f'S {x["short"]["strike"]} ]]\t'
                f'Debit: {x["net_debit"]*size:,.02f}\t'
                f'Size: {size}\t'
                f'Profit: {x["max_profit"]*size:,.02f}\t'
                f'Return: {x["roc"]*100:,.02f}%\t'
                f'Probability: {x["pop"]:,.02f}%\t'
                f'Breakeven: <{x["breakeven"]:,.02f}\t'
                f'Per Day: {profit_per_day:,.02f}\t'
                f'Long Volume: {x["long"]["volume"]}\t@ {percent_volume*100:,.02f}%'
            )
            print(msg)
        print('\n-- Bear Put --')
        for x in ds['puts']:
            #print(x)
            if x['long']['volume'] < args.volume: continue
            if x['long']['ratio'] > args.ratio: continue
            if x['pop'] < args.pop: continue
            if x['roc'] < args.roc: continue
            size = args.size // abs(x['net_debit'])
            percent_volume = (size / x['long']['volume'])
            profit_per_day = x['max_profit'] / dte
            msg = (
                f'[[ L {x["long"]["strike"]} / '
                f'S {x["short"]["strike"]} ]]\t'
                f'Debit: {x["net_debit"]*size:,.02f}\t'
                f'Size: {size}\t'
                f'Profit: {x["max_profit"]*size:,.02f}\t'
                f'Return: {x["roc"]*100:,.02f}%\t'
                f'Probability: {x["pop"]:,.02f}%\t'
                f'Breakeven: >{x["breakeven"]:,.02f}\t'
                f'Per Day: {profit_per_day:,.02f}\t'
                f'Long Volume: {x["long"]["volume"]}\t@ {percent_volume*100:,.02f}%'
            )
            print(msg)
else:
    print('-- expirations --')
    exp = t.options
    for x in exp:
        if is_monthly(x):
            print(f'{x} - Monthly')
        else:
            print(x)
