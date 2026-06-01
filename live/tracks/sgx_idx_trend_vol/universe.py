"""Universe definitions for SGX + IDX trend_vol port.

yfinance ticker conventions:
  - SGX: `<code>.SI`  (e.g. `D05.SI` = DBS)
  - IDX: `<code>.JK`  (e.g. `BBCA.JK` = Bank Central Asia)

**Survivorship bias warning:** these lists are current-as-of-2026 index
constituents. Tickers that delisted before 2026 are absent; tickers that
joined the index recently are present for their full yfinance history.
The pre-registered gate (`../../wiki/decisions/001-track-a-gate.md`)
acknowledges this bias. Point-in-time constituents would be the v2 fix.

**Verification status:** lists assembled from public index pages. Treat
as a starting universe; cross-check before any result is published.
Tickers that yfinance can't resolve are dropped at fetch time.
"""

from __future__ import annotations

# ─── SGX ──────────────────────────────────────────────────────────────────────

# STI 30 large-caps (banks, telcos, REITs, industrials). Approx, needs check.
STI_30: tuple[str, ...] = (
    "D05.SI",    # DBS Group
    "O39.SI",    # OCBC
    "U11.SI",    # UOB
    "Z74.SI",    # Singtel
    "C6L.SI",    # SIA
    "C38U.SI",   # CapitaLand Integrated Commercial Trust
    "A17U.SI",   # Ascendas REIT
    "BN4.SI",    # Keppel Corp
    "F34.SI",    # Wilmar
    "C09.SI",    # City Developments
    "J36.SI",    # Jardine Matheson
    "H78.SI",    # Hongkong Land
    "S68.SI",    # SGX
    "Y92.SI",    # Thai Beverage
    "G13.SI",    # Genting Singapore
    "C07.SI",    # Jardine Cycle & Carriage
    "C52.SI",    # ComfortDelGro
    "N2IU.SI",   # Mapletree PanAsia Commercial Trust
    "ME8U.SI",   # Mapletree Industrial Trust
    "AJBU.SI",   # Keppel DC REIT
    "M44U.SI",   # Mapletree Logistics Trust
    "S58.SI",    # SATS
    "S63.SI",    # ST Engineering
    "BS6.SI",    # YZJ Shipbuilding
    "U96.SI",    # Sembcorp Industries
    "9CI.SI",    # CapitaLand Investment
    "U14.SI",    # UOL Group
    "T39.SI",    # SIA Engineering
    "V03.SI",    # Venture Corp
    "H02.SI",    # Haw Par
)

# SGX mid-caps — add liquidity below STI 30. Needs verification.
SGX_MIDCAPS: tuple[str, ...] = (
    "S59.SI",    # SIA Engineering Co (placeholder; verify)
    "AIY.SI",    # iFAST
    "RE4.SI",    # First REIT
    "OV8.SI",    # Sheng Siong
    "5UF.SI",    # Bukit Sembawang
    "ER0.SI",    # Riverstone
    "TQ5.SI",    # Frasers Property
    "Q5T.SI",    # Hutchison Port Trust
    "5DD.SI",    # Top Glove
    "BUOU.SI",   # Frasers Logistics & Commercial Trust
    "M1GU.SI",   # Sasseur REIT
    "CY6U.SI",   # CapitaLand Ascendas China Trust
    "RW0U.SI",   # Mapletree Commercial Trust (legacy ticker; verify)
    "K71U.SI",   # Keppel REIT
    "T82U.SI",   # Suntec REIT
    "C2PU.SI",   # Parkway Life REIT
    "U06.SI",    # Singapore Land Group
    "S20.SI",    # Singapore Shipping
    "BSL.SI",    # Raffles Medical Group (legacy ticker; verify)
    "U10.SI",    # United Industrial Corp
)

SGX_UNIVERSE: tuple[str, ...] = STI_30 + SGX_MIDCAPS


# ─── IDX ──────────────────────────────────────────────────────────────────────

# LQ45 — top 45 by liquidity on IDX. Approx, needs check.
LQ45: tuple[str, ...] = (
    "BBCA.JK",   # Bank Central Asia
    "BBRI.JK",   # Bank Rakyat Indonesia
    "BMRI.JK",   # Bank Mandiri
    "BBNI.JK",   # Bank Negara Indonesia
    "TLKM.JK",   # Telkom Indonesia
    "ASII.JK",   # Astra International
    "UNVR.JK",   # Unilever Indonesia
    "GGRM.JK",   # Gudang Garam
    "HMSP.JK",   # HM Sampoerna
    "ICBP.JK",   # Indofood CBP
    "INDF.JK",   # Indofood
    "KLBF.JK",   # Kalbe Farma
    "ADRO.JK",   # Adaro Energy
    "PTBA.JK",   # Bukit Asam
    "ITMG.JK",   # Indo Tambangraya
    "ANTM.JK",   # Aneka Tambang
    "MDKA.JK",   # Merdeka Copper Gold
    "INCO.JK",   # Vale Indonesia
    "SMGR.JK",   # Semen Indonesia
    "INTP.JK",   # Indocement
    "TKIM.JK",   # Tjiwi Kimia
    "INKP.JK",   # Indah Kiat Pulp
    "PGAS.JK",   # Perusahaan Gas Negara
    "PTPP.JK",   # PP Persero
    "WIKA.JK",   # Wijaya Karya
    "WSKT.JK",   # Waskita Karya
    "JSMR.JK",   # Jasa Marga
    "EXCL.JK",   # XL Axiata
    "ISAT.JK",   # Indosat
    "TOWR.JK",   # Sarana Menara Nusantara
    "TBIG.JK",   # Tower Bersama
    "BUKA.JK",   # Bukalapak
    "GOTO.JK",   # GoTo Gojek Tokopedia
    "EMTK.JK",   # Elang Mahkota Teknologi
    "MNCN.JK",   # Media Nusantara Citra
    "SCMA.JK",   # Surya Citra Media
    "AKRA.JK",   # AKR Corporindo
    "UNTR.JK",   # United Tractors
    "BRPT.JK",   # Barito Pacific
    "TPIA.JK",   # Chandra Asri Petrochemical
    "MEDC.JK",   # Medco Energi
    "ENRG.JK",   # Energi Mega Persada
    "BSDE.JK",   # Bumi Serpong Damai
    "PWON.JK",   # Pakuwon Jati
    "CTRA.JK",   # Ciputra Development
)


# ─── HSI (cross-cycle stress test per decisions/006) ──────────────────────────

# Hang Seng Index constituents — current-as-of-2026, best-effort.
HSI: tuple[str, ...] = (
    "0700.HK",   # Tencent
    "0941.HK",   # China Mobile
    "0939.HK",   # China Construction Bank
    "1398.HK",   # ICBC
    "3988.HK",   # Bank of China
    "0001.HK",   # CK Hutchison
    "0005.HK",   # HSBC
    "0011.HK",   # Hang Seng Bank
    "0016.HK",   # Sun Hung Kai Properties
    "0017.HK",   # New World Development
    "0027.HK",   # Galaxy Entertainment
    "0066.HK",   # MTR
    "0388.HK",   # HKEX
    "0688.HK",   # China Overseas Land
    "0762.HK",   # China Unicom
    "0823.HK",   # Link REIT
    "0857.HK",   # PetroChina
    "0883.HK",   # CNOOC
    "0992.HK",   # Lenovo
    "1038.HK",   # CK Infrastructure
    "1093.HK",   # CSPC Pharmaceutical
    "1109.HK",   # China Resources Land
    "1113.HK",   # CK Asset
    "1177.HK",   # Sino Biopharmaceutical
    "1299.HK",   # AIA
    "1810.HK",   # Xiaomi
    "1928.HK",   # Sands China
    "1997.HK",   # Wharf REIC
    "2018.HK",   # AAC Technologies
    "2020.HK",   # ANTA Sports
    "2269.HK",   # WuXi Biologics
    "2313.HK",   # Shenzhou International
    "2318.HK",   # Ping An
    "2319.HK",   # China Mengniu
    "2331.HK",   # Li Ning
    "2382.HK",   # Sunny Optical
    "2388.HK",   # BOC Hong Kong
    "2628.HK",   # China Life Insurance
    "2688.HK",   # ENN Energy
    "3690.HK",   # Meituan
    "9618.HK",   # JD.com
    "9633.HK",   # Nongfu Spring
    "9888.HK",   # Baidu
    "9988.HK",   # Alibaba
    "6862.HK",   # Haidilao
)


def all_tickers(market: str | None = None) -> tuple[str, ...]:
    """Return tickers for `market` ∈ {'sgx', 'idx', 'hsi', None=all}."""
    if market is None:
        return SGX_UNIVERSE + LQ45 + HSI
    if market == "sgx":
        return SGX_UNIVERSE
    if market == "idx":
        return LQ45
    if market == "hsi":
        return HSI
    raise ValueError(f"unknown market: {market!r}")
