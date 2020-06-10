#!/usr/bin/env python3

import os
import sys

from .base import main


def cli():
    main(sys.argv[1:], sys.stdout, sys.stderr, sys.exit, os.environ)


if __name__ == "__main__":
    cli()
