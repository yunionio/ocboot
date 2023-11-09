#!/usr/bin/env python3

import os

from lib.compose.manifest import new_oc_manifest

if __name__ == "__main__":
    version = os.getenv('VERSION', 'v3.10.7')

    m = new_oc_manifest(version)
    print(m.to_yaml())
