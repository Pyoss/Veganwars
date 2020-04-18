
#!/bin/sh
ERROR_MSG=$(git pull)
export ERROR_MSG
python -m bot_watcher
nohup ./main_server_monitor.sh
