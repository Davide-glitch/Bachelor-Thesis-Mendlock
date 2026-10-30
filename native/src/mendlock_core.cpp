#include "../include/mendlock_core.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

#if defined(__AVX2__)
#include <immintrin.h>
#endif

namespace {

std::string normalize_for_trigrams(const char* raw) {
    if (!raw) return "";
    std::string out;
    out.reserve(std::strlen(raw) + 4);
    out.push_back(' ');
    out.push_back(' ');

    bool in_word = false;
    bool has_any = false;
    for (const unsigned char* p = reinterpret_cast<const unsigned char*>(raw); *p != '\0'; ++p) {
        unsigned char c = *p;
        if (c >= 'A' && c <= 'Z') c = static_cast<unsigned char>(c + ('a' - 'A'));
        if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) {
            if (!in_word && has_any) {
                out.push_back(' ');
            }
            out.push_back(static_cast<char>(c));
            in_word = true;
            has_any = true;
        } else {
            in_word = false;
        }
    }

    if (!has_any) return "";
    out.push_back(' ');
    return out;
}

struct TrigramEntry {
    uint32_t key;
    uint32_t count;
};

std::vector<TrigramEntry> extract_trigram_counts(const std::string& padded) {
    if (padded.size() < 3) return {};
    const size_t n = padded.size() - 2;
    std::vector<uint32_t> raw_keys(n);
    const auto* bytes = reinterpret_cast<const uint8_t*>(padded.data());

    for (size_t i = 0; i < n; ++i) {
        raw_keys[i] = (static_cast<uint32_t>(bytes[i]) << 16) |
                      (static_cast<uint32_t>(bytes[i + 1]) << 8) |
                      static_cast<uint32_t>(bytes[i + 2]);
    }

    std::sort(raw_keys.begin(), raw_keys.end());

    std::vector<TrigramEntry> counts;
    counts.reserve(n);
    for (uint32_t k : raw_keys) {
        if (!counts.empty() && counts.back().key == k) {
            counts.back().count++;
        } else {
            counts.push_back({k, 1});
        }
    }
    return counts;
}

size_t count_matching_chars(
    const char* s1, size_t lo1, size_t hi1,
    const char* s2, size_t lo2, size_t hi2,
    std::vector<uint16_t>& dp_buf, size_t stride
) {
    size_t best_i = lo1, best_j = lo2, best_size = 0;

    for (size_t i = lo1; i < hi1; ++i) {
        for (size_t j = lo2; j < hi2; ++j) {
            if (s1[i] == s2[j]) {
                uint16_t k = (i > lo1 && j > lo2) ? static_cast<uint16_t>(dp_buf[(i - 1) * stride + (j - 1)] + 1) : 1;
                dp_buf[i * stride + j] = k;
                if (k > best_size) {
                    best_size = k;
                    best_i = i + 1 - k;
                    best_j = j + 1 - k;
                }
            } else {
                dp_buf[i * stride + j] = 0;
            }
        }
    }

    if (best_size == 0) return 0;

    size_t left = (best_i > lo1 && best_j > lo2)
        ? count_matching_chars(s1, lo1, best_i, s2, lo2, best_j, dp_buf, stride)
        : 0;
    size_t right = (best_i + best_size < hi1 && best_j + best_size < hi2)
        ? count_matching_chars(s1, best_i + best_size, hi1, s2, best_j + best_size, hi2, dp_buf, stride)
        : 0;

    return left + best_size + right;
}

float compute_ncc(const float* x, const float* y, size_t n) {
    if (n == 0) return 0.0f;

    double sum_x = 0.0, sum_y = 0.0;
    for (size_t i = 0; i < n; ++i) {
        sum_x += x[i];
        sum_y += y[i];
    }
    const float mean_x = static_cast<float>(sum_x / static_cast<double>(n));
    const float mean_y = static_cast<float>(sum_y / static_cast<double>(n));

    float cov = 0.0f, var_x = 0.0f, var_y = 0.0f;
    size_t i = 0;

#if defined(__AVX2__)
    __m256 v_mx = _mm256_set1_ps(mean_x);
    __m256 v_my = _mm256_set1_ps(mean_y);
    __m256 v_cov = _mm256_setzero_ps();
    __m256 v_vx = _mm256_setzero_ps();
    __m256 v_vy = _mm256_setzero_ps();

    for (; i + 8 <= n; i += 8) {
        __m256 vx = _mm256_sub_ps(_mm256_loadu_ps(x + i), v_mx);
        __m256 vy = _mm256_sub_ps(_mm256_loadu_ps(y + i), v_my);
        v_cov = _mm256_fmadd_ps(vx, vy, v_cov);
        v_vx = _mm256_fmadd_ps(vx, vx, v_vx);
        v_vy = _mm256_fmadd_ps(vy, vy, v_vy);
    }

    alignas(32) float buf_cov[8], buf_vx[8], buf_vy[8];
    _mm256_store_ps(buf_cov, v_cov);
    _mm256_store_ps(buf_vx, v_vx);
    _mm256_store_ps(buf_vy, v_vy);
    for (int k = 0; k < 8; ++k) {
        cov += buf_cov[k];
        var_x += buf_vx[k];
        var_y += buf_vy[k];
    }
#endif

    for (; i < n; ++i) {
        float dx = x[i] - mean_x;
        float dy = y[i] - mean_y;
        cov += dx * dy;
        var_x += dx * dx;
        var_y += dy * dy;
    }

    const float std_x = std::sqrt(var_x / static_cast<float>(n));
    const float std_y = std::sqrt(var_y / static_cast<float>(n));

    if (std_x < 1e-3f || std_y < 1e-3f) {
        return (std_x < 1e-3f && std_y < 1e-3f) ? 1.0f : 0.0f;
    }

    float ncc = (cov / static_cast<float>(n)) / (std_x * std_y);
    return std::max(0.0f, ncc);
}

} // namespace

extern "C" {

MENDLOCK_API float mendlock_trigram_cosine(const char* s1, const char* s2) {
    std::string n1 = normalize_for_trigrams(s1);
    std::string n2 = normalize_for_trigrams(s2);
    if (n1.empty() || n2.empty()) return 0.0f;

    auto c1 = extract_trigram_counts(n1);
    auto c2 = extract_trigram_counts(n2);
    if (c1.empty() || c2.empty()) return 0.0f;

    uint64_t dot = 0;
    uint64_t norm1 = 0;
    uint64_t norm2 = 0;

    for (const auto& e : c1) norm1 += static_cast<uint64_t>(e.count) * e.count;
    for (const auto& e : c2) norm2 += static_cast<uint64_t>(e.count) * e.count;

    size_t i = 0, j = 0;
    while (i < c1.size() && j < c2.size()) {
        if (c1[i].key == c2[j].key) {
            dot += static_cast<uint64_t>(c1[i].count) * c2[j].count;
            ++i;
            ++j;
        } else if (c1[i].key < c2[j].key) {
            ++i;
        } else {
            ++j;
        }
    }

    double denom = std::sqrt(static_cast<double>(norm1)) * std::sqrt(static_cast<double>(norm2));
    return denom > 0.0 ? static_cast<float>(static_cast<double>(dot) / denom) : 0.0f;
}

MENDLOCK_API float mendlock_levenshtein_ratio(const char* s1, const char* s2) {
    if (!s1 || !s2) return 0.0f;
    const size_t len1 = std::strlen(s1);
    const size_t len2 = std::strlen(s2);
    if (len1 == 0 && len2 == 0) return 1.0f;
    if (len1 == 0 || len2 == 0) return 0.0f;
    if (len1 == len2 && std::memcmp(s1, s2, len1) == 0) return 1.0f;

    const size_t l1 = std::min<size_t>(len1, 512);
    const size_t l2 = std::min<size_t>(len2, 512);

    std::vector<uint16_t> dp_buf(l1 * l2, 0);
    size_t matches = count_matching_chars(s1, 0, l1, s2, 0, l2, dp_buf, l2);
    return static_cast<float>((2.0 * static_cast<double>(matches)) / static_cast<double>(l1 + l2));
}

MENDLOCK_API float mendlock_visual_similarity(
    const float* img_a,
    const float* img_b,
    int width,
    int height
) {
    if (!img_a || !img_b || width < 3 || height < 3) return 0.0f;

    const size_t num_pixels = static_cast<size_t>(width) * static_cast<size_t>(height);
    double sum_a[3] = {0.0, 0.0, 0.0};
    double sum_b[3] = {0.0, 0.0, 0.0};

    std::vector<float> gray_a(num_pixels);
    std::vector<float> gray_b(num_pixels);

    for (size_t i = 0; i < num_pixels; ++i) {
        const size_t idx = i * 3;
        float ra = img_a[idx], ga = img_a[idx + 1], ba = img_a[idx + 2];
        float rb = img_b[idx], gb = img_b[idx + 1], bb = img_b[idx + 2];

        sum_a[0] += ra; sum_a[1] += ga; sum_a[2] += ba;
        sum_b[0] += rb; sum_b[1] += gb; sum_b[2] += bb;

        gray_a[i] = (ra + ga + ba) / 3.0f;
        gray_b[i] = (rb + gb + bb) / 3.0f;
    }

    const double inv_n = 1.0 / static_cast<double>(num_pixels);
    double diff_r = std::abs(sum_a[0] * inv_n - sum_b[0] * inv_n);
    double diff_g = std::abs(sum_a[1] * inv_n - sum_b[1] * inv_n);
    double diff_b = std::abs(sum_a[2] * inv_n - sum_b[2] * inv_n);
    float color_sim = static_cast<float>(1.0 - (diff_r + diff_g + diff_b) / 3.0);

    float lum_ncc = compute_ncc(gray_a.data(), gray_b.data(), num_pixels);

    const int gw = width - 1;
    const int gh = height - 1;
    const size_t grad_size = static_cast<size_t>(gw) * static_cast<size_t>(gh);
    std::vector<float> mag_a(grad_size);
    std::vector<float> mag_b(grad_size);

    for (int r = 0; r < gh; ++r) {
        const int row_offset = r * width;
        const int next_row = (r + 1) * width;
        const int out_row = r * gw;
        for (int c = 0; c < gw; ++c) {
            float gxa = gray_a[row_offset + c + 1] - gray_a[row_offset + c];
            float gya = gray_a[next_row + c] - gray_a[row_offset + c];
            mag_a[out_row + c] = std::hypot(gxa, gya);

            float gxb = gray_b[row_offset + c + 1] - gray_b[row_offset + c];
            float gyb = gray_b[next_row + c] - gray_b[row_offset + c];
            mag_b[out_row + c] = std::hypot(gxb, gyb);
        }
    }

    float grad_ncc = compute_ncc(mag_a.data(), mag_b.data(), grad_size);
    return 0.20f * color_sim + 0.30f * lum_ncc + 0.50f * grad_ncc;
}

} // extern "C"
