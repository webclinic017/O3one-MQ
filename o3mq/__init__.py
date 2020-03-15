""" O3MQ - Ozone Messaging framework for Python """
VERSION = (0, 1, 0)
__version__ = '0.1'
__author__ = "Pho3"
__homepage__ = "https://github.com/TheRainbowPhoenix/"


def version_string(short=False):
    from platform import architecture
    return f"O3one MQ {__version__} " + (f"({'.'.join(['{}'.format(i) for i in VERSION])}) {' '.join(architecture())}" if not short else "")
