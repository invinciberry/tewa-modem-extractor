def generate_a1(hex_str):
    cts = [
        'QbNUTaMecPWVSKdCgXIJRrsfYXwyqpvnDHWzQuPmAGtAxRTphBcwBnNkjbFmvVMqaFkEutSrDCxsCKjBzEyDEUJTZfHZghMHYFdeASGNaUgFtdbYRkshJHkFNXMcKdfw',
        'NXMcKdfwRkshJHkFaUgFtdbYYFdeASGNZfHZghMHzEyDEUJTDCxsCKjBaFkEutSrjbFmvVMqhBcwBnNkAGtAxRTpDHWzQuPmYXwyqpvngXIJRrsfcPWVSKdCQbNUTaMe',
        'eMaTUNbQCdKSVWPcfsrRJIXgnvpqywXYmPuQzWHDpTRxAtGAkNnBwcBhqMVvmFbjrStuEkFaBjKCsxCDTJUEDyEzHMhgZHfZNGSAedFYYbdtFgUaFkHJhskRwfdKcMXN',
        'CbntTaMGFPWTSkdCtXIYRrsfaXyyqpvRbHWAJuPSAGtacRTpVKcmBnNevbFMvSMPDFkEuRSDXCssCKjszEyDEUJCZfckghBHYFseASaNaUgFPfbYRLSubTkFKXMcKdfH',
        'gXIJRrsfNXMcKdfwYXwZqpvnQuPmDHWzAGtQxRTpjbFmvVMqDCxsjBCKzEyDEUJTHbCwBnIkZfHZghMHYASGFdeNcPWVSKdCaUgFtdbYRkshJHkFQbNUTaMeaFkLutSr',
    ]
    hex_clean = ''.join(c for c in hex_str.upper() if c in '0123456789ABCDEF')
    if len(hex_clean) < 12:
        return "MAC错误"
    v19 = [ord(c) for c in reversed(hex_clean[-8:])]
    v10 = next(((c - 48 | j) for j, c in enumerate(v19) if 49 <= c <= 57), 5)
    results = [[] for _ in range(len(cts))]
    for k in range(len(v19)):
        v15 = v19[k] & v19[7 - k] if k < 4 else v19[k] | v19[k - 4]
        v16 = v15 + v10
        if v16 > 127:
            v16, v10 = k, k
        for i in range(len(cts)):
            results[i].append(cts[i][v16])
        v10 += max(k, 1)
    return '  '.join(''.join(lst) for lst in results)


if __name__ == "__main__":
    import sys
    mac = sys.argv[1] if len(sys.argv) > 1 else input("Enter MAC address: ")
    print(generate_a1(mac))
