"""
Gunicorn configuration file for Django deployment on Render.
"""

import os
import multiprocessing

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "8000")
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
worker_class = 'sync'
worker_connections = 1000
timeout = 300
keepalive = 2

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Startup
preload_app = True

# Worker lifecycle
graceful_timeout = 120
max_requests = 1000
max_requests_jitter = 50

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def pre_fork(server, worker):
    pass

def when_ready(server):
    server.log.info("Server is ready. Spawning workers")

def worker_int(worker):
    worker.log.info("worker received INT or QUIT signal")

def worker_abort(worker):
    worker.log.info("worker received SIGABRT signal") 