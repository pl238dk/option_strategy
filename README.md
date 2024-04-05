# Option Spread Strategy Calculator

## Usage

```
usage: main.py [-h] [--exp EXP] [--width WIDTH] [--credit | --no-credit] [--debit | --no-debit] [--volume VOLUME] [--ratio RATIO] [--pop POP] [--roc ROC] [--size SIZE] symbol

positional arguments:
  symbol                ticker to retrieve data

options:
  -h, --help            show this help message and exit
  --exp EXP             expiration to grab option data
  --width WIDTH         width of strikes (default 1)
  --credit, --no-credit
                        show credit spreads (default: True)
  --debit, --no-debit   show debit spreads (default: False)
  --volume VOLUME       filter above long volume (default 200)
  --ratio RATIO         filter above long ratio (default .1)
  --pop POP             filter above pop (default 60)
  --roc ROC             filter above return (default .07)
  --size SIZE           set position size in dollars
```

As an example command:
    Symbol: META
    Expiration: 2024-04-19
    Size: 25,000
    Filter Probability of Profit: > 60%
    Filter Long Volume: > 200
    Filter Return on Capital: > 0.07 (raw percent)
    Filter Long Bid/Ask Ratio: > 0.1 (raw percent)
    Display Credit Spreads
    Display Debit Spreads
```
python3 cli.py META --exp=2024-04-19 --size=25000 --credit --pop=60 --volume=200 --roc=0.07 --debit --ratio=0.1
```

## Installation

```
python3 -m pip install -r requirements.txt
```
