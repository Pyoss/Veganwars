
#!/bin/sh
ERROR_MSG=$(git pull)
export ERROR_MSG
python -m bot_watcher
./monitor.sh
