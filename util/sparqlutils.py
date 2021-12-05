from SPARQLWrapper import SPARQLWrapper, JSON, GET, POST, BASIC, DIGEST
import urllib
import requests
import sys
from urllib.request import urlopen
import json
from qgis.core import Qgis, QgsGeometry
from qgis.core import QgsMessageLog
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import QSettings
from rdflib import Graph

MESSAGE_CATEGORY = "SPARQLUtils"


class SPARQLUtils:
    supportedLiteralTypes = {"http://www.opengis.net/ont/geosparql#wktLiteral": "wkt",
                             "http://www.opengis.net/ont/geosparql#gmlLiteral": "gml",
                             "http://www.opengis.net/ont/geosparql#wkbLiteral": "wkb",
                             "http://www.opengis.net/ont/geosparql#geoJSONLiteral": "geojson",
                             "http://www.opengis.net/ont/geosparql#kmlLiteral": "kml",
                             "http://www.opengis.net/ont/geosparql#dggsLiteral": "dggs"}

    authmethods={"HTTP BASIC":BASIC,"HTTP DIGEST":DIGEST}

    classicon=QIcon(":/icons/resources/icons/class.png")
    geoclassicon=QIcon(":/icons/resources/icons/geoclass.png")
    instanceicon=QIcon(":/icons/resources/icons/instance.png")
    geometrycollectionicon=QIcon(":/icons/resources/icons/geometrycollection.png")
    featurecollectionicon=QIcon(":/icons/resources/icons/featurecollection.png")
    earthinstanceicon=QIcon(":/icons/resources/icons/earthinstance.png")
    classnode="Class"
    geoclassnode="GeoClass"
    instancenode="Instance"
    geoinstancenode="GeoInstance"
    collectionclassnode="CollectionClass"
    instancesloadedindicator="InstancesLoaded"
    treeNodeToolTip="Double click to load, right click for menu"

    @staticmethod
    def executeQuery(triplestoreurl, query,triplestoreconf=None):
        s = QSettings()  # getting proxy from qgis options settings
        proxyEnabled = s.value("proxy/proxyEnabled")
        proxyType = s.value("proxy/proxyType")
        proxyHost = s.value("proxy/proxyHost")
        proxyPort = s.value("proxy/proxyPort")
        proxyUser = s.value("proxy/proxyUser")
        proxyPassword = s.value("proxy/proxyPassword")
        if proxyHost != None and proxyHost != "" and proxyPort != None and proxyPort != "":
            QgsMessageLog.logMessage('Proxy? ' + str(proxyHost), MESSAGE_CATEGORY, Qgis.Info)
            proxy = urllib.request.ProxyHandler({'http': proxyHost})
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)
        QgsMessageLog.logMessage('Started task "{}"'.format(query.replace("<","").replace(">","")), MESSAGE_CATEGORY, Qgis.Info)
        sparql = SPARQLWrapper(triplestoreurl)
        if triplestoreconf!=None and "auth" in triplestoreconf and "userCredential" in triplestoreconf["auth"] \
                and triplestoreconf["auth"]["userCredential"]!="" \
                and "userPassword" in triplestoreconf["auth"] \
                and triplestoreconf["auth"]["userPassword"] != None:
            #QgsMessageLog.logMessage('Credentials? ' + str(triplestoreconf["auth"]["userCredential"])+" "+str(triplestoreconf["auth"]["userPassword"]), MESSAGE_CATEGORY, Qgis.Info)
            if "method" in triplestoreconf["auth"] and triplestoreconf["auth"]["method"] in SPARQLUtils.authmethods:
                sparql.setHTTPAuth(SPARQLUtils.authmethods[triplestoreconf["auth"]["method"]])
            else:
                sparql.setHTTPAuth(BASIC)
            sparql.setCredentials(triplestoreconf["auth"]["userCredential"], triplestoreconf["auth"]["userPassword"])
        sparql.setQuery(query)
        sparql.setMethod(GET)
        sparql.setReturnFormat(JSON)
        try:
            results = sparql.queryAndConvert()
            if "status_code" in results:
                QgsMessageLog.logMessage("Result: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
                raise Exception
        except Exception as e:
            try:
                sparql = SPARQLWrapper(triplestoreurl,
                                       agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11")
                sparql.setQuery(query)
                if triplestoreconf != None and "auth" in triplestoreconf and "userCredential" in triplestoreconf["auth"] \
                        and triplestoreconf["auth"]["userCredential"] != "" \
                        and "userPassword" in triplestoreconf["auth"] \
                        and triplestoreconf["auth"]["userPassword"] != None:
                    #QgsMessageLog.logMessage(
                    #    'Credentials? ' + str(triplestoreconf["auth"]["userCredential"]) + " " + str(
                    #       triplestoreconf["auth"]["userPassword"]), MESSAGE_CATEGORY, Qgis.Info)
                    if "method" in triplestoreconf["auth"] and triplestoreconf["auth"][
                        "method"] in SPARQLUtils.authmethods:
                        sparql.setHTTPAuth(SPARQLUtils.authmethods[triplestoreconf["auth"]["method"]])
                    else:
                        sparql.setHTTPAuth(BASIC)
                    sparql.setCredentials(triplestoreconf["auth"]["userCredential"],
                                          triplestoreconf["auth"]["userPassword"])
                sparql.setMethod(POST)
                sparql.setReturnFormat(JSON)
                results = sparql.queryAndConvert()
                if "status_code" in results:
                    QgsMessageLog.logMessage("Result: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
                    raise Exception
            except:
                QgsMessageLog.logMessage("Exception: " + str(e), MESSAGE_CATEGORY, Qgis.Info)
                if "OntopUnsupportedInputQueryException: The expression Exists" in str(e):
                    return "Exists error"
                return False
        QgsMessageLog.logMessage("Result: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
        return results

    @staticmethod
    def invertPrefixes(prefixes):
        #QgsMessageLog.logMessage("Invert Prefixes: " + str(prefixes), MESSAGE_CATEGORY, Qgis.Info)
        inv_map = {v: k for k, v in prefixes.items()}
        return inv_map

    @staticmethod
    def labelFromURI(uri,prefixlist=None):
        if "#" in uri:
            prefix=uri[:uri.rfind("#")+1]
            if prefixlist!=None and prefix in prefixlist:
                return str(prefixlist[prefix])+":"+str(uri[uri.rfind("#") + 1:])
            return uri[uri.rfind("#") + 1:]
        if "/" in uri:
            prefix=uri[:uri.rfind("/")+1]
            if prefixlist!=None and prefix in prefixlist:
                return str(prefixlist[prefix])+":"+str(uri[uri.rfind("/") + 1:])
            return uri[uri.rfind("/") + 1:]
        return uri

    @staticmethod
    def shortenLiteral(literal,numchars):
        return literal[numchars:]

    @staticmethod
    def expandRelValToAmount(query,amount):
        QgsMessageLog.logMessage('ExpandQuery '+str(amount)+"_" + str(query), MESSAGE_CATEGORY, Qgis.Info)
        if "?rel" not in query and "?val" not in query:
            return query
        selectpart=query[0:query.find("WHERE")]
        optionals="?item ?rel ?val . "
        if amount>1:
            for i in range(1,amount+1):
                selectpart+=" ?rel"+str(i)+" ?val"+str(i)+" "
                if i==1:
                    optionals += "OPTIONAL { ?val ?rel" + str(i) + " ?val" + str(i) + " . "
                else:
                    optionals+="OPTIONAL { ?val"+str(i-1)+" ?rel"+str(i)+" ?val"+str(i)+" . "
            for i in range(1,amount+1):
                optionals+="}"
        query=query.replace(query[0:query.find("WHERE")],selectpart).replace("?item ?rel ?val . ",optionals)
        QgsMessageLog.logMessage('ExpandQuery '+str(query), MESSAGE_CATEGORY, Qgis.Info)
        return query

    @staticmethod
    def loadGraph(graphuri):
        s = QSettings()  # getting proxy from qgis options settings
        proxyEnabled = s.value("proxy/proxyEnabled")
        proxyType = s.value("proxy/proxyType")
        proxyHost = s.value("proxy/proxyHost")
        proxyPort = s.value("proxy/proxyPort")
        proxyUser = s.value("proxy/proxyUser")
        proxyPassword = s.value("proxy/proxyPassword")
        if proxyHost != None and proxyHost != "" and proxyPort != None and proxyPort != "":
            #QgsMessageLog.logMessage('Proxy? ' + str(proxyHost), MESSAGE_CATEGORY, Qgis.Info)
            proxy = urllib.request.ProxyHandler({'http': proxyHost})
            opener = urllib.request.build_opener(proxy)
            urllib.request.install_opener(opener)
        #QgsMessageLog.logMessage('Started task "{}"'.format("Load Graph"), MESSAGE_CATEGORY, Qgis.Info)
        graph = Graph()
        try:
            if graphuri.startswith("http"):
                graph.load(graphuri)
            else:
                filepath = graphuri.split(".")
                result = graph.parse(graphuri, format=filepath[len(filepath) - 1])
        except Exception as e:
            QgsMessageLog.logMessage('Failed "{}"'.format(str(e)), MESSAGE_CATEGORY, Qgis.Info)
            # self.exception = str(e)
            return None
        return graph

    @staticmethod
    def detectLiteralType(literal):
        try:
            geom = QgsGeometry.fromWkt(literal)
            return "wkt"
        except:
            print("no wkt")
        try:
            geom = QgsGeometry.fromWkb(bytes.fromhex(literal))
            return "wkb"
        except:
            print("no wkb")
        try:
            json.loads(literal)
            return "geojson"
        except:
            print("no geojson")
        return ""

    @staticmethod
    def handleURILiteral(uri):
        result = []
        if uri.startswith("http") and uri.endswith(".map"):
            try:
                f = urlopen(uri)
                myjson = json.loads(f.read())
                if "data" in myjson and "type" in myjson["data"] and myjson["data"]["type"] == "FeatureCollection":
                    features = myjson["data"]["features"]
                    for feat in features:
                        result.append(feat["geometry"])
                return result
            except:
                QgsMessageLog.logMessage("Error getting geoshape " + str(uri) + " - " + str(sys.exc_info()[0]))
        return None

    ## Executes a SPARQL endpoint specific query to find labels for given classes. The query may be configured in the configuration file.
    #  @param self The object pointer.
    #  @param classes array of classes to find labels for
    #  @param query the class label query
    @staticmethod
    def getLabelsForClasses(classes, query, triplestoreconf, triplestoreurl):
        result = {}
        # url="https://www.wikidata.org/w/api.php?action=wbgetentities&props=labels&ids="
        if "SELECT" in query:
            vals = "VALUES ?class { "
            for qid in classes:
                vals += qid + " "
            vals += "}\n"
            query = query.replace("%%concepts%%", vals)
            results = SPARQLUtils.executeQuery(triplestoreurl, query)
            if results == False:
                return result
            for res in results["results"]["bindings"]:
                result[res["class"]["value"]] = res["label"]["value"]
        else:
            url = triplestoreconf["classlabelquery"]
            i = 0
            qidquery = ""
            for qid in classes:
                if "Q" in qid:
                    qidquery += "Q" + qid.split("Q")[1]
                if (i % 50) == 0:
                    print(url.replace("%%concepts%%", qidquery))
                    myResponse = json.loads(requests.get(url.replace("%%concepts%%", qidquery)).text)
                    print(myResponse)
                    for ent in myResponse["entities"]:
                        print(ent)
                        if "en" in myResponse["entities"][ent]["labels"]:
                            result[ent] = myResponse["entities"][ent]["labels"]["en"]["value"]
                    qidquery = ""
                else:
                    qidquery += "|"
                i = i + 1
        return result