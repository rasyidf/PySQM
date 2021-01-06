
""" Sky Quality Meter Client.

Usage:
  pysqm.py init <observatory> [--config=<f>] 
  pysqm.py serve [--config=<f>] [--input=<f>] 
  pysqm.py plot 
  pysqm.py dashboard
  pysqm.py (-h | --help)
  pysqm.py --version

Options:
  -h --help      Show this screen.
  --version      Show version.
  --config=<f>   Set Configuration [default: config.py].
  -i --input=<f> Set Input file. 

"""
from docopt import docopt


if __name__ == '__main__':
    arguments = docopt(__doc__, version='Sky Quality Meter Client')
    print(arguments)