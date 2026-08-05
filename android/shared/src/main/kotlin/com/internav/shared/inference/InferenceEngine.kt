package com.internav.shared.inference

import com.internav.shared.model.CandidateCell
import com.internav.shared.model.FeatureSchema
import kotlin.math.pow
import kotlin.math.sqrt

data class InferenceResult(
    val predictedCellId: String?,
    val centerX: Double?,
    val centerY: Double?,
    val confidence: Double,
    val candidateCells: List<CandidateCell>,
    val inferenceTimeMs: Double
)

data class ReferenceVector(
    val cellId: String,
    val centerX: Double,
    val centerY: Double,
    val vector: DoubleArray
)

class InferenceEngine(
    private val referenceVectors: List<ReferenceVector>,
    private val featureSchema: FeatureSchema?,
    private val k: Int = 3
) {
    private val bssidVocabulary: List<String> = featureSchema?.bssidVocabulary ?: emptyList()
    private val missingApValue: Double = featureSchema?.missingApValue ?: 0.0

    fun estimatePosition(observations: List<RssiObservation>): InferenceResult {
        val startTime = System.nanoTime()

        if (observations.isEmpty() || referenceVectors.isEmpty()) {
            return InferenceResult(null, null, null, 0.0, emptyList(), 0.0)
        }

        val queryVector = buildFeatureVector(observations)
        val distances = referenceVectors.map { rv ->
            DistanceResult(rv, euclideanDistance(queryVector, rv.vector))
        }.sortedBy { it.distance }

        val topK = distances.take(k)
        if (topK.isEmpty()) {
            return InferenceResult(null, null, null, 0.0, emptyList(), 0.0)
        }

        val totalScore = topK.sumOf { 1.0 / (it.distance + 0.001) }
        val candidates = topK.map { d ->
            val score = 1.0 / (d.distance + 0.001)
            CandidateCell(cellId = d.reference.cellId, score = score)
        }

        val best = topK.first()
        val confidence = if (totalScore > 0) (1.0 / (best.distance + 0.001)) / totalScore else 0.0

        val elapsed = (System.nanoTime() - startTime) / 1_000_000.0

        return InferenceResult(
            predictedCellId = best.reference.cellId,
            centerX = best.reference.centerX,
            centerY = best.reference.centerY,
            confidence = confidence,
            candidateCells = candidates,
            inferenceTimeMs = elapsed
        )
    }

    private fun buildFeatureVector(observations: List<RssiObservation>): DoubleArray {
        if (bssidVocabulary.isEmpty()) {
            return DoubleArray(0)
        }

        val vector = DoubleArray(bssidVocabulary.size) { missingApValue }
        val obsMap = observations.associate { it.bssid to it.rssi }

        for ((index, bssid) in bssidVocabulary.withIndex()) {
            val rssi = obsMap[bssid]
            if (rssi != null) {
                vector[index] = normalizeRssi(rssi)
            }
        }

        return vector
    }

    private fun normalizeRssi(rssi: Int): Double {
        val normalized = (rssi + 100.0) / 100.0
        return normalized.coerceIn(0.0, 1.0)
    }

    private fun euclideanDistance(a: DoubleArray, b: DoubleArray): Double {
        if (a.size != b.size) return Double.MAX_VALUE
        var sum = 0.0
        for (i in a.indices) {
            sum += (a[i] - b[i]).pow(2)
        }
        return sqrt(sum)
    }

    companion object {
        private const val TAG = "InferenceEngine"
    }
}

data class RssiObservation(
    val bssid: String,
    val rssi: Int
)

private data class DistanceResult(
    val reference: ReferenceVector,
    val distance: Double
)
