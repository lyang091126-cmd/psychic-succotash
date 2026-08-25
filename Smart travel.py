<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 智能旅行行程与预算沙盘</title>
    <!-- Tailwind CSS for modern, clean, and accessible styling -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        brand: {
                            50: '#f0fdf4',
                            100: '#dcfce7',
                            500: '#22c55e',
                            600: '#16a34a',
                            700: '#15803d',
                        }
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col font-sans antialiased">

    <!-- Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-xs">
        <div class="max-w-7xl mx-auto px-4 py-4 sm:px-6 flex justify-between items-center">
            <div class="flex items-center space-x-3">
                <div class="bg-brand-600 text-white p-2.5 rounded-xl shadow-md">
                    <i class="fa-solid fa-compass text-xl"></i>
                </div>
                <div>
                    <div class="flex items-center space-x-2">
                        <h1 class="text-xl font-bold text-slate-900 tracking-tight">AI 智慧旅行行程规划</h1>
                        <span class="text-[11px] bg-brand-50 text-brand-700 border border-brand-200 px-2 py-0.5 rounded-full font-semibold flex items-center">
                            <i class="fa-solid fa-wand-magic-sparkles mr-1 text-[10px]"></i> 智能优化器
                        </span>
                    </div>
                    <p class="text-xs text-slate-500">量体裁衣，轻松规划你的旅行预算与专属行程</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <div class="hidden sm:flex items-center space-x-2 text-xs text-slate-600 bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
                    <i class="fa-solid fa-coins text-amber-500"></i>
                    <span>货币符号:</span>
                    <select class="bg-transparent font-semibold outline-none cursor-pointer">
                        <option>USD ($)</option>
                        <option>CNY (¥)</option>
                        <option>EUR (€)</option>
                        <option>SGD ($)</option>
                    </select>
                </div>
                <button onclick="resetApp()" class="px-3 py-1.5 text-sm text-slate-600 hover:text-red-600 hover:bg-red-50 rounded-xl transition border border-slate-200 flex items-center">
                    <i class="fa-solid fa-rotate-right mr-1.5"></i> 重置
                </button>
            </div>
        </div>
    </header>

    <!-- Main Content Layout -->
    <main class="max-w-7xl mx-auto px-4 py-6 sm:px-6 grid grid-cols-1 lg:grid-cols-12 gap-6 w-full flex-grow">
        
        <!-- Left Panel: Inputs & Configuration (5 cols) -->
        <section id="inputPanel" class="lg:col-span-5 bg-white p-6 rounded-2xl shadow-sm border border-slate-200 h-fit sticky top-24 space-y-6 transition-all duration-300">
            <div class="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 class="font-semibold text-slate-800 flex items-center text-sm">
                    <i class="fa-solid fa-sliders text-brand-600 mr-2"></i> 行程参数设置
                </h2>
                <div class="flex items-center space-x-2">
                    <span class="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-medium">步骤 1 / 2</span>
                    <button type="button" id="togglePanelBtn" onclick="toggleInputPanel()" class="hidden text-xs text-slate-500 hover:text-slate-800 bg-slate-100 px-2 py-1 rounded-lg">
                        <i class="fa-solid fa-chevron-up"></i>
                    </button>
                </div>
            </div>

            <!-- Quick Destination Selector Pills -->
            <div>
                <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">热门目的地</label>
                <div class="flex flex-wrap gap-1.5" id="popularDestinations">
                    <button type="button" onclick="selectDestination('新加坡')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-semibold border border-brand-500 bg-brand-50 text-brand-700 transition shadow-2xs">新加坡</button>
                    <button type="button" onclick="selectDestination('东京')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition">东京</button>
                    <button type="button" onclick="selectDestination('巴黎')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition">巴黎</button>
                    <button type="button" onclick="selectDestination('罗马')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition">罗马</button>
                    <button type="button" onclick="selectDestination('纽约')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition">纽约</button>
                    <button type="button" onclick="selectDestination('巴厘岛')" class="dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition">巴厘岛</button>
                </div>
            </div>

            <form id="tripForm" onsubmit="handleGenerate(event)" class="space-y-5">
                <!-- Destination Input -->
                <div>
                    <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">目的地城市</label>
                    <div class="relative">
                        <span class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                            <i class="fa-solid fa-location-dot"></i>
                        </span>
                        <input type="text" id="destination" required value="新加坡" placeholder="例如：新加坡、东京、巴黎"
                            class="w-full pl-10 pr-3 py-2.5 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:ring-2 focus:ring-brand-500 focus:bg-white outline-none transition font-medium">
                    </div>
                </div>

                <!-- Number of Travel Days & Total Budget Grid -->
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <!-- Days -->
                    <div class="bg-slate-50/70 p-3 rounded-2xl border border-slate-200">
                        <div class="flex justify-between items-center mb-1">
                            <label class="text-xs font-semibold text-slate-700">出行天数</label>
                            <span id="daysBadge" class="text-[10px] font-bold bg-brand-100 text-brand-700 px-2 py-0.5 rounded">3 天</span>
                        </div>
                        <div class="flex items-center space-x-2 mt-2">
                            <button type="button" onclick="adjustDays(-1)" class="w-8 h-8 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 flex items-center justify-center font-bold text-slate-700 shadow-2xs transition">-</button>
                            <input type="number" id="days" required min="1" max="10" value="3" oninput="updateDaysBadge(this.value)"
                                class="w-full text-center py-1.5 bg-white border border-slate-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-brand-500 outline-none">
                            <button type="button" onclick="adjustDays(1)" class="w-8 h-8 rounded-lg bg-white border border-slate-300 hover:bg-slate-100 flex items-center justify-center font-bold text-slate-700 shadow-2xs transition">+</button>
                        </div>
                        <span class="text-[10px] text-slate-400 mt-1 block">建议：2 至 7 天</span>
                    </div>

                    <!-- Budget -->
                    <div class="bg-slate-50/70 p-3 rounded-2xl border border-slate-200">
                        <div class="flex justify-between items-center mb-1">
                            <label class="text-xs font-semibold text-slate-700">总预算 ($)</label>
                            <span id="dailyEstimate" class="text-[10px] font-bold text-slate-500">~$500/天</span>
                        </div>
                        <div class="relative mt-2">
                            <span class="absolute inset-y-0 left-0 pl-3 flex items-center font-bold text-slate-400 text-sm">$</span>
                            <input type="number" id="totalBudget" required min="100" step="50" value="1500" oninput="updateDailyPerHead()"
                                class="w-full pl-7 pr-3 py-1.5 bg-white border border-slate-300 rounded-xl text-sm font-bold focus:ring-2 focus:ring-brand-500 outline-none">
                        </div>
                        <!-- Quick Budget Buttons -->
                        <div class="flex space-x-1 mt-2">
                            <button type="button" onclick="setBudget(350)" class="flex-1 text-[10px] bg-white border border-slate-200 py-1 rounded hover:bg-slate-100 font-medium text-slate-600 transition">$350</button>
                            <button type="button" onclick="setBudget(800)" class="flex-1 text-[10px] bg-white border border-slate-200 py-1 rounded hover:bg-slate-100 font-medium text-slate-600 transition">$800</button>
                            <button type="button" onclick="setBudget(1500)" class="flex-1 text-[10px] bg-brand-50 border border-brand-300 py-1 rounded font-bold text-brand-700 transition">$1500</button>
                            <button type="button" onclick="setBudget(3000)" class="flex-1 text-[10px] bg-white border border-slate-200 py-1 rounded hover:bg-slate-100 font-medium text-slate-600 transition">$3000</button>
                        </div>
                    </div>
                </div>

                <!-- Budget Allocation Sliders Section -->
                <div class="bg-slate-50 p-3.5 rounded-2xl border border-slate-200 space-y-3">
                    <div class="flex justify-between items-center">
                        <label class="text-xs font-semibold text-slate-700">预算分配比例 (%)</label>
                        <span id="allocTotalWarn" class="text-[10px] font-bold text-brand-600">合计: 100%</span>
                    </div>

                    <!-- Hotel Slider -->
                    <div>
                        <div class="flex justify-between text-[11px] mb-1">
                            <span class="text-slate-600">住宿</span>
                            <span id="valHotel" class="font-bold text-slate-800">40%</span>
                        </div>
                        <input type="range" id="sliderHotel" min="10" max="70" value="40" class="w-full accent-brand-600 cursor-pointer" oninput="updateAllocations('hotel')">
                    </div>

                    <!-- Food Slider -->
                    <div>
                        <div class="flex justify-between text-[11px] mb-1">
                            <span class="text-slate-600">餐饮</span>
                            <span id="valFood" class="font-bold text-slate-800">30%</span>
                        </div>
                        <input type="range" id="sliderFood" min="10" max="70" value="30" class="w-full accent-brand-600 cursor-pointer" oninput="updateAllocations('food')">
                    </div>

                    <!-- Activities Slider -->
                    <div>
                        <div class="flex justify-between text-[11px] mb-1">
                            <span class="text-slate-600">门票与交通</span>
                            <span id="valActivity" class="font-bold text-slate-800">30%</span>
                        </div>
                        <input type="range" id="sliderActivity" min="10" max="70" value="30" class="w-full accent-brand-600 cursor-pointer" oninput="updateAllocations('activity')">
                    </div>
                </div>

                <!-- Select Travel Style (Cards Grid) -->
                <div>
                    <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">选择旅行风格</label>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3" id="travelStyleContainer">
                        <!-- Style 1 -->
                        <label class="style-card border-2 border-brand-500 bg-brand-50/40 rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative shadow-2xs">
                            <input type="radio" name="travelStyle" value="packed" class="absolute top-3 right-3 accent-brand-600" checked onchange="updateStyleSelection()">
                            <div class="flex items-center space-x-2.5 mb-2">
                                <div class="w-8 h-8 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center font-bold">
                                    <i class="fa-solid fa-bolt text-sm"></i>
                                </div>
                                <span class="text-xs font-bold text-slate-900">特种兵 / 紧凑打卡</span>
                            </div>
                            <p class="text-[11px] text-slate-600 leading-snug">地标建筑、高空观景与经典拍照打卡点</p>
                        </label>

                        <!-- Style 2 -->
                        <label class="style-card border-2 border-slate-200 bg-white rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative hover:border-slate-300 shadow-2xs">
                            <input type="radio" name="travelStyle" value="food" class="absolute top-3 right-3 accent-brand-600" onchange="updateStyleSelection()">
                            <div class="flex items-center space-x-2.5 mb-2">
                                <div class="w-8 h-8 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center font-bold">
                                    <i class="fa-solid fa-utensils text-sm"></i>
                                </div>
                                <span class="text-xs font-bold text-slate-900">美食探索</span>
                            </div>
                            <p class="text-[11px] text-slate-600 leading-snug">地道街头小吃、夜市、特色餐厅与咖啡馆</p>
                        </label>

                        <!-- Style 3 -->
                        <label class="style-card border-2 border-slate-200 bg-white rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative hover:border-slate-300 shadow-2xs">
                            <input type="radio" name="travelStyle" value="culture" class="absolute top-3 right-3 accent-brand-600" onchange="updateStyleSelection()">
                            <div class="flex items-center space-x-2.5 mb-2">
                                <div class="w-8 h-8 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center font-bold">
                                    <i class="fa-solid fa-landmark text-sm"></i>
                                </div>
                                <span class="text-xs font-bold text-slate-900">博物馆与人文</span>
                            </div>
                            <p class="text-[11px] text-slate-600 leading-snug">艺术馆、历史城堡、古迹寺庙与戏剧演出</p>
                        </label>

                        <!-- Style 4 -->
                        <label class="style-card border-2 border-slate-200 bg-white rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative hover:border-slate-300 shadow-2xs">
                            <input type="radio" name="travelStyle" value="relaxed" class="absolute top-3 right-3 accent-brand-600" onchange="updateStyleSelection()">
                            <div class="flex items-center space-x-2.5 mb-2">
                                <div class="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center font-bold">
                                    <i class="fa-solid fa-leaf text-sm"></i>
                                </div>
                                <span class="text-xs font-bold text-slate-900">自然风光与休闲</span>
                            </div>
                            <p class="text-[11px] text-slate-600 leading-snug">公园植物园、海岸步道与宁静自然景点</p>
                        </label>
                    </div>
                </div>

                <!-- Modern Interest Tag Pills -->
                <div>
                    <label class="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">偏好标签 (可多选)</label>
                    <div class="flex flex-wrap gap-2" id="interestTagsContainer">
                        <button type="button" onclick="toggleInterestTag(this)" class="tag-pill active px-3 py-1.5 rounded-full text-xs font-medium border border-brand-500 bg-brand-50 text-brand-700 transition flex items-center space-x-1">
                            <i class="fa-solid fa-tree text-[10px]"></i>
                            <span>自然与户外</span>
                        </button>
                        <button type="button" onclick="toggleInterestTag(this)" class="tag-pill active px-3 py-1.5 rounded-full text-xs font-medium border border-brand-500 bg-brand-50 text-brand-700 transition flex items-center space-x-1">
                            <i class="fa-solid fa-mug-hot text-[10px]"></i>
                            <span>网红打卡&咖啡</span>
                        </button>
                        <button type="button" onclick="toggleInterestTag(this)" class="tag-pill active px-3 py-1.5 rounded-full text-xs font-medium border border-brand-500 bg-brand-50 text-brand-700 transition flex items-center space-x-1">
                            <i class="fa-solid fa-monument text-[10px]"></i>
                            <span>历史与文化</span>
                        </button>
                        <button type="button" onclick="toggleInterestTag(this)" class="tag-pill px-3 py-1.5 rounded-full text-xs font-medium border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition flex items-center space-x-1">
                            <i class="fa-solid fa-martini-glass-citrus text-[10px]"></i>
                            <span>酒吧与夜生活</span>
                        </button>
                    </div>
                </div>

                <!-- Submit Button -->
                <button type="submit" class="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3 px-4 rounded-xl shadow-md transition flex items-center justify-center space-x-2">
                    <i class="fa-solid fa-wand-magic-sparkles"></i>
                    <span>生成优化行程方案</span>
                </button>
            </form>
        </section>

        <!-- Right Panel: Output & Itinerary Timeline (7 cols) -->
        <section id="outputPanel" class="lg:col-span-7 flex flex-col space-y-6 relative z-10">
            
            <!-- Dynamic Budget Dashboard Summary Banner -->
            <div id="budgetDashboard" class="bg-white p-5 rounded-2xl shadow-sm border border-slate-200 hidden relative z-20">
                <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4">
                    <div>
                        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">财务总览</span>
                        <h3 class="text-lg font-bold text-slate-900" id="summaryDestTitle">行程概览</h3>
                    </div>
                    <!-- Global Budget Modifier Slider (-20% to +20%) -->
                    <div class="bg-slate-50 px-3 py-2 rounded-xl border border-slate-200 w-full sm:w-auto">
                        <div class="flex justify-between items-center text-xs mb-1">
                            <span class="text-slate-600 font-medium mr-4">预算调节系数</span>
                            <span id="scaleFactorVal" class="font-bold text-brand-600">100%</span>
                        </div>
                        <input type="range" id="globalBudgetScale" min="80" max="120" value="100" class="w-full accent-brand-600 cursor-pointer" oninput="applyBudgetScale(this.value)">
                    </div>
                </div>

                <!-- Progress / Breakdown Bar -->
                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                        <span class="text-xs text-slate-500 block">总分配预算</span>
                        <span id="statTotalBudget" class="text-base font-bold text-slate-800">$1,500</span>
                    </div>
                    <div class="bg-slate-50 p-3 rounded-xl border border-slate-100">
                        <span class="text-xs text-slate-500 block">预计总支出</span>
                        <span id="statEstCost" class="text-base font-bold text-brand-600">$1,380</span>
                    </div>
                    <div class="bg-slate-50 p-3 rounded-xl border border-slate-100" id="budgetStatusCard">
                        <span class="text-xs text-slate-500 block">预算状态</span>
                        <span id="statStatus" class="text-xs font-semibold text-emerald-600 flex items-center mt-1">
                            <i class="fa-solid fa-circle-check mr-1"></i> 预算充足
                        </span>
                    </div>
                </div>
            </div>

            <!-- Empty State / Welcome Notice -->
            <div id="emptyState" class="bg-white p-12 rounded-2xl shadow-sm border border-slate-200 text-center flex flex-col items-center justify-center flex-grow relative z-20">
                <div class="w-16 h-16 bg-brand-50 text-brand-600 rounded-full flex items-center justify-center text-2xl mb-4 shadow-inner">
                    <i class="fa-solid fa-map-location-dot"></i>
                </div>
                <h3 class="text-lg font-bold text-slate-800 mb-1">尚未生成行程方案</h3>
                <p class="text-sm text-slate-500 max-w-md mb-6">请在左侧选择目的地、天数、预算和旅行风格，然后点击 <strong>“生成优化行程方案”</strong>。</p>
                <button onclick="fillPreset()" class="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-medium px-4 py-2.5 rounded-xl transition flex items-center mx-auto">
                    <i class="fa-solid fa-bolt mr-1.5 text-amber-500"></i> 一键填入示例（新加坡 3 天）
                </button>
            </div>

            <!-- Itinerary Timeline Output Container -->
            <div id="itineraryContainer" class="space-y-4 hidden relative z-20">
                <!-- Days will be dynamically injected here -->
            </div>

        </section>

    </main>

    <!-- Footer Note -->
    <footer class="max-w-7xl mx-auto px-4 py-6 text-center text-xs text-slate-400">
        AI 智能旅行行程与预算沙盘 &bull; 打造专属的个性化旅游路线
    </footer>

    <!-- JavaScript Application Logic -->
    <script>
        // Mock database for realistic customized itinerary generation
        const mockDatabase = {
            "新加坡": {
                hotel: { name: "YOTEL 新加坡乌节路酒店", baseCost: 160, desc: "位于购物中心地带的现代舱房风格酒店。" },
                spots: [
                    { time: "09:00 AM", title: "新加坡植物园", desc: "漫步于这座联合国教科文组织评定的热带植物园。", duration: "2.5 小时", type: "自然", cost: 15, image: "https://images.unsplash.com/photo-1525625293386-3f8f99389edd?auto=format&fit=crop&w=400&q=80" },
                    { time: "12:00 PM", title: "老巴刹美食广场", desc: "品尝正宗海南鸡饭与沙爹烤串。", duration: "1.5 小时", type: "美食", cost: 20, image: "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=400&q=80", alternatives: [
                        { title: "麦士威熟食中心", desc: "牛车水经典的传奇熟食摊位。", cost: 18 },
                        { title: "珍宝海鲜 (克拉码头)", desc: "沿河享受经典的辣椒螃蟹大餐。", cost: 65 },
                        { title: "小印度竹脚中心", desc: "充满色彩与正宗印度美食的市场。", cost: 15 }
                    ]},
                    { time: "02:30 PM", title: "新加坡国家美术馆", desc: "在历史建筑中欣赏东南亚现代艺术作品。", duration: "2 小时", type: "人文", cost: 25, image: "https://images.unsplash.com/photo-1565967511849-76a60a516170?auto=format&fit=crop&w=400&q=80" },
                    { time: "05:00 PM", title: "哈芝巷与阿拉伯街", desc: "探索潮流小店、彩色壁画与特色咖啡馆。", duration: "2 小时", type: "休闲咖啡", cost: 30, image: "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?auto=format&fit=crop&w=400&q=80", alternatives: [
                        { title: "中巴鲁面包房与咖啡馆", desc: "复古街区里的手工咖啡与法式糕点。", cost: 22 },
                        { title: "滨海湾花园花穹", desc: "充满奇花异草的未来主义冷室。", cost: 35 },
                        { title: "牛车水原貌馆", desc: "沉浸式了解早期华人移民的生活历史。", cost: 20 }
                    ]},
                    { time: "07:30 PM", title: "滨海湾金沙水舞秀", desc: "俯瞰天际线的震撼水幕灯光秀。", duration: "1.5 小时", type: "自然", cost: 0, image: "https://images.unsplash.com/photo-1508009603885-50cf7c579365?auto=format&fit=crop&w=400&q=80" }
                ],
                commute: "地铁 MRT & 步行（预计耗时: 15-25 分钟）"
            },
            "巴黎": {
                hotel: { name: "Hôtel Le Marais 巴黎玛黑区酒店", baseCost: 190, desc: "位于历史悠久的玛黑区的精品优雅酒店。" },
                spots: [
                    { time: "09:00 AM", title: "卢浮宫博物馆", desc: "探访《蒙娜丽莎》与《胜利女神》等世界级艺术珍品。", duration: "3 小时", type: "人文", cost: 22, image: "https://images.unsplash.com/photo-1549877452-9c387954fbc2?auto=format&fit=crop&w=400&q=80" },
                    { time: "12:30 PM", title: "花神咖啡馆 (Café de Flore)", desc: "著名历史咖啡馆，品尝浓郁热巧克力与法式甜点。", duration: "1.5 小时", type: "休闲咖啡", cost: 28, image: "https://images.unsplash.com/photo-1502602898657-3e91760cbb34?auto=format&fit=crop&w=400&q=80", alternatives: [
                        { title: "Le Procope 普罗科普咖啡馆", desc: "巴黎历史最悠久的餐厅，极具历史韵味。", cost: 45 },
                        { title: "Poilâne 手工面包坊", desc: "享誉世界的传统法式手工面包与水果塔。", cost: 15 },
                        { title: "双叟咖啡馆 (Les Deux Magots)", desc: "哲学大师与艺术家经常光顾的名店。", cost: 30 }
                    ]},
                    { time: "03:00 PM", title: "卢森堡公园 (Jardin du Luxembourg)", desc: "漫步于法式林荫道、美第奇喷泉与绿意草坪。", duration: "2 小时", type: "自然", cost: 0, image: "https://images.unsplash.com/photo-1520939817895-060bdaf4fe1b?auto=format&fit=crop&w=400&q=80" },
                    { time: "06:00 PM", title: "塞纳河日落游船", desc: "在水上欣赏夜幕低垂下的巴黎古桥与埃菲尔铁塔。", duration: "1.5 小时", type: "自然", cost: 18, image: "https://images.unsplash.com/photo-1509439576707-1b26cfd4268d?auto=format&fit=crop&w=400&q=80" }
                ],
                commute: "巴黎地铁 Métro & 步行（预计耗时: 15-20 分钟）"
            },
            "东京": {
                hotel: { name: "新宿格兰贝尔酒店 (Shinjuku Granbell)", baseCost: 175, desc: "紧邻繁华商业区与交通枢纽的设计型酒店。" },
                spots: [
                    { time: "09:00 AM", title: "明治神宫与代代木公园", desc: "城市中心绿树成荫的清静神社与公园。", duration: "2 小时", type: "自然", cost: 0, image: "https://images.unsplash.com/photo-1503899036084-c55cdd92da26?auto=format&fit=crop&w=400&q=80" },
                    { time: "12:00 PM", title: "一兰拉面 (涉谷店)", desc: "享誉全球的单人隔间浓厚豚骨拉面。", duration: "1 小时", type: "美食", cost: 15, image: "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?auto=format&fit=crop&w=400&q=80", alternatives: [
                        { title: "原宿饺子楼", desc: "深受本地人喜爱的休闲煎饺店。", cost: 12 },
                        { title: "涉谷回转寿司", desc: "食材新鲜且平板点餐快捷的特色寿司店。", cost: 25 },
                        { title: "Depachika 美食地下街", desc: "涉谷大型百货地下豪华美食街。", cost: 20 }
                    ]},
                    { time: "02:00 PM", title: "涉谷十字路口与猫街", desc: "打卡世界上最繁忙的十字路口及潮流小店。", duration: "2.5 小时", type: "休闲咖啡", cost: 25, image: "https://images.unsplash.com/photo-1542051841857-5f90071e7989?auto=format&fit=crop&w=400&q=80", alternatives: [
                        { title: "表参道丘建筑群", desc: "充斥着精品咖啡馆与现代建筑风格的大道。", cost: 18 },
                        { title: "明治通古着店探店", desc: "淘选独一无二的日系复古古着古物。", cost: 30 },
                        { title: "代代木面包咖啡馆", desc: "公园旁的优雅手工面包与精品咖啡店。", cost: 15 }
                    ]},
                    { time: "05:00 PM", title: "浅草寺与仲见世商店街", desc: "东京最古老且最热闹的古刹与传统集市。", duration: "2 小时", type: "人文", cost: 0, image: "https://images.unsplash.com/photo-1536098561742-ca998e48cbcc?auto=format&fit=crop&w=400&q=80" }
                ],
                commute: "东京地铁一日券 & 步行（预计耗时: 15 分钟）"
            }
        };

        let currentItineraryState = null;
        let globalScaleFactor = 1.0;
        let isPanelCollapsed = false;

        // Toggle destination pills
        function selectDestination(cityName) {
            document.getElementById('destination').value = cityName;
            document.querySelectorAll('.dest-pill').forEach(btn => {
                if (btn.innerText.trim() === cityName) {
                    btn.className = "dest-pill px-3 py-1.5 rounded-xl text-xs font-semibold border border-brand-500 bg-brand-50 text-brand-700 transition shadow-2xs";
                } else {
                    btn.className = "dest-pill px-3 py-1.5 rounded-xl text-xs font-medium border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700 transition";
                }
            });
        }

        // Adjust days with +/-
        function adjustDays(delta) {
            const daysInput = document.getElementById('days');
            let val = parseInt(daysInput.value) + delta;
            if (val >= 1 && val <= 10) {
                daysInput.value = val;
                updateDaysBadge(val);
            }
        }

        function updateDaysBadge(val) {
            document.getElementById('daysBadge').innerText = val + ' 天';
            updateDailyPerHead();
        }

        function setBudget(amount) {
            document.getElementById('totalBudget').value = amount;
            updateDailyPerHead();
            if (currentItineraryState) renderItineraryUI();
        }

        function updateDailyPerHead() {
            const days = parseInt(document.getElementById('days').value) || 1;
            const budget = parseFloat(document.getElementById('totalBudget').value) || 0;
            const perDay = Math.round(budget / days);
            document.getElementById('dailyEstimate').innerText = `~$${perDay}/天`;
        }

        // Budget allocation sliders logic
        function updateAllocations(changed) {
            let h = parseInt(document.getElementById('sliderHotel').value);
            let f = parseInt(document.getElementById('sliderFood').value);
            let a = parseInt(document.getElementById('sliderActivity').value);

            let total = h + f + a;
            let warn = document.getElementById('allocTotalWarn');
            
            if (total !== 100) {
                warn.innerText = `合计: ${total}% (建议设为 100%)`;
                warn.className = "text-[10px] font-bold text-amber-600";
            } else {
                warn.innerText = `合计: 100%`;
                warn.className = "text-[10px] font-bold text-brand-600";
            }

            document.getElementById('valHotel').innerText = h + '%';
            document.getElementById('valFood').innerText = f + '%';
            document.getElementById('valActivity').innerText = a + '%';

            if (currentItineraryState) {
                renderItineraryUI();
            }
        }

        function toggleInterestTag(btn) {
            btn.classList.toggle('active');
            if (btn.classList.contains('active')) {
                btn.className = "tag-pill active px-3 py-1.5 rounded-full text-xs font-medium border border-brand-500 bg-brand-50 text-brand-700 transition flex items-center space-x-1";
            } else {
                btn.className = "tag-pill px-3 py-1.5 rounded-full text-xs font-medium border border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100 transition flex items-center space-x-1";
            }
        }

        function updateStyleSelection() {
            document.querySelectorAll('.style-card').forEach(card => {
                const radio = card.querySelector('input[type="radio"]');
                if (radio.checked) {
                    card.className = "style-card border-2 border-brand-500 bg-brand-50/40 rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative shadow-2xs";
                } else {
                    card.className = "style-card border-2 border-slate-200 bg-white rounded-2xl p-3.5 flex flex-col justify-between cursor-pointer transition relative hover:border-slate-300 shadow-2xs";
                }
            });
        }

        function toggleInputPanel() {
            const form = document.getElementById('tripForm');
            const destPills = id('popularDestinations').parentElement;
            const toggleBtn = document.getElementById('togglePanelBtn');

            if (isPanelCollapsed) {
                form.classList.remove('hidden');
                destPills.classList.remove('hidden');
                toggleBtn.innerHTML = '<i class="fa-solid fa-chevron-up"></i>';
                isPanelCollapsed = false;
            } else {
                form.classList.add('hidden');
                destPills.classList.add('hidden');
                toggleBtn.innerHTML = '<i class="fa-solid fa-chevron-down"></i> 展开参数';
                isPanelCollapsed = true;
            }
        }

        function id(e) { return document.getElementById(e); }

        function fillPreset() {
            selectDestination("新加坡");
            document.getElementById('days').value = 3;
            updateDaysBadge(3);
            document.getElementById('totalBudget').value = 1500;
            updateDailyPerHead();
            document.querySelector('input[name="travelStyle"][value="packed"]').checked = true;
            updateStyleSelection();
            handleGenerate(new Event('submit'));
        }

        // Handle Form Submission
        function handleGenerate(e) {
            e.preventDefault();
            
            const destInput = document.getElementById('destination').value.trim();
            const daysInput = parseInt(document.getElementById('days').value);
            const budgetInput = parseFloat(document.getElementById('totalBudget').value);
            const style = document.querySelector('input[name="travelStyle"]:checked').value;

            // Intelligent lookup or fallback
            let destKey = Object.keys(mockDatabase).find(k => k.toLowerCase() === destInput.toLowerCase());
            let template;
            if (destKey) {
                template = mockDatabase[destKey];
            } else {
                destKey = destInput || "巴黎";
                template = {
                    hotel: { name: `${destKey} 尊享中心酒店`, baseCost: 150, desc: `位于 ${destKey} 市中心便利地段。` },
                    spots: [
                        { time: "09:00 AM", title: `${destKey} 城市中央标志地标`, desc: `探索 ${destKey} 标志性的建筑与人文中心。`, duration: "2.5 小时", type: "人文", cost: 20, image: "https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=400&q=80" },
                        { time: "12:30 PM", title: `${destKey} 特色风味小馆`, desc: "品尝当地代表性的特色美食与咖啡。", duration: "1.5 小时", type: "美食", cost: 22, image: "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=400&q=80", alternatives: [
                            { title: `${destKey} 夜市与街头小吃`, desc: "充满生活气息的摊位与风味美味。", cost: 15 },
                            { title: `高空全景顶楼餐厅`, desc: "俯瞰全城美丽夜景并享用精致下午点心。", cost: 35 }
                        ]},
                        { time: "03:00 PM", title: `${destKey} 植物公园与绿道`, desc: "感受大自然的清新空气与风景漫步道。", duration: "2 小时", type: "自然", cost: 10, image: "https://images.unsplash.com/photo-1519331379826-f10be5486c6f?auto=format&fit=crop&w=400&q=80" },
                        { time: "06:30 PM", title: `城市商业街晚间漫步`, desc: "探索特色小店与繁华夜景。", duration: "2 小时", type: "休闲咖啡", cost: 15, image: "https://images.unsplash.com/photo-1514565131-fce0801e5785?auto=format&fit=crop&w=400&q=80" }
                    ],
                    commute: "公共交通与步行（预计耗时: 20 分钟）"
                };
            }

            let daysData = [];
            for (let d = 1; d <= daysInput; d++) {
                let daySpots = JSON.parse(JSON.stringify(template.spots));
                if (style === 'relaxed' && daySpots.length > 3) {
                    daySpots.pop();
                }
                daysData.push({
                    day: d,
                    hotel: template.hotel,
                    spots: daySpots,
                    commute: template.commute
                });
            }

            currentItineraryState = {
                destination: destKey,
                daysCount: daysInput,
                totalBudget: budgetInput,
                style: style,
                days: daysData
            };

            globalScaleFactor = 1.0;
            document.getElementById('globalBudgetScale').value = 100;
            document.getElementById('scaleFactorVal').innerText = "100%";

            document.getElementById('emptyState').classList.add('hidden');
            document.getElementById('budgetDashboard').classList.remove('hidden');
            document.getElementById('itineraryContainer').classList.remove('hidden');

            document.getElementById('togglePanelBtn').classList.remove('hidden');

            renderItineraryUI();

            // Automatically collapse left panel for better view on mobile/tablet
            if (window.innerWidth < 1024) {
                toggleInputPanel();
            }

            document.getElementById('budgetDashboard').scrollIntoView({ behavior: 'smooth' });
        }

        function applyBudgetScale(val) {
            globalScaleFactor = val / 100;
            document.getElementById('scaleFactorVal').innerText = val + '%';
            renderItineraryUI();
        }

        function renderItineraryUI() {
            if (!currentItineraryState) return;

            const state = currentItineraryState;
            const inputBudget = parseFloat(document.getElementById('totalBudget').value) || state.totalBudget;
            const scaledBudget = inputBudget * globalScaleFactor;

            const allocHotelPct = (parseInt(document.getElementById('sliderHotel').value) || 40) / 100;
            const allocFoodPct = (parseInt(document.getElementById('sliderFood').value) || 30) / 100;
            const allocActPct = (parseInt(document.getElementById('sliderActivity').value) || 30) / 100;

            document.getElementById('statTotalBudget').innerText = `$${scaledBudget.toFixed(0)}`;
            document.getElementById('summaryDestTitle').innerText = `${state.daysCount} 天定制行程：${state.destination}`;

            let totalEstCost = 0;
            state.days.forEach(d => {
                let hotelCost = (d.hotel.baseCost * (allocHotelPct / 0.4)) * globalScaleFactor;
                let spotCost = d.spots.reduce((acc, s) => acc + (s.cost * globalScaleFactor), 0);
                totalEstCost += (hotelCost + spotCost);
            });

            document.getElementById('statEstCost').innerText = `$${totalEstCost.toFixed(0)}`;

            const statusText = document.getElementById('statStatus');
            if (totalEstCost <= scaledBudget) {
                statusText.innerHTML = `<i class="fa-solid fa-circle-check mr-1"></i> 预算充足 (结余 $${(scaledBudget - totalEstCost).toFixed(0)})`;
                statusText.className = "text-xs font-semibold text-emerald-600 flex items-center mt-1";
            } else {
                statusText.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1"></i> 超出预算 $${(totalEstCost - scaledBudget).toFixed(0)}`;
                statusText.className = "text-xs font-semibold text-rose-600 flex items-center mt-1";
            }

            let container = document.getElementById('itineraryContainer');
            container.innerHTML = "";

            state.days.forEach((dayObj, dIdx) => {
                let dayCard = document.createElement('div');
                dayCard.className = "bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden relative";

                let spotsHtml = "";
                dayObj.spots.forEach((spot, sIdx) => {
                    let adjustedCost = Math.round(spot.cost * globalScaleFactor);

                    let altDropdownHtml = "";
                    if (spot.alternatives && spot.alternatives.length > 0) {
                        altDropdownHtml = `
                            <div class="mt-3 pt-3 border-t border-slate-100">
                                <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-1.5"><i class="fa-solid fa-shuffle mr-1 text-brand-600"></i> 备选方案 (点击一键替换)：</span>
                                <div class="grid grid-cols-1 sm:grid-cols-3 gap-2">
                                    ${spot.alternatives.map((alt, aIdx) => `
                                        <button onclick="swapAlternative(${dIdx}, ${sIdx}, ${aIdx})" class="text-left p-2 rounded-lg bg-white hover:bg-brand-50 hover:border-brand-300 border border-slate-200 transition text-xs group shadow-2xs">
                                            <div class="font-medium text-slate-800 group-hover:text-brand-700 truncate">${alt.title}</div>
                                            <div class="text-[10px] text-slate-500 truncate">预估: $${Math.round(alt.cost * globalScaleFactor)}</div>
                                        </button>
                                    `).join('')}
                                </div>
                            </div>
                        `;
                    }

                    spotsHtml += `
                        <div class="relative pl-6 sm:pl-8 pb-5 last:pb-0">
                            ${sIdx !== dayObj.spots.length - 1 ? '<div class="absolute left-2.5 sm:left-3.5 top-3 bottom-0 w-0.5 bg-slate-200 z-0"></div>' : ''}
                            <div class="absolute left-1 sm:left-2 top-1.5 w-3.5 h-3.5 rounded-full bg-brand-500 border-2 border-white shadow-sm z-10"></div>

                            <div class="bg-white border border-slate-200/90 rounded-xl p-4 shadow-2xs transition relative z-20">
                                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                                    <div class="flex items-center space-x-2">
                                        <span class="text-xs font-bold text-brand-700 bg-brand-100 px-2 py-0.5 rounded-md">${spot.time}</span>
                                        <span class="text-xs text-slate-500"><i class="fa-regular fa-clock mr-1"></i>${spot.duration}</span>
                                    </div>
                                    <span class="text-xs font-semibold text-slate-600 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 w-fit">预计费用: $${adjustedCost}</span>
                                </div>

                                <div class="flex flex-col sm:flex-row gap-4 items-start">
                                    <img src="${spot.image}" alt="${spot.title}" class="w-full sm:w-24 h-24 object-cover rounded-lg shadow-sm border border-slate-200 flex-shrink-0 bg-slate-100" onerror="this.src='https://images.unsplash.com/photo-1488646953014-85cb44e25828?auto=format&fit=crop&w=400&q=80'">
                                    <div class="flex-grow">
                                        <h5 class="text-sm font-bold text-slate-800 mb-1">${spot.title}</h5>
                                        <p class="text-xs text-slate-600 mb-2">${spot.desc}</p>
                                        <div class="flex items-center text-[11px] text-slate-500">
                                            <i class="fa-solid fa-tag mr-1 text-brand-600"></i> 分类: ${spot.type}
                                        </div>
                                    </div>
                                </div>
                                ${altDropdownHtml}
                            </div>
                        </div>
                    `;
                });

                dayCard.innerHTML = `
                    <div class="bg-slate-100 px-5 py-3.5 border-b border-slate-200 flex justify-between items-center">
                        <div class="flex items-center space-x-3">
                            <span class="bg-brand-600 text-white font-bold text-xs px-2.5 py-1 rounded-lg">第 ${dayObj.day} 天</span>
                            <span class="text-xs font-medium text-slate-600"><i class="fa-solid fa-hotel mr-1 text-slate-400"></i> 推荐住宿：${dayObj.hotel.name}</span>
                        </div>
                        <button onclick="modifyDay(${dIdx})" class="text-xs text-brand-600 hover:text-brand-700 font-medium hover:underline bg-white px-2 py-1 rounded border border-slate-200 shadow-2xs">
                            <i class="fa-solid fa-pen-to-square mr-1"></i> 调整当天行程
                        </button>
                    </div>
                    <div class="p-5 space-y-4 bg-white">
                        <div class="text-xs text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-200/80 flex items-center">
                            <i class="fa-solid fa-train-subway mr-2 text-brand-600"></i>
                            <span><strong>交通与通勤:</strong> ${dayObj.commute}</span>
                        </div>
                        <div class="mt-4">
                            ${spotsHtml}
                        </div>
                    </div>
                `;

                container.appendChild(dayCard);
            });
        }

        function swapAlternative(dayIdx, spotIdx, altIdx) {
            let currentSpot = currentItineraryState.days[dayIdx].spots[spotIdx];
            let chosenAlt = currentSpot.alternatives[altIdx];

            let tempTitle = currentSpot.title;
            let tempDesc = currentSpot.desc;
            let tempCost = currentSpot.cost;

            currentSpot.title = chosenAlt.title;
            currentSpot.desc = chosenAlt.desc;
            currentSpot.cost = chosenAlt.cost;

            currentSpot.alternatives[altIdx] = {
                title: tempTitle,
                desc: tempDesc,
                cost: tempCost
            };

            renderItineraryUI();
        }

        function modifyDay(dIdx) {
            let newActivityName = prompt(`修改第 ${dIdx + 1} 天行程: 请输入要增加或替换的活动地点：`, "夜市游览与城市观景区");
            if (newActivityName) {
                currentItineraryState.days[dIdx].spots.push({
                    time: "08:00 PM",
                    title: newActivityName,
                    desc: "根据你的个性化需求新增的自定义项目。",
                    duration: "1.5 小时",
                    type: "自定义",
                    cost: 20,
                    image: "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=400&q=80"
                });
                renderItineraryUI();
            }
        }

        function resetApp() {
            currentItineraryState = null;
            document.getElementById('tripForm').reset();
            document.getElementById('emptyState').classList.remove('hidden');
            document.getElementById('budgetDashboard').classList.add('hidden');
            document.getElementById('itineraryContainer').classList.add('hidden');
            document.getElementById('togglePanelBtn').classList.add('hidden');
            if (isPanelCollapsed) toggleInputPanel();
            updateDaysBadge(3);
            updateAllocations('hotel');
            updateStyleSelection();
        }
    </script>
</body>
</html>