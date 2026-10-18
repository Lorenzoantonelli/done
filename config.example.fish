# Add these to your personal config.fish. Both enable Telegram delivery.
set -g DONE_TG_BOT_TOKEN your-bot-token
set -g DONE_TG_CHAT_ID your-chat-id

# Optional: only send Telegram messages for failed commands.
# set -g __done_tg_only_failures

# Delivery errors are appended to $__fish_user_data_dir/done_tg.log.
