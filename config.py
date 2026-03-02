# config.py
# Owner and Admins
OWNER_ID = 8104850843
ADMIN_IDS = [5987905091]   # Owner ke alawa extra admins

# Force Join Channels
CHANNELS = [-1003090922367, -1003698567122, -1003672015073]
CHANNEL_LINKS = [
    "https://t.me/all_data_here",
    "https://t.me/osint_lookup",
    "https://t.me/legend_chats_osint"
]

# Log Channels (apni IDs yahan daalein)
LOG_CHANNELS = {
    'num': -1003482423742,
    'ifsc': -1003624886596,
    'email': -1003431549612,
    'gst': -1003634866992,
    'vehicle': -1003237155636,
    'pincode': -1003677285823,
    'instagram': -1003498414978,
    'github': -1003576017442,
    'pakistan': -1003663672738,
    'ip': -1003665811220,
    # New APIs (sab ek hi channel mein log ho rahe hain)
    'aadhar': -1003482423742,
    'ration': -1003643170105,
    'tg2num': -1003642820243,
    'vehicle_to_number': -1003237155636,
    'vehicle_chalan': -1003237155636,
    'ff_info': -1003588577282,
    'ff_ban': -1003521974255,
}

# APIs with per-API branding removal
APIS = {
    'num': {
        'url': 'https://num-free-rootx-jai-shree-ram-14-day.vercel.app/?key=lundkinger&number={}',
        'param': 'number',
        'log': LOG_CHANNELS['num'],
        'desc': 'Mobile number lookup',
        'extra_blacklist': [
            'Ruk ja bhencho itne m kya unlimited request lega?? Paid lena h to bolo 100-400₹ @Simpleguy444.'
        ]
    },
    'ifsc': {
        'url': 'https://abbas-apis.vercel.app/api/ifsc?ifsc={}',
        'param': 'ifsc',
        'log': LOG_CHANNELS['ifsc'],
        'desc': 'IFSC code lookup',
        'extra_blacklist': []
    },
    'email': {
        'url': 'https://abbas-apis.vercel.app/api/email?mail={}',
        'param': 'email',
        'log': LOG_CHANNELS['email'],
        'desc': 'Email validation & domain info',
        'extra_blacklist': []
    },
    'gst': {
        'url': 'https://api.b77bf911.workers.dev/gst?number={}',
        'param': 'gst',
        'log': LOG_CHANNELS['gst'],
        'desc': 'GST number lookup',
        'extra_blacklist': []
    },
    'vehicle': {
        'url': 'https://vehicle-info-aco-api.vercel.app/info?vehicle={}',
        'param': 'RC number',
        'log': LOG_CHANNELS['vehicle'],
        'desc': 'Vehicle registration details',
        'extra_blacklist': []
    },
    'pincode': {
        'url': 'https://api.postalpincode.in/pincode/{}',
        'param': 'pincode',
        'log': LOG_CHANNELS['pincode'],
        'desc': 'Pincode details',
        'extra_blacklist': []
    },
    'instagram': {
        'url': 'https://mkhossain.alwaysdata.net/instanum.php?username={}',
        'param': 'username',
        'log': LOG_CHANNELS['instagram'],
        'desc': 'Instagram user info',
        'extra_blacklist': []
    },
    'github': {
        'url': 'https://abbas-apis.vercel.app/api/github?username={}',
        'param': 'username',
        'log': LOG_CHANNELS['github'],
        'desc': 'GitHub user info',
        'extra_blacklist': []
    },
    'pakistan': {
        'url': 'https://abbas-apis.vercel.app/api/pakistan?number={}',
        'param': 'number',
        'log': LOG_CHANNELS['pakistan'],
        'desc': 'Pakistan mobile number lookup',
        'extra_blacklist': []
    },
    'ip': {
        'url': 'https://abbas-apis.vercel.app/api/ip?ip={}',
        'param': 'ip',
        'log': LOG_CHANNELS['ip'],
        'desc': 'IP address geolocation',
        'extra_blacklist': []
    },
    # New APIs
    'aadhar': {
        'url': 'https://abduldevstorebot.up.railway.app/api/v1?key=ak_78237c25513cd1ffa6155a0f725d9cec&match={}',
        'param': 'aadhaar number',
        'log': LOG_CHANNELS['aadhar'],
        'desc': 'Aadhaar info lookup',
        'extra_blacklist': ['meta']
    },
    'ration': {
        'url': 'https://aadhar-to-family-demo.vercel.app/?key=DEMOOOOOO&id={}',
        'param': 'aadhaar number',
        'log': LOG_CHANNELS['ration'],
        'desc': 'Ration info lookup',
        'extra_blacklist': ['attempt', 'cached', 'owner', 'proxyUsed']
    },
    'tg2num': {
        'url': 'https://tg2num-owner-api.vercel.app/?userid={}',
        'param': 'telegram user ID',
        'log': LOG_CHANNELS['tg2num'],
        'desc': 'Telegram to number lookup',
        'extra_blacklist': ['credit', 'channel', 'validity']
    },
    # Fixed Vehicle APIs
    'vehicle_to_number': {
        'url': 'https://vehicle-apiovttr.vercel.app/api.php?rc={}',
        'param': 'vehicle number',
        'log': LOG_CHANNELS['vehicle_to_number'],
        'desc': 'Vehicle to number lookup (owner details)',
        'extra_blacklist': []
    },
    'vehicle_chalan': {
        'url': 'https://api.b77bf911.workers.dev/vehicle?registration={}',
        'param': 'vehicle number',
        'log': LOG_CHANNELS['vehicle_chalan'],
        'desc': 'Vehicle challan lookup',
        'extra_blacklist': []
    },
    'ff_info': {
        'url': 'https://abbas-apis.vercel.app/api/ff-info?uid={}',
        'param': 'Free Fire UID',
        'log': LOG_CHANNELS['ff_info'],
        'desc': 'Free Fire player info',
        'extra_blacklist': []
    },
    'ff_ban': {
        'url': 'https://abbas-apis.vercel.app/api/ff-ban?uid={}',
        'param': 'Free Fire UID',
        'log': LOG_CHANNELS['ff_ban'],
        'desc': 'Free Fire ban check',
        'extra_blacklist': []
    },
}

# Developer branding
DEV_USERNAME = "@Nullprotocol_X"
POWERED_BY = "NULL PROTOCOL"

# Backup channel
BACKUP_CHANNEL = -1003740236326
