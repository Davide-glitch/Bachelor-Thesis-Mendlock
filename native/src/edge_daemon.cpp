#include "../include/mendlock_core.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstring>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>

namespace
{

    float read_cpu_temp_celsius()
    {
        std::ifstream f("/sys/class/thermal/thermal_zone0/temp");
        if (!f.is_open())
            return -1.0f;
        int millideg = 0;
        f >> millideg;
        return static_cast<float>(millideg) / 1000.0f;
    }

    // Protocol: "TRIGRAM\t<s1>\t<s2>\n" or "SEQ\t<s1>\t<s2>\n" or "PING\n"
    std::string handle_command(const std::string &line)
    {
        auto t0 = std::chrono::high_resolution_clock::now();
        std::istringstream iss(line);
        std::string cmd, a, b;
        std::getline(iss, cmd, '\t');
        std::getline(iss, a, '\t');
        std::getline(iss, b, '\n');

        float score = 0.0f;
        if (cmd == "TRIGRAM")
        {
            score = mendlock_trigram_cosine(a.c_str(), b.c_str());
        }
        else if (cmd == "SEQ")
        {
            score = mendlock_levenshtein_ratio(a.c_str(), b.c_str());
        }
        else if (cmd == "PING")
        {
            score = 1.0f;
        }

        auto t1 = std::chrono::high_resolution_clock::now();
        double us = std::chrono::duration<double, std::micro>(t1 - t0).count();
        float temp = read_cpu_temp_celsius();

        std::ostringstream oss;
        oss << "{\"score\":" << score << ",\"compute_us\":" << us << ",\"cpu_temp_c\":" << temp << "}\n";
        return oss.str();
    }

} // namespace

int main(int argc, char **argv)
{
    int port = (argc > 1) ? std::stoi(argv[1]) : 9090;
    int server_fd = ::socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0)
    {
        std::cerr << "Failed to create socket\n";
        return 1;
    }

    int opt = 1;
    ::setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(static_cast<uint16_t>(port));

    if (::bind(server_fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0 ||
        ::listen(server_fd, 16) < 0)
    {
        std::cerr << "Failed to bind/listen on port " << port << "\n";
        ::close(server_fd);
        return 1;
    }

    std::cout << "Mendlock C++20 Edge Daemon listening on 0.0.0.0:" << port << "...\n";

    while (true)
    {
        sockaddr_in client_addr{};
        socklen_t client_len = sizeof(client_addr);
        int client_fd = ::accept(server_fd, reinterpret_cast<sockaddr *>(&client_addr), &client_len);
        if (client_fd < 0)
            continue;

        char buffer[4096];
        ssize_t n = ::read(client_fd, buffer, sizeof(buffer) - 1);
        if (n > 0)
        {
            buffer[n] = '\0';
            std::string resp = handle_command(std::string(buffer));
            (void)::write(client_fd, resp.data(), resp.size());
        }
        ::close(client_fd);
    }
    return 0;
}