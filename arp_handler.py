from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.packet.ethernet import ethernet, ETHER_BROADCAST
from pox.lib.packet.arp import arp

log = core.getLogger()

class ArpController(object):
    def __init__(self, connection):
        self.connection = connection
        connection.addListeners(self)
        
        # IP to MAC mapping (ARP Cache)
        self.arp_table = {}
        # MAC to Port mapping (For standard forwarding)
        self.mac_to_port = {}

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            return

        # Learn which port this MAC address is connected to
        self.mac_to_port[packet.src] = event.port

        # Intercept ARP packets
        if packet.type == packet.ARP_TYPE:
            arp_pkt = packet.payload
            self.arp_table[arp_pkt.protosrc] = arp_pkt.hwsrc

            if arp_pkt.opcode == arp.REQUEST:
                if arp_pkt.protodst in self.arp_table:
                    log.info("Controller answering ARP request for %s", arp_pkt.protodst)
                    
                    arp_reply = arp()
                    arp_reply.opcode = arp.REPLY
                    arp_reply.hwsrc = self.arp_table[arp_pkt.protodst]
                    arp_reply.hwdst = arp_pkt.hwsrc
                    arp_reply.protosrc = arp_pkt.protodst
                    arp_reply.protodst = arp_pkt.protosrc

                    eth = ethernet(type=packet.type, 
                                   src=self.arp_table[arp_pkt.protodst], 
                                   dst=packet.src)
                    eth.set_payload(arp_reply)

                    msg = of.ofp_packet_out()
                    msg.data = eth.pack()
                    # FIX: Use OFPP_IN_PORT to bypass switch loop-prevention drops
                    msg.actions.append(of.ofp_action_output(port = of.OFPP_IN_PORT))
                    msg.in_port = event.port
                    self.connection.send(msg)
                
                else:
                    log.info("Unknown IP. Flooding ARP request for %s", arp_pkt.protodst)
                    msg = of.ofp_packet_out()
                    msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                    msg.data = event.ofp
                    msg.in_port = event.port
                    self.connection.send(msg)
            
            elif arp_pkt.opcode == arp.REPLY:
                log.info("Learned new MAC from network: %s -> %s", arp_pkt.protosrc, arp_pkt.hwsrc)

        # Handle non-ARP traffic (like ICMP Ping or TCP/UDP)
        else:
            if packet.dst in self.mac_to_port:
                out_port = self.mac_to_port[packet.dst]
                
                log.info("Installing flow rule for %s -> %s", packet.src, packet.dst)
                
                # Create the Flow Modification message
                flow_msg = of.ofp_flow_mod()
                flow_msg.match = of.ofp_match.from_packet(packet, event.port)
                flow_msg.actions.append(of.ofp_action_output(port = out_port))
                
                # 60-second timeouts so you have plenty of time to screenshot!
                flow_msg.idle_timeout = 60 
                flow_msg.hard_timeout = 120 
                
                self.connection.send(flow_msg)

                # Forward the actual packet
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = out_port))
                msg.data = event.ofp
                msg.in_port = event.port
                self.connection.send(msg)
            else:
                # We don't know the destination, flood it
                msg = of.ofp_packet_out()
                msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
                msg.data = event.ofp
                msg.in_port = event.port
                self.connection.send(msg)

def launch():
    def start_switch(event):
        log.info("Controlling Switch %s", event.connection)
        ArpController(event.connection)
    
    core.openflow.addListenerByName("ConnectionUp", start_switch)
