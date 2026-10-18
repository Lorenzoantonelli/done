function done_tg_test --description 'Send a test Telegram notification'
    if not set -q DONE_TG_BOT_TOKEN DONE_TG_CHAT_ID
        echo "done_tg_test: set DONE_TG_BOT_TOKEN and DONE_TG_CHAT_ID first" >&2
        return 1
    end
    __done_tg_notify "Test notification" done_tg_test 1
    echo "Sent. If nothing arrives, check $__fish_user_data_dir/done_tg.log"
end
