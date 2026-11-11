# bourse-sdk

Python client for the [Bourse API](https://www.bourse.pl/api/): stock trades of members of Congress, President Trump and the Cabinet (OGE 278-T), SEC Form 4 insiders, Form 144, 13F funds, lobbying, government contracts, WARN layoffs, Jim Cramer's calls, Google Trends, Treasury yields, COT positioning and backtested strategies.

```bash
pip install bourse-sdk            # add [pandas] for DataFrames
```

```python
from bourse import Bourse

b = Bourse("bk_...")                       # or set BOURSE_KEY
b.get("congress", ticker="NVDA")           # one page
rows = b.all("house", from_="2026-01-01")  # every page
df = b.df("tv-picks", person="Cramer")     # pandas DataFrame
b.ticker("AAPL")                           # everything about one ticker
b.get("insider-clusters", days=30)         # analytics
```

Get a free key (1,000 requests a day) in the Bourse app: Settings -> API key. Premium raises it to 20,000 a day and adds bulk downloads; API Pro (commercial license) to 250,000.

## Webhooks

```python
from bourse import Bourse

ok = Bourse.verify_webhook(secret, request.headers["Bourse-Signature"], request.get_data())
```

## MCP server (Claude, ChatGPT, Cursor)

Remote MCP server with 6 tools (datasets, ticker profile, insider clusters, Congress and Trump trades):

```
URL:     https://api.bourse.pl/mcp
Header:  Authorization: Bearer bk_...
```

Clients that only take a URL can use `https://api.bourse.pl/mcp?key=bk_...`. Listed in the official MCP Registry as `io.github.ofylypczuk/bourse`.

## Links

- Docs and OpenAPI: https://www.bourse.pl/api/ and https://api.bourse.pl/v1/openapi.json
- Commercial use (API Pro): https://www.bourse.pl/api/pro/
- License for the data: https://www.bourse.pl/legal/api/

Data comes from public filings. Not investment advice. The code in this repository is MIT licensed.
