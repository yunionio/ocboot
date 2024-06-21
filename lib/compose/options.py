_public_ip = False


def set_has_public_ip(enable: bool):
    global _public_ip
    _public_ip = enable


def has_public_ip():
    return _public_ip
