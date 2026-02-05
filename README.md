# 🚀 Enterprise-Grade HTTP Load Balancer

A robust, multi-threaded Layer 7 Load Balancer built entirely from scratch using Python's raw socket library. This project demonstrates advanced distributed system concepts including Weighted Round Robin algorithms, in-memory caching, path-based routing, and application-layer security.

---

## 🧠 Project Overview

This is not just a traffic forwarder. It is a fully functional Reverse Proxy designed to handle high-concurrency scenarios. It sits between clients (browsers) and a cluster of backend servers, intelligently distributing load based on server capacity and network conditions.

---

## 🏗️ Architecture

```
graph LR
    Client[Client / Browser] -- HTTP Request --> LB(Load Balancer :8080)
    LB -- "Route /app1" --> S1[Server 1 (High Spec)]
    LB -- "Route /app2" --> S2[Server 2 (Legacy)]
    LB -- "Round Robin" --> S3[Server 3 (Scalable)]
    LB -.-> Cache[(In-Memory Cache)]
    LB -.-> Firewall{DDoS Protection}
```

---

## 🌟 Key Features

### ⚡ Performance & Scaling

**Weighted Round Robin:**
Distributes traffic based on server weights (e.g., Server 1 gets 3x load of Server 2). Useful for heterogeneous clusters.

**In-Memory Caching:**
Reduces backend load by caching frequent responses in RAM. (Includes Auto-Expiry/TTL).

**Active Health Checks:**
Background threads continuously "ping" servers. If a server dies, it is instantly removed from rotation. When it recovers, it is automatically re-added.

---

### 🛡️ Security & Routing

**Layer 7 Content Switching:**
Routes traffic based on URL paths.

* /app1 → Forced to Server 1
* /app2 → Forced to Server 2

**DDoS Mitigation:**
Application-layer rate limiting. Automatically bans IPs that exceed request limits (e.g., >20 requests/10s).

**Admin Dashboard:**
Real-time web interface to monitor server health, request counts, and security logs.

---

## 📂 Project Structure

| File        | Description                                                                          |
| ----------- | ------------------------------------------------------------------------------------ |
| ultra_lb.py | The Core Engine. Contains the Load Balancer, Cache Manager, and Security Middleware. |
| server1.py  | Backend Server 1 (Simulated High-Performance Node, Port 9001).                       |
| server2.py  | Backend Server 2 (Simulated Standard Node, Port 9002).                               |
| server3.py  | Backend Server 3 (Simulated Scalable Node, Port 9003).                               |
| README.md   | Project Documentation.                                                               |

---

## 🚀 Getting Started

### Prerequisites

* Python 3.x installed.
* No external dependencies (uses standard libraries only).

---

### Installation

Clone the repository:

```
git clone https://github.com/Ashishayu100/Advanced-HTTP-Load-Balancer.git
cd Advanced-HTTP-Load-Balancer
```

---

## Running the System

You need to run the backend servers first, then the load balancer. Open 4 separate terminal windows:

### Terminal 1 (Server 1):

```
python server1.py
```

### Terminal 2 (Server 2):

```
python server2.py
```

### Terminal 3 (Server 3):

```
python server3.py
```

### Terminal 4 (The Load Balancer):

```
python ultra_lb.py
```

---

## 🎮 How to Test (Demo Scenarios)

Once running, open your browser to:

```
http://127.0.0.1:8080
```

---

### 1. Test Weighted Round Robin

**Action:** Refresh the page multiple times slowly.

**Result:** Check the terminal logs. You will see Server 1 receiving more traffic than Server 2 or 3, respecting the configured weights.

---

### 2. Test Caching (Speed)

**Action:** Refresh the page twice quickly.

**Result:** The first request hits the server. The second request shows
⚡ [CACHE HIT] in the logs and is served instantly without touching the backend.

---

### 3. Test Fault Tolerance (Self-Healing)

**Action:** Go to Terminal 1 and press Ctrl+C to kill Server 1.

**Result:** The Load Balancer detects it within 5 seconds ([-] Server 9001 is DOWN). Refresh the browser, and traffic will seamlessly shift to Server 2 and 3.

---

### 4. Test DDoS Protection

**Action:** Mash the F5 (Refresh) key as fast as you can.

**Result:** You will be banned! The browser will show
**429 Too Many Requests.**

**Verify:** Go to the Admin Dashboard:

```
http://127.0.0.1:8080/stats
```

to see your IP in the "Banned" list.

---

## 📊 Admin Dashboard

Visit:

```
http://127.0.0.1:8080/stats
```

You can see:

* Backend Status: Live Up/Down status.
* Traffic Metrics: Total request counts per server.
* Security Logs: List of currently banned IPs and remaining ban duration.

---

## 👥 Team Members

* **Ashish Kumar**
  Roll No: 2301MC61
  Department: Mathematics and Computing

* **T. Lakshmi Narasimham**
  Roll No: 2301MC14
  Department: Mathematics and Computing

* **G. Sri Thanishka**
  Roll No: 2301MC28
  Department: Mathematics and Computing

* **Mala Ram**
  Roll No: 2301MC46
  Department: Mathematics and Computing

---

This project was built for the **Computer Networks course at IIT Patna** to demonstrate low-level socket programming and distributed system architecture.
