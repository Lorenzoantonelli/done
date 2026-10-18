function __done_tg_notify --argument-names title commandline exit_status
    if not set -q DONE_TG_BOT_TOKEN DONE_TG_CHAT_ID
        return
    end
    if set -q __done_tg_only_failures; and test "$exit_status" -eq 0
        return
    end

    # Telegram rejects messages over 4096 characters.
    if test (string length -- "$commandline") -gt 3500
        set commandline (string sub -l 3499 -- "$commandline" | string collect)…
    end
    set -l wd (string replace --regex "^$HOME" "~" -- $PWD)
    set -l html (printf '%s\n' "$title" "$wd" "$commandline" | string replace -a '&' '&amp;' | string replace -a '<' '&lt;' | string replace -a '>' '&gt;')
    set -l text "📝 $html[1]"\n"📂 $html[2]"\n\n"<pre>"(string join \n -- $html[3..-1] | string collect)"</pre> ✨"

    mkdir -p "$__fish_user_data_dir"
    # The URL is fed through stdin so the bot token never appears in argv (ps).
    printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$DONE_TG_BOT_TOKEN" |
        command curl -sS --fail --max-time 10 -o /dev/null -K - \
            --data-urlencode "chat_id=$DONE_TG_CHAT_ID" \
            --data-urlencode "text=$text" \
            --data-urlencode parse_mode=HTML \
            2>>"$__fish_user_data_dir/done_tg.log" &
    disown $last_pid
end
