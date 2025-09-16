#!/usr/bin/env python3
"""
Wrapper script to run Astrid compiler
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run main
from astrid2.main import main

if __name__ == "__main__":
    main()
