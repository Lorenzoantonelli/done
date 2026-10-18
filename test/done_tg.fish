# Run with: fish --no-config test/done_tg.fish
set -l tmp (mktemp -d)
set -gx CAPTURE $tmp/capture
printf '#!/bin/sh\nprintf "%%s\\n" "$@" > "$CAPTURE.argv"\ncat > "$CAPTURE.stdin"\n' >$tmp/curl
chmod +x $tmp/curl
set -gx PATH $tmp $PATH
source (status dirname)/../functions/__done_tg_notify.fish
set -g DONE_TG_BOT_TOKEN secret-token
set -g DONE_TG_CHAT_ID 123
set -g failed 0
mkdir $tmp/a\&b
cd $tmp/a\&b

function send
    rm -f $CAPTURE.argv $CAPTURE.stdin
    __done_tg_notify $argv
    for i in (seq 40)
        test -s $CAPTURE.stdin; and return 0
        sleep 0.05
    end
    return 1
end

function check -a desc
    if test $status -eq 0
        echo "ok - $desc"
    else
        echo "not ok - $desc"
        set -g failed 1
    end
end

send 'Failed (1) after 6s' (printf '%s\n' 'echo "a<&>b"' '' 'echo done' | string collect) 1
check "sends a message"
set -l argv_text (cat $CAPTURE.argv | string collect)
string match -q -- '*text=📝 Failed (1) after 6s

📂 '(string replace -a '&' '&amp;' -- $PWD)'

<pre>echo "a&lt;&amp;&gt;b"

echo done</pre> ✨*' $argv_text
check "escapes HTML, shows the directory and keeps multi-line commands"
not string match -q -- '*secret-token*' $argv_text
check "token stays out of argv"
string match -q -- '*/botsecret-token/sendMessage*' (cat $CAPTURE.stdin)
check "token is passed via stdin"

set -g __done_tg_only_failures
not send 'Done in 6s' 'sleep 6' 0
check "only_failures skips successes"
send 'Failed (1) after 6s' false 1
check "only_failures still sends failures"

send 'Failed (1) after 6s' (string repeat -n 4000 a) 1
string match -q -- "*<pre>"(string repeat -n 3499 a)"…</pre>*" (cat $CAPTURE.argv)
check "truncates long commands with an ellipsis"

send 'Failed (1) after 6s' (string repeat -n 3500 a) 1
string match -q -- "*<pre>"(string repeat -n 3500 a)"</pre>*" (cat $CAPTURE.argv)
check "keeps commands at the limit intact"

set -g __done_tg_min_cmd_duration 60000
not send 'Failed (1) after 30s' 'sleep 30' 1 30000
check "min_cmd_duration skips shorter commands"
send 'Failed (1) after 1m 30s' 'sleep 90' 1 90000
check "min_cmd_duration sends longer commands"
send 'Test notification' done_tg_test 1
check "min_cmd_duration ignores calls without a duration"
set -e __done_tg_min_cmd_duration

set -e __done_tg_only_failures
set -g __done_tg_silent_success
send 'Done in 6s' 'sleep 6' 0
string match -q -- disable_notification=true (cat $CAPTURE.argv)
check "silent_success silences successes"
send 'Failed (1) after 6s' false 1
string match -q -- disable_notification=false (cat $CAPTURE.argv)
check "silent_success still buzzes on failures"

cd /
rm -rf $tmp
exit $failed
