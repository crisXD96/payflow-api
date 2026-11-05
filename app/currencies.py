"""Monedas ISO 4217 en circulación y su número de decimales (minor units).

El dashboard (frontend/index.html) replica estas listas; tests/test_frontend_sync.py
falla si se desalinean.
"""

ACTIVE_CURRENCIES: frozenset[str] = frozenset((
    "AED AFN ALL AMD AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD "
    "CAD CDF CHF CLP CNY COP CRC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP "
    "GMD GNF GTQ GYD HKD HNL HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD "
    "KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN "
    "NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP "
    "SLE SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND "
    "VUV WST XAF XCD XCG XOF XPF YER ZAR ZMW ZWG"
).split())

# Excepciones a los 2 decimales por defecto, según la tabla oficial ISO 4217.
_ZERO_DECIMALS = frozenset(
    "BIF CLP DJF GNF ISK JPY KMF KRW PYG RWF UGX VND VUV XAF XOF XPF".split()
)
_THREE_DECIMALS = frozenset("BHD IQD JOD KWD LYD OMR TND".split())


def minor_units(code: str) -> int:
    """Número de decimales que admite la moneda (0, 2 o 3)."""
    if code in _ZERO_DECIMALS:
        return 0
    if code in _THREE_DECIMALS:
        return 3
    return 2
