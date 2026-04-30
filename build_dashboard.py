# build_dashboard.py
import json
import os

def build_dashboard():
    json_path = 'gcc_dashboard.json'
    output_path = 'dashboard.html'
    
    if not os.path.exists(json_path):
        print(f"ERROR: {json_path} not found!")
        print("Run 'python etl.py' first to generate the data file.")
        return False
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"Loaded {json_path}")
    print(f"   country_overview: {len(data.get('country_overview', []))} countries")
    print(f"   brand_analysis: {len(data.get('brand_analysis', []))} records")
    print(f"   country_comparison: {len(data.get('country_comparison', []))} countries")
    print(f"   category_analysis: {len(data.get('category_analysis', []))} records")
    
    html = create_dashboard(data)
    
    with open(output_path, 'w', encoding='utf-8', errors='replace') as f:
        f.write(html)
    
    print(f"Dashboard built: {output_path}")
    return True

def create_dashboard(data):
    data_json = json.dumps(data, default=str, ensure_ascii=True)
    
    return '''<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GCC Consumer Pulse — Units Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    
    <!-- Firebase SDK -->
    <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/10.7.1/firebase-database-compat.js"></script>
    
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: '#38bdf8',
                        'primary-foreground': '#0f172a',
                        positive: '#34d399',
                        negative: '#f87171',
                    },
                    fontFamily: {
                        display: ['Fraunces', 'Georgia', 'serif'],
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
                    },
                }
            }
        }
    </script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700&family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        :root {
            --bg: #f8f9fa;
            --surface: #ffffff;
            --surface-alt: #f1f5f9;
            --surface-elevated: #e2e8f0;
            --text: #1a1a2e;
            --text-muted: #64748b;
            --border: #e2e8f0;
            --hover-bg: #f0f9ff;
        }
        .dark {
            --bg: #060b14;
            --surface: #0d1321;
            --surface-alt: #131b2e;
            --surface-elevated: #1a2744;
            --text: #f1f5f9;
            --text-muted: #94a3b8;
            --border: #1e293b;
            --hover-bg: #1e293b;
        }
        
        * { font-family: 'Inter', system-ui, sans-serif; }
        body { background: var(--bg); color: var(--text); min-height: 100vh; -webkit-font-smoothing: antialiased; transition: background 0.3s, color 0.3s; }
        .font-display { font-family: 'Fraunces', Georgia, serif; letter-spacing: -0.02em; }
        .font-mono-tabular { font-family: 'JetBrains Mono', monospace; font-variant-numeric: tabular-nums; }
        
        .idc-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; transition: all 0.2s ease; }
        .idc-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-color: #38bdf8; }
        
        .idc-card-bg { background: var(--bg); border: 1px solid var(--border); border-radius: 12px; transition: all 0.2s ease; }
        .idc-card-bg:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-color: #38bdf8; }
        
        .idc-card-transparent { background: transparent; border: 1px solid var(--border); border-radius: 12px; transition: all 0.2s ease; }
        .idc-card-transparent:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.15); border-color: #38bdf8; }
        
        .brand-inner { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; transition: all 0.2s ease; }
        .brand-inner:hover { border-color: #38bdf8; background: var(--surface-alt); }
        
        .country-btn {
            background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
            transition: all 0.2s ease; cursor: pointer; position: relative; overflow: hidden;
            color: var(--text); flex: 1 1 auto; min-width: 130px; padding: 20px 18px;
        }
        .country-btn:hover { border-color: #38bdf8; box-shadow: 0 8px 25px rgba(0,0,0,0.25); z-index: 10; }
        .country-btn.active { border-color: #38bdf8 !important; background: var(--hover-bg) !important; box-shadow: 0 0 0 2px rgba(56,189,248,0.2); }
        .country-btn.active::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px; background: #38bdf8; }
        
        .filter-group {
            display: inline-flex; align-items: stretch; gap: 0;
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
            border: 1px solid rgba(255,255,255,0.10); border-radius: 12px;
            padding: 4px; box-shadow: 0 1px 0 rgba(255,255,255,0.04) inset, 0 4px 16px -8px rgba(0,0,0,0.5);
            backdrop-filter: blur(8px);
        }
        .filter-cell { display: inline-flex; align-items: center; gap: 8px; padding: 4px 10px; border-radius: 9px; transition: background 0.2s; }
        .filter-cell + .filter-cell { border-left: 1px solid rgba(255,255,255,0.08); }
        .filter-cell:hover { background: rgba(56,189,248,0.08); }
        .filter-label {
            font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em;
            color: #64748b; white-space: nowrap;
        }
        .filter-select {
            background: transparent; color: #f1f5f9; border: none;
            border-radius: 6px; padding: 6px 24px 6px 4px; font-size: 13px; font-weight: 600;
            cursor: pointer; outline: none; appearance: none; -webkit-appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' fill='%2338bdf8' viewBox='0 0 16 16'%3E%3Cpath d='M8 11L3 6h10z'/%3E%3C/svg%3E");
            background-repeat: no-repeat; background-position: right 4px center; transition: color 0.2s;
            min-width: 90px;
        }
        .filter-select:hover { color: #38bdf8; }
        .filter-select:focus { color: #38bdf8; }
        .filter-select option { background: #0d1321; color: #f1f5f9; font-weight: 500; }
        .light .filter-group { background: linear-gradient(180deg, rgba(15,23,42,0.04), rgba(15,23,42,0.01)); border-color: rgba(15,23,42,0.10); }
        .light .filter-cell + .filter-cell { border-left-color: rgba(15,23,42,0.08); }
        .light .filter-select { color: #1a1a2e; }
        .light .filter-label { color: #64748b; }
        .light .filter-select option { background: #ffffff; color: #1a1a2e; }
        
        .accordion-content { max-height: 0; overflow: hidden; transition: max-height 0.3s ease; }
        .accordion-content.open { max-height: 4000px; }
        .progress-bar { transition: width 0.7s cubic-bezier(0.16, 1, 0.3, 1); }
        
        .idc-table th { font-size: 10px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); background: var(--surface-alt); border-bottom: 2px solid var(--border); }
        .idc-table td { border-bottom: 1px solid var(--border); color: var(--text); }
        .idc-table tr:hover td { background: var(--hover-bg); }
        
        .idc-header-bg { background: rgba(6,11,20,0.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px); }
        
        .bg-positive-soft { background: rgba(52,211,153,0.1); }
        .bg-negative-soft { background: rgba(248,113,113,0.1); }
        
        .brand-note-input {
            width: 100%; background: var(--surface-alt); border: 1px solid var(--border); border-radius: 6px;
            padding: 6px 10px; font-size: 12px; color: var(--text); resize: vertical; min-height: 28px;
            margin-top: 8px; font-family: 'Inter', sans-serif; font-weight: 600; white-space: pre-wrap;
        }
        .light .brand-note-input { color: #0066a1; }
        .dark .brand-note-input { color: #ffffff; }
        .brand-note-input:focus { outline: none; border-color: #38bdf8; }
        .brand-note-input::placeholder { font-weight: 400; color: var(--text-muted); }
        .brand-note-input.orange { border-left: 3px solid #f59e0b; }
        .brand-note-input.purple { border-left: 3px solid #a855f7; }
        .brand-note-input.green { border-left: 3px solid #34d399; }
        .brand-note-input.blue { border-left: 3px solid #3b82f6; }

        .brand-note-display {
            font-size: 12px; color: var(--text-muted); margin-top: 8px; padding: 6px 10px;
            background: var(--surface-alt); border-radius: 6px; cursor: pointer; line-height: 1.4; font-weight: 600;
            white-space: pre-wrap; border-left: 3px solid transparent;
        }
        .light .brand-note-display { color: #0066a1; }
        .dark .brand-note-display { color: #ffffff; }
        .brand-note-display:hover { background: var(--hover-bg); }
        .brand-note-display.orange { border-left-color: #f59e0b; }
        .brand-note-display.purple { border-left-color: #a855f7; }
        .brand-note-display.green { border-left-color: #34d399; }
        .brand-note-display.blue { border-left-color: #3b82f6; }

        .note-edit-btn { font-size: 11px; color: #38bdf8; cursor: pointer; margin-left: 8px; opacity: 0; transition: opacity 0.2s; font-weight: 400; }
        .brand-note-display:hover .note-edit-btn { opacity: 1; }
        
        .note-color-picker { display: flex; gap: 6px; margin-top: 6px; align-items: center; }
        .note-color-dot { width: 16px; height: 16px; border-radius: 50%; cursor: pointer; border: 2px solid transparent; transition: all 0.15s; }
        .note-color-dot:hover { transform: scale(1.2); }
        .note-color-dot.selected { border-color: #fff; box-shadow: 0 0 0 2px currentColor; }
        .note-color-dot.orange { background: #f59e0b; color: #f59e0b; }
        .note-color-dot.purple { background: #a855f7; color: #a855f7; }
        .note-color-dot.green { background: #34d399; color: #34d399; }
        .note-color-dot.blue { background: #3b82f6; color: #3b82f6; }
        
        .refresh-btn {
            background: rgba(255,255,255,0.08); color: #94a3b8; border: 1px solid rgba(255,255,255,0.12);
            border-radius: 8px; padding: 6px 14px; font-size: 12px; font-weight: 500; cursor: pointer;
            transition: all 0.2s; display: flex; align-items: center; gap: 6px;
        }
        .refresh-btn:hover { background: rgba(255,255,255,0.14); border-color: rgba(56,189,248,0.4); color: #fff; }
        .refresh-btn:active { transform: scale(0.97); }
        .refresh-btn.refreshing { opacity: 0.6; pointer-events: none; }
        
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .spin { animation: spin 1s linear infinite; }
        
        .brands-scroll { max-height: 500px; overflow-y: auto; }
        
        .sync-status {
            position: fixed;
            bottom: 16px;
            right: 16px;
            padding: 8px 14px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 500;
            z-index: 100;
            transition: opacity 0.3s;
        }
        .sync-status.synced { background: #064e3b; color: #34d399; }
        .sync-status.syncing { background: #1e293b; color: #fbbf24; }
        .sync-status.error { background: #7f1d1d; color: #f87171; }
        
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
    </style>
</head>
<body>

    <!-- Sync Status Indicator -->
    <div class="sync-status synced" id="syncStatus">✓ Notes synced</div>

    <header class="idc-header-bg sticky top-0 z-50 shadow-lg border-b border-white/5">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-4">
            <div class="flex items-center justify-between">
                <div class="flex items-center gap-4">
                    <div class="h-9 w-9 rounded-lg border border-primary/30 bg-primary/10 flex items-center justify-center">
                        <svg class="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                        </svg>
                    </div>
                    <div>
                        <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-primary">GCC Smartphone · Units Intelligence</div>
                        <h1 class="font-display text-xl font-semibold text-white tracking-tight">Country Units Dashboard</h1>
                    </div>
                </div>
                <div class="flex items-center gap-3">
                    <div class="filter-group">
                        <div class="filter-cell">
                            <span class="filter-label">Category</span>
                            <select id="categoryFilter" onchange="filterByCategory(this.value)" class="filter-select">
                                <option value="Total">Total</option>
                                <option value="Smartphone">Smartphone</option>
                                <option value="Feature Phone">Feature Phone</option>
                            </select>
                        </div>
                        <div class="filter-cell">
                            <span class="filter-label">Quarter</span>
                            <select id="quarterFilter" onchange="filterByQuarter(this.value)" class="filter-select" style="min-width:110px;"></select>
                        </div>
                    </div>
                    <button onclick="toggleDarkMode()" class="p-2 rounded-lg hover:bg-white/5 transition-colors" style="color:#94a3b8;" id="darkToggle" title="Toggle theme">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 space-y-5">

        <section>
            <div class="mb-3 flex items-center justify-between">
                <h2 class="text-xs font-semibold uppercase tracking-wider" style="color:var(--text-muted)">Select a Country</h2>
                <span class="text-[10px]" style="color:var(--text-muted)">QoQ = vs previous quarter</span>
            </div>
            <div class="flex flex-nowrap gap-2 overflow-x-auto pb-1" id="countrySelector"></div>
        </section>

        <section class="space-y-5" id="countryDetail">
            <div class="flex items-end gap-3 border-b pb-4" style="border-color:var(--border)">
                <span class="text-4xl leading-none" id="countryFlag"></span>
                <div>
                    <div class="text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">Country Deep-Dive · Units</div>
                    <h2 class="font-display text-3xl font-semibold tracking-tight" id="countryName"></h2>
                </div>
            </div>

            <div class="grid gap-4 lg:grid-cols-3" style="align-items:stretch;">
                <div class="lg:col-span-1 flex flex-col gap-3" id="kpiColumn">
                    <div class="idc-card-transparent p-4 relative overflow-hidden flex-1 flex flex-col justify-center">
                        <div class="absolute top-0 left-0 w-1 h-full bg-primary"></div>
                        <div class="flex items-center gap-2 mb-1"><span class="h-2 w-2 rounded-full bg-primary flex-shrink-0"></span><div class="text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">Total Units · <span id="selectedQuarterLabel">—</span></div></div>
                        <div class="mt-1"><span class="font-display font-mono-tabular text-3xl font-semibold tracking-tight" id="totalUnitsK">—</span></div>
                        <div class="mt-0.5 text-xs" style="color:var(--text-muted)" id="totalUnitsExact"></div>
                    </div>
                    <div class="idc-card-transparent p-4 relative overflow-hidden flex-1 flex flex-col justify-center">
                        <div class="absolute top-0 left-0 w-1 h-full bg-positive"></div>
                        <div class="flex items-center gap-2 mb-1"><span class="h-2 w-2 rounded-full bg-positive flex-shrink-0"></span><div class="text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">QoQ Growth</div></div>
                        <div class="mt-2 font-mono-tabular text-3xl font-bold tracking-tight" id="qoqValue">—</div>
                        <div class="mt-0.5 text-xs" style="color:var(--text-muted)">vs Previous Quarter</div>
                    </div>
                    <div class="idc-card-transparent p-4 relative overflow-hidden flex-1 flex flex-col justify-center">
                        <div class="absolute top-0 left-0 w-1 h-full bg-primary/60"></div>
                        <div class="flex items-center gap-2 mb-1"><span class="h-2 w-2 rounded-full flex-shrink-0" style="background:rgba(56,189,248,0.6);"></span><div class="text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">YoY Growth</div></div>
                        <div class="mt-2 font-mono-tabular text-3xl font-bold tracking-tight" id="yoyValue">—</div>
                        <div class="mt-0.5 text-xs" style="color:var(--text-muted)">vs Same Quarter Last Year</div>
                    </div>
                </div>
                <div class="lg:col-span-2 idc-card-transparent p-5 flex flex-col" id="chartCard">
                    <div class="mb-3"><div class="text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">Quarterly Units</div><div class="font-display text-lg font-medium" id="chartTitle">Volume Path</div></div>
                    <div class="flex-1" style="min-height:0;"><canvas id="trendChart"></canvas></div>
                </div>
            </div>

            <div class="grid gap-4 lg:grid-cols-3">
                <div class="idc-card-bg p-5 flex flex-col">
                    <header class="mb-4 flex-shrink-0">
                        <div class="flex items-center gap-2 mb-2">
                            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-positive-soft text-positive">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/></svg>
                            </div>
                            <div><h3 class="font-display text-base font-semibold">Top Performers</h3><p class="text-xs" style="color:var(--text-muted)">All brands by QoQ growth</p></div>
                        </div>
                    </header>
                    <div class="space-y-2 brands-scroll flex-1" id="gainersList"></div>
                </div>
                <div class="idc-card-bg p-5 flex flex-col">
                    <header class="mb-4 flex-shrink-0">
                        <div class="flex items-center gap-2 mb-2">
                            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-negative-soft text-negative">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6"/></svg>
                            </div>
                            <div><h3 class="font-display text-base font-semibold">Underperforming</h3><p class="text-xs" style="color:var(--text-muted)">All brands by QoQ decline</p></div>
                        </div>
                    </header>
                    <div class="space-y-2 brands-scroll flex-1" id="declinersList"></div>
                </div>
                <div class="idc-card-bg p-5 flex flex-col">
                    <header class="mb-4 flex-shrink-0">
                        <div class="flex items-center gap-2 mb-2">
                            <div class="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
                            </div>
                            <div><h3 class="font-display text-base font-semibold">Market Movers</h3><p class="text-xs" style="color:var(--text-muted)">Largest unit swings</p></div>
                        </div>
                    </header>
                    <div class="space-y-2 brands-scroll flex-1" id="moversList"></div>
                </div>
            </div>

            <div class="idc-card">
                <div class="p-5 border-b flex items-center justify-between" style="border-color:var(--border)">
                    <h3 class="font-display text-lg font-semibold">Brand Market Share — <span class="text-primary" id="tableCountryLabel">All Brands</span></h3>
                    <span class="text-xs" style="color:var(--text-muted)" id="tableQuarterLabel">—</span>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-sm idc-table">
                        <thead><tr><th class="text-left py-3 px-4">Brand</th><th class="text-right py-3 px-4">Units</th><th class="text-right py-3 px-4">Share</th><th class="text-right py-3 px-4">QoQ</th><th class="text-right py-3 px-4">YoY</th></tr></thead>
                        <tbody id="brandTableBody"></tbody>
                    </table>
                </div>
            </div>

            <div class="idc-card p-5">
                <header class="mb-4"><h3 class="font-display text-lg font-semibold">GCC Cross-Country Comparison</h3><p class="text-xs" style="color:var(--text-muted)">Sorted by market size</p></header>
                <div class="space-y-2">
                    <div class="grid grid-cols-12 gap-4 px-3 mb-1 text-[10px] uppercase tracking-wider font-semibold" style="color:var(--text-muted)">
                        <div class="col-span-3">Country</div><div class="col-span-2 text-right">Units</div><div class="col-span-3">QoQ</div><div class="col-span-3">YoY</div><div class="col-span-1"></div>
                    </div>
                    <div id="comparisonRows"></div>
                </div>
            </div>

            <div class="idc-card">
                <div class="p-5 flex items-center justify-between cursor-pointer select-none" onclick="toggleAccordion()">
                    <div><h3 class="font-display text-lg font-semibold">GCC Brand Rankings</h3><p class="text-xs mt-1" style="color:var(--text-muted)">Click to expand</p></div>
                    <svg id="accordionChevron" class="w-5 h-5 transition-transform duration-200" style="color:var(--text-muted)" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </div>
                <div class="accordion-content" id="rankingsAccordion"><div class="px-5 pb-5 overflow-x-auto">
                    <table class="w-full text-sm idc-table">
                        <thead><tr><th class="text-left py-3 px-4 w-12">#</th><th class="text-left py-3 px-4">Brand</th><th class="text-right py-3 px-4">Total Units</th><th class="text-right py-3 px-4">Countries</th><th class="text-right py-3 px-4">Avg/Quarter</th></tr></thead>
                        <tbody id="rankingsTableBody"></tbody>
                    </table>
                </div></div>
            </div>
        </section>

        <footer class="border-t pt-4 text-xs" style="border-color:var(--border);color:var(--text-muted)"></footer>
    </main>

    <script>

        var FIREBASE_DATABASE_URL = "https://gcc-dashboard-6cd52-default-rtdb.firebaseio.com/";

        var D = ''' + data_json + ''';

        var isDark = true;
        var selectedQuarter = null;
        var selectedCategory = 'Total';
        var selectedCountry = null;
        var trendChart = null;
        var allQuarters = [];
        var brandNotes = {};
        var noteColors = {};
        var notesLoaded = false;
        var db = null;
        var notesRef = null;

        // ============================================================
        // FIREBASE INIT
        // ============================================================
        function initFirebase() {
            try {
                if (FIREBASE_DATABASE_URL.indexOf('YOUR-PROJECT-ID') !== -1) {
                    console.warn('Firebase not configured. Notes will be saved locally only.');
                    loadLocalNotes();
                    return;
                }
                firebase.initializeApp({ databaseURL: FIREBASE_DATABASE_URL });
                db = firebase.database();
                notesRef = db.ref('gcc_dashboard_notes');
                
                // Listen for real-time changes
                notesRef.on('value', function(snapshot) {
                    var data = snapshot.val() || {};
                    brandNotes = data.notes || {};
                    noteColors = data.colors || {};
                    notesLoaded = true;
                    updateSyncStatus('synced', '✓ Notes synced');
                    // Re-render brand panels if country is selected
                    if (selectedCountry) {
                        var ba = findBa();
                        if (ba && ba.length) {
                            renderBrandPanels(ba);
                            renderMovers(ba);
                        }
                    }
                });
                
                // Also try loading once
                notesRef.once('value').then(function(snapshot) {
                    var data = snapshot.val() || {};
                    brandNotes = data.notes || {};
                    noteColors = data.colors || {};
                    notesLoaded = true;
                }).catch(function(e) {
                    console.error('Firebase load error:', e);
                    loadLocalNotes();
                });
                
            } catch(e) {
                console.error('Firebase init error:', e);
                loadLocalNotes();
            }
        }
        
        function loadLocalNotes() {
            try {
                var s = localStorage.getItem('gcc_brand_notes_local');
                if (s) { var d = JSON.parse(s); brandNotes = d.notes || {}; noteColors = d.colors || {}; }
            } catch(e) { brandNotes = {}; noteColors = {}; }
            notesLoaded = true;
            updateSyncStatus('syncing', '⚠ Local storage only');
        }
        
        function saveLocalNotes() {
            try {
                localStorage.setItem('gcc_brand_notes_local', JSON.stringify({ notes: brandNotes, colors: noteColors }));
            } catch(e) {}
        }
        
        function updateSyncStatus(status, message) {
            var el = document.getElementById('syncStatus');
            if (el) {
                el.className = 'sync-status ' + status;
                el.textContent = message;
                setTimeout(function() { el.style.opacity = '0.5'; }, 3000);
                el.style.opacity = '1';
            }
        }

        // ============================================================
        // NOTES FUNCTIONS
        // ============================================================
        function getNoteKey(c, b, q) { return c + '|||' + b + '|||' + q; }
        function getNote(c, b, q) { return brandNotes[getNoteKey(c, b, q)] || ''; }
        function getNoteColor(c, b, q) { return noteColors[getNoteKey(c, b, q)] || ''; }
        function setNote(c, b, q, t) {
            var k = getNoteKey(c, b, q);
            if (t.trim()) brandNotes[k] = t; else delete brandNotes[k];
            saveNotes();
        }
        function setNoteColor(c, b, q, col) {
            var k = getNoteKey(c, b, q);
            if (col) noteColors[k] = col; else delete noteColors[k];
            saveNotes();
        }
        function saveNotes() {
            if (notesRef) {
                updateSyncStatus('syncing', '↻ Syncing...');
                notesRef.set({ notes: brandNotes, colors: noteColors }).then(function() {
                    updateSyncStatus('synced', '✓ Notes synced');
                }).catch(function() {
                    saveLocalNotes();
                    updateSyncStatus('error', '✗ Sync failed');
                });
            } else {
                saveLocalNotes();
            }
        }

        function editNote(nid, c, b) {
            var d = document.getElementById('display-' + nid);
            var ta = document.getElementById(nid);
            var picker = document.getElementById('picker-' + nid);
            if (d) d.style.display = 'none';
            if (ta) { ta.style.display = 'block'; ta.focus(); }
            if (picker) picker.style.display = 'flex';
        }
        function saveNoteText(nid, c, b) {
            var ta = document.getElementById(nid); if (!ta) return; var t = ta.value; setNote(c, b, selectedQuarter, t);
            var d = document.getElementById('display-' + nid); var picker = document.getElementById('picker-' + nid);
            var nc = getNoteColor(c, b, selectedQuarter) || '';
            if (t.trim()) {
                if (!d) { d = document.createElement('div'); d.id = 'display-' + nid; d.className = 'brand-note-display ' + nc; d.setAttribute('onclick', 'editNote(\\'' + nid + '\\',\\'' + c.replace(/'/g, "\\\\'") + '\\',\\'' + b.replace(/'/g, "\\\\'") + '\\')'); ta.parentNode.insertBefore(d, ta.nextSibling); }
                d.innerHTML = t.replace(/\\n/g, '<br>') + '<span class="note-edit-btn">edit</span>'; d.style.display = 'block'; d.className = 'brand-note-display ' + nc;
                ta.style.display = 'none'; ta.className = 'brand-note-input ' + nc;
                if (picker) picker.style.display = 'none';
            } else { if (d) d.style.display = 'none'; ta.style.display = 'block'; ta.value = ''; ta.className = 'brand-note-input ' + nc; if (picker) picker.style.display = 'flex'; }
        }
        function applyColor(nid, c, b, col) {
            setNoteColor(c, b, selectedQuarter, col);
            var ta = document.getElementById(nid); if (ta) { ta.className = 'brand-note-input ' + col; ta.style.display = 'block'; }
            var d = document.getElementById('display-' + nid); if (d) { d.className = 'brand-note-display ' + col; d.style.display = 'none'; }
            var dots = document.querySelectorAll('#picker-' + nid + ' .note-color-dot');
            for (var i = 0; i < dots.length; i++) { dots[i].classList.remove('selected'); if (dots[i].classList.contains(col)) dots[i].classList.add('selected'); }
            if (ta) ta.focus();
        }

        // ============================================================
        // UTILITIES
        // ============================================================
        function detectQuarters() { var qs = {}; var co = D.country_overview || []; for (var i = 0; i < co.length; i++) { var keys = Object.keys(co[i]); for (var j = 0; j < keys.length; j++) { if (/^\\d{4}Q\\d$/.test(keys[j])) qs[keys[j]] = true; } } allQuarters = Object.keys(qs).sort(); }
        function fmt(n) { if (n == null || isNaN(n)) return '0'; return Math.round(n).toLocaleString(); }
        function getFlag(c) { var f = { 'Saudi Arabia': '\\uD83C\\uDDF8\\uD83C\\uDDE6', 'United Arab Emirates': '\\uD83C\\uDDE6\\uD83C\\uDDEA', 'Qatar': '\\uD83C\\uDDF6\\uD83C\\uDDE6', 'Kuwait': '\\uD83C\\uDDF0\\uD83C\\uDDFC', 'Oman': '\\uD83C\\uDDF4\\uD83C\\uDDF2', 'Bahrain': '\\uD83C\\uDDE7\\uD83C\\uDDED', 'Iraq': '\\uD83C\\uDDEE\\uD83C\\uDDF6' }; return f[c] || ''; }
        function getCountryCode(c) { var codes = { 'Saudi Arabia': 'SA', 'United Arab Emirates': 'AE', 'Qatar': 'QA', 'Kuwait': 'KW', 'Oman': 'OM', 'Bahrain': 'BH', 'Iraq': 'IQ' }; return codes[c] || c.substring(0, 2).toUpperCase(); }
        function getPrevQuarter(q) { var i = allQuarters.indexOf(q); return i > 0 ? allQuarters[i - 1] : null; }
        function getPrevYearQuarter(q) { var i = allQuarters.indexOf(q); return i >= 4 ? allQuarters[i - 4] : null; }
        function getCategoryUnits(co, quarter, cat) { if (!co || !quarter) return 0; if (cat === 'Total') return co[quarter] || 0; var ca = (D.category_analysis || []).filter(function (x) { return x.Country === selectedCountry && x['Product Category'] === cat; }); return ca.length ? (ca[0][quarter] || 0) : 0; }
        function getCategoryUnitsForCountry(co, quarter, cat, country) { if (!co || !quarter) return 0; if (cat === 'Total') return co[quarter] || 0; var ca = (D.category_analysis || []).filter(function (x) { return x.Country === country && x['Product Category'] === cat; }); return ca.length ? (ca[0][quarter] || 0) : 0; }
        function posColor(v) { return (v || 0) >= 0 ? '#34d399' : '#f87171'; }
        function posSign(v) { return (v || 0) > 0 ? '+' : ''; }

        function toggleDarkMode() {
            isDark = !isDark; document.documentElement.classList.toggle('dark', isDark);
            var btn = document.getElementById('darkToggle');
            btn.innerHTML = isDark ? '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/></svg>' : '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/></svg>';
            if (selectedCountry && selectedQuarter) refreshAll();
        }
        function renderQuarterDropdown() { var ct = document.getElementById('quarterFilter'); if (!ct) return; ct.innerHTML = allQuarters.map(function (q) { var lb = q.replace(/(\\d{4})Q(\\d)/, 'Q$2 $1'); return '<option value="' + q + '"' + (q === selectedQuarter ? ' selected' : '') + '>' + lb + '</option>'; }).join(''); }
        function filterByQuarter(q) { selectedQuarter = q; refreshAll(); renderCountrySelector(D.country_comparison || []); renderComparison(); }
        function filterByCategory(cat) { selectedCategory = cat; refreshAll(); renderCountrySelector(D.country_comparison || []); renderComparison(); }
        function refreshAll() { if (!selectedCountry || !selectedQuarter) return; var co = findCo(); var ba = findBa(); document.getElementById('selectedQuarterLabel').textContent = selectedQuarter.replace(/(\\d{4})Q(\\d)/, 'Q$2 $1'); document.getElementById('tableQuarterLabel').textContent = selectedQuarter.replace(/(\\d{4})Q(\\d)/, 'Q$2 $1'); renderKPIs(co); renderChart(co); renderBrandPanels(ba); renderMovers(ba); renderBrandTable(ba); }
        function findCo() { return (D.country_overview || []).find(function (x) { return x.Country === selectedCountry; }); }
        function findBa() { return (D.brand_analysis || []).filter(function (x) { return x.Country === selectedCountry; }); }

        async function refreshData() {
            var btn = document.getElementById('refreshBtn'); btn.classList.add('refreshing'); btn.innerHTML = '<svg class="w-4 h-4 spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Refreshing...';
            try { var resp = await fetch('gcc_dashboard.json?t=' + Date.now()); if (resp.ok) { D = await resp.json(); detectQuarters(); selectedQuarter = allQuarters[allQuarters.length - 1]; renderQuarterDropdown(); var cs = D.country_comparison || []; if (cs.length) { selectedCountry = cs[0].Country; renderCountrySelector(cs); selectCountry(selectedCountry); } } } catch(e) { console.error('Refresh failed:', e); }
            btn.classList.remove('refreshing'); btn.innerHTML = '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Refresh';
        }

        function init() {
            initFirebase();
            detectQuarters();
            if (!allQuarters.length) return;
            selectedQuarter = allQuarters[allQuarters.length - 1];
            renderQuarterDropdown();
            var cs = D.country_comparison || [];
            if (!cs.length) return;
            selectedCountry = cs[0].Country;
            renderCountrySelector(cs);
            selectCountry(selectedCountry);
        }

        function renderCountrySelector(cs) {
            if (!cs || !cs.length) return;
            var h = '';
            for (var i = 0; i < cs.length; i++) {
                var c = cs[i], a = c.Country === selectedCountry;
                var ov = findOvByCountry(c.Country);
                var q1 = ov ? getCategoryUnitsForCountry(ov, selectedQuarter, selectedCategory, c.Country) : 0;
                var qoq = computeQoqForCountry(ov, c.Country);
                h += '<button onclick="selectCountry(\\'' + c.Country.replace(/'/g, "\\\\'") + '\\')" class="country-btn flex flex-col justify-between gap-1 text-left ' + (a ? 'active' : '') + '">' +
                    '<div class="flex items-start justify-between"><span class="text-xs font-bold uppercase tracking-wider" style="color:var(--text-muted)">' + getCountryCode(c.Country) + '</span><span class="font-mono-tabular text-xs font-bold" style="color:' + posColor(qoq) + '">' + (qoq != null ? posSign(qoq) + qoq.toFixed(1) + '%' : '—') + '</span></div>' +
                    '<div class="text-sm font-semibold" style="color:var(--text)">' + c.Country + '</div>' +
                    '<div class="font-mono-tabular text-xs" style="color:var(--text-muted)">' + fmt(q1) + ' units</div></button>';
            }
            document.getElementById('countrySelector').innerHTML = h;
        }
        function findOvByCountry(cn) { return (D.country_overview || []).find(function (x) { return x.Country === cn; }); }
        function computeQoqForCountry(ov, country) { if (!ov || !selectedQuarter) return null; var curr = getCategoryUnitsForCountry(ov, selectedQuarter, selectedCategory, country); var pq = getPrevQuarter(selectedQuarter); var prev = pq ? getCategoryUnitsForCountry(ov, pq, selectedCategory, country) : 0; return prev ? ((curr - prev) / prev) * 100 : null; }

        function selectCountry(country) {
            selectedCountry = country;
            var btns = document.querySelectorAll('.country-btn'); for (var i = 0; i < btns.length; i++) { btns[i].classList.toggle('active', btns[i].textContent.indexOf(country) !== -1); }
            document.getElementById('countryFlag').textContent = getFlag(country); document.getElementById('countryName').textContent = country;
            document.getElementById('chartTitle').textContent = country + ' Volume Path'; document.getElementById('tableCountryLabel').textContent = country;
            refreshAll(); renderComparison(); renderRankings();
        }

        function renderKPIs(co) {
            if (!co || !selectedQuarter) return;
            var units = getCategoryUnits(co, selectedQuarter, selectedCategory);
            var pq = getPrevQuarter(selectedQuarter); var pyq = getPrevYearQuarter(selectedQuarter);
            var pu = pq ? getCategoryUnits(co, pq, selectedCategory) : 0; var pyu = pyq ? getCategoryUnits(co, pyq, selectedCategory) : 0;
            var qoq = pu ? ((units - pu) / pu) * 100 : 0; var yoy = pyu ? ((units - pyu) / pyu) * 100 : 0;
            document.getElementById('totalUnitsK').textContent = fmt(units); document.getElementById('totalUnitsExact').textContent = 'handsets';
            var qe = document.getElementById('qoqValue'); qe.textContent = (qoq >= 0 ? '+' : '') + qoq.toFixed(1) + '%'; qe.style.color = posColor(qoq);
            var ye = document.getElementById('yoyValue'); ye.textContent = (yoy >= 0 ? '+' : '') + yoy.toFixed(1) + '%'; ye.style.color = posColor(yoy);
        }

        function renderChart(co) {
            var cv = document.getElementById('trendChart'); if (!cv || !co || !selectedQuarter) return; var ctx = cv.getContext('2d'); if (trendChart) { trendChart.destroy(); trendChart = null; }
            var lbs = allQuarters.map(function (q) { return q.replace('20', "'"); }); var vls = allQuarters.map(function (q) { return getCategoryUnits(co, q, selectedCategory); });
            var gc = isDark ? 'rgba(148,163,184,0.08)' : '#f1f5f9'; var tc = isDark ? '#94a3b8' : '#64748b';
            var gd = ctx.createLinearGradient(0, 0, 0, 400); gd.addColorStop(0, 'rgba(56,189,248,0.2)'); gd.addColorStop(1, 'rgba(56,189,248,0)');
            trendChart = new Chart(ctx, {
                type: 'line', data: { labels: lbs, datasets: [{ data: vls, borderColor: '#38bdf8', backgroundColor: gd, fill: true, tension: 0.4, borderWidth: 2.5, pointRadius: 2, pointHoverRadius: 6, pointBackgroundColor: '#38bdf8', pointBorderColor: isDark ? '#0d1321' : '#fff', pointBorderWidth: 2, pointHoverBackgroundColor: '#ffffff', pointHoverBorderColor: '#38bdf8', pointHoverBorderWidth: 3 }] },
                options: {
                    responsive: true, maintainAspectRatio: false, interaction: { mode: 'index', intersect: false },
                    plugins: { legend: { display: false }, tooltip: { enabled: true, backgroundColor: isDark ? 'rgba(15,23,42,0.95)' : 'rgba(255,255,255,0.95)', titleColor: tc, bodyColor: isDark ? '#f1f5f9' : '#1a1a2e', borderColor: '#38bdf8', borderWidth: 1, cornerRadius: 12, padding: 14, displayColors: false, titleFont: { family: 'Inter', size: 12, weight: '600' }, bodyFont: { family: 'JetBrains Mono', size: 13, weight: '600' }, titleMarginBottom: 6, callbacks: { title: function(ctx) { return ctx[0].label; }, label: function(ctx) { return ctx.parsed.y.toLocaleString() + ' units'; } }, animation: { duration: 200, easing: 'easeOutCubic' } } },
                    scales: { x: { grid: { display: false }, ticks: { color: tc, font: { size: 11 } }, border: { display: false } }, y: { grid: { color: gc }, ticks: { color: tc, font: { size: 11 }, callback: function (v) { return (v / 1000).toFixed(0) + 'K'; }, padding: 8 }, border: { display: false }, beginAtZero: false, grace: '5%' } }
                }
            });
        }

        function brandQoq(b) {
            var pq = getPrevQuarter(selectedQuarter); if (!pq) return null;
            var c = b['Units_' + selectedQuarter] || 0, p = b['Units_' + pq] || 0;
            return p ? ((c - p) / p) * 100 : null;
        }
        function brandYoy(b) {
            var pyq = getPrevYearQuarter(selectedQuarter); if (!pyq) return null;
            var c = b['Units_' + selectedQuarter] || 0, p = b['Units_' + pyq] || 0;
            return p ? ((c - p) / p) * 100 : null;
        }
        function renderBrandPanels(ba) {
            var gc = document.getElementById('gainersList'), dc = document.getElementById('declinersList');
            if (!ba || !ba.length) { gc.innerHTML = dc.innerHTML = '<div class="text-xs text-center py-6" style="color:var(--text-muted)">No data</div>'; return; }
            var enriched = ba.map(function (b) { return Object.assign({}, b, { _qoq: brandQoq(b), _yoy: brandYoy(b) }); });
            var withQoq = enriched.filter(function (b) { return b._qoq != null; });
            var gs = withQoq.filter(function (b) { return b._qoq > 0; }).sort(function (a, b) { return b._qoq - a._qoq; });
            var ds = withQoq.filter(function (b) { return b._qoq <= 0; }).sort(function (a, b) { return a._qoq - b._qoq; });
            var gM = Math.max(1, gs.reduce(function (m, b) { return Math.max(m, Math.abs(b._qoq)); }, 0));
            var dM = Math.max(1, ds.reduce(function (m, b) { return Math.max(m, Math.abs(b._qoq)); }, 0));
            gc.innerHTML = gs.length ? gs.map(function (b) { return brandRow(b, true, gM); }).join('') : '<div class="text-xs text-center py-4" style="color:var(--text-muted)">No positive QoQ brands.</div>';
            dc.innerHTML = ds.length ? ds.map(function (b) { return brandRow(b, false, dM); }).join('') : '<div class="text-xs text-center py-4" style="color:var(--text-muted)">No declining brands.</div>';
        }
        function brandRow(b, pos, max) {
            var qoq = b._qoq != null ? b._qoq : 0, yoy = b._yoy != null ? b._yoy : 0, pct = Math.min(100, (Math.abs(qoq) / max) * 100);
            var uk = 'Units_' + selectedQuarter, pq = getPrevQuarter(selectedQuarter), u1 = b[uk] || 0, u4 = pq ? (b['Units_' + pq] || 0) : 0;
            var bc = pos ? '#34d399' : '#f87171';
            var nid = 'note-' + selectedCountry.replace(/[^a-zA-Z0-9]/g, '_') + '-' + b['Brand'].replace(/[^a-zA-Z0-9]/g, '_') + '-' + selectedQuarter;
            var en = getNote(selectedCountry, b['Brand'], selectedQuarter);
            var nc = getNoteColor(selectedCountry, b['Brand'], selectedQuarter) || '';
            var ce = selectedCountry.replace(/'/g, "\\'"), be = b['Brand'].replace(/'/g, "\\'");
            var nh = '';
            if (en) {
                nh = '<div class="brand-note-display ' + nc + '" onclick="editNote(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\')" id="display-' + nid + '">' + en.replace(/\\n/g, '<br>') + '<span class="note-edit-btn">edit</span></div>' +
                    '<textarea class="brand-note-input ' + nc + '" id="' + nid + '" style="display:none;" onblur="saveNoteText(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\')" placeholder="Add reason...">' + en + '</textarea>';
            } else {
                nh = '<textarea class="brand-note-input ' + nc + '" id="' + nid + '" onblur="saveNoteText(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\')" placeholder="Add reason for performance..."></textarea>';
            }
            nh += '<div class="note-color-picker" id="picker-' + nid + '" style="display:' + (en ? 'none' : 'flex') + ';">' +
                '<span class="note-color-dot orange' + (nc === 'orange' ? ' selected' : '') + '" onclick="applyColor(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\',\\'orange\\')" title="Orange"></span>' +
                '<span class="note-color-dot purple' + (nc === 'purple' ? ' selected' : '') + '" onclick="applyColor(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\',\\'purple\\')" title="Purple"></span>' +
                '<span class="note-color-dot green' + (nc === 'green' ? ' selected' : '') + '" onclick="applyColor(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\',\\'green\\')" title="Green"></span>' +
                '<span class="note-color-dot blue' + (nc === 'blue' ? ' selected' : '') + '" onclick="applyColor(\\'' + nid + '\\',\\'' + ce + '\\',\\'' + be + '\\',\\'blue\\')" title="Blue"></span>' +
                '</div>';
            return '<div class="brand-inner p-3">' +
                '<div class="flex items-baseline justify-between gap-2"><span class="font-semibold text-sm">' + b['Brand'] + '</span><span class="font-mono-tabular text-sm font-bold" style="color:' + posColor(qoq) + '">' + (qoq > 0 ? '+' : '') + qoq.toFixed(1) + '%</span></div>' +
                '<div class="mt-1 flex items-center justify-between font-mono-tabular text-[11px]" style="color:var(--text-muted)"><span>' + fmt(u1) + ' · prev ' + fmt(u4) + '</span><span style="color:' + posColor(yoy) + '">YoY ' + (yoy > 0 ? '+' : '') + yoy.toFixed(1) + '%</span></div>' +
                '<div class="mt-2 h-1 overflow-hidden rounded-full bg-gray-700/20"><div class="h-full rounded-full progress-bar" style="width:' + pct + '%;background:' + bc + ';"></div></div>' + nh + '</div>';
        }

        function renderMovers(ba) {
            var c = document.getElementById('moversList'); if (!ba || !ba.length) { c.innerHTML = '<div class="text-xs text-center py-6" style="color:var(--text-muted)">Select a country</div>'; return; }
            var uk = 'Units_' + selectedQuarter, pq = getPrevQuarter(selectedQuarter), pk = pq ? 'Units_' + pq : null;
            var ms = ba.map(function (b) { var c0 = b[uk] || 0, p0 = pk ? (b[pk] || 0) : 0; return { name: b['Brand'], q1: c0, q4: p0, delta: c0 - p0, qoq: (pk && p0) ? ((c0 - p0) / p0) * 100 : null }; }).sort(function (a, b) { return Math.abs(b.delta) - Math.abs(a.delta); });
            var max = Math.max(1, ms.reduce(function (m, x) { return Math.max(m, Math.abs(x.delta)); }, 0));
            c.innerHTML = ms.map(function (m) { var pct = (Math.abs(m.delta) / max) * 100, bc = m.delta >= 0 ? '#34d399' : '#f87171';
                return '<div class="brand-inner p-3">' +
                    '<div class="flex items-baseline justify-between gap-2"><span class="font-semibold text-sm">' + m.name + '</span><span class="font-mono-tabular text-sm font-bold" style="color:' + posColor(m.delta) + '">' + posSign(m.delta) + m.delta.toLocaleString() + '</span></div>' +
                    '<div class="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-700/20"><div class="h-full rounded-full progress-bar" style="width:' + pct + '%;background:' + bc + ';"></div></div>' +
                    '<div class="mt-1 font-mono-tabular text-[11px]" style="color:var(--text-muted)">' + selectedQuarter.replace(/(\\d{4})Q(\\d)/, 'Q$2\\'$1') + ' ' + fmt(m.q1) + ' · QoQ ' + (m.qoq != null ? m.qoq.toFixed(1) : '—') + '%</div></div>';
            }).join('');
        }

        function renderBrandTable(ba) {
            var tb = document.getElementById('brandTableBody'); if (!ba || !ba.length) { tb.innerHTML = '<tr><td colspan="5" class="text-center py-8" style="color:var(--text-muted)">No data</td></tr>'; return; }
            var uk = 'Units_' + selectedQuarter; ba.sort(function (a, b) { return (b[uk] || 0) - (a[uk] || 0); }); var tot = ba.reduce(function (s, b) { return s + (b[uk] || 0); }, 0); var h = '';
            for (var i = 0; i < ba.length; i++) { var b = ba[i], u = b[uk] || 0, s = tot ? (u / tot * 100) : 0, q = brandQoq(b), y = brandYoy(b);
                h += '<tr><td class="py-3 px-4 font-semibold">' + b['Brand'] + '</td><td class="py-3 px-4 text-right font-mono-tabular">' + u.toLocaleString() + '</td>' +
                    '<td class="py-3 px-4 text-right"><div class="flex items-center justify-end gap-2"><div class="w-20 h-1.5 rounded-full overflow-hidden" style="background:var(--border)"><div class="h-full rounded-full" style="width:' + s + '%;background:#38bdf8;"></div></div><span class="font-mono-tabular text-xs">' + s.toFixed(1) + '%</span></div></td>' +
                    '<td class="py-3 px-4 text-right font-mono-tabular text-sm" style="color:' + posColor(q) + '">' + (q != null ? posSign(q) + q.toFixed(1) + '%' : '—') + '</td>' +
                    '<td class="py-3 px-4 text-right font-mono-tabular text-sm" style="color:' + posColor(y) + '">' + (y != null ? posSign(y) + y.toFixed(1) + '%' : '—') + '</td></tr>'; }
            tb.innerHTML = h;
        }

        function renderComparison() {
            var cs = D.country_comparison || [], ct = document.getElementById('comparisonRows'); if (!cs.length) return;
            var pq = getPrevQuarter(selectedQuarter), pyq = getPrevYearQuarter(selectedQuarter);
            var rs = cs.map(function (c) {
                var ov = (D.country_overview || []).find(function (x) { return x.Country === c.Country; }) || {};
                var t = getCategoryUnitsForCountry(ov, selectedQuarter, selectedCategory, c.Country);
                var pt = pq ? getCategoryUnitsForCountry(ov, pq, selectedCategory, c.Country) : 0;
                var pyt = pyq ? getCategoryUnitsForCountry(ov, pyq, selectedCategory, c.Country) : 0;
                return { name: c.Country, total: t, qoq: pt ? ((t - pt) / pt) * 100 : null, yoy: pyt ? ((t - pyt) / pyt) * 100 : null };
            }).sort(function (a, b) { return b.total - a.total; });
            var mQ = Math.max(1, rs.reduce(function (m, r) { return Math.max(m, Math.abs(r.qoq || 0)); }, 0));
            var mY = Math.max(1, rs.reduce(function (m, r) { return Math.max(m, Math.abs(r.yoy || 0)); }, 0));
            ct.innerHTML = rs.map(function (r) {
                return '<div class="border rounded-lg p-4 hover:border-primary/20 transition-all" style="border-color:var(--border);background:var(--surface)">' +
                    '<div class="grid grid-cols-12 items-center gap-4">' +
                        '<div class="col-span-3 flex items-center gap-2"><span class="text-lg">' + getFlag(r.name) + '</span><span class="font-medium text-sm">' + r.name + '</span></div>' +
                        '<div class="col-span-2 text-right font-mono-tabular text-sm font-semibold">' + fmt(r.total) + '</div>' +
                        '<div class="col-span-3">' + cBar(r.qoq, mQ) + '</div>' +
                        '<div class="col-span-3">' + cBar(r.yoy, mY) + '</div>' +
                        '<div class="col-span-1"></div>' +
                    '</div></div>';
            }).join('');
        }
        function cBar(v, m) { if (v == null) return '<div class="text-center text-xs" style="color:var(--text-muted)">—</div>'; var p = v >= 0, pct = (Math.abs(v) / m) * 100, bc = p ? '#34d399' : '#f87171'; return '<div><div class="relative flex items-center"><div class="relative flex h-6 w-full items-center overflow-hidden rounded" style="background:var(--border)"><div class="absolute left-1/2 top-0 h-full w-px" style="background:var(--surface)"></div><div class="absolute h-full" style="width:' + (pct / 2) + '%;background:' + bc + ';' + (p ? 'left:50%;' : 'right:50%;') + '"></div><span class="relative ml-auto mr-2 font-mono-tabular text-xs font-bold" style="color:' + bc + '">' + (p ? '+' : '') + v.toFixed(1) + '%</span></div></div></div>'; }

        function renderRankings() { var rk = D.brand_rankings || [], tb = document.getElementById('rankingsTableBody'); if (!rk.length) { tb.innerHTML = '<tr><td colspan="5" class="text-center py-8" style="color:var(--text-muted)">No data</td></tr>'; return; } var tc = (D.country_overview || []).length, h = ''; for (var i = 0; i < Math.min(rk.length, 25); i++) { var b = rk[i], r = b.Rank || (i + 1), rc = r <= 3 ? 'bg-yellow-500/20 text-yellow-400 font-bold' : ''; h += '<tr><td class="py-3 px-4"><span class="inline-flex items-center justify-center w-8 h-8 rounded-full text-xs font-bold ' + rc + '" style="' + (!rc ? 'color:var(--text-muted);background:var(--border)' : '') + '">' + r + '</span></td><td class="py-3 px-4 font-semibold">' + b.Brand + '</td><td class="py-3 px-4 text-right font-mono-tabular">' + fmt(b.Total_Units) + '</td><td class="py-3 px-4 text-right">' + (b.Countries_Present || 0) + ' / ' + tc + '</td><td class="py-3 px-4 text-right font-mono-tabular">' + fmt(Math.round(b.Avg_Quarterly_Units || 0)) + '</td></tr>'; } tb.innerHTML = h; }
        function toggleAccordion() { var c = document.getElementById('rankingsAccordion'), v = document.getElementById('accordionChevron'); if (c.classList.contains('open')) { c.classList.remove('open'); v.style.transform = 'rotate(0deg)'; } else { c.classList.add('open'); v.style.transform = 'rotate(180deg)'; } }

        init();
    </script>
</body>
</html>'''

if __name__ == '__main__':
    build_dashboard()