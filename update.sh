
#!/bin/sh
ERROR_MSG=$(git pull)
export ERROR_MSG
python -m bot_watcher
nohup ./dev_monitor.sh
