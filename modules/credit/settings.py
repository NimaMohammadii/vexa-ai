# پلن‌های نمونه به تومان (صرفاً برای نمایش؛ ملاک نهایی، رسید پرداخت است)
PAYMENT_PLANS = [
    {"title": " 600 → 99,000T", "amount_toman": 99_000, "credits": 600},
    {"title": " 2899 → 180,000T", "amount_toman": 180_000, "credits": 2899},
    {"title": " 6100 → 295,000T", "amount_toman": 295_000, "credits": 6100},
    {"title": " 9200 → 470,000T", "amount_toman": 470_000, "credits": 9200},
    {"title": " 15K → 782,000T", "amount_toman": 782_000, "credits": 15000},

    {"title": " 21K → 999,000T", "amount_toman": 999_000, "credits": 21000},
    {"title": " 46K → 2,600,000T", "amount_toman": 2_600_000, "credits": 46000},
    {"title": " 88K → 3,999,000T", "amount_toman": 3_999_000, "credits": 88000},

    {"title": " 120K → 5,390,000T", "amount_toman": 5_390_000, "credits": 120000},
    {"title": " 150K → 6,880,000T", "amount_toman": 6_880_000, "credits": 150000},
]

# بسته‌های Telegram Stars
STAR_PACKAGES = [
    {"stars": 250, "credits": 10000, "title": "• Starter "},
    {"stars": 1000, "credits": 40000, "title": "🎯 Creator ", "plan_name": "creator"},
    {"stars": 3000, "credits": 120000, "title": "⚡️ Pro ", "plan_name": "pro"},
    {"stars": 6999, "credits": 300000, "title": "👑 Studio", "plan_name": "studio"},
]

# زمان انتظار برای ارسال رسید (ثانیه)
RECEIPT_WAIT_TTL = 10 * 60  # 10 دقیقه
