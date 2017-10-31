# coding: utf-8
#
# LICENSE
# Please refer to the LICENSE.txt in the https://github.com/JPCERTCC/aa-tools/
#

import sys
import os
import re
import urllib.request
import json
import datetime
import numpy as np
import pandas as pd
import configparser
import argparse
from util.multi_layer_net_extend import MultiLayerNetExtend
from util.utils import Adam

parser = argparse.ArgumentParser(description="Detecting LM commands with Deep Learning.")
parser.add_argument("-m", "--mapping", action="store_true", default=False, help="Create mapping")
parser.add_argument("-i", "--ignore", action="store_true", default=False,
                    help="Ignore mode. If you learn normal command execution, use this mode.")
parser.add_argument("-v", "--verbose", action="store_true", default=False, help="verbose messages")
args = parser.parse_args()

CONFIG_FILE = "config/config.ini"

inifile = configparser.SafeConfigParser()
if os.path.exists(CONFIG_FILE):
    inifile.read(CONFIG_FILE)
    print("[*] Load ini file.")
else:
    sys.exit("[!] %s is not found." % CONFIG_FILE)

DATA_CSV = inifile.get("settings", "data_csv_name")
BLACKLIST = inifile.get("settings", "blacklist")
LEARNING_RATE = inifile.getfloat("settings", "learning_rate")
MAX_EPOCHS = inifile.getint("settings", "max_epochs")
ELSHOST = inifile.get("settings", "els_server")
ELSPORT = inifile.get("settings", "els_port")
CHECK_HOURS = inifile.getint("settings", "ml_check_hour")

NODES = [re.compile("tasklist", re.IGNORECASE), re.compile("ver", re.IGNORECASE),
         re.compile("ipconfig", re.IGNORECASE), re.compile("net time", re.IGNORECASE),
         re.compile("cd ", re.IGNORECASE), re.compile("systeminfo", re.IGNORECASE),
         re.compile("netstat", re.IGNORECASE), re.compile("whoami", re.IGNORECASE),
         re.compile("nbtstat", re.IGNORECASE), re.compile("net start", re.IGNORECASE),
         re.compile("set", re.IGNORECASE), re.compile("qprocess", re.IGNORECASE),
         re.compile("nslookup", re.IGNORECASE), re.compile("fsutil", re.IGNORECASE),
         re.compile("net view", re.IGNORECASE), re.compile("type ", re.IGNORECASE),
         re.compile("net use ", re.IGNORECASE), re.compile("echo ", re.IGNORECASE),
         re.compile("net user", re.IGNORECASE), re.compile("net group", re.IGNORECASE),
         re.compile("net localgroup", re.IGNORECASE), re.compile("dsquery", re.IGNORECASE),
         re.compile("net config", re.IGNORECASE), re.compile("csvde", re.IGNORECASE),
         re.compile("net share", re.IGNORECASE), re.compile("quser", re.IGNORECASE),
         re.compile("net session", re.IGNORECASE), re.compile("query ", re.IGNORECASE),
         re.compile("tracert", re.IGNORECASE), re.compile("nltest", re.IGNORECASE),
         re.compile("at ", re.IGNORECASE), re.compile("move ", re.IGNORECASE),
         re.compile("schtasks", re.IGNORECASE), re.compile("copy ", re.IGNORECASE),
         re.compile("ren ", re.IGNORECASE), re.compile("reg ", re.IGNORECASE),
         re.compile("wmic", re.IGNORECASE), re.compile("powershell", re.IGNORECASE),
         re.compile("md ", re.IGNORECASE), re.compile("cscript", re.IGNORECASE),
         re.compile("runas ", re.IGNORECASE), re.compile("sc ", re.IGNORECASE),
         re.compile("netsh", re.IGNORECASE), re.compile("wusa", re.IGNORECASE),
         re.compile("icacls", re.IGNORECASE), re.compile("del ", re.IGNORECASE),
         re.compile("taskkill", re.IGNORECASE), re.compile("klist", re.IGNORECASE),
         re.compile("wevtutil", re.IGNORECASE), re.compile("rd ", re.IGNORECASE)]


# Learning and check answer
def commnd_check(t_train, x_train, t_test, x_test, hostnames, commands, ihostnames, icommands, colum_size, train_size):
    if ihostnames:
        for host in ihostnames:
            icom_set = np.zeros((1, 50), dtype=int)
            for command in icommands:
                if host in command[0]:
                    ccount = 0
                    for node in NODES:
                        if node.match(command[1]):
                            icom_set[0, ccount] = 1
                        ccount += 1
            t_train = np.append(t_train, 0)
            x_train = np.append(x_train, icom_set, axis=0)

    while 1:
        network = MultiLayerNetExtend(input_size=colum_size, hidden_size_list=[100, 50, 20], output_size=2)
        optimizer = Adam(lr=LEARNING_RATE)

        iter_per_epoch = max(train_size / 100, 1)
        epoch_cnt = 0

        for i in range(10000):
            batch_mask = np.random.choice(train_size, 100)
            x_batch = x_train[batch_mask]
            t_batch = t_train[batch_mask]

            grads = network.gradient(x_batch, t_batch)
            optimizer.update(network.params, grads)

            if i % int(iter_per_epoch) == 0:
                accuracy, precision, recall = network.check(x_test, t_test)
                accuracy_t, precision_t, recall_t = network.check(x_train, t_train)
                try:
                    f = (2 * recall * precision) / (recall + precision)
                    f_t = (2 * recall_t * precision_t) / (recall_t + precision_t)
                except ZeroDivisionError:
                    continue

                if args.verbose == True:
                    print("[*] test epoch:%i  | accuracy %f, precision %f, recall %f, F-measure %f"
                        % (epoch_cnt, accuracy, precision, recall, f))
                    print("[*] train epoch:%i | accuracy %f, precision %f, recall %f, F-measure %f"
                        % (epoch_cnt, accuracy_t, precision_t, recall_t, f_t))

                accuracy_gap = accuracy - accuracy_t
                epoch_cnt += 1
                if epoch_cnt >= MAX_EPOCHS or f >= 0.965 or accuracy == 1 or accuracy_t == 1:
                    print("[*] Learning finished.")
                    break
        if f >= 0.965 and accuracy_gap < 0.02 and accuracy_gap > -0.02 and accuracy != 1 and accuracy_t != 1:
            break
        else:
            print("[!] Learning again.")

    result = []
    for host in hostnames:
        com_set = np.zeros((1, 50), dtype=int)
        for command in commands:
            if host in command[0]:
                ccount = 0
                for node in NODES:
                    if node.match(command[1]):
                        com_set[0, ccount] = 1
                    ccount += 1
        result.append([host, network.answer(com_set)[0]])

    print("[*] Check finished.")
    return result


# Check blacklist
def blacklist_check(data):
    url = "http://" + ELSHOST + ":" + ELSPORT + "/cmdlogs/command/"
    method = "POST"
    headers = {"Content-Type": "application/json"}
    postdata = {"script": "ctx._source.AlertLevel=2"}
    json_data = json.dumps(postdata).encode("utf-8")

    blackcmp = []
    f = open(BLACKLIST, "r")
    for blitem in f:
        blitem = blitem.rstrip()
        blackcmp.append(re.compile(blitem, re.IGNORECASE))
    f.close()

    for item in data:
        for blackitem in blackcmp:
            if blackitem.search(item["_source"]["command"]):
                urlpost = url + item["_id"] + "/_update?pretty"
                try:
                    request = urllib.request.Request(urlpost, data=json_data, method=method, headers=headers)
                    urllib.request.urlopen(request)
                    print("[*] Updated Elasticsearch data id %s." % item["_id"])
                except:
                    sys.exit("[!] Can't update Elasticsearch server data.")


# Change Elasticsearch data
def els_query(attack_results, data):
    url = "http://" + ELSHOST + ":" + ELSPORT + "/cmdlogs/command/"
    method = "POST"
    headers = {"Content-Type": "application/json"}
    postdata = {"script": "ctx._source.AlertLevel=1"}
    ignoredata = {"script": "ctx._source.Ignore=1"}
    json_data = json.dumps(postdata).encode("utf-8")
    json_idata = json.dumps(ignoredata).encode("utf-8")

    for result in attack_results:
        if result[1] == 1:
            for item in data:
                if result[0] in item["_source"]["Hostname"]:
                    for node in NODES:
                        if node.match(item["_source"]["command"]):
                            urlpost = url + item["_id"] + "/_update?pretty"
                            try:
                                request = urllib.request.Request(urlpost, data=json_data, method=method, headers=headers)
                                urllib.request.urlopen(request)
                                print("[*] Updated Elasticsearch data id %s." % item["_id"])
                            except:
                                sys.exit("[!] Can't update Elasticsearch server data.")

    if args.ignore:
        for item in data:
            urlpost = url + item["_id"] + "/_update?pretty"
            try:
                request = urllib.request.Request(urlpost, data=json_idata, method=method, headers=headers)
                urllib.request.urlopen(request)
                print("[*] Updated Elasticsearch data id %s." % item["_id"])
            except:
                sys.exit("[!] Can't update Elasticsearch server data.")


# Load Elasticsearch data
def els_search():
    url = "http://" + ELSHOST + ":" + ELSPORT + "/cmdlogs/command/_search?pretty"
    method = "POST"
    headers = {"Content-Type": "application/json"}

    date = datetime.datetime.today()
    todate = date.strftime("%Y-%m-%d %H:%M:%S")
    date -= datetime.timedelta(hours=CHECK_HOURS)
    fromdate = date.strftime("%Y-%m-%d %H:%M:%S")

    obj = {"size" : 10000, "query": {"bool": {"must": [{"match": {"AlertLevel": 0}}, {"match": {"Ignore": 0}}],
                              "filter": {"range": {"timestamp": {"gte": fromdate, "lt": todate, "format": "yyyy-MM-dd HH:mm:ss"}}}}}}
    obj_ignore = {"size" : 10000, "query": {"match": {"Ignore": 1}}}
    #obj = {"query": {"range" : {"timestamp" : {"gte" : "now-6H/m","lt" :  "now/m"}}}}
    json_data = json.dumps(obj).encode("utf-8")
    json_data_ignore = json.dumps(obj_ignore).encode("utf-8")

    try:
        request = urllib.request.Request(url, data=json_data, method=method, headers=headers)
        request_ignore = urllib.request.Request(url, data=json_data_ignore, method=method, headers=headers)

        with urllib.request.urlopen(request) as response:
            response_body = response.read().decode("utf-8")
        json_result = json.loads(response_body)

        with urllib.request.urlopen(request_ignore) as response_ignore:
            response_body_ignore = response_ignore.read().decode("utf-8")
        json_result_ignore = json.loads(response_body_ignore)

        print("[*] Get Elasticsearch data.")
    except:
        sys.exit("[!] Can't connect Elasticsearch server.")

    return json_result, json_result_ignore


# Create mapping
def els_mapping():
    url = "http://" + ELSHOST + ":" + ELSPORT + "/cmdlogs/"
    headers = {"Content-Type": "application/json"}

    try:
        request = urllib.request.Request(url, method="GET")
        urllib.request.urlopen(request)
        print("[*] Already created mapping.")
    except:
        try:
            obj = {"mappings": {"command": {"properties": {"Hostname": {"type": "string"},
                                                           "Username": {"type": "string"},
                                                           "command": {"type": "string"},
                                                           "AlertLevel": {"type": "integer"},
                                                           "Ignore": {"type": "integer"},
                                                           "timestamp": {"type": "date", "format": "YYYY-MM-dd HH:mm:ss"}
                                                           }}}}
            json_data = json.dumps(obj).encode("utf-8")
            request = urllib.request.Request(url, data=json_data, method="PUT", headers=headers)
            urllib.request.urlopen(request)
            print("[*] Created mapping.")
        except:
            sys.exit("[!] Can't connect Elasticsearch server.")


def main():
    if args.mapping:
        els_mapping()
        sys.exit("[*] Done.")

    json_result, json_data_ignore = els_search()

    hostnames = []
    commands = []
    if int(json_result["hits"]["total"]) > 0:
        hit_items = json_result["hits"]["hits"]
        for item in hit_items:
            hostnames.append(item["_source"]["Hostname"])
            commands.append([item["_source"]["Hostname"],
                             item["_source"]["command"]])
        hostnames = set(hostnames)
    else:
        sys.exit("[*] There is no current log.")

    ihostnames = []
    icommands = []
    if int(json_data_ignore["hits"]["total"]) > 0:
        hit_items = json_data_ignore["hits"]["hits"]
        for item in hit_items:
            ihostnames.append(item["_source"]["Hostname"])
            icommands.append([item["_source"]["Hostname"],
                             item["_source"]["command"]])
        ihostnames = set(ihostnames)

    try:
        data = pd.read_csv(DATA_CSV, dtype="int")
    except:
        sys.exit("[!] Can't open training data csv.")

    result_all = []
    load = data
    nn = len(load.index)/10
    dp = load.sample(n=int(nn))

    for j in dp.index:
        load = load.drop(j, axis=0)

    colum_size = len(load.columns) - 1

    t_train = load["attack"].as_matrix()
    x_train = load.drop("attack", axis=1).as_matrix()
    t_test = dp["attack"].as_matrix()
    x_test = dp.drop("attack", axis=1).as_matrix()

    train_size = x_train.shape[0]
    attack_results = commnd_check(t_train, x_train, t_test, x_test, hostnames, commands, ihostnames, icommands, colum_size, train_size)

    els_query(attack_results, json_result["hits"]["hits"])

    blacklist_check(json_result["hits"]["hits"])

if __name__ == "__main__":
    main()
