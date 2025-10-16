# python-bufferbloat-test

Bufferbloat is undesirable network latency caused by excessive packet buffering in network equipment like routers and switches, resulting in delays especially during network congestion.

This script measures bufferbloat by comparing network latency on TCP connect to a couple of anycast IP addresses in unloaded state and while downloading a large file.

You can run the script by either of:
- Executing it directly (which will install dependencies using `uv` transparently): `./python-bufferbloat-test.py`
- or explicitly running `uv run python-bufferbloat-test.py`
- or installing `requests` using any other method (e.g. `pip install requests`) and then running `python3 python-bufferbloat-test.py`.
