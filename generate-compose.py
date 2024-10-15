#!/usr/bin/env python3

import os

from lib.compose.manifest import new_manifest, PRODUCT_VERSION_CMP

if __name__ == "__main__":
    version = os.getenv('VERSION', 'v3.11.8')
    product_version = os.getenv("PRODUCT_VERSION", PRODUCT_VERSION_CMP)

    m = new_manifest(version, product_version)
    print(m.to_yaml())
