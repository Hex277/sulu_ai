# search_config.py

# ══════════════════════════════════════════════════════════════
#  SABİTLƏR
# ══════════════════════════════════════════════════════════════
ANYTXT_URL        = "http://127.0.0.1:9920"
ANYTXT_DELAY      = 0.15          # Sorğular arası fasilə (saniyə)
SIZE_LIMIT_BYTES  = 20 * 1024     # 10 KB — tam mətn oxuma limiti
SIBLING_MAX       = 10            # Qonşu fayl limiti

# ══════════════════════════════════════════════════════════════
#  STOP WORDS
# ══════════════════════════════════════════════════════════════
LEXICAL_STOP_WORDS = {
    'ver', 'verin', 'goster', 'tap', 'mene', 'haqqinda', 'siyahisi',
    'listini', 'melumat', 'yaz', 'etrafli', 'indi', 'axtar', 'bildir',
    'de', 'tapmaq', 'lazim', 'isteyirem', 'butun', 'hamisi',
    'nece', 'nedir', 'kimdir', 'hansi', 'olan', 'ucun', 'ile',
    'var', 'yox', 'edir', 'olub', 'etdi'
}

ANYTXT_STOP_WORDS = LEXICAL_STOP_WORDS | {
    've', 'va', 'da', 'ki', 'bu', 'bir', 'ol', 'ne',
    'cox', 'bele', 'amma', 'lakin', 'ancaq', 'hem',
    'ise', 'eger', 'olar', 'olur', 'deyil', 'etmek',
    'olaraq', 'kimi', 'qadar', 'bari', 'onun', 'bunun',
    'ona', 'buna', 'onlar', 'bunlar', 'menim', 'senin',
    'bizim', 'sizin', 'onlarin', 'get', 'gel', 'bax',
    'gor', 'et', 'ha', 'bilmek', 'lazim', 'gelir'
}