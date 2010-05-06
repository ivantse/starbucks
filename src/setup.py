from distutils.core import setup
import py2exe

setup(console=['src/fetcher.py', 'src/brew_builder.py'])
