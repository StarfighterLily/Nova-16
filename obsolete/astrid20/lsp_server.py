#!/usr/bin/env python3
"""
Astrid 2.0 Language Server Launcher
Launches the LSP server for IDE integration.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run LSP server
from astrid2.lsp.server import main

if __name__ == "__main__":
    main()
