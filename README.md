# SDN-Mininet-ARP-Handler (Orange Problem)

| | |
|---|---|
| **Name** | Subramani B M |
| **Section** | 4H |
| **SRN** | PES1UG24CS473 |


## 📌 Project Overview
This repository contains the solution for the "Orange Problem" assignment. The objective of this project is to implement a custom Software-Defined Networking (SDN) controller application that shifts Address Resolution Protocol (ARP) handling away from traditional switch-level flooding and centralizes it within the SDN controller. 

By actively intercepting ARP requests, dynamically learning MAC addresses, and installing hardware flow rules, this implementation significantly reduces broadcast traffic and optimizes network latency.

---

## 🛠️ Topology & Environment
* **Environment:** Ubuntu Linux VM
* **Network Emulator:** Mininet
* **Topology:** `single,3` (One OpenFlow switch connected to three hosts)
* **SDN Controller:** POX (OpenFlow 1.0)
* **Language:** Python 3

**Why this topology?**
A single switch with three hosts is the minimal viable environment to perfectly demonstrate ARP broadcasting, controller interception, and MAC learning without introducing unnecessary routing complexities.

---

## 🧠 Controller Logic (`arp_handler.py`)
The custom POX module implements the following core SDN mechanisms:

1. **Dynamic MAC Learning:** The controller monitors `PacketIn` events. When an ARP request arrives, it extracts the sender's IP and MAC address and stores them in an internal dictionary (`self.arp_table`).
2. **ARP Interception & Forging:** Instead of flooding known ARP requests, the controller intercepts them. If the target MAC is known, the controller crafts an ARP Reply packet and sends it directly back out the ingress port using the `of.OFPP_IN_PORT` action to bypass OpenFlow loop-prevention drops.
3. **Proactive Flow Rule Installation:** Once the MAC addresses are resolved, standard traffic (like ICMP Ping) triggers the controller to push explicit `ofp_flow_mod` rules to the switch. These hardware rules (`idle_timeout=60`, `hard_timeout=120`) allow the switch to route subsequent packets at line-rate without querying the controller.

---

## 🚀 Execution Steps

### 1. Start the Controller
Navigate to your POX directory and launch the custom ARP handler:
```bash
cd ~/pox
./pox.py arp_handler
```

### 2. Start the Network
Open a second terminal, clear any stale network states, and launch the Mininet topology:
```bash
sudo mn -c
sudo mn --topo single,3 --controller remote
```

### 3. Test Host Discovery
In the Mininet CLI, initiate an ICMP ping to trigger the ARP resolution and flow rule installation:
```
mininet> h1 ping -c 5 h2
```

### 4. Verify OpenFlow Rules
Immediately after the ping completes, verify that the controller successfully pushed the hardware rules to the switch:
```
mininet> dpctl dump-flows
```

---

## 📊 Performance Observation & Analysis
By analyzing the ICMP ping statistics, the impact of the SDN controller's logic is clearly visible:

* **Initial Latency Spike:** The very first ping sequence takes significantly longer (e.g., ~1086 ms). This is because the controller must process the `PacketIn` event, flood the initial unknown ARP request, process the reply, forge the response back to H1, and calculate the route.

* **Line-Rate Drop:** Subsequent pings drop to near-zero latency (e.g., ~0.113 ms). This proves that the `ofp_flow_mod` rule was successfully installed on the switch hardware, allowing packets to bypass the controller entirely.

---

## 📸 Proof of Execution

### 1. Controller Logs (MAC Learning & Interception)
This screenshot demonstrates the controller flooding the initial request, learning the MAC, answering subsequent requests directly, and pushing the OpenFlow rules.

<img width="783" height="351" alt="image" src="https://github.com/user-attachments/assets/3ff692ce-0eec-4c14-bc51-f887cc97aaf0" />

---

### 2. ICMP Ping Statistics (Latency Optimization)
This screenshot proves the massive latency drop between the 1st ping (controller handled) and the 3rd/4th pings (switch hardware handled).

<img width="618" height="473" alt="image" src="https://github.com/user-attachments/assets/04dfb8d2-de97-48f0-aa7e-d46d5b7d9abb" />

---

### 3. OpenFlow Table Dump (`dpctl dump-flows`)
This screenshot validates that the explicit flow rules (with `idle_timeout=60`) were successfully pushed to `s1`.

<img width="1836" height="114" alt="image" src="https://github.com/user-attachments/assets/93411430-13f7-4039-893a-95ea7abaa0e9" />

---

### 4. Wireshark Packet Trace
This packet capture proves the functional behavior on the wire: The initial ARP Broadcast, the Controller's direct ARP Reply, and the seamless ICMP Echo sequence.

<img width="1847" height="344" alt="image" src="https://github.com/user-attachments/assets/8815d2f2-a7b6-4f1d-b4b4-032bf7f2fb50" />
