#!/usr/bin/env python3
"""python -m envdiff 入口。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from envdiff import main

if __name__ == "__main__":
    sys.exit(main())
