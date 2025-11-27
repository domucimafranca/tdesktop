#!/bin/bash
SESSION="desktop"

tmux new-session -d -s $SESSION
tmux split-window -h -t $SESSION -c /home/dom/Projects/newsfeed
tmux split-window -v -l 3  -t $SESSION:0.1 -c /home/dom/Projects/newsfeed

tmux send-keys -t $SESSION:0.1 'uv run rss_reader.py' C-m
tmux send-keys -t $SESSION:0.2 'uv run pomodoro.py' C-m

tmux attach -t $SESSION
