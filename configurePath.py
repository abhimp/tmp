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
        print r
        print >> fp, r
    fp.close()
    p = subprocess.call("sudo bash " + scriptName, shell=True)

def getDefaultRoute(ip, netmask, ifc):
    net = netaddr.IPNetwork("%s/%s"%(ip, netmask))
    net = "%s/%s"%(net.network, net.prefixlen)
    route = "route add -net %s dev %s"%(net, ifc)
    return route

def getIps():
    return {w['addr']:x for x in netifaces.interfaces()  for y,z in netifaces.ifaddresses(x).items() if y==netifaces.AF_INET for w in z if 'addr' in w}

def getNextHopIp(edges, s, r):
    
    ip2Net = {x[0] if not x[1].startswith("s") else x[1]:x[2] for x in edges if x[0] == r or x[1] == r}
    return ip2Net.get(s, None)

def adjustRouting(routs, host, edges):
    if not host.startswith("h"):
        routs = routs[host]
    else:
        pseudoRouts = [y+[x.split("x")[1]] for x in routs if x.startswith(host+"x") for y in routs[x]]
        print pseudoRouts
        routs = pseudoRouts
        
    newRouts = []
    for x in routs:
        net = netaddr.IPNetwork(x[0])
        x[0] = "%s/%s"%(net.network, net.prefixlen)
        x[2] = getNextHopIp(edges, x[1], x[2])
        newRouts += [x]
    return newRouts

def saveViscousIp(gw, ip, ifc):
    path="/tmp/viscous_ifconf/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = os.path.join(path, ifc)
    fp = open(fname, "w")
    print >> fp, "iface=%s"%(ifc)
    print >> fp, "ip=%s"%(ip)
    print >> fp, "gw=%s"%(gw)
    fp.close()
        

def setRoutingTable(net2Ip, routes):
    ips = getIps()
    #print ips
    routeEntries = []
    #create local routes to 

    intfs = set()
    ipRuleRoute = []
    fileContent = []
    for x in routes:
        #print x[0], net2Ip[x[1]], getNextHopIp(edges, x[1], x[2])
        if net2Ip[x[1]][0] not in ips:
            continue
        #print x[0], ips.get(net2Ip[x[1]][0], "unknown"), getNextHopIp(edges, x[1], x[2])
        ip = net2Ip[x[1]]
        ifc = ips.get(ip[0], "unknown")
        localNet = netaddr.IPNetwork(ip[0], ip[1])
        #network = netaddr.IPNetwork(x[0])
        if len(x) > 3 and x[0] == "0.0.0.0/0": # x= ['0.0.0.0/0', u's4', '10.1.0.97'(, u'2')]
            ipRuleRoute += [ "ip rule add from {ip} table {table}".format(ip=net2Ip[x[1]][0], table=x[3])]
            ipRuleRoute += [ "ip route add {network} dev {ifc} scope link table {table}".format(network=str(localNet.network)+"/"+str(localNet.prefixlen), ifc=ifc, table=x[3])]
            ipRuleRoute += [ "ip route add default via %s dev %s table %s"%(x[2], ifc, x[3])]
            fileContent += [[x[2], ip[0], ifc]]
        else:
            routeEntries += ["route add -net %s gw %s dev %s"%(x[0], x[2], ifc)]
            intfs.add((ip[0], ip[1], ifc))

    localrout = []
    print "policy route", ipRuleRoute
    print "fileContent", fileContent
    for fc in fileContent:
        saveViscousIp(*fc)

    for iface in intfs:
        #print "iface", iface
        removeRoutingTable(iface[2])
        localrout += [getDefaultRoute(iface[0], iface[1], iface[2])]
    #print intfs
    #print routes

    addRouteingTable(localrout + routeEntries)
    addRouteingTable(ipRuleRoute)

def setServerIp(host, edges):
    if not host.startswith("hvc"):
        return
    cid = host[3:]
    ips = []
    server = 'hvs'+cid
    ips = [x[2] for x in edges if x[1] == server]
    serverMacro = "VISCOUS_SERVER_"+server
    fp = open("/etc/bash.bashrc", "a")
    print >> fp, ""
    for ip in ips:
        print >> fp, "export $"+serverMacro+"="+ip
    fp.close()

def loadInfo():
    info = json.load(open("/local/data.json"))
    host = socket.gethostname().split(".")[0]

    if "VHOST" in os.environ and len(os.environ["VHOST"]) != 0:
        host = os.environ["VHOST"]

    edges = [[str(x).split("x")[0] if str(x).find("x")>=0 else str(x) for x in y] for y in info['edges']]
    
    net2Ip = {x[0] if not x[1].startswith("s") else x[1]:(x[2], x[3]) for x in edges if x[0] == host or x[1] == host}
    #print net2Ip
    route = adjustRouting(info['rout'], host, edges)
    print net2Ip


    if "VHOST" in os.environ and len(os.environ["VHOST"]) != 0:
        return
    setRoutingTable(net2Ip, route)

    setServerIp(host, edges)



def main():
    loadInfo()
    exit()

if __name__ == "__main__":
    main()
