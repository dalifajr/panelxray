package com.dalifajr.jualan_listener.utils

object RupiahParser {
    private data class AmountCandidate(
        val amount: Long,
        val score: Int,
        val index: Int,
    )

    private val amountRegex = Regex(
        pattern = """(?i)(?:rp|idr)\s*([0-9]{1,3}(?:[.,\s][0-9]{3})+|[0-9]+)(?:[.,][0-9]{1,2})?"""
    )

    private val genericAmountRegex = Regex(
        pattern = """(?<![0-9])([0-9]{1,3}(?:[.,\s][0-9]{3})+|[0-9]{3,})(?![0-9])"""
    )

    private val paymentKeywords = listOf(
        "pembayaran",
        "bayar",
        "transfer",
        "masuk",
        "diterima",
        "berhasil",
        "kredit",
        "debit",
        "transaksi",
        "trx",
    )

    private val avoidKeywords = listOf(
        "saldo",
        "tersisa",
        "sisa",
        "limit",
        "tagihan",
        "fee",
        "biaya",
    )

    fun parseAmount(rawText: String): Long? {
        val text = rawText.replace('\u00A0', ' ').trim()
        if (text.isEmpty()) return null

        val fromRupiahKeyword = amountRegex.findAll(text)
            .mapNotNull { match ->
                val amount = normalizeNumber(match.groupValues.getOrNull(1).orEmpty()) ?: return@mapNotNull null
                val context = extractContext(text, match.range.first, match.range.last)
                AmountCandidate(amount = amount, score = scoreContext(context), index = match.range.first)
            }
            .toList()

        if (fromRupiahKeyword.isNotEmpty()) {
            return pickBestCandidate(fromRupiahKeyword)
        }

        val normalized = text.lowercase()
        val hasPaymentKeyword = paymentKeywords.any { key -> normalized.contains(key) }
        if (!hasPaymentKeyword) {
            return null
        }

        // Fallback if notification omits currency symbol but still likely payment-related.
        val fallback = genericAmountRegex.findAll(text)
            .mapNotNull { match ->
                val amount = normalizeNumber(match.groupValues.getOrNull(1).orEmpty()) ?: return@mapNotNull null
                val context = extractContext(text, match.range.first, match.range.last)
                AmountCandidate(amount = amount, score = scoreContext(context), index = match.range.first)
            }
            .toList()

        return pickBestCandidate(fallback)
    }

    private fun pickBestCandidate(candidates: List<AmountCandidate>): Long? {
        if (candidates.isEmpty()) return null

        val best = candidates
            .sortedWith(compareByDescending<AmountCandidate> { it.score }.thenBy { it.index })
            .firstOrNull()
            ?: return null

        if (best.score < 0) {
            return null
        }

        return best.amount
    }

    private fun extractContext(text: String, start: Int, end: Int): String {
        val left = (start - 40).coerceAtLeast(0)
        val right = (end + 40).coerceAtMost(text.lastIndex)
        return text.substring(left, right + 1).lowercase()
    }

    private fun scoreContext(context: String): Int {
        var score = 0

        if (context.contains("rp") || context.contains("idr")) {
            score += 2
        }

        paymentKeywords.forEach { keyword ->
            if (context.contains(keyword)) {
                score += 2
            }
        }

        avoidKeywords.forEach { keyword ->
            if (context.contains(keyword)) {
                score -= 3
            }
        }

        return score
    }

    private fun normalizeNumber(raw: String): Long? {
        val digits = raw
            .replace(".", "")
            .replace(",", "")
            .replace(" ", "")
            .trim()
        if (digits.isEmpty()) return null
        return digits.toLongOrNull()
    }
}
