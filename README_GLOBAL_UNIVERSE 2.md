# Catalyst AI — Global Universe Expansion

This patch expands the default scan universe from the small starter list to a curated liquid global universe.

## Coverage

- US large caps and sector ETFs
- UK large caps
- Continental Europe
- Japan
- Hong Kong, Taiwan, South Korea and Australia
- Canada
- India and Latin America ADRs
- Global equity, bond, commodity and currency ETFs

The bundled global file contains **323 unique symbols**. When the live S&P 500 and Nasdaq-100 lists load successfully, Catalyst can scan up to the configured **650-symbol cap**.

## Install

Merge the patch into the Catalyst repository, replacing `engine/universe_builder.py` and `version.py`, and adding the CSV and test file.

Run `python3 -m pytest` and restart Streamlit.
