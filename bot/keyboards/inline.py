"""
Inline Keyboards

All inline keyboard builders for the Telegram bot.
Uses index-based callbacks to avoid Telegram's 64-byte callback_data limit.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("📊 Positions", callback_data="positions"),
            InlineKeyboardButton("💰 Balance", callback_data="balance")
        ],
        [
            InlineKeyboardButton("🛒 Buy", callback_data="buy"),
            InlineKeyboardButton("🔍 Search", callback_data="search")
        ],
        [
            InlineKeyboardButton("⭐ Favorites", callback_data="favorites"),
            InlineKeyboardButton("🔥 Hot Markets", callback_data="hot")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def positions_keyboard(positions: list) -> InlineKeyboardMarkup:
    """Keyboard for positions list - uses index reference."""
    keyboard = []
    
    for i, pos in enumerate(positions[:10]):  # Max 10 positions
        pnl_emoji = "📈" if pos.pnl >= 0 else "📉"
        short_question = pos.market_question[:25] + "..." if len(pos.market_question) > 25 else pos.market_question
        
        keyboard.append([
            InlineKeyboardButton(
                f"{pnl_emoji} {short_question}",
                callback_data=f"pos_{i}"  # Index-based
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Menu", callback_data="menu"),
        InlineKeyboardButton("🔄 Refresh", callback_data="positions")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def position_detail_keyboard(pos_index: int, has_shares: bool = True) -> InlineKeyboardMarkup:
    """Keyboard for position details with sell options - uses index."""
    keyboard = []
    
    if has_shares:
        keyboard.append([
            InlineKeyboardButton("💯 Sell 100%", callback_data=f"sell_{pos_index}_100"),
            InlineKeyboardButton("50%", callback_data=f"sell_{pos_index}_50")
        ])
        keyboard.append([
            InlineKeyboardButton("25%", callback_data=f"sell_{pos_index}_25"),
            InlineKeyboardButton("✏️ Custom", callback_data=f"sell_{pos_index}_c")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Positions", callback_data="positions"),
        InlineKeyboardButton("⭐ Favorite", callback_data=f"fav_a_{pos_index}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def sell_confirm_keyboard(pos_index: int, percent: int) -> InlineKeyboardMarkup:
    """Confirm sell action keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm Sell", callback_data=f"csell_{pos_index}_{percent}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"pos_{pos_index}")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def category_keyboard() -> InlineKeyboardMarkup:
    """Category selection for buying."""
    keyboard = [
        [
            InlineKeyboardButton("🏈 Sports", callback_data="cat_sports"),
            InlineKeyboardButton("🗳️ Politics", callback_data="cat_politics")
        ],
        [
            InlineKeyboardButton("🪙 Crypto", callback_data="cat_crypto"),
            InlineKeyboardButton("🎬 Entertainment", callback_data="cat_ent")
        ],
        [InlineKeyboardButton("🔙 Menu", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


def sports_keyboard() -> InlineKeyboardMarkup:
    """Sports selection keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("🏏 Cricket", callback_data="sp_cricket"),
            InlineKeyboardButton("⚽ Football", callback_data="sp_football")
        ],
        [
            InlineKeyboardButton("🏀 NBA", callback_data="sp_nba"),
            InlineKeyboardButton("🎾 Tennis", callback_data="sp_tennis")
        ],
        [
            InlineKeyboardButton("🥊 UFC/MMA", callback_data="sp_ufc"),
            InlineKeyboardButton("🏈 NFL", callback_data="sp_nfl")
        ],
        [InlineKeyboardButton("🔙 Categories", callback_data="buy")]
    ]
    return InlineKeyboardMarkup(keyboard)


def markets_keyboard(markets: list, page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    """Keyboard for market selection - uses index reference."""
    keyboard = []
    
    start = page * page_size
    end = start + page_size
    page_markets = markets[start:end]
    
    for i, market in enumerate(page_markets):
        idx = start + i  # Global index in markets list
        short_q = market.question[:30] + "..." if len(market.question) > 30 else market.question
        keyboard.append([
            InlineKeyboardButton(
                f"📊 {short_q}",
                callback_data=f"mkt_{idx}"  # Index-based, not condition_id
            )
        ])
    
    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"pg_{page-1}"))
    if end < len(markets):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"pg_{page+1}"))
    
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="buy")])
    
    return InlineKeyboardMarkup(keyboard)


def outcome_keyboard() -> InlineKeyboardMarkup:
    """Yes/No outcome selection - market already in context."""
    keyboard = [
        [
            InlineKeyboardButton("✅ YES", callback_data="out_yes"),
            InlineKeyboardButton("❌ NO", callback_data="out_no")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="buy")]
    ]
    return InlineKeyboardMarkup(keyboard)


def amount_keyboard() -> InlineKeyboardMarkup:
    """Amount selection for buying - token already in context."""
    keyboard = [
        [
            InlineKeyboardButton("$10", callback_data="amt_10"),
            InlineKeyboardButton("$25", callback_data="amt_25"),
            InlineKeyboardButton("$50", callback_data="amt_50")
        ],
        [
            InlineKeyboardButton("$100", callback_data="amt_100"),
            InlineKeyboardButton("✏️ Custom", callback_data="amt_c")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="buy")]
    ]
    return InlineKeyboardMarkup(keyboard)


def buy_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm buy action keyboard - all data in context."""
    keyboard = [
        [
            InlineKeyboardButton("🚀 EXECUTE BUY", callback_data="exec_buy"),
            InlineKeyboardButton("❌ Cancel", callback_data="buy")
        ],
        [
            InlineKeyboardButton("⭐ Add Favorite", callback_data="fav_add")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def favorites_keyboard(favorites: list) -> InlineKeyboardMarkup:
    """Favorites list keyboard - uses index."""
    keyboard = []
    
    for i, fav in enumerate(favorites[:10]):
        short_label = fav.label[:22] + "..." if len(fav.label) > 22 else fav.label
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {short_label} ({fav.outcome})",
                callback_data=f"fv_{i}"  # Index-based
            ),
            InlineKeyboardButton("🗑️", callback_data=f"fd_{i}")
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Menu", callback_data="menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def search_results_keyboard(markets: list) -> InlineKeyboardMarkup:
    """Search results keyboard - uses index."""
    keyboard = []
    
    for i, market in enumerate(markets[:8]):
        short_q = market.question[:28] + "..." if len(market.question) > 28 else market.question
        keyboard.append([
            InlineKeyboardButton(
                f"📊 {short_q}",
                callback_data=f"mkt_{i}"  # Index-based
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Menu", callback_data="menu"),
        InlineKeyboardButton("🔍 New Search", callback_data="search")
    ])
    
    return InlineKeyboardMarkup(keyboard)
