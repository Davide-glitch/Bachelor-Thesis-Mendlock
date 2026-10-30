#ifndef MENDLOCK_CORE_H
#define MENDLOCK_CORE_H

#include <stddef.h>
#include <stdint.h>

#if defined(_WIN32) || defined(__CYGWIN__)
#define MENDLOCK_API __declspec(dllexport)
#else
#define MENDLOCK_API __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C"
{
#endif

    /**
     * Computes character-trigram cosine similarity on normalized strings.
     * Matches mendlock.text.trigram_sim() exactly.
     */
    MENDLOCK_API float mendlock_trigram_cosine(const char *s1, const char *s2);

    /**
     * Computes sequence similarity ratio in [0.0, 1.0] (2 * M / (|s1| + |s2|)).
     * Matches difflib.SequenceMatcher(None, s1, s2).ratio() on ID and DOM path strings.
     */
    MENDLOCK_API float mendlock_levenshtein_ratio(const char *s1, const char *s2);

    /**
     * Computes visual similarity between two contiguous RGB float32 thumbnails
     * of shape (height, width, 3) with values in [0.0, 1.0].
     * Combines 20% RGB mean similarity, 30% luminance NCC, and 50% Sobel/gradient NCC.
     */
    MENDLOCK_API float mendlock_visual_similarity(
        const float *img_a,
        const float *img_b,
        int width,
        int height);

#ifdef __cplusplus
}
#endif

#endif // MENDLOCK_CORE_H