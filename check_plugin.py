from livekit.plugins import silero

print("Available in silero plugin:")
for attr in dir(silero):
    if not attr.startswith('_'):
        print(f"  - {attr}")