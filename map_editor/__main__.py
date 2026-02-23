#!/usr/bin/env python3
"""
Map Editor Launcher for Terminus Realm
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from map_editor.editor import main

if __name__ == "__main__":
    main()
