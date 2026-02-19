# Proxy Setup Notes (Bright Data Backconnect)

## For Application Use

To run the pipeline in `--mode=online`, the application requires the following environment variables to be set. The transport layer will use these to construct the full proxy URL for each request, including a random session ID for rotation.

```bash
# Replace with your actual Bright Data credentials
export BRD_USERNAME_BASE="brd-customer-hl_XXXXXXXX-zone-datacenter_proxy_akshare"
export BRD_PASSWORD="your_brightdata_password"
```
The application will automatically handle session rotation (e.g., `-session-12345`).

## For Manual Connectivity Testing

If you need to test your proxy connection manually, you can use a `curl` command. Note that you must manually add a session ID to the username.

```bash
# Replace with your credentials and a random session number
curl -i \
  --proxy brd.superproxy.io:33335 \
  --proxy-user "your_username_base-session-123456:your_password" \
  "https://geo.brdtest.com/mygeo.json"
```