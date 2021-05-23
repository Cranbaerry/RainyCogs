

class MaximumProxyRequests(Exception):
    pass

try:
    raise MaximumProxyRequests()
    print("what")
except MaximumProxyRequests:
    print("wot")
