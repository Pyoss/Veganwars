 
#!/bin/bash
until python bot.py 2>error_text; do
    export ERROR_MSG=$(cat error_text)
    python -m bot_watcher
    sleep 5
done
