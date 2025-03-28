#!/usr/bin/env bash
# start.sh - Custom startup script for Render

# Run the Django application with the correct WSGI path
exec gunicorn wsgi:application 