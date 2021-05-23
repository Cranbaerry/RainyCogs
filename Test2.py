

class MaximumProxyRequests(Exception):
    pass

try:
    raise MaximumProxyRequests()
    print("what")
except MaximumProxyRequests:
    data = MaximumProxyRequests
    raise MaximumProxyRequests()

    if data is MaximumProxyRequests:
        print("yes2")


    print("wot")
