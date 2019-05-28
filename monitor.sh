 
#!/bin/bash
until python -m bot; do
    export ERROR_MSG="'vwars' crashed with exit code $?. Restarting..." &>1
    python -m bot_watcher
    sleep 1
done
