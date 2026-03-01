# config.py
import os

# ---------- OWNER & ADMINS ----------
# Hardcoded values (ya environment variables se bhi le sakte ho)
OWNER_ID = int(os.getenv("OWNER_ID", 8104850843))  # Replace with your owner ID
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "5987905091").split(",")]  # Extra admins

# ---------- FORCE JOIN CHANNELS ----------
# Channel IDs (negative values for private/supergroups)
CHANNELS = [
    int(os.getenv("CHANNEL1", -1003090922367)),
    int(os.getenv("CHANNEL2", -1003698567122)),
    int(os.getenv("CHANNEL3", -1003672015073))
]

# Channel invite links
CHANNEL_LINKS = [
    os.getenv("CHANNEL_LINK1", "https://t.me/all_data_here"),
    os.getenv("CHANNEL_LINK2", "https://t.me/osint_lookup"),
    os.getenv("CHANNEL_LINK3", "https://t.me/legend_chats_osint")
]

# ---------- APIS ----------
# Har API ki poori info – yahan kuch bhi change mat karna agar APIs kaam kar rahe hain
APIS = {
    'num': {
        'url': 'https://num-free-rootx-jai-shree-ram-14-day.vercel.app/?key=lundkinger&number={}',
        'param': 'number',
        'log_channel': -1003482423742,
        'desc': 'Mobile number lookup',
        'blacklist': [
            'Ruk ja bhencho itne m kya unlimited request lega?? Paid lena h to bolo 100-400₹ @Simpleguy444.'
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

# ---------- BRANDING ----------
# Developer branding (response mein add hoga)
DEV_USERNAME = os.getenv("DEV_USERNAME", "@Nullprotocol_X")
POWERED_BY = os.getenv("POWERED_BY", "NULL PROTOCOL")

# ---------- BACKUP CHANNEL ----------
# Daily backup yahan bhejna hai
BACKUP_CHANNEL = int(os.getenv("BACKUP_CHANNEL", -1003740236326))
