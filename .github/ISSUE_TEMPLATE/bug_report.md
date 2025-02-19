---
name: Bug report
title: ''
labels: 'bug'
assignees: ''
---

### Describe the bug
A clear and concise description of what the bug is.

### Environment
- OS: [e.g. Ubuntu 22.04, Windows 11]
- Python Version: [e.g. 3.10.5]
- Project Version/Branch: [e.g. main - commit abc123]
- Running Mode: [Test/Production]

### Configuration
Relevant configurations (without sensitive data):
```yaml
# Example configuration used
FILTERS:
  min_liquidity: 5000  # USD
  min_age_days: 3
  coin_blacklist:
    - "0x123...def"  # Token contract addresses only
    - "0x456...abc"
  dev_blacklist:
    - "0x789...fed"  # Developer wallet addresses
  chain_whitelist:
    - "ethereum"  # Use official chain names from DexScreener
    - "bsc"


    