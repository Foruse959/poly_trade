"""
Trading Handlers

Handles /buy command with category selection flow.
Uses index-based callbacks with context storage.
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from core.polymarket_client import get_polymarket_client
from bot.keyboards.inline import (
    category_keyboard, sports_keyboard, markets_keyboard,
    outcome_keyboard, amount_keyboard, buy_confirm_keyboard
)


# Conversation states
CUSTOM_AMOUNT = 0


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /buy command - start buy flow."""
    text = """
🛒 <b>Buy Position</b>

Select a category to browse markets:
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=category_keyboard()
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=category_keyboard()
        )


async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle category selection."""
    query = update.callback_query
    await query.answer()
    
    category = query.data.split('_')[1]  # cat_sports -> sports
    context.user_data['category'] = category
    
    if category == 'sports':
        text = """
🏆 <b>Select Sport</b>

Choose a sport to browse markets:
"""
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=sports_keyboard()
        )
    else:
        # For non-sports, search directly
        client = get_polymarket_client()
        cat_query = 'entertainment' if category == 'ent' else category
        markets = await client.search_markets(cat_query, limit=15)
        context.user_data['markets'] = markets
        
        if not markets:
            await query.edit_message_text(
                f"📭 No active {category} markets found.\n\nTry /search <query>",
                reply_markup=category_keyboard()
            )
            return
        
        text = f"""
📊 <b>{category.title()} Markets</b>

Found {len(markets)} markets:
"""
        await query.edit_message_text(
            text,
            parse_mode='HTML',
            reply_markup=markets_keyboard(markets)
        )


async def sport_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sport selection."""
    query = update.callback_query
    await query.answer("🔍 Loading markets...")
    
    sport = query.data.split('_')[1]  # sp_cricket -> cricket
    context.user_data['sport'] = sport
    
    sport_emoji = Config.get_sport_emoji(sport)
    
    client = get_polymarket_client()
    markets = await client.get_sports_markets(sport=sport, limit=20)
    context.user_data['markets'] = markets
    
    if not markets:
        # Try broader search
        markets = await client.search_markets(sport, limit=15)
        context.user_data['markets'] = markets
    
    if not markets:
        await query.edit_message_text(
            f"📭 No active {sport} markets found.\n\nTry /search <query>",
            reply_markup=sports_keyboard()
        )
        return
    
    text = f"""
{sport_emoji} <b>{sport.upper()} Markets</b>

Found {len(markets)} active markets:
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=markets_keyboard(markets)
    )


async def page_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pagination."""
    query = update.callback_query
    await query.answer()
    
    page = int(query.data.split('_')[1])  # pg_1 -> 1
    markets = context.user_data.get('markets', [])
    
    sport = context.user_data.get('sport', 'sports')
    sport_emoji = Config.get_sport_emoji(sport)
    
    text = f"""
{sport_emoji} <b>{sport.upper()} Markets</b>

Found {len(markets)} active markets (Page {page + 1}):
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=markets_keyboard(markets, page=page)
    )


async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market selection - show Yes/No options."""
    query = update.callback_query
    await query.answer()
    
    # Get market by index from context
    idx = int(query.data.split('_')[1])  # mkt_0 -> 0
    markets = context.user_data.get('markets', [])
    
    if idx >= len(markets):
        await query.edit_message_text("⚠️ Market not found. Try again with /buy")
        return
    
    market = markets[idx]
    context.user_data['selected_market'] = market
    context.user_data['selected_market_index'] = idx
    
    # Calculate implied probabilities
    yes_prob = market.yes_price * 100
    no_prob = market.no_price * 100
    
    text = f"""
📊 <b>Market Details</b>

📋 <b>{market.question}</b>

💹 <b>Prices:</b>
   ✅ YES: {yes_prob:.0f}¢ (${market.yes_price:.2f})
   ❌ NO: {no_prob:.0f}¢ (${market.no_price:.2f})

📈 <b>Volume:</b> ${market.volume:,.0f}

<b>Select outcome to buy:</b>
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=outcome_keyboard()
    )


async def outcome_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle outcome selection - show amount options."""
    query = update.callback_query
    await query.answer()
    
    outcome = query.data.split('_')[1].upper()  # out_yes -> YES
    
    market = context.user_data.get('selected_market')
    if not market:
        await query.edit_message_text("⚠️ Market not found. Start over with /buy")
        return
    
    # Get the correct token and price
    if outcome == 'YES':
        token_id = market.yes_token_id
        price = market.yes_price
    else:
        token_id = market.no_token_id
        price = market.no_price
    
    context.user_data['selected_token_id'] = token_id
    context.user_data['selected_outcome'] = outcome
    context.user_data['selected_price'] = price
    
    text = f"""
💵 <b>Enter Amount</b>

📋 {market.question}
🎯 <b>Buying:</b> {outcome} @ ${price:.2f}

<b>Select amount (USD):</b>
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=amount_keyboard()
    )


async def amount_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount selection - show confirmation."""
    query = update.callback_query
    await query.answer()
    
    amount_str = query.data.split('_')[1]  # amt_10 -> 10
    
    if amount_str == 'c':  # custom
        await query.edit_message_text(
            "✏️ <b>Custom Amount</b>\n\nEnter amount in USD (min $5, max $100):",
            parse_mode='HTML'
        )
        return CUSTOM_AMOUNT
    
    amount = float(amount_str)
    return await show_buy_confirmation(query, context, amount)


async def show_buy_confirmation(query, context, amount: float):
    """Show buy confirmation screen."""
    market = context.user_data.get('selected_market')
    outcome = context.user_data.get('selected_outcome', 'YES')
    price = context.user_data.get('selected_price', 0.5)
    
    if not market:
        await query.edit_message_text("⚠️ Market not found. Start over with /buy")
        return
    
    est_shares = amount / price if price > 0 else 0
    
    context.user_data['buy_amount'] = amount
    
    mode_text = "📝 PAPER" if Config.is_paper_mode() else "💱 LIVE"
    
    text = f"""
🚀 <b>Confirm Buy Order</b>

📋 <b>{market.question}</b>

🎯 <b>Outcome:</b> {outcome}
📍 <b>Price:</b> ${price:.4f}
💵 <b>Amount:</b> ${amount:.2f}
📦 <b>Est. Shares:</b> {est_shares:.2f}

<b>Mode:</b> {mode_text}

<i>🔥 Market order = instant execution</i>
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=buy_confirm_keyboard()
    )


async def execute_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the buy order."""
    query = update.callback_query
    await query.answer("⚡ Executing buy...")
    
    # Get all data from context
    token_id = context.user_data.get('selected_token_id')
    amount = context.user_data.get('buy_amount')
    market = context.user_data.get('selected_market')
    outcome = context.user_data.get('selected_outcome', 'YES')
    
    if not token_id or not amount:
        await query.edit_message_text("⚠️ Session expired. Use /buy to start over.")
        return
    
    market_info = {
        'condition_id': market.condition_id if market else '',
        'question': market.question if market else 'Unknown',
        'outcome': outcome
    }
    
    client = get_polymarket_client()
    result = await client.buy_market(token_id, amount, market_info=market_info)
    
    if result.success:
        text = f"""
✅ <b>Buy Executed!</b>

📋 {market.question if market else 'Position'}
🎯 <b>Outcome:</b> {outcome}

📦 <b>Shares:</b> {result.filled_size:.2f}
💵 <b>Avg Price:</b> ${result.avg_price:.4f}
🆔 <b>Order ID:</b> <code>{result.order_id[:16]}...</code>

{'📝 Paper trade' if Config.is_paper_mode() else '💱 Live trade'}

Use /positions to view your position.
"""
    else:
        text = f"""
❌ <b>Buy Failed</b>

Error: {result.error}

Please try again.
"""
    
    await query.edit_message_text(text, parse_mode='HTML')


async def custom_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom amount input."""
    try:
        amount = float(update.message.text.strip().replace('$', ''))
        
        if amount < Config.MIN_TRADE_USD:
            await update.message.reply_text(f"⚠️ Minimum amount is ${Config.MIN_TRADE_USD}")
            return CUSTOM_AMOUNT
        
        if amount > Config.MAX_TRADE_USD:
            await update.message.reply_text(f"⚠️ Maximum amount is ${Config.MAX_TRADE_USD}")
            return CUSTOM_AMOUNT
        
        token_id = context.user_data.get('selected_token_id')
        market = context.user_data.get('selected_market')
        outcome = context.user_data.get('selected_outcome', 'YES')
        price = context.user_data.get('selected_price', 0.5)
        
        if not token_id:
            await update.message.reply_text("⚠️ Session expired. Use /buy to start over.")
            return ConversationHandler.END
        
        est_shares = amount / price if price > 0 else 0
        
        context.user_data['buy_amount'] = amount
        
        mode_text = "📝 PAPER" if Config.is_paper_mode() else "💱 LIVE"
        
        text = f"""
🚀 <b>Confirm Buy Order</b>

📋 <b>{market.question if market else 'Unknown'}</b>

🎯 <b>Outcome:</b> {outcome}
📍 <b>Price:</b> ${price:.4f}
💵 <b>Amount:</b> ${amount:.2f}
📦 <b>Est. Shares:</b> {est_shares:.2f}

<b>Mode:</b> {mode_text}
"""
        
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=buy_confirm_keyboard()
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number")
        return CUSTOM_AMOUNT
