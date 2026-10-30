#include "../include/mendlock_core.h"

#include <cassert>
#include <chrono>
#include <cmath>
#include <iostream>
#include <vector>

int main()
{
    std::cout << "Running Mendlock C++20 Native Kernel Tests...\n";

    // 1. Regression test for the old 32-byte prefix bug:
    // Two strings with identical first 40 characters but different suffixes MUST NOT return 1.0.
    const char *long_a = "button_primary_checkout_action_container_submit_now";
    const char *long_b = "button_primary_checkout_action_container_cancel_all";
    float sim_long = mendlock_levenshtein_ratio(long_a, long_b);
    assert(sim_long < 0.90f && sim_long > 0.70f);
    std::cout << "  [PASS] Full-length string check (no 32-byte truncation): score = " << sim_long << "\n";

    // 2. Trigram cosine test
    float tri_identical = mendlock_trigram_cosine("place order", "place order");
    float tri_partial = mendlock_trigram_cosine("place order", "place order preview");
    float tri_disjoint = mendlock_trigram_cosine("place order", "delete account");
    assert(std::abs(tri_identical - 1.0f) < 1e-5f);
    assert(tri_partial > 0.60f && tri_partial < 0.95f);
    assert(tri_disjoint < 0.25f);
    std::cout << "  [PASS] Trigram cosine similarity: identical=" << tri_identical
              << ", partial=" << tri_partial << ", disjoint=" << tri_disjoint << "\n";

    // 3. Visual similarity test (32x16x3 float32 thumbnails)
    const int W = 32, H = 16;
    std::vector<float> img1(W * H * 3, 0.2f);
    std::vector<float> img2(W * H * 3, 0.2f);
    for (int i = 0; i < W * H; ++i)
    {
        img1[i * 3] = static_cast<float>(i % W) / static_cast<float>(W);
        img2[i * 3] = static_cast<float>(i % W) / static_cast<float>(W);
    }
    float vis_same = mendlock_visual_similarity(img1.data(), img2.data(), W, H);
    assert(std::abs(vis_same - 1.0f) < 1e-5f);
    std::cout << "  [PASS] Visual gradient + luminance NCC: identical=" << vis_same << "\n";

    // 4. Micro-benchmark: 10,000 candidate evaluations
    const int ITERS = 10000;
    auto t0 = std::chrono::high_resolution_clock::now();
    volatile float sink = 0.0f;
    for (int i = 0; i < ITERS; ++i)
    {
        sink += mendlock_trigram_cosine("place the order and confirm payment", "place order");
        sink += mendlock_levenshtein_ratio("body/main/section/div/button", "body/main/section/div/div/button");
        sink += mendlock_visual_similarity(img1.data(), img2.data(), W, H);
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    double total_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    std::cout << "  [BENCH] " << ITERS << " full candidate signal evaluations in "
              << total_ms << " ms (" << (total_ms * 1000.0 / ITERS) << " us / candidate)\n";
    return 0;
}