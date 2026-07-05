import json
from instagrapi.types import Track
print(dir(Track))
if hasattr(Track, '__annotations__'):
    print(Track.__annotations__)
else:
    print("No annotations")
