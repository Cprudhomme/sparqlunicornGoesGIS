from ..util.sparqlutils import SPARQLUtils
from qgis.core import Qgis,QgsTask, QgsMessageLog
from qgis.PyQt.QtWidgets import QLabel

MESSAGE_CATEGORY = 'FindRelatedGeoConceptQueryTask'

class FindRelatedGeoConceptQueryTask(QgsTask):

    def __init__(self, description, triplestoreurl,dlg,concept,triplestoreconf):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.triplestoreurl = triplestoreurl
        self.dlg=dlg
        self.triplestoreconf=triplestoreconf
        self.concept=concept

    def run(self):
        QgsMessageLog.logMessage('Started task "{}"'.format(self.description()), MESSAGE_CATEGORY, Qgis.Info)
        thequery="SELECT ?rel WHERE { ?con <"+str(self.triplestoreconf["typeproperty"])+"> <"+str(self.concept)+"> . ?con ?rel ?item . "+str(self.triplestoreconf["geotriplepattern"][0])+" }"
        QgsMessageLog.logMessage("SELECT ?rel WHERE { ?con "+str(self.triplestoreconf["typeproperty"])+" "+str(self.concept)+" . ?con ?rel ?item . "+str(self.triplestoreconf["geotriplepattern"][0])+" }", MESSAGE_CATEGORY, Qgis.Info)
        results = SPARQLUtils.executeQuery(self.triplestoreurl,thequery,self.triplestoreconf)
        QgsMessageLog.logMessage("Query results: " + str(results), MESSAGE_CATEGORY, Qgis.Info)
        self.queryresult={}
        for result in results["results"]["bindings"]:
            if "style" in result:
                self.queryresult[result["style"]["value"]]={}
                if "stylelabel" in result:
                    self.queryresult[result["style"]["value"]] ={"label":result["stylelabel"]["value"]}
                else:
                    self.queryresult[result["style"]["value"]] ={"label":SPARQLUtils.labelFromURI(result["stylelabel"]["value"])}
        return True

    def finished(self, result):
        QgsMessageLog.logMessage('Started task "{}"'.format(
            str(self.concept)), MESSAGE_CATEGORY, Qgis.Info)
        resstring = ""
        counter = 1
        for res in self.queryresult:
            if "http" in res:
                resstring += "<a href=\"" + str(res) + "\"><b>" + str(self.queryresult[res]["label"])+"</b></a> "
            elif "datatype" in self.queryresult[res]:
                resstring += "<a href=\"" + str(self.queryresult[res]["datatype"]) + "\"><b>" + str(
                    self.queryresult[res]["label"])+"</b></a> "
            else:
                resstring += "<b>" + str(self.queryresult[res]["label"])+"</b> "
            if counter % 5 == 0:
                resstring += "<br/>"
            counter += 1
        item = QLabel()
        item.setOpenExternalLinks(True)
        item.setText(resstring)
        #self.dlg.dataSchemaTableView.takeItem(self.row, self.column)
        #self.dlg.dataSchemaTableView.setCellWidget(self.row, self.column, item)
