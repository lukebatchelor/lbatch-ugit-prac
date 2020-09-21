import os

GIT_DIR='.ugit'

def init():
  # use makedirs instead of mkdir to create if it doesn't exist
  os.makedirs(GIT_DIR)