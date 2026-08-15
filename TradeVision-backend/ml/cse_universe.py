"""
CSE training universe — the tickers ml/fetch_data.py downloads.

This list exists to make the TRAINING SET big, which is the single biggest lever
available on a weak-signal problem. It is deliberately separate from
services/ticker_registry.py, which serves a different purpose (company names for
the news scraper) and does not constrain what the model can predict.

Since Asset_ID was removed from the feature set the model is cross-sectional, so
this list has no bearing on which symbols can be PREDICTED — any CSE ticker
works. Adding or removing entries here changes only how much data training sees,
and the order carries no meaning.

Symbols use the canonical CSE form (JKH.N0000); fetch_data.py converts them to
Yahoo's form (JKH-N0000.CM). Not every entry will resolve on Yahoo — coverage of
the CSE is uneven — and fetch_data.py reports and skips the misses rather than
failing.

Names are only used for logging here; the news scraper's names come from the
serving registry.
"""

# ~50 of the more liquid CSE counters, spread across sectors so the model sees
# varied volatility and volume regimes rather than nine large caps.
CSE_UNIVERSE = [
    # --- Banks, finance & insurance ---
    ("COMB.N0000", "Commercial Bank of Ceylon"),
    ("HNB.N0000",  "Hatton National Bank"),
    ("SAMP.N0000", "Sampath Bank"),
    ("NDB.N0000",  "National Development Bank"),
    ("DFCC.N0000", "DFCC Bank"),
    ("SEYB.N0000", "Seylan Bank"),
    ("NTB.N0000",  "Nations Trust Bank"),
    ("PABC.N0000", "Pan Asia Banking Corporation"),
    ("UBC.N0000",  "Union Bank of Colombo"),
    ("LOLC.N0000", "LOLC Holdings"),
    ("LFIN.N0000", "LB Finance"),
    ("CFIN.N0000", "Central Finance"),
    ("PLC.N0000",  "People's Leasing & Finance"),
    ("SFIN.N0000", "Senkadagala Finance"),
    ("AAIC.N0000", "Softlogic Life Insurance"),
    ("CINS.N0000", "Ceylinco Insurance"),
    ("JINS.N0000", "Janashakthi Insurance"),

    # --- Diversified holdings ---
    ("JKH.N0000",  "John Keells Holdings"),
    ("HAYL.N0000", "Hayleys"),
    ("SPEN.N0000", "Aitken Spence"),
    ("RICH.N0000", "Richard Pieris"),
    ("VONE.N0000", "Vallibel One"),
    ("SOFT.N0000", "Softlogic Holdings"),
    ("EXPO.N0000", "Expolanka Holdings"),
    ("CARS.N0000", "Carson Cumberbatch"),
    ("BUKI.N0000", "Bukit Darah"),

    # --- Telecom & technology ---
    ("DIAL.N0000", "Dialog Axiata"),
    ("SLTL.N0000", "Sri Lanka Telecom"),

    # --- Manufacturing & materials ---
    ("TKYO.N0000", "Tokyo Cement"),
    ("RCL.N0000",  "Royal Ceramics Lanka"),
    ("TILE.N0000", "Lanka Tiles"),
    ("ACL.N0000",  "ACL Cables"),
    ("KZOO.N0000", "Kelani Cables"),
    ("DIPD.N0000", "Dipped Products"),
    ("CIC.N0000",  "CIC Holdings"),
    ("GRAN.N0000", "Ceylon Grain Elevators"),
    ("LLUB.N0000", "Chevron Lubricants Lanka"),
    ("CTBL.N0000", "Ceylon Tobacco Company"),

    # --- Food, beverage & retail ---
    ("DIST.N0000", "Distilleries Company of Sri Lanka"),
    ("LION.N0000", "Lion Brewery Ceylon"),
    ("NEST.N0000", "Nestle Lanka"),
    ("CCS.N0000",  "Ceylon Cold Stores"),
    ("MELS.N0000", "Melstacorp"),
    ("CARG.N0000", "Cargills Ceylon"),

    # --- Energy & utilities ---
    ("LIOC.N0000", "Lanka IOC"),
    ("LGL.N0000",  "Laugfs Gas"),
    ("VPEL.N0000", "Vidullanka"),

    # --- Hotels & leisure ---
    ("AHUN.N0000", "Aitken Spence Hotel Holdings"),
    ("KHL.N0000",  "John Keells Hotels"),
    ("RHTL.N0000", "Renuka Hotels"),

    # --- Plantations & healthcare ---
    ("KVAL.N0000", "Kotagala Plantations"),
    ("WATA.N0000", "Watawala Plantations"),
    ("ASIR.N0000", "Asiri Hospital Holdings"),
    ("LHCL.N0000", "Lanka Hospitals"),
]


def to_yahoo_symbol(symbol: str) -> str:
    """
    Canonical CSE symbol -> Yahoo Finance symbol.

        JKH.N0000  ->  JKH-N0000.CM

    Same convention as services/ticker_registry.py; kept here so the training
    scripts do not depend on the serving registry.
    """
    return symbol.strip().upper().replace(".", "-") + ".CM"
