# database.py
import asyncpg
import os
import time
import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Any

DATABASE_URL = os.getenv("DATABASE_URL")
# Connection pool global variable
_pool = None

async def get_pool():
    """Get or create connection pool"""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60,
            max_inactive_connection_lifetime=300
        )
    return _pool

def parse_time_string(time_str):
    """Parse time string like '30m', '2h', '1h30m' into minutes."""
    if not time_str or str(time_str).lower() == 'none':
        return None
    time_str = str(time_str).lower()
    total_minutes = 0
    hour_match = re.search(r'(\d+)h', time_str)
    if hour_match:
        total_minutes += int(hour_match.group(1)) * 60
    minute_match = re.search(r'(\d+)m', time_str)
    if minute_match:
        total_minutes += int(minute_match.group(1))
    if not hour_match and not minute_match and time_str.isdigit():
        total_minutes = int(time_str)
    return total_minutes if total_minutes > 0 else None

async def init_db():
    """Initialize database tables"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Users table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username TEXT,
                credits INTEGER DEFAULT 5,
                joined_date TEXT,
                referrer_id BIGINT,
                is_banned INTEGER DEFAULT 0,
                total_earned INTEGER DEFAULT 0,
                last_active TEXT,
                is_premium INTEGER DEFAULT 0,
                premium_expiry TEXT
            )
        """)
        
        # Admins table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id BIGINT PRIMARY KEY,
                level TEXT DEFAULT 'admin',
                added_by BIGINT,
                added_date TEXT
            )
        """)
        
        # Redeem codes table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS redeem_codes (
                code TEXT PRIMARY KEY,
                amount INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expiry_minutes INTEGER,
                created_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Redeem logs
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS redeem_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                code TEXT,
                claimed_date TEXT,
                UNIQUE(user_id, code)
            )
        """)
        
        # Stats table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                date TEXT PRIMARY KEY,
                total_users INTEGER DEFAULT 0,
                active_users INTEGER DEFAULT 0,
                total_lookups INTEGER DEFAULT 0,
                credits_used INTEGER DEFAULT 0
            )
        """)
        
        # Lookup logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS lookup_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                api_type TEXT,
                input_data TEXT,
                result TEXT,
                lookup_date TEXT
            )
        """)
        
        # Premium plans table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS premium_plans (
                plan_id TEXT PRIMARY KEY,
                price INTEGER,
                duration_days INTEGER,
                description TEXT
            )
        """)
        
        # Insert default plans if not exist
        await conn.execute("""
            INSERT INTO premium_plans (plan_id, price, duration_days, description)
            VALUES ('weekly', 69, 7, 'Weekly Plan')
            ON CONFLICT (plan_id) DO NOTHING
        """)
        await conn.execute("""
            INSERT INTO premium_plans (plan_id, price, duration_days, description)
            VALUES ('monthly', 199, 30, 'Monthly Plan')
            ON CONFLICT (plan_id) DO NOTHING
        """)
        
        # Discount codes for plans
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                code TEXT PRIMARY KEY,
                plan_id TEXT,
                discount_percent INTEGER,
                max_uses INTEGER,
                current_uses INTEGER DEFAULT 0,
                expiry_minutes INTEGER,
                created_date TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)
        
        # Create indexes for better performance
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_referrer ON users(referrer_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_lookup_logs_user ON lookup_logs(user_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_lookup_logs_date ON lookup_logs(lookup_date)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_redeem_logs_user ON redeem_logs(user_id)")

# ---------- User functions ----------
async def get_user(user_id: int) -> Optional[Tuple]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

async def add_user(user_id: int, username: str, referrer_id: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if user exists
        exists = await conn.fetchval("SELECT user_id FROM users WHERE user_id = $1", user_id)
        if exists:
            return
        
        credits = 5
        current_time = str(time.time())
        await conn.execute("""
            INSERT INTO users 
            (user_id, username, credits, joined_date, referrer_id, is_banned, total_earned, last_active, is_premium, premium_expiry)
            VALUES ($1, $2, $3, $4, $5, 0, 0, $4, 0, NULL)
        """, user_id, username, credits, current_time, referrer_id)

async def update_credits(user_id: int, amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if amount > 0:
            await conn.execute("""
                UPDATE users 
                SET credits = credits + $1, total_earned = total_earned + $1 
                WHERE user_id = $2
            """, amount, user_id)
        else:
            await conn.execute("UPDATE users SET credits = credits + $1 WHERE user_id = $2", amount, user_id)

async def set_ban_status(user_id: int, status: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET is_banned = $1 WHERE user_id = $2", status, user_id)

async def get_all_users() -> List[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT user_id FROM users")
        return [row['user_id'] for row in rows]

async def get_user_by_username(username: str) -> Optional[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT user_id FROM users WHERE username = $1", username)
        return row['user_id'] if row else None

async def update_last_active(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET last_active = $1 WHERE user_id = $2", 
                         datetime.now().isoformat(), user_id)

# ---------- Premium functions ----------
async def set_user_premium(user_id: int, days: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if days:
            expiry = (datetime.now() + timedelta(days=days)).isoformat()
            await conn.execute("UPDATE users SET is_premium = 1, premium_expiry = $1 WHERE user_id = $2", 
                             expiry, user_id)
        else:
            await conn.execute("UPDATE users SET is_premium = 1, premium_expiry = NULL WHERE user_id = $1", 
                             user_id)

async def remove_user_premium(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET is_premium = 0, premium_expiry = NULL WHERE user_id = $1", user_id)

async def is_user_premium(user_id: int) -> bool:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT is_premium, premium_expiry FROM users WHERE user_id = $1", user_id)
        if not row:
            return False
        is_premium, expiry = row['is_premium'], row['premium_expiry']
        if not is_premium:
            return False
        if expiry:
            expiry_dt = datetime.fromisoformat(expiry)
            if expiry_dt < datetime.now():
                await remove_user_premium(user_id)
                return False
        return True

async def get_premium_users() -> List[Tuple]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, premium_expiry FROM users WHERE is_premium = 1")

# ---------- Premium plans functions ----------
async def get_plan_price(plan_id: str) -> Optional[int]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT price FROM premium_plans WHERE plan_id = $1", plan_id)
        return row['price'] if row else None

async def update_plan_price(plan_id: str, price: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE premium_plans SET price = $1 WHERE plan_id = $2", price, plan_id)

# ---------- Discount codes ----------
async def create_discount_code(code: str, plan_id: str, discount_percent: int, max_uses: int, expiry_minutes: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO discount_codes
            (code, plan_id, discount_percent, max_uses, expiry_minutes, created_date, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, 1)
            ON CONFLICT (code) DO UPDATE SET
                plan_id = EXCLUDED.plan_id,
                discount_percent = EXCLUDED.discount_percent,
                max_uses = EXCLUDED.max_uses,
                expiry_minutes = EXCLUDED.expiry_minutes,
                created_date = EXCLUDED.created_date,
                is_active = 1
        """, code, plan_id, discount_percent, max_uses, expiry_minutes, datetime.now().isoformat())

async def redeem_discount_code(user_id: int, code: str, plan_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check code validity
        row = await conn.fetchrow("""
            SELECT discount_percent, max_uses, current_uses, expiry_minutes, created_date, is_active 
            FROM discount_codes WHERE code = $1
        """, code)
        
        if not row:
            return "invalid"
        
        discount_percent, max_uses, current_uses, expiry_minutes, created_date, is_active = row
        
        if not is_active:
            return "inactive"
        if current_uses >= max_uses:
            return "limit_reached"
        if expiry_minutes:
            created_dt = datetime.fromisoformat(created_date)
            if datetime.now() > created_dt + timedelta(minutes=expiry_minutes):
                return "expired"
        
        # Update usage count
        await conn.execute("UPDATE discount_codes SET current_uses = current_uses + 1 WHERE code = $1", code)
        return discount_percent

# ---------- Redeem codes (regular) ----------
async def create_redeem_code(code: str, amount: int, max_uses: int, expiry_minutes: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO redeem_codes
            (code, amount, max_uses, expiry_minutes, created_date, is_active)
            VALUES ($1, $2, $3, $4, $5, 1)
            ON CONFLICT (code) DO UPDATE SET
                amount = EXCLUDED.amount,
                max_uses = EXCLUDED.max_uses,
                expiry_minutes = EXCLUDED.expiry_minutes,
                created_date = EXCLUDED.created_date,
                is_active = 1
        """, code, amount, max_uses, expiry_minutes, datetime.now().isoformat())

async def redeem_code_db(user_id: int, code: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Check if already claimed
        claimed = await conn.fetchval("SELECT 1 FROM redeem_logs WHERE user_id = $1 AND code = $2", user_id, code)
        if claimed:
            return "already_claimed"
        
        # Get code details
        row = await conn.fetchrow("""
            SELECT amount, max_uses, current_uses, expiry_minutes, created_date, is_active 
            FROM redeem_codes WHERE code = $1
        """, code)
        
        if not row:
            return "invalid"
        
        amount, max_uses, current_uses, expiry_minutes, created_date, is_active = row
        
        if not is_active:
            return "inactive"
        if current_uses >= max_uses:
            return "limit_reached"
        if expiry_minutes:
            created_dt = datetime.fromisoformat(created_date)
            if datetime.now() > created_dt + timedelta(minutes=expiry_minutes):
                return "expired"
        
        # Use transaction to update both tables
        async with conn.transaction():
            await conn.execute("UPDATE redeem_codes SET current_uses = current_uses + 1 WHERE code = $1", code)
            await conn.execute("UPDATE users SET credits = credits + $1, total_earned = total_earned + $1 WHERE user_id = $2", 
                             amount, user_id)
            await conn.execute("INSERT INTO redeem_logs (user_id, code, claimed_date) VALUES ($1, $2, $3)", 
                             user_id, code, datetime.now().isoformat())
        
        return amount

async def get_all_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT code, amount, max_uses, current_uses, expiry_minutes, created_date, is_active 
            FROM redeem_codes ORDER BY created_date DESC
        """)

async def deactivate_code(code: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE redeem_codes SET is_active = 0 WHERE code = $1", code)

async def get_active_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT code, amount, max_uses, current_uses FROM redeem_codes WHERE is_active = 1")

async def get_inactive_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT code, amount, max_uses, current_uses FROM redeem_codes WHERE is_active = 0")

async def get_expired_codes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT code, amount, current_uses, max_uses, expiry_minutes, created_date
            FROM redeem_codes
            WHERE is_active = 1 AND expiry_minutes IS NOT NULL AND expiry_minutes > 0
            AND (created_date::timestamp + (expiry_minutes || ' minutes')::interval) < NOW()
        """)

async def delete_redeem_code(code: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM redeem_codes WHERE code = $1", code)

# ---------- Lookup logs ----------
async def log_lookup(user_id: int, api_type: str, input_data: str, result: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO lookup_logs (user_id, api_type, input_data, result, lookup_date)
            VALUES ($1, $2, $3, $4, $5)
        """, user_id, api_type, input_data[:500], str(result)[:1000], datetime.now().isoformat())

async def get_user_lookups(user_id: int, limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT api_type, input_data, lookup_date
            FROM lookup_logs
            WHERE user_id = $1
            ORDER BY lookup_date DESC
            LIMIT $2
        """, user_id, limit)

async def get_total_lookups() -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM lookup_logs")

async def get_lookup_stats(user_id: int = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if user_id:
            return await conn.fetch("SELECT api_type, COUNT(*) FROM lookup_logs WHERE user_id = $1 GROUP BY api_type", user_id)
        else:
            return await conn.fetch("SELECT api_type, COUNT(*) FROM lookup_logs GROUP BY api_type")

# ---------- Statistics ----------
async def get_bot_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
        active_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE credits > 0")
        total_credits = await conn.fetchval("SELECT COALESCE(SUM(credits), 0) FROM users")
        credits_distributed = await conn.fetchval("SELECT COALESCE(SUM(total_earned), 0) FROM users")
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_credits': total_credits,
            'credits_distributed': credits_distributed
        }

async def get_user_stats(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM users WHERE referrer_id = $1) as referrals,
                (SELECT COUNT(*) FROM redeem_logs WHERE user_id = $1) as codes_claimed,
                (SELECT COALESCE(SUM(amount), 0) FROM redeem_logs rl JOIN redeem_codes rc ON rl.code = rc.code WHERE rl.user_id = $1) as total_from_codes
        """, user_id)

async def get_recent_users(limit: int = 20):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, joined_date FROM users ORDER BY joined_date DESC LIMIT $1", limit)

async def get_top_referrers(limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("""
            SELECT referrer_id, COUNT(*) as referrals
            FROM users
            WHERE referrer_id IS NOT NULL
            GROUP BY referrer_id
            ORDER BY referrals DESC
            LIMIT $1
        """, limit)

async def get_users_in_range(start_date: str, end_date: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, credits, joined_date FROM users WHERE joined_date BETWEEN $1 AND $2", 
                              start_date, end_date)

async def get_leaderboard(limit: int = 10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, credits FROM users WHERE is_banned = 0 ORDER BY credits DESC LIMIT $1", limit)

async def get_low_credit_users():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, credits FROM users WHERE credits <= 5 ORDER BY credits ASC")

async def get_inactive_users(days: int = 30):
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, username, last_active FROM users WHERE last_active < $1 AND is_banned = 0 ORDER BY last_active ASC", cutoff)

# ---------- Admin management ----------
async def add_admin(user_id: int, level: str = 'admin'):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO admins (user_id, level) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET level = EXCLUDED.level", 
                         user_id, level)

async def remove_admin(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM admins WHERE user_id = $1", user_id)

async def get_all_admins():
    pool = await get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch("SELECT user_id, level FROM admins")

async def is_admin(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT level FROM admins WHERE user_id = $1", user_id)
        return row['level'] if row else None

# ---------- Utility ----------
async def search_users(query: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Try to parse as integer for user_id search
        try:
            user_id = int(query)
            return await conn.fetch("SELECT user_id, username, credits FROM users WHERE user_id = $1", user_id)
        except ValueError:
            # Search by username
            return await conn.fetch("SELECT user_id, username, credits FROM users WHERE username ILIKE $1 LIMIT 20", 
                                  f"%{query}%")

async def delete_user(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("DELETE FROM redeem_logs WHERE user_id = $1", user_id)
            await conn.execute("UPDATE users SET referrer_id = NULL WHERE referrer_id = $1", user_id)
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)

async def reset_user_credits(user_id: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("UPDATE users SET credits = 0 WHERE user_id = $1", user_id)

async def bulk_update_credits(user_ids: List[int], amount: int):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            for uid in user_ids:
                if amount > 0:
                    await conn.execute("UPDATE users SET credits = credits + $1, total_earned = total_earned + $1 WHERE user_id = $2", 
                                     amount, uid)
                else:
                    await conn.execute("UPDATE users SET credits = credits + $1 WHERE user_id = $2", amount, uid)

# ---------- Close pool function (call on shutdown) ----------
async def close_db():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
