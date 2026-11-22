# PhotoHop

Jump randomly into the history of your life and rediscover memories you'd forgotten you had.

A simple photo viewer, written in Python, for jumping randomly around your photo collection.

## Installation

Create a virtual environment:
```sh
python -m venv .venv
. .venv/bin/activate
```

Install system dependencies for `wxPython`: gcc, g++, gtk3, gtk+.
```sh
sudo dnf install -y \
  gcc gcc-c++ make pkgconf \
  python3-devel \
  gtk3-devel
  
  webkit2gtk4.1-devel \
  gstreamer1-devel gstreamer1-plugins-base-devel \
  libjpeg-turbo-devel libpng-devel libtiff-devel \
  SDL2-devel libnotify-devel libSM-devel freeglut-devel
```
or similar for your distro.

Install Python dependencies:
```sh

```