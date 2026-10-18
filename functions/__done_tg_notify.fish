function __done_tg_notify --argument-names title commandline
    if not set -q DONE_TG_BOT_TOKEN DONE_TG_CHAT_ID
        return
    end

    set -l script (dirname (status filename))/__done_tg_notify.py
    mkdir -p "$__fish_user_data_dir"
    command python3 "$script" -- "$title" "$commandline" >>"$__fish_user_data_dir/done_tg.log" 2>&1 &
    disown $last_pid
end
