<div align="center">
<pre>
██╗    ██╗███████╗ ██████╗██╗     ██╗
██║    ██║██╔════╝██╔════╝██║     ██║
██║ █╗ ██║█████╗  ██║     ██║     ██║
██║███╗██║██╔══╝  ██║     ██║     ██║
╚███╔███╔╝███████╗╚██████╗███████╗██║
 ╚══╝╚══╝ ╚══════╝ ╚═════╝╚══════╝╚═╝
---------------------------------------------------
python cli to execute options trades
</pre>
</div>

Webull options chain is too hard to use? Following analysts is too slow? Try WeCli instead -- A python program that interprets messages, finds option details, and execute trades off those details. Highly configurable to your own needs.

![image](https://github.com/8pz/wecli/assets/70970973/bf871e33-997c-45dd-9a19-e7a86e3b9795)

This project is a submodule of [Ren Options Trader](https://github.com/8pz/ren-options-trader/) -- an automated webull options trader that can follow any analyst's entries and exits on Discord.

# Table of Contents

- [Getting Started](https://github.com/8pz/wecli#configuration)
- [Configuration](https://github.com/8pz/wecli#configuration)
- [Changelog](https://github.com/8pz/wecli#changelog)
- [Disclaimer](https://github.com/8pz/wecli#disclaimer)
- [License](https://github.com/8pz/wecli#license)
<!-- - [Wiki](https://github.com/8pz/wecli/wiki) -->

# Getting Started

1. Install [Python](https://www.python.org/downloads/release/python-3116/) 3.11.6

   ```powershell
   # check your version
   python --version
   ```

2. [Download](https://github.com/8pz/wecli/archive/refs/heads/main.zip) and extract the program.

   ```powershell
   git clone https://github.com/8pz/wecli.git
   ```

3. Install requirements

   ```powershell
   pip install -r requirements.txt 
   ```

4. Set up ```src/misc/config.json```. See [configuration](https://github.com/8pz/options-alert-trader/wiki/Configuration) on a detailed guide.

5. Run [main.py](https://github.com/8pz/wecli/blob/main/src/main.py)

# Configuration

The config system is located inside `src/misc/config.json`. Change the path to the config file in `main.py`.

## Login

```"email"``` is the email for your Webull account.

```"password"``` is the password for your Webull account.

```"did"``` is an access token for your Webull account. Find how to get that [here](https://github.com/8pz/wecli/wiki/Guides#how-to-get-your-did)

```"trading_pin"``` is the trading pin to unlock your Webull account for trading. Not required for paper trading.

```json
"login": {
    "email": "",
    "password": "",
    "did": "",
    "trading_pin": ""
},
```

## Trade Settings

`"api_type"` changes the what account orders are placed on.

`"auto_cancel_order"` will automatically cancel an order after 5 tries, 3 seconds apart.

`"frequency"` is a list of integers that determine how often / total tries the program will allow before moving on.

`"bto_offset"` is the offset when placing buy orders.

`"stc_offset"` is the offset when placing sell orders.

`"max_per_trade"` is how it will determine how many contracts to buy. The program will buy as many as possible as long it does not exceed this amount.


```json
"api_type": "paper", // paper, live
"auto_cancel_order": true,
"frequency": [3, 5]
"bto_offset": 0.05,
"stc_offset": -0.03,
"max_per_trade": 750,
```

## Debugging/Paths

`"debug"` turns debug logs on and off.

`"log_path"` is where logs are outputted.

`"log_format"` is the log format.

`"csv_path"` is where trade info will be printed

`"variable_path"` is where the persistance module stores lists to.

```json
"debug": false,
"log_path": "src/misc/app.log",
"log_format": "%(asctime)s %(message)s",
"csv_path": "src/misc/trades.csv",
"variable_path": "src/misc/current_positions.pkl"
```

## Tickers

```"tickers"``` is a list of tickers that the program will use to look for the option.

```json
"tickers": [
    "SPX",
    "SPY",
    "QQQ",
    "META",
    "AAPL",
    "TSLA",
    "NVDA",
    "NFLX",
    "SNOW",
    "GLD",
    "IWM",
    "AMZN",
    "XOM"
],
```

## Triggers

```"entry"``` is a list of keywords that allows the program to determine that your entry will create a new trade.

```"trim"``` is a list of keywords that allows the program to determine that your entry will trim half of a current position.

```"exit"``` is a list of keywords that allows the program to determine that your entry will close a current position.

**Disclaimer:** Do not change the order of these as that will break the priority order.

```json
"triggers": {
    "trim": ["trim"],
    "exit": ["exit"],
    "entry": ["buy"] // leaving this empty allows the program to enter trades without a keyword. Lowest priority so it will trim/exit if those criteria are met first
}
```

# Changelog

### 11/25/23

- Initial release

### 11/27/23

- Refactored API system for readability
- Auto fetch last position
- Persist positions list
- Auto cancel order (if not filled)

# Disclaimer

This project is a submodule of [Ren Options Trader](https://github.com/8pz/ren-options-trader/) -- an automated webull options trader that can follow any analyst's entries and exits on Discord.

This project is in development. Bugs **will** occur, please test and monitor the system yourself.

This project and all dependencies have not been tested extensively. Use with caution.

**By using this project, you expressly acknowledge and agree to be bound by all the terms and conditions outlined below.**

<details>
<summary>Terms and Conditions</summary>

<br>

1. Not Investment Advice:
   This project and the alerts it tracks do not provide financial or investment advice. Users are solely responsible for their trading decisions, and should not rely on this program for investment guidance.

2. No Guarantees:
   Trading involves risks, and there are no guarantees of success. Past performance is not indicative of future results. Users should be aware of the inherent risks associated with trading.

3. Not Responsible for Losses:
   The creators and contributors of this project are not liable for any financial losses incurred by users due to their trading activities. Users use the program at their own risk.

4. Use at Your Own Risk:
   Users are encouraged to use this project at their own risk and with caution. It is recommended to seek professional financial advice before making any investment decisions.

5. No Endorsement of Alerts:
   This project does not endorse or validate the alerts it tracks. It is a tool for tracking and automation purposes only.

6. Disclaimer of Accuracy:
   The information provided by this project may not always be accurate or up-to-date. Users should verify and cross-check the information independently.

7. No Legal or Regulatory Compliance:
   This project does not offer legal or regulatory compliance services. Users are responsible for complying with all applicable laws and regulations.

</details>

# License

The project is licensed under: **CC-NY-BC**

Contact me for commercial use

- discord @ 123781023
- tele @ onasn
- email @ 123781023@proton.me
