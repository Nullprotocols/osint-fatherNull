# Owner and Admins (Hardcoded)
# Apna Telegram user ID yahan daalo (numeric ID)
OWNER_ID = 8104850843   # <-- YAHAN APNA ID DAALO

# Extra admin IDs (owner ke alawa)
ADMIN_IDS = [5987905091]   # <-- YAHAN ADMIN IDS DAALO

# Force Join Channels (Channel IDs and Invite Links)
CHANNELS = [
    -1003090922367,
    -1003698567122,
    -1003672015073
]

CHANNEL_LINKS = [
    "https://t.me/all_data_here",
    "https://t.me/osint_lookup",
    "https://t.me/legend_chats_osint"
]

# APIs – Har API ki poori info (URL, param, log channel, blacklist)
APIS = {
    'num': {
        'url': 'https://num-free-rootx-jai-shree-ram-14-day.vercel.app/?key=lundkinger&number={}',
        'param': 'number',
        'log_channel': -1003482423742,
        'desc': 'Mobile number lookup',
        'blacklist': [
            'Ruk ja bhencho itne m kya unlimited request lega?? Paid lena h to bolo 100-400₹ @Simpleguy444'
        ]
    },
    'ifsc': {
        'url': 'https://abbas-apis.vercel.app/api/ifsc?ifsc={}',
        'param': 'ifsc',
        'log_channel': -1003624886596,
        'desc': 'IFSC code lookup',
        'blacklist': []
    },
    'email': {
        'url': 'https://abbas-apis.vercel.app/api/email?mail={}',
        'param': 'email',
        'log_channel': -1003431549612,
        'desc': 'Email validation & domain info',
        'blacklist': []
    },
    'gst': {
        'url': 'https://api.b77bf911.workers.dev/gst?number={}',
        'param': 'gst',
        'log_channel': -1003634866992,
        'desc': 'GST number lookup',
        'blacklist': []
    },
    'vehicle': {
        'url': 'https://vehicle-info-aco-api.vercel.app/info?vehicle={}',
        'param': 'vehicle',
        'log_channel': -1003237155636,
        'desc': 'Vehicle RC details',
        'blacklist': []
    },
    'pincode': {
        'url': 'https://api.postalpincode.in/pincode/{}',
        'param': 'pincode',
        'log_channel': -1003677285823,
        'desc': 'Pincode details',
        'blacklist': []
    },
    'instagram': {
        'url': 'https://mkhossain.alwaysdata.net/instanum.php?username={}',
        'param': 'username',
        'log_channel': -1003498414978,
        'desc': 'Instagram user info',
        'blacklist': []
    },
    'github': {
        'url': 'https://abbas-apis.vercel.app/api/github?username={}',
        'param': 'username',
        'log_channel': -1003576017442,
        'desc': 'GitHub user info',
        'blacklist': []
    },
    'pakistan': {
        'url': 'https://abbas-apis.vercel.app/api/pakistan?number={}',
        'param': 'number',
        'log_channel': -1003663672738,
        'desc': 'Pakistan mobile number lookup',
        'blacklist': []
    },
    'ip': {
        'url': 'https://abbas-apis.vercel.app/api/ip?ip={}',
        'param': 'ip',
        'log_channel': -1003665811220,
        'desc': 'IP address geolocation',
        'blacklist': []
    },
    'ff_info': {
        'url': 'https://abbas-apis.vercel.app/api/ff-info?uid={}',
        'param': 'uid',
        'log_channel': -1003588577282,
        'desc': 'Free Fire player info',
        'blacklist': []
    },
    'ff_ban': {
        'url': 'https://abbas-apis.vercel.app/api/ff-ban?uid={}',
        'param': 'uid',
        'log_channel': -1003521974255,
        'desc': 'Free Fire ban check',
        'blacklist': []
    },
}

# Developer branding (response mein add hoga)
DEV_USERNAME = "@Nullprotocol_X"
POWERED_BY = "NULL PROTOCOL"

# Backup channel (daily backup yahan bhejna hai)
BACKUP_CHANNEL = -1003740236326
