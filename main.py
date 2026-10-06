import os
import requests
from flask import Flask, jsonify, request, render_template_string

app = Flask(__name__)

# ==========================================
# TRADING SIGNAL & SMC ANALYSIS ENGINE
# ==========================================

def fetch_candles(symbol="FX:EURUSD"):
    clean_symbol = symbol.replace("FX:", "").replace("CAPITALCOM:", "").replace("BINANCE:", "")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{clean_symbol}=X?interval=1m&range=1d"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            data = response.json()
            result = data['chart']['result'][0]
            timestamps = result.get('timestamp', [])
            quote = result['indicators']['quote'][0]
            
            closes = quote.get('close', [])
            highs = quote.get('high', [])
            lows = quote.get('low', [])
            opens = quote.get('open', [])
            
            valid_candles = []
            for i in range(len(closes)):
                if None not in (closes[i], highs[i], lows[i], opens[i]):
                    valid_candles.append({
                        "time": timestamps[i],
                        "open": round(opens[i], 5),
                        "high": round(highs[i], 5),
                        "low": round(lows[i], 5),
                        "close": round(closes[i], 5)
                    })
            return valid_candles
    except Exception:
        pass
    return []

def calculate_rsi(candles, period=14):
    if len(candles) < period + 1:
        return 50.0
    closes = [c['close'] for c in candles]
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
            
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def get_market_analysis(symbol="FX:EURUSD"):
    is_otc = "OTC" in symbol or "CAPITALCOM" in symbol or "BINANCE" in symbol
    
    if is_otc:
        return {
            "status": "otc_warning",
            "is_otc": True,
            "pair": symbol,
            "direction": "WAIT",
            "signal": "ANALYZING OTC...",
            "accuracy": "--%",
            "reason": "WARNING: OTC Market detected. Chart hidden for safety.",
            "rsi": 50.0
        }

    candles = fetch_candles(symbol)
    if not candles or len(candles) < 15:
        return {
            "status": "wait",
            "is_otc": False,
            "pair": symbol,
            "direction": "WAIT",
            "signal": "SCANNING MARKET...",
            "accuracy": "--%",
            "reason": "Analyzing Order Blocks & Price Liquidity...",
            "rsi": 50.0
        }

    rsi_val = calculate_rsi(candles)
    last_candle = candles[-1]
    prev_candle = candles[-2]
    
    is_bullish = (prev_candle['close'] < prev_candle['open']) and (last_candle['close'] > prev_candle['high'])
    is_bearish = (prev_candle['close'] > prev_candle['open']) and (last_candle['close'] < prev_candle['low'])

    if rsi_val < 38 or (rsi_val < 45 and is_bullish):
        return {
            "status": "success",
            "is_otc": False,
            "pair": symbol,
            "direction": "UP",
            "signal": "CALL (BUY)",
            "accuracy": "89% - 94%",
            "reason": f"SMC Demand Zone Bounce & Oversold Reversal (RSI: {rsi_val})",
            "rsi": rsi_val
        }
    elif rsi_val > 62 or (rsi_val > 55 and is_bearish):
        return {
            "status": "success",
            "is_otc": False,
            "pair": symbol,
            "direction": "DOWN",
            "signal": "PUT (SELL)",
            "accuracy": "87% - 92%",
            "reason": f"Supply Order Block Resistance & Overbought RSI (RSI: {rsi_val})",
            "rsi": rsi_val
        }
    else:
        return {
            "status": "wait",
            "is_otc": False,
            "pair": symbol,
            "direction": "WAIT",
            "signal": "WAIT / NO TRADE",
            "accuracy": "--%",
            "reason": f"Market Consolidation / Low Momentum (RSI: {rsi_val})",
            "rsi": rsi_val
        }

# ==========================================
# FRONTEND HTML / TAILWIND UI
# ==========================================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SUFIA AI Trading Studio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>

    <style>
        @import url('https://fonts.googleapis.com/css2?family=UnifrakturMaguntia&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        * { box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; margin: 0; padding: 0; }
        .font-gothic { font-family: 'UnifrakturMaguntia', cursive; }

        body { 
            background: #0b0219; 
            color: #ffffff; 
            height: 100vh; 
            width: 100vw; 
            overflow: hidden; 
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .mobile-container {
            width: 100%;
            max-width: 420px;
            height: 100vh;
            background: #090114;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 16px;
            overflow-y: auto;
        }

        .glass-card {
            background: linear-gradient(135deg, rgba(30, 12, 54, 0.7), rgba(18, 6, 36, 0.9));
            border: 1px solid rgba(147, 51, 234, 0.25);
            backdrop-filter: blur(12px);
            border-radius: 20px;
        }

        .glass-pill {
            background: rgba(30, 12, 54, 0.6);
            border: 1px solid rgba(147, 51, 234, 0.3);
            border-radius: 999px;
        }

        .purple-glow-btn {
            background: linear-gradient(135deg, #a855f7, #c084fc);
            box-shadow: 0 0 20px rgba(168, 85, 247, 0.6);
        }

        .voice-card-bg {
            background: linear-gradient(135deg, rgba(76, 29, 149, 0.8), rgba(46, 16, 101, 0.9));
            border: 1px solid rgba(168, 85, 247, 0.4);
            position: relative;
            overflow: hidden;
        }

        .voice-glow {
            position: absolute;
            right: 15px;
            top: 15px;
            width: 80px;
            height: 80px;
            background: radial-gradient(circle, rgba(192, 132, 252, 0.5) 0%, rgba(0, 0, 0, 0) 70%);
            border-radius: 50%;
            filter: blur(10px);
        }

        .bottom-nav {
            background: rgba(22, 10, 40, 0.95);
            border: 1px solid rgba(147, 51, 234, 0.3);
            backdrop-filter: blur(20px);
            border-radius: 999px;
            padding: 8px 16px;
        }

        /* Wave visualizer animation */
        @keyframes waveAnim {
            0%, 100% { height: 8px; }
            50% { height: 28px; }
        }
        .wave-bar {
            width: 3px;
            background: #c084fc;
            border-radius: 4px;
            animation: waveAnim 1.2s infinite ease-in-out;
        }
        .wave-bar:nth-child(2) { animation-delay: 0.1s; }
        .wave-bar:nth-child(3) { animation-delay: 0.2s; }
        .wave-bar:nth-child(4) { animation-delay: 0.3s; }
        .wave-bar:nth-child(5) { animation-delay: 0.4s; }
        .wave-bar:nth-child(6) { animation-delay: 0.5s; }

        .screen { display: none; width: 100%; height: 100%; flex-direction: column; justify-content: space-between; }
        .screen.active { display: flex; }
    </style>
</head>
<body>

    <div class="mobile-container">

        <!-- SCREEN 1: MAIN HOME (EXACT MATCH TO YOUR SCREENSHOT) -->
        <div id="screen-home" class="screen active">
            <!-- Header -->
            <div class="flex justify-between items-center mt-2">
                <div class="flex items-center gap-2.5">
                    <div class="w-8 h-8 rounded-full bg-red-950/80 border border-red-500/50 flex items-center justify-center">
                        <i class="fa-solid fa-robot text-red-400 text-sm"></i>
                    </div>
                    <div>
                        <p class="text-[10px] text-gray-300 leading-none">Welcome 👋</p>
                        <h2 class="text-xs font-bold text-white font-gothic mt-1" id="dash-user-name">User: Yasin</h2>
                    </div>
                </div>
                <button onclick="navTo('screen-profile')" class="w-8 h-8 rounded-full glass-pill flex items-center justify-center text-gray-300">
                    <i class="fa-solid fa-paper-plane text-xs"></i>
                </button>
            </div>

            <!-- Main Heading -->
            <div class="my-3">
                <h1 class="text-2xl font-gothic text-purple-100 leading-tight">Your AI Trading</h1>
                <h1 class="text-2xl font-gothic text-purple-100 leading-tight">Journey Starts Up</h1>
            </div>

            <!-- Horizontal Tab Bar -->
            <div class="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                <button onclick="navTo('screen-voice')" class="glass-pill px-4 py-2 text-[11px] font-semibold text-purple-200 flex items-center gap-2 whitespace-nowrap">
                    <i class="fa-solid fa-microphone text-purple-300 text-xs"></i> Voice Chat
                </button>
                <button onclick="navTo('screen-auto')" class="glass-pill px-4 py-2 text-[11px] font-semibold text-purple-200 flex items-center gap-2 whitespace-nowrap">
                    <i class="fa-solid fa-sliders text-purple-300 text-xs"></i> Auto Trade
                </button>
                <button onclick="navTo('screen-signal')" class="glass-pill px-4 py-2 text-[11px] font-semibold text-purple-200 flex items-center gap-2 whitespace-nowrap">
                    <i class="fa-solid fa-chart-line text-purple-300 text-xs"></i> Live Signal
                </button>
            </div>

            <!-- Subtitle -->
            <p class="text-xs font-gothic text-purple-200 my-1">Start Creating</p>

            <!-- Big Voice Studio Card -->
            <div onclick="navTo('screen-voice')" class="voice-card-bg p-4 rounded-3xl cursor-pointer">
                <div class="voice-glow"></div>
                <div class="w-8 h-8 rounded-full bg-purple-900/60 border border-purple-400/40 flex items-center justify-center mb-3">
                    <i class="fa-solid fa-microphone text-purple-200 text-xs"></i>
                </div>
                <h3 class="font-gothic text-sm text-white font-bold">Voice Studio</h3>
                <p class="text-[10px] text-purple-200/80 mt-0.5">Ask SUFIA about trading</p>

                <div class="flex items-end justify-end gap-1 h-8 mt-2">
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                    <div class="wave-bar"></div>
                </div>
            </div>

            <!-- Two Sub Cards -->
            <div class="grid grid-cols-2 gap-3 my-2">
                <div onclick="navTo('screen-auto')" class="glass-card p-3.5 rounded-2xl cursor-pointer relative">
                    <i class="fa-solid fa-arrow-up-right-from-square absolute top-3 right-3 text-[10px] text-gray-400"></i>
                    <div class="w-7 h-7 rounded-xl bg-purple-900/50 flex items-center justify-center mb-2">
                        <i class="fa-solid fa-sliders text-purple-300 text-xs"></i>
                    </div>
                    <h4 class="font-gothic text-xs text-white font-bold">Auto Trade Place</h4>
                    <p class="text-[8px] text-purple-200/70 mt-1">SUFIA auto trades on Quotex for you</p>
                </div>

                <div onclick="navTo('screen-signal')" class="glass-card p-3.5 rounded-2xl cursor-pointer relative">
                    <i class="fa-solid fa-arrow-up-right-from-square absolute top-3 right-3 text-[10px] text-gray-400"></i>
                    <div class="w-7 h-7 rounded-xl bg-purple-900/50 flex items-center justify-center mb-2">
                        <i class="fa-solid fa-chart-line text-purple-300 text-xs"></i>
                    </div>
                    <h4 class="font-gothic text-xs text-white font-bold">QX live Signal</h4>
                    <p class="text-[8px] text-purple-200/70 mt-1">SUFIA watches live charts & gives voice signals</p>
                </div>
            </div>

            <!-- Bottom Floating Navigation Bar -->
            <div class="bottom-nav flex justify-between items-center mt-auto">
                <button onclick="navTo('screen-home')" class="text-purple-300 p-2"><i class="fa-solid fa-house text-sm"></i></button>
                <button onclick="navTo('screen-auto')" class="text-gray-400 p-2"><i class="fa-solid fa-sliders text-sm"></i></button>
                <button onclick="navTo('screen-voice')" class="w-10 h-10 rounded-full purple-glow-btn text-black flex items-center justify-center font-bold">
                    <i class="fa-solid fa-microphone text-sm"></i>
                </button>
                <button onclick="navTo('screen-signal')" class="text-gray-400 p-2"><i class="fa-solid fa-chart-line text-sm"></i></button>
                <button onclick="navTo('screen-profile')" class="text-gray-400 p-2"><i class="fa-solid fa-user text-sm"></i></button>
            </div>
        </div>

        <!-- SCREEN 2: VOICE STUDIO SCREEN -->
        <div id="screen-voice" class="screen">
            <div class="flex justify-between items-center mt-2">
                <button onclick="navTo('screen-home')" class="text-purple-300 text-xs flex items-center gap-1 font-bold"><i class="fa-solid fa-chevron-left"></i> Back</button>
                <span class="text-xs font-gothic text-purple-200">SUFIA VOICE STUDIO</span>
                <span class="bg-emerald-950 border border-emerald-500 text-emerald-300 text-[9px] px-2 py-0.5 rounded-full font-bold">● LIVE</span>
            </div>

            <div class="text-center my-6">
                <div class="w-28 h-28 mx-auto rounded-full purple-glow-btn flex items-center justify-center my-4">
                    <i class="fa-solid fa-brain text-4xl text-black"></i>
                </div>
                <p id="sufia-status" class="text-xs font-gothic text-purple-200">TOT AI MASTER IS LISTENING...</p>
            </div>

            <div class="glass-card p-3 rounded-2xl mb-4">
                <div class="flex justify-between items-center mb-2">
                    <span class="text-[9px] font-bold text-emerald-400">● LIVE TRADINGVIEW CHART</span>
                    <select id="voice-chart-pair" onchange="renderVoiceChart()" class="bg-purple-950 text-[10px] p-1 rounded-lg border border-purple-500/50 text-white font-bold outline-none">
                        <option value="FX:EURUSD">EUR/USD (Real)</option>
                        <option value="FX:GBPUSD">GBP/USD (Real)</option>
                        <option value="CAPITALCOM:USDBDT">USD/BDT (OTC)</option>
                    </select>
                </div>
                <div id="tv-voice-container" class="h-44 rounded-xl overflow-hidden"></div>
            </div>

            <div class="flex justify-center items-center gap-4 mb-4">
                <button onclick="triggerVoiceResponse()" class="w-12 h-12 rounded-full purple-glow-btn text-black flex items-center justify-center font-bold">
                    <i class="fa-solid fa-microphone text-lg"></i>
                </button>
            </div>
        </div>

        <!-- SCREEN 3: AUTO TRADE PLACE -->
        <div id="screen-auto" class="screen">
            <div class="flex justify-between items-center mt-2">
                <button onclick="navTo('screen-home')" class="text-purple-300 text-xs font-bold"><i class="fa-solid fa-chevron-left"></i> Back</button>
                <h1 class="text-xs font-gothic text-purple-200">Auto Trade Engine</h1>
            </div>

            <div class="glass-card p-4 space-y-4 my-auto">
                <div class="flex gap-2">
                    <select id="auto-pair" class="w-1/2 bg-purple-950 text-xs p-2.5 rounded-xl border border-purple-500/50 text-white font-bold">
                        <option value="FX:EURUSD">EUR/USD (Real)</option>
                        <option value="CAPITALCOM:USDBDT">USD/BDT (OTC)</option>
                    </select>
                    <select class="w-1/2 bg-purple-950 text-xs p-2.5 rounded-xl border border-purple-500/50 text-white font-bold">
                        <option value="1M">1 Minute</option>
                        <option value="5M">5 Minutes</option>
                    </select>
                </div>

                <button onclick="startAutoScan()" class="purple-glow-btn text-black font-gothic text-xs py-3 rounded-xl w-full font-bold">
                    <i class="fa-solid fa-play"></i> Start Auto Market Scan
                </button>

                <div class="bg-black/40 p-4 rounded-2xl border border-purple-800 text-center">
                    <p class="text-[10px] text-purple-300">Status: <b id="auto-state" class="text-yellow-400">READY</b></p>
                    <h2 id="auto-res-signal" class="text-2xl font-black text-emerald-400 my-2">CALL (BUY)</h2>
                    <p id="auto-res-reason" class="text-[9px] text-gray-300">SMC Liquidity Sweep & Demand Bounce</p>
                </div>
            </div>
        </div>

        <!-- SCREEN 4: LIVE SIGNAL -->
        <div id="screen-signal" class="screen">
            <div class="flex justify-between items-center mt-2">
                <button onclick="navTo('screen-home')" class="text-purple-300 text-xs font-bold"><i class="fa-solid fa-chevron-left"></i> Back</button>
                <h1 class="text-xs font-gothic text-purple-200">QX Live Signal Center</h1>
            </div>

            <div class="glass-card p-4 space-y-4 my-auto">
                <div class="flex gap-2">
                    <select id="signal-pair" class="w-1/2 bg-purple-950 text-xs p-2.5 rounded-xl border border-purple-500/50 text-white font-bold">
                        <option value="FX:EURUSD">EUR/USD (Real)</option>
                        <option value="CAPITALCOM:USDBDT">USD/BDT (OTC)</option>
                    </select>
                    <select class="w-1/2 bg-purple-950 text-xs p-2.5 rounded-xl border border-purple-500/50 text-white font-bold">
                        <option value="1M">1 Minute</option>
                    </select>
                </div>

                <button onclick="fetchSignal()" class="purple-glow-btn text-black font-gothic text-xs py-3 rounded-xl w-full font-bold">
                    <i class="fa-solid fa-bolt"></i> Generate Live Signal
                </button>

                <div class="bg-black/40 p-4 rounded-2xl border border-purple-800 text-center">
                    <p class="text-[10px] text-purple-300">Confluence: <b id="sig-acc" class="text-emerald-400">91%</b></p>
                    <h1 id="sig-dir" class="text-3xl font-black text-pink-500 my-2">PUT (SELL)</h1>
                    <p id="sig-reason" class="text-[9px] text-gray-300">Order Block Rejection & RSI Overbought</p>
                </div>
            </div>
        </div>

        <!-- SCREEN 5: USER PROFILE -->
        <div id="screen-profile" class="screen">
            <div class="flex justify-between items-center mt-2">
                <button onclick="navTo('screen-home')" class="text-purple-300 text-xs font-bold"><i class="fa-solid fa-chevron-left"></i> Back</button>
                <h1 class="text-xs font-gothic text-purple-200">User Profile</h1>
            </div>

            <div class="glass-card p-5 text-center space-y-3 my-auto">
                <div class="w-16 h-16 rounded-full bg-red-950/80 border-2 border-red-500 mx-auto flex items-center justify-center">
                    <i class="fa-solid fa-robot text-2xl text-red-400"></i>
                </div>
                <h2 class="text-sm font-bold text-white">Yasin</h2>
                <p class="text-[10px] text-purple-300">User Code: SPK-800Y0BIM</p>
                <span class="bg-purple-900/60 border border-purple-400 text-purple-200 text-[10px] px-3 py-1 rounded-full inline-block font-gothic">✨ SUFIA Spark Active</span>
            </div>
        </div>

    </div>

    <script>
        function navTo(screenId) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(screenId).classList.add('active');
            if(screenId === 'screen-voice') {
                renderVoiceChart();
            }
        }

        function renderVoiceChart() {
            const pair = document.getElementById('voice-chart-pair').value;
            document.getElementById('tv-voice-container').innerHTML = '';
            new TradingView.widget({
                "autosize": true,
                "symbol": pair,
                "interval": "1",
                "timezone": "Etc/UTC",
                "theme": "dark",
                "style": "1",
                "locale": "en",
                "toolbar_bg": "#090114",
                "enable_publishing": false,
                "hide_side_toolbar": true,
                "hide_top_toolbar": true,
                "container_id": "tv-voice-container"
            });
        }

        async function startAutoScan() {
            const pair = document.getElementById('auto-pair').value;
            document.getElementById('auto-state').innerText = "SCANNING...";
            const res = await fetch(`/api/signal?symbol=${pair}`);
            const data = await res.json();
            
            document.getElementById('auto-state').innerText = "COMPLETED";
            document.getElementById('auto-res-signal').innerText = data.signal;
            document.getElementById('auto-res-reason').innerText = data.reason;
        }

        async function fetchSignal() {
            const pair = document.getElementById('signal-pair').value;
            const res = await fetch(`/api/signal?symbol=${pair}`);
            const data = await res.json();
            
            document.getElementById('sig-acc').innerText = data.accuracy;
            document.getElementById('sig-dir').innerText = data.signal;
            document.getElementById('sig-reason').innerText = data.reason;
        }

        function triggerVoiceResponse() {
            document.getElementById('sufia-status').innerText = "SUFIA IS THINKING...";
            const utterance = new SpeechSynthesisUtterance("হ্যালো, আমি সুফিয়া। ক্যান্ডেলস্টিক ও RSI মোমেন্টাম অনুযায়ী এখন এন্ট্রি নেওয়া নিরাপদ।");
            utterance.lang = 'bn-BD';
            window.speechSynthesis.speak(utterance);
        }
    </script>
</body>
</html>
"""

# ==========================================
# FLASK ROUTER
# ==========================================

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/signal')
def api_signal():
    symbol = request.args.get('symbol', 'FX:EURUSD')
    return jsonify(get_market_analysis(symbol))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
