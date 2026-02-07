"""
Position Handlers

Handles /positions command and sell operations.
Uses index-based callbacks with context storage.
"""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
from core.polymarket_client import get_polymarket_client, Position
from bot.keyboards.inline import (
    positions_keyboard, position_detail_keyboard, sell_confirm_keyboard
)


# Conversation states
CUSTOM_SELL_PERCENT = 0


async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /positions command - show all active positions."""
    client = get_polymarket_client()
    positions = await client.get_positions()
    
    # Store positions in context for callback reference
    context.user_data['positions'] = positions
    
    if not positions:
        text = """
📊 <b>Active Positions</b>

<i>No open positions</i>

Use /buy to open a new position.
"""
        if update.callback_query:
            await update.callback_query.edit_message_text(text, parse_mode='HTML')
        else:
            await update.message.reply_text(text, parse_mode='HTML')
        return
    
    # Build positions display
    total_value = sum(p.value for p in positions)
    total_pnl = sum(p.pnl for p in positions)
    pnl_emoji = "📈" if total_pnl >= 0 else "📉"
    
    text = f"""
📊 <b>Active Positions ({len(positions)})</b>

💰 <b>Total Value:</b> ${total_value:.2f}
{pnl_emoji} <b>Unrealized P&L:</b> ${total_pnl:+.2f}

<i>Select a position for details:</i>
"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, 
            parse_mode='HTML',
            reply_markup=positions_keyboard(positions)
        )
    else:
        await update.message.reply_text(
            text, 
            parse_mode='HTML',
            reply_markup=positions_keyboard(positions)
        )


async def position_detail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle position detail view callback."""
    query = update.callback_query
    await query.answer()
    
    # Extract position index from callback: pos_0 -> 0
    idx = int(query.data.split('_')[1])
    
    positions = context.user_data.get('positions', [])
    if idx >= len(positions):
        await query.edit_message_text("⚠️ Position not found")
        return
    
    pos = positions[idx]
    
    # Store current position for sell operations
    context.user_data['current_position'] = pos
    context.user_data['current_position_index'] = idx
    
    pnl_emoji = "📈" if pos.pnl >= 0 else "📉"
    pnl_color = "🟢" if pos.pnl >= 0 else "🔴"
    
    text = f"""
📊 <b>Position Details</b>

📋 <b>{pos.market_question}</b>

🎯 <b>Outcome:</b> {pos.outcome}
📦 <b>Shares:</b> {pos.size:.2f}

💵 <b>Avg Entry:</b> ${pos.avg_price:.4f}
📍 <b>Current:</b> ${pos.current_price:.4f}

💰 <b>Value:</b> ${pos.value:.2f}
{pnl_color} <b>P&L:</b> ${pos.pnl:+.2f} ({pos.pnl_percent:+.1f}%)

<i>Select sell percentage:</i>
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=position_detail_keyboard(idx)
    )


async def sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sell button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Parse: sell_0_100 or sell_0_c
    parts = query.data.split('_')
    pos_index = int(parts[1])
    percent_str = parts[2]
    
    if percent_str == 'c':
        # Ask for custom percentage
        await query.edit_message_text(
            "✏️ <b>Custom Sell</b>\n\nEnter percentage to sell (1-100):",
            parse_mode='HTML'
        )
        context.user_data['sell_pos_index'] = pos_index
        return CUSTOM_SELL_PERCENT
    
    percent = int(percent_str)
    pos = context.user_data.get('current_position')
    
    if not pos:
        # Try to get from positions list
        positions = context.user_data.get('positions', [])
        if pos_index < len(positions):
            pos = positions[pos_index]
            context.user_data['current_position'] = pos
    
    if not pos:
        await query.edit_message_text("⚠️ Position not found")
        return
    
    sell_value = pos.value * (percent / 100)
    sell_shares = pos.size * (percent / 100)
    
    context.user_data['sell_percent'] = percent
    
    text = f"""
⚡ <b>Confirm Sell</b>

📋 {pos.market_question}
🎯 {pos.outcome}

💯 <b>Selling:</b> {percent}%
📦 <b>Shares:</b> {sell_shares:.2f}
💵 <b>Est. Value:</b> ${sell_value:.2f}
📍 <b>Current Price:</b> ${pos.current_price:.4f}

<i>This is a market order (instant execution)</i>
"""
    
    await query.edit_message_text(
        text,
        parse_mode='HTML',
        reply_markup=sell_confirm_keyboard(pos_index, percent)
    )


async def confirm_sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Execute the sell order."""
    query = update.callback_query
    await query.answer("⚡ Executing sell...")
    
    # Parse: csell_0_100
    parts = query.data.split('_')
    pos_index = int(parts[1])
    percent = int(parts[2])
    
    pos = context.user_data.get('current_position')
    if not pos:
        positions = context.user_data.get('positions', [])
        if pos_index < len(positions):
            pos = positions[pos_index]
    
    if not pos:
        await query.edit_message_text("⚠️ Position not found. Use /positions to refresh.")
        return
    
    client = get_polymarket_client()
    result = await client.sell_market(pos.token_id, percent=percent)
    
    if result.success:
        text = f"""
✅ <b>Sell Executed!</b>

📦 <b>Sold:</b> {result.filled_size:.2f} shares
💵 <b>Avg Price:</b> ${result.avg_price:.4f}
🆔 <b>Order ID:</b> <code>{result.order_id[:16]}...</code>

<i>{'📝 Paper trade' if Config.is_paper_mode() else '💱 Live trade'}</i>
"""
    else:
        text = f"""
❌ <b>Sell Failed</b>

Error: {result.error}

Please try again or check your position.
"""
    
    await query.edit_message_text(text, parse_mode='HTML')


async def custom_sell_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom sell percentage input."""
    try:
        percent = int(update.message.text.strip())
        if percent < 1 or percent > 100:
            await update.message.reply_text("⚠️ Enter a number between 1 and 100")
            return CUSTOM_SELL_PERCENT
        
        pos_index = context.user_data.get('sell_pos_index', 0)
        pos = context.user_data.get('current_position')
        
        if not pos:
            positions = context.user_data.get('positions', [])
            if pos_index < len(positions):
                pos = positions[pos_index]
        
        if not pos:
            await update.message.reply_text("⚠️ Position not found. Use /positions again.")
            return ConversationHandler.END
        
        sell_value = pos.value * (percent / 100)
        sell_shares = pos.size * (percent / 100)
        
        context.user_data['sell_percent'] = percent
        
        text = f"""
⚡ <b>Confirm Sell</b>

📋 {pos.market_question}
🎯 {pos.outcome}

💯 <b>Selling:</b> {percent}%
📦 <b>Shares:</b> {sell_shares:.2f}
💵 <b>Est. Value:</b> ${sell_value:.2f}

<i>This is a market order (instant execution)</i>
"""
        
        await update.message.reply_text(
            text,
            parse_mode='HTML',
            reply_markup=sell_confirm_keyboard(pos_index, percent)
        )
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("⚠️ Please enter a valid number (1-100)")
        return CUSTOM_SELL_PERCENT
