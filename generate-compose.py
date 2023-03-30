#!/usr/bin/env python3


from lib.compose.manifest import new_oc_manifest

if __name__ == "__main__":
    m = new_oc_manifest("v3.9.8")
    print(m.to_yaml())
