### current bpython session - make changes and save to reevaluate session.
### lines beginning with ### will be ignored.
### To return to bpython without reevaluating make no changes to this file
### or save an empty file.
import json
import netifaces
import os
import socket
import subprocess
import shlex
import netaddr

def removeRoutingTable(inf):
    scriptName = "/tmp/" + inf + ".sh"
    cmd = 'printf "sudo route del -net %s gw %s netmask %s dev %s\n" `route -n | grep '+inf+' | sed "s/ \+/ /g" | cut -d\  -f1,2,3,8` > ' + scriptName
    args = shlex.split(cmd)
    print args
    p = subprocess.call(cmd, shell=True)
    print p
    if p is not 0:
        raise "error"

    p = subprocess.call("bash " + scriptName, shell=True)
    print p

def addRouteingTable(routes):
    scriptName = "/tmp/routes"
    fp = open(scriptName, "w")
    for r in routes:
        print >> fp, r
    fp.close()
    p = subprocess.call("sudo bash " + scriptName, shell=True)

def getDefaultRoute(ip, netmask, ifc):
    net = netaddr.IPNetwork("%s/%s"%(ip, netmask))
    net = "%s/%s"%(net.netmask, net.prefixlen)
    route = "route add -net %s dev %s"%(net, ifc)
    return route

def getIps():
    return {w['addr']:x for x in netifaces.interfaces()  for y,z in netifaces.ifaddresses(x).items() if y==netifaces.AF_INET for w in z if 'addr' in w}

def getNextHopIp(edges, s, r):
    
    ip2Net = {x[0] if not x[1].startswith("s") else x[1]:x[2] for x in edges if x[0] == r or x[1] == r}
    return ip2Net.get(s, None)

def loadInfo():
    info = json.load(open("/local/data.json"))
    host = socket.gethostname().split(".")[0]

    if "VHOST" in os.environ and len(os.environ["VHOST"]) != 0:
        host = os.environ["VHOST"]

    edges = [[str(x).split("x")[0] if str(x).find("x")>=0 else str(x) for x in y] for y in info['edges']]
    
    net2Ip = {x[0] if not x[1].startswith("s") else x[1]:(x[2], x[3]) for x in edges if x[0] == host or x[1] == host}
    #print net2Ip

    ips = getIps()
    #print ips
    routes = []
    #create local routes to 

    intfs = set()
    for x in info["rout"][host]:
        #print x[0], net2Ip[x[1]], getNextHopIp(edges, x[1], x[2])
        if net2Ip[x[1]][0] not in ips:
            continue
        #print x[0], ips.get(net2Ip[x[1]][0], "unknown"), getNextHopIp(edges, x[1], x[2])
        ip = net2Ip[x[1]]
        ifc = ips.get(ip[0], "unknown")
        network = netaddr.IPNetwork(x[0])
        route = "route add -net %s/%s gw %s dev %s"%(network.network, network.prefixlen, getNextHopIp(edges, x[1], x[2]), ifc)
        print route
        routes += [route]
        intfs.add((ip[0], ip[1], ifc))

    localrout = []
    for iface in intfs:
        localrout += [getDefaultRoute(*iface)]
        removeRoutingTable(iface[2])
    print intfs
    print routes

    addRouteingTable(localrout + routes)






def main():
    loadInfo()
    exit()

if __name__ == "__main__":
    main()
