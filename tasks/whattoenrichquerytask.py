import json
import requests
import urllib
from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis
from qgis.PyQt.QtWidgets import QListWidgetItem, QMessageBox, QProgressDialog
from SPARQLWrapper import SPARQLWrapper, JSON
from qgis.core import (
    QgsApplication, QgsTask, QgsMessageLog,
)

MESSAGE_CATEGORY = 'WhatToEnrichQueryTask'


class WhatToEnrichQueryTask(QgsTask):
    """This shows how to subclass QgsTask"""

    def __init__(self, description, triplestoreurl, query, searchTerm, prefixes, searchResult, progress):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.triplestoreurl = triplestoreurl
        self.query = query
        self.progress = progress
        self.prefixes = prefixes
        self.labels = None
        # self.progress = progress
        self.urilist = None
        self.sortedatt = None
        self.searchTerm = searchTerm
        self.searchResult = searchResult
        self.results = None
        s = QSettings()  # getting proxy from qgis options settings
        self.proxyEnabled = s.value("proxy/proxyEnabled")
        self.proxyType = s.value("proxy/proxyType")
        self.proxyHost = s.value("proxy/proxyHost")
        self.proxyPort = s.value("proxy/proxyPort")
        self.proxyUser = s.value("proxy/proxyUser")
        self.proxyPassword = s.value("proxy/proxyPassword")

    def run(self):
        QgsMessageLog.logMessage('Started task "{}"'.format(self.description()), MESSAGE_CATEGORY, Qgis.Info)
        if self.searchTerm == "":
            return False
        concept = "<" + self.searchTerm + ">"
        if self.proxyHost != None and self.proxyHost != "" and self.proxyPort != None and self.proxyPort != "":
            QgsMessageLog.logMessage('Proxy? ' + str(self.proxyHost), MESSAGE_CATEGORY, Qgis.Info)
            proxy = urllib.request.ProxyHandler({'http': self.proxyHost})
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)
        sparql = SPARQLWrapper(self.triplestoreurl,
                               agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11")
        sparql.setQuery("".join(self.prefixes) + self.query)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        self.searchResult.clear()
        if len(results["results"]["bindings"]) == 0:
            return False
        maxcons = int(results["results"]["bindings"][0]["countcon"]["value"])
        attlist = {}
        self.urilist = {}
        for result in results["results"]["bindings"]:
            attlist[result["rel"]["value"][result["rel"]["value"].rfind('/') + 1:]] = round(
                (int(result["countrel"]["value"]) / maxcons) * 100, 2)
            self.urilist[result["rel"]["value"][result["rel"]["value"].rfind('/') + 1:]] = result["rel"]["value"]
        self.sortedatt = sorted(attlist.items(), reverse=True, key=lambda kv: kv[1])
        self.labels = {}
        postdata = {}
        postdata["language"] = "en"
        postdata["format"] = "json"
        postdata["action"] = "wbgetentities"
        atts = [""]
        attcounter = 0
        count = 0
        for att in attlist.keys():
            if att.startswith("P") and count < 50:
                atts[attcounter] += att + "|"
                count += 1
        atts[0] = atts[0][:-1]
        i = 0
        for att in atts:
            url = "https://www.wikidata.org/w/api.php"  # ?action=wbgetentities&format=json&language=en&ids="+atts
            postdata["ids"] = att
            # msgBox=QMessageBox()
            # msgBox.setText(str(postdata))
            # msgBox.exec()
            myResponse = json.loads(requests.post(url, postdata).text)
            # msgBox=QMessageBox()
            # msgBox.setText(str(myResponse))
            # msgBox.exec()
            for ent in myResponse["entities"]:
                print(ent)
                if "en" in myResponse["entities"][ent]["labels"]:
                    self.labels[ent] = myResponse["entities"][ent]["labels"]["en"]["value"]
                i = i + 1
        return True

    def finished(self, result):
        counter = 0
        if self.sortedatt != None:
            for att in self.sortedatt:
                if att[1] < 1:
                    continue
                if att[0] in self.labels:
                    item = QListWidgetItem()
                    item.setText(self.labels[att[0]] + " (" + str(att[1]) + "%)")
                    item.setData(1, self.urilist[att[0]])
                    self.searchResult.addItem(item)
                    counter += 1
                else:
                    item = QListWidgetItem()
                    item.setText(att[0] + " (" + str(att[1]) + "%)")
                    item.setData(1, self.urilist[att[0]])
                    self.searchResult.addItem(item)
        else:
            msgBox = QMessageBox()
            msgBox.setText("The enrichment search query did not yield any results!")
            msgBox.exec()
        self.progress.close()
