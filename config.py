# config.py
# Owner and Admins (Hardcoded)
OWNER_ID = 8104850843
ADMIN_IDS = [5987905091]   # Owner ke alawa extra admins (owner ID already included as owner)

# Force Join Channels (IDs and Links)
CHANNELS = [-1003090922367, -1003698567122, -1003672015073]
CHANNEL_LINKS = [
    "https://t.me/all_data_here",
    "https://t.me/osint_lookup",
    "https://t.me/legend_chats_osint"
]

# Log Channels (Hardcoded IDs)
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
}

# APIs with per-API branding removal (extra_blacklist)
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
}

# Developer branding (flattened)
DEV_USERNAME = "@Nullprotocol_X"
POWERED_BY = "NULL PROTOCOL"

# Backup channel (hardcoded)
BACKUP_CHANNEL = -1003740236326
