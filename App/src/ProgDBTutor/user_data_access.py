# Data Access Object pattern: see
# http://best-practice-software-engineering.ifs.tuwien.ac.at/patterns/dao.html
# For clean separation of concerns, create separate data layer that abstracts
# all data access to/from RDBM

# Depends on psycopg2 librarcy: see (tutor)
# https://wiki.postgresql.org/wiki/Using_psycopg2_with_PostgreSQL
import os.path
import sys
import time
import operator

from psycopg2.extras import execute_values
from flask_login import UserMixin
import algorithms_src.util as util
from algorithms_src.cross_validation.strong_generalization import strong_generalization

from algorithms_src.cross_validation.weak_generalization import weak_generalization
from model_training import *
from algorithms_src.cross_validation import *
from csv2sql import *

import pandas as pd
import psycopg2
import random

import numpy


class DBConnection:
    def __init__(self, dbname, dbuser):
        try:
            self.conn = psycopg2.connect(
                "dbname='{}' user='{}'".format(dbname, dbuser))
        except:
            print('ERROR: Unable to connect to database')
            raise

    def close(self):
        self.conn.close()

    def get_connection(self):
        return self.conn

    def get_cursor(self):
        return self.conn.cursor()

    def commit(self):
        return self.conn.commit()

    def rollback(self):
        return self.conn.rollback()


class User(UserMixin):
    def __init__(self, iden, email, password, username, fullname):
        self.id = iden
        self.fullname = fullname
        self.username = username
        self.email = email
        self.password = password

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def to_dct(self):
        return {'id': self.id, 'fullname': self.fullname,
                'username': self.username, 'email': self.email,
                'password': self.password}


class Dataset:
    def __init__(self, set_id, name, uid, interaction, sequence, date, info):
        self.setID = set_id
        self.name = name
        self.UID = uid
        self.interaction = interaction
        self.sequence = sequence
        self.info = info
        self.date = date


class Experiment:
    def __init__(self, name, modelName, scenario_name, setId):
        self.name = name
        self.modelName = modelName
        self.scenario = scenario_name
        self.setId = setId


class Model:
    def __init__(self, model_name, algorithm, parameters, scenario_name, set_id,
                 info=None, time=None, gen=None, gen_par=None):
        self.Model_name = model_name
        self.Algorithm = algorithm
        self.Parameters = parameters
        self.Scenario_name = scenario_name
        self.SetID = set_id
        self.info = info
        self.time = time

        self.gen = gen
        self.genPar = gen_par


def check_type(num):
    if isinstance(num, numpy.int64):
        return num.item()
    else:
        return num


class datasetDataAcces:
    def __init__(self, dbconnect):
        self.dbconnect = dbconnect

    def generateRecallAtK(self, givenModelInfo:Model):
        cursor = self.dbconnect.get_cursor()
        try:
            setId = givenModelInfo.SetID
            scenarioName = givenModelInfo.Scenario_name
            cursor.execute(
                'SELECT * FROM scenario WHERE scenario_name=%s and setid=%s',
                (scenarioName, setId))
            genInfo = cursor.fetchone()[-1]
            if genInfo:
                itemdictionary = self.makeDictionary(setId,scenarioName)
                maxItemId = max(itemdictionary)
                for i in range(maxItemId):
                    if i not in itemdictionary:
                        newIndex = len(itemdictionary)
                        if newIndex > maxItemId:
                            break
                        itemdictionary[i] = newIndex
                cursor.execute('SELECT distinct user_id FROM subset_of_dataset WHERE setid=%s AND scenario_name=%s',(setId,scenarioName))
                listOfIds = [item[0] for item in cursor.fetchall()]
                useridlisthistory = []
                valOutCompareList = []
                for uid in listOfIds:
                    useridlisthistory.append(self.makeHistoryForStaticUser(uid,setId,scenarioName))
                    valOutCompareList.append(self.getValOutForUser(uid,setId,scenarioName))

                staticInteractions = self.fillHistoryMatrix(useridlisthistory,itemdictionary)
                # todo (optional) last val (5) is amount of recs, higher
                #  = more accurate recall
                top_k = 5
                listOfRec = self.runalgo(givenModelInfo.Algorithm,listOfIds,staticInteractions,givenModelInfo,top_k)
                teller = 0
                listOfIdHistSizeRecall = ""
                recallSum = 0
                recallCounter = 0
                for userId in listOfIds:
                    recsForUser = listOfRec[teller][0]
                    countCorrect = 0
                    for rec in recsForUser:
                        if rec in valOutCompareList[teller]:
                            countCorrect += 1
                    histSize = len(useridlisthistory[teller])
                    if valOutCompareList[teller]:
                        recallValue = int(countCorrect/min(len(recsForUser),len(valOutCompareList[teller]))*100)
                        recallSum += recallValue
                        recallCounter += 1
                        listOfIdHistSizeRecall += f"{userId};{histSize};{recallValue},"
                    teller+=1
                recallSum = recallSum/recallCounter
                listOfIdHistSizeRecall += f"{recallSum}"
                # print(listOfIdHistSizeRecall)
                cursor.execute('UPDATE model SET recall_cache = %s WHERE setid=%s AND model_name=%s AND scenario_name=%s',(listOfIdHistSizeRecall,setId,givenModelInfo.Model_name,scenarioName))
                self.dbconnect.commit()
                return
            else:
                return
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to generate RecallAtK')

    def makeHistoryForStaticUser(self,userid,setid,scenarioName):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT item_id FROM subset_of_dataset WHERE setid=%s AND scenario_name=%s AND user_id=%s AND (gen_param=%s OR gen_param=%s)',(setid,scenarioName,userid,"T,Vi",",Vi"))
        return [item[0] for item in cursor.fetchall()]

    def getValOutForUser(self,uid,setId,scenarioName):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT item_id FROM subset_of_dataset WHERE setid=%s AND scenario_name=%s AND user_id=%s AND gen_param=%s',(setId,scenarioName,uid,",Vo"))
        return [item[0] for item in cursor.fetchall()]

    def get_dataset_source_names(self, given_user_id):
        """
        returns list of sourcefilenames from datasets the givenUserID owns
        :param given_user_id: the uid we search for in dataset table
        :return: the list of sourcefilenames
        """
        cursor = self.dbconnect.get_cursor()
        dataset_sources = []
        cursor.execute('SELECT sourcefile FROM dataset WHERE uid = %s',
                       (given_user_id,))
        for row in cursor:
            dataset_sources.append(row[0])
        return dataset_sources

    def delete_experiment_user(self, e_user_id, e_id, model_name, scenario_name,
                               set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'DELETE FROM experiment_user WHERE e_user_id = %s AND e_id = %s AND model_name=%s AND scenario_name=%s AND setid=%s',
            (e_user_id, e_id, model_name, scenario_name, set_id))
        self.dbconnect.commit()

    def get_specific_metadata_info(self, current_set):
        cursor = self.dbconnect.get_cursor()
        givenSetID = current_set[0]
        metadataSources = []
        metadataEntries = []
        cursor.execute(
            'SELECT DISTINCT sourcefile FROM metadata WHERE setID = %s',
            (givenSetID,))
        allSourceFiles = cursor.fetchall()
        for src in allSourceFiles:
            metadataSources.append(src[0])
            currentSourceList = []
            cursor.execute(
                'select distinct(datatype,data_meaning) from metadata where sourcefile =%s AND setid = %s',
                (src[0], givenSetID))
            for row in cursor:
                insTuple = row[0][1:-1].split(',')
                currentSourceList.append(insTuple)
            metadataEntries.append(currentSourceList)
        return [metadataSources, metadataEntries]

    def get_metadata_info(self, given_user_id):
        """
        returns metadata's source file names and type+meaning tuples for
        all metadata provided for all datasets the givenUserID owns
        :param given_user_id: the dataset for which the metadata must be
        :return: a list [[sources,entries],...] where:
                sources = list of metadata sourcefiles
                entries = list of tuples '(type,meaning)'
                and these are grouped together by set
                (so returned list index 0 gives sources and entries for user's
                first dataset)
        """
        cursor = self.dbconnect.get_cursor()
        returnList = []
        cursor.execute('SELECT setid FROM dataset WHERE uid = %s',
                       (given_user_id,))
        allSets = cursor.fetchall()
        for currentSet in allSets:
            returnList.append(self.get_specific_metadata_info(currentSet))
        return returnList

    def set_dataset_statistics(self, given_dataset_id,given_identifier):
        # on create of dataset, we cache the statistics for better performance
        cursor = self.dbconnect.get_cursor()
        statistics:str = ""
        cursor.execute(
            'SELECT COUNT ( DISTINCT interaction_id ) FROM dataset_content WHERE setid=(%s)',
            (given_dataset_id,))
        statistics += str((cursor.fetchone()[0])) + ","
        cursor.execute(
            'SELECT COUNT ( DISTINCT user_id ) FROM dataset_content WHERE setid=(%s)',
            (given_dataset_id,))
        statistics += str((cursor.fetchone()[0])) + ","
        cursor.execute(
            'SELECT COUNT ( DISTINCT item_id ) FROM dataset_content WHERE setid=(%s)',
            (given_dataset_id,))
        statistics += str((cursor.fetchone()[0]))

        cursor.execute('UPDATE dataset SET statistics = %s WHERE setid = %s',(statistics,given_dataset_id,))

        cursor.execute('UPDATE dataset SET identifier = %s WHERE setid = %s',(given_identifier,given_dataset_id))
        self.dbconnect.commit()
        return

    def get_dataset_statistic_and_info(self, given_dataset_row):
        cursor = self.dbconnect.get_cursor()
        # datasetEntry structure:
        # (id, setname, sourcefile,createdon,ownerID,ownerUserName,statistics)
        cursor.execute('SELECT username FROM users WHERE uid = %s',
                       (given_dataset_row[4],))
        datasetEntry = (
            [given_dataset_row[0], given_dataset_row[1], given_dataset_row[2],
             given_dataset_row[3], given_dataset_row[4], cursor.fetchone()[0]])
        statistics = given_dataset_row[5]
        return datasetEntry, statistics

    def get_datasets(self, given_uid=1, also_shared_with=False):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM dataset WHERE uid=(%s)', (given_uid,))
        datasets = []
        statistics_long = []
        user_datasets = cursor.fetchall()
        for row in user_datasets:
            gotTuple = self.get_dataset_statistic_and_info(row)
            datasets.append(gotTuple[0])
            statistics_long.append(gotTuple[1])
        if also_shared_with:
            cursor.execute(
                'SELECT setid FROM dataset_shared_with WHERE uid=(%s)',
                (given_uid,))
            sharedSetIds = cursor.fetchall()
            for setId in sharedSetIds:
                cursor.execute('SELECT * FROM dataset WHERE setid = %s',
                               (setId,))
                dataset = cursor.fetchall()[0]
                cursor.execute('SELECT username FROM users WHERE uid = %s',
                               (dataset[4],))
                datasetAddedOwner = dataset + cursor.fetchone()
                datasets.append(datasetAddedOwner)
        return datasets, statistics_long

    def get_datasets_shared_with(self, given_uid):
        cursor = self.dbconnect.get_cursor()
        datasets = []
        statisticsLong = []
        cursor.execute('SELECT setid FROM dataset_shared_with WHERE uid = %s',
                       (given_uid,))
        setList = cursor.fetchall()
        metaDataList = []
        for dataset in setList:
            cursor.execute('SELECT * FROM dataset WHERE setid = %s',
                           (dataset[0],))
            row = cursor.fetchone()
            gotTuple = self.get_dataset_statistic_and_info(row)
            datasets.append(gotTuple[0])
            statisticsLong.append(gotTuple[1])
            metaDataList.append(self.get_specific_metadata_info([dataset[0]]))
        return [datasets, statisticsLong], metaDataList

    def add_dataset(self, dataset, filename, dataframes):
        cursor = self.dbconnect.get_cursor()
        list_metadata = []
        count = 0
        for x in dataset.info:
            tuple_data = []
            for y in x["columns"]:
                tuple_data.append([y["type"], y["meaning"]])
            primary_identidier = x["columnPrimaryIdentifier"]
            m = convert_metadata("uploads/" + x["fileName"], tuple_data,
                                 x["fileName"], int(primary_identidier),
                                 dataframes[count])
            count += 1
            list_metadata.append(m)
        try:
            cursor.execute(
                'INSERT INTO dataset(Dataset_name,sourcefile,created_on,'
                'UID) VALUES(%s,%s,%s,%s)',
                (dataset.name, dataset.interaction, dataset.date, dataset.UID))
            cursor.execute('SELECT LASTVAL();')
            setidn = cursor.fetchone()[0]
            newfile = open(filename).read().replace("\n",f",{setidn}\n")
            open(filename,"w").write(newfile)
            columnNames = ['user_id','item_id','tmstmp']
            col0Name:str
            col1Name:str
            col2Name:str
            index = 0
            for i in dataset.sequence:
                if i == '0':
                    col0Name = columnNames[index]
                elif i == '1':
                    col1Name = columnNames[index]
                else:
                    col2Name = columnNames[index]
                index +=1
            filename = os.path.abspath(filename)
            if dataset.sequence[-1] != 'none':
                statement = f"COPY dataset_content({col0Name},{col1Name},{col2Name},setid) FROM \'{filename}\' DELIMITER \',\' CSV HEADER"
                cursor.copy_expert(statement,sys.stdout)
            else:
                statement = f"COPY dataset_content({col0Name},{col1Name},setid) FROM \'{filename}\' DELIMITER \',\' CSV HEADER"
                cursor.copy_expert(statement, sys.stdout)

            for z in list_metadata:
                for x in z:
                    for y in x:
                        cursor.execute(
                            'INSERT INTO metadata(item_id,Datatype,Data_meaning,integ,string,sourcefile,setid) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                            (y[0], y[1], y[2], y[3], y[4], y[5], setidn))
            self.dbconnect.commit()
            return setidn

        except:
            self.dbconnect.rollback()
            raise Exception('Unable to save dataset!')

    def get_interaction_sample(self, given_set_id):
        if given_set_id == '':
            return
        cursor = self.dbconnect.get_cursor()
        # limit 5 for readability, may update later to be less/more
        cursor.execute('SELECT * FROM dataset_content WHERE setId = %s LIMIT 5',
                       (given_set_id,))
        header = ['userID', 'itemID']
        allRows = []
        interactionRows = cursor.fetchall()
        isTimestamp = False
        if interactionRows[0][2] is not None:
            header.append('timestamp')
            isTimestamp = True
        for row in interactionRows:
            rowList = [{'val': str(row[0])}, {'val': str(row[1])}]
            if isTimestamp:
                rowList.append({'val': str(row[2])})
            allRows.append({'value': rowList})
        return [header, allRows]

    def get_metadata_sample(self, given_set_id, given_source_file):
        cursor = self.dbconnect.get_cursor()
        header = ['itemID']
        rows = []
        cursor.execute(
            'SELECT DISTINCT data_meaning FROM metadata WHERE setid = %s AND sourcefile = %s',
            (given_set_id, given_source_file))
        dataMeaningsAlphabetical = cursor.fetchall()
        cursor.execute(
            'SELECT data_meaning,metadatakey FROM metadata WHERE setid = %s AND sourcefile = %s',
            (given_set_id, given_source_file))
        for row in cursor:
            if len(header) == len(dataMeaningsAlphabetical) + 1:
                break
            if str(row[0]) not in header:
                header.append(str(row[0]))

        cursor.execute(
            'SELECT DISTINCT(item_id) FROM metadata WHERE setid = %s AND sourcefile = %s',
            (given_set_id, given_source_file))
        allPossibleIds = cursor.fetchall()
        totalItemCount = len(allPossibleIds)
        allItemIds = []
        for i in range(3):  # todo (optional) let user sample size
            randOffset = random.randrange(0,int(totalItemCount))
            allItemIds.append(allPossibleIds[randOffset][0])
        for id in allItemIds:
            tempItemData = header
            currentItemData = []
            cursor.execute(
                'SELECT * FROM metadata WHERE item_id = %s AND setid = %s and sourceFile = %s',
                (id, given_set_id, given_source_file))
            gottenData = cursor.fetchall()
            currentItemData.append({'val': str(gottenData[0][1])})
            for i in range(len(header)-1):
                currentItemData.append({})
            for entry in gottenData:
                meaning = entry[3]
                isUrl: bool = False
                offset: int = 0
                if entry[2] == 'int':
                    offset = 0
                elif entry[2] == 'string':
                    offset = 1
                elif entry[2] == 'url':
                    offset = 1
                    isUrl = True
                entryDict = dict()
                entryVal = str(entry[4 + offset])
                if entry[2] == 'string':  # limit string size for sample
                    if len(entryVal) > 128:
                        entryVal = entryVal[:128] + "..."
                    if entryVal[:4] == "www.":  # and remove www. for urls
                        entryVal = entryVal[4:]
                entryDict['val'] = entryVal
                if isUrl:
                    entryDict['data-type'] = 'URL'
                index = 0
                for pos in tempItemData:  # makes header & column entry match
                    if meaning == pos:
                        currentItemData[index] = entryDict
                    index += 1
            dictEntry = dict()
            dictEntry['value'] = currentItemData
            rows.append(dictEntry)
        return [header, rows]

    def change_dataset_name(self, given_set_id, given_new_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('UPDATE dataset SET dataset_name = %s WHERE setid = %s',
                       (given_new_name, given_set_id))
        self.dbconnect.commit()

    def delete_dataset(self, given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('DELETE FROM dataset WHERE setid = %s', (given_set_id,))
        self.dbconnect.commit()

    def change_scenario_name(self, old_scenario_name, given_new_name,
                             given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'UPDATE scenario SET scenario_name = %s WHERE scenario_name = %s and setid = %s'
            , (given_new_name, old_scenario_name, given_set_id))
        self.dbconnect.commit()

    def get_dataset_scenario_count(self, given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(scenario_name) FROM scenario WHERE setid = %s',
            (given_set_id,))
        return cursor.fetchone()[0]

    def get_steps_for_scenario(self, given_set_id, given_scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT * FROM processing_step WHERE setid = %s AND scenario_name = %s',
            (given_set_id, given_scenario_name))
        returnDict = {"datasetSelector": given_set_id}
        retargetingActive: bool = False
        for row in cursor:
            stepType = row[1]
            if stepType == 'retargetingActive':
                retargetingActive = True
                continue
            fromVal = row[2].split(',')[0]
            toVal = row[2].split(',')[1]
            if stepType == "filterTime":
                returnDict["filterTime"] = True
                returnDict["filterTimeCollapse"] = "show"
                if fromVal == '1/1/1':
                    returnDict["filterTimeFromBeginning"] = True
                else:
                    returnDict["filterTimeFrom"] = fromVal
                if toVal == '99999/12/30':
                    returnDict["filterTimeToEnd"] = True
                else:
                    returnDict["filterTimeTo"] = toVal
            elif stepType == "filterUser":
                returnDict["filterUsers"] = True
                returnDict["filterUsersCollapse"] = "show"
                returnDict["filterUsersMinimum"] = fromVal
                if toVal == "999999999":
                    returnDict["filterUsersAll"] = True
                else:
                    returnDict["filterUsersMaximum"] = toVal
            elif stepType == "filterItem":
                returnDict["filterItems"] = True
                returnDict["filterItemsCollapse"] = "show"
                returnDict["filterItemsMinimum"] = fromVal
                if toVal == "999999999":
                    returnDict["filterItemsMax"] = True
                else:
                    returnDict["filterItemsMaximum"] = toVal
        returnDict["disableRetargeting"] = not retargetingActive
        return returnDict

    def get_scenarios(self, user_id, add_owner_of_dataset=False):
        cursor = self.dbconnect.get_cursor()
        listOfDataSets = self.get_datasets(user_id,True)[0]
        scenarioList = []
        for dataSet in listOfDataSets:
            cursor.execute('SELECT * FROM scenario WHERE setid =%s',
                           (dataSet[0],))
            listOfScenarios = cursor.fetchall()
            for row in listOfScenarios:
                if add_owner_of_dataset:
                    extendedRow = row + (self.get_dataset_name(row[1]),)
                    scenarioList.append(extendedRow)
                else:
                    scenarioList.append(row)
        return scenarioList

    def get_dataset_name(self, given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT dataset_name FROM dataset WHERE setid = %s',
                       (given_set_id,))
        return cursor.fetchone()[0]

    def get_dataset_given_scenario_and_user(self, given_user_id,
                                            given_scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT setid FROM scenario WHERE scenario_name = %s AND setid IN (SELECT setid FROM dataset WHERE uid = %s)',
            (given_scenario_name, given_user_id))
        val = cursor.fetchone()
        return val

    def get_set_owner(self, given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT uid FROM dataset WHERE setid = %s',
                       (given_set_id,))
        userId = cursor.fetchone()[0]
        cursor.execute('SELECT username FROM users WHERE uid = %s', (userId,))
        return cursor.fetchone()[0]

    def get_processing_steps(self, given_set_id, given_scenario_name):
        cursor = self.dbconnect.get_cursor()
        listOfProcessingSteps = []
        cursor.execute(
            'SELECT * FROM processing_step WHERE setid = %s AND scenario_name = %s',
            (given_set_id, given_scenario_name))
        for row in cursor:
            listOfProcessingSteps.append(row)
        return listOfProcessingSteps

    def get_user_scenarios(self, given_user_id):
        scenarioList = self.get_scenarios(given_user_id, True)
        processingList = []
        for scenario in scenarioList:
            scenarioName = scenario[0]
            setId = scenario[1]
            processingSteps = self.get_processing_steps(setId, scenarioName)
            processingList.append(processingSteps)
        return [scenarioList, processingList]

    def create_scenario(self, scenario_json_form):
        cursor = self.dbconnect.get_cursor()
        scenarioName = scenario_json_form['name']
        setID = scenario_json_form['dataset']

        genType = scenario_json_form['generalizationType']
        valIn = scenario_json_form['validationIn']  # still a %-val
        trainUsers = scenario_json_form['trainingUsers']  # still a %-val
        if genType == "WG":
            trainUsers = "100"
        genColValue = ""
        if genType:
            genColValue = f'{genType},{valIn},{trainUsers}'
        cursor.execute('INSERT INTO scenario(scenario_name,setid,genInfo) VALUES(%s,%s,%s)',
                       (scenarioName, setID,genColValue))
        creationDate = None
        stepIdCounter = 0
        for processingStep in scenario_json_form['preProcessingSteps']:
            processingType = processingStep['type']
            fromVal:str = processingStep['from']
            toVal:str = processingStep['to']
            isMin = processingStep['min']
            isMax = processingStep['max']
            if processingType == 'filterTime':
                if isMin:
                    cursor.execute('SELECT MIN(tmstmp) FROM dataset_content WHERE setid = %s',(setID,))
                    fromVal = cursor.fetchone()[0]
                if isMax:
                    cursor.execute(
                        'SELECT MAX(tmstmp) FROM dataset_content WHERE setid = %s',
                        (setID,))
                    toVal = cursor.fetchone()[0]
                fromToString = f"{fromVal},{toVal}"
                cursor.execute(
                    'INSERT INTO processing_step(p_id,code,parameters,scenario_name,setid,tmstmp) VALUEs(%s,%s,%s,%s,%s,%s)',
                    (stepIdCounter, 'filterTime', fromToString, scenarioName, setID,
                     creationDate,))
            elif processingType == "filterUser":
                if isMin:
                    cursor.execute('SELECT MIN(count) FROM (SELECT COUNT(item_id) from dataset_content WHERE setid = %s GROUP BY user_id) as mincount;',(setID,))
                    fromVal = cursor.fetchone()[0]
                if isMax:
                    cursor.execute('SELECT MAX(count) FROM (SELECT COUNT(item_id) from dataset_content WHERE setid = %s GROUP BY user_id) as maxcount;',(setID,))
                    toVal = cursor.fetchone()[0]
                fromToString = f"{fromVal},{toVal}"
                cursor.execute(
                    'INSERT INTO processing_step(p_id,code,parameters,scenario_name,setid,tmstmp) VALUEs(%s,%s,%s,%s,%s,%s)',
                    (stepIdCounter, 'filterUser', fromToString, scenarioName, setID,
                     creationDate,))
            elif processingType == "filterItem":
                if isMin:
                    cursor.execute('SELECT MIN(count) FROM (SELECT COUNT(user_id) from dataset_content WHERE setid = %s GROUP BY item_id) as mincount;',(setID,))
                    fromVal = cursor.fetchone()[0]
                if isMax:
                    cursor.execute(
                        'SELECT MAX(count) FROM (SELECT COUNT(user_id) from dataset_content WHERE setid = %s GROUP BY item_id) as maxcount;',
                        (setID,))
                    toVal = cursor.fetchone()[0]
                fromToString = f"{fromVal},{toVal}"
                cursor.execute(
                    'INSERT INTO processing_step(p_id,code,parameters,scenario_name,setid,tmstmp) VALUEs(%s,%s,%s,%s,%s,%s)',
                    (stepIdCounter, 'filterItem', fromToString, scenarioName, setID,
                     creationDate,))
            stepIdCounter += 1

        disableRetargeting = scenario_json_form['disableRetargeting']
        if not disableRetargeting:
            cursor.execute(
                'INSERT INTO processing_step(p_id,code,parameters,scenario_name,setid,tmstmp) VALUEs(%s,%s,%s,%s,%s,%s)',
                (
                    stepIdCounter, 'retargetingActive', '', scenarioName, setID,
                    creationDate,))
        self.dbconnect.commit()

    def delete_scenario(self, given_scenario_name, given_set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'DELETE FROM scenario WHERE setid = %s AND scenario_name = %s',
            (given_set_id, given_scenario_name))
        self.dbconnect.commit()

    def get_scenario_model_count(self, given_set_id, given_scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(model_name) FROM model WHERE setid = %s AND scenario_name = %s',
            (given_set_id, given_scenario_name))
        return cursor.fetchone()[0]

    def get_model(self, model_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM model WHERE Model_name= %s',
                       (model_name,))
        return cursor.fetchone()

    def find_all_experiment_users(self, experiment_id, model_name,
                                  scenario_name, set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT * FROM experiment_user WHERE e_id = %s AND model_name = %s AND scenario_name = %s AND setid = %s',
            (experiment_id, model_name, scenario_name, set_id))
        return cursor.fetchall()
    def splitParameters(self,parameters):
        listparameters=parameters.split(',')
        return listparameters

    def runalgo(self,algorithm,listofids,expinterinteractions,model,top_k:int):
        parameters=self.splitParameters(model.Parameters)
        if algorithm == "Random":
            return rand_load(listofids, expinterinteractions,top_k)
        elif algorithm == "Popularity":
            return pop_load(listofids, expinterinteractions,
                             model.info + ".npy",top_k)
        elif algorithm == "Item nearest neighbours":
            p2 = parameters[1].lower()
            booleanparam=False
            if p2 == "true":
                booleanparam = True
            return iknn_load(listofids, expinterinteractions,
                             model.info + ".npz",top_k,int(parameters[0]),booleanparam)
        elif algorithm == "EASE":
            return ease_load(listofids, expinterinteractions,
                            model.info + ".npz",top_k,float(parameters[0]))
        elif algorithm == "Weighted Matrix Factorization":
            return wmf_load(listofids, expinterinteractions,
                        model.info + ".npy",top_k,float(parameters[0]),int(parameters[1]),float(parameters[2]),int(parameters[3]))

    def find_all_experiments_users_used_items_by_user(self, e_user_id,
                                                      experiment_id, model_name,
                                                      scenario_name, setid):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT item_id FROM item_to_e_user WHERE e_user_id = %s AND e_id = %s AND model_name = %s AND scenario_name = %s AND setid = %s',
            (e_user_id, experiment_id, model_name, scenario_name, setid))
        return cursor.fetchall()

    def get_text_for_item(self, setid, given_item_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT identifier FROM dataset WHERE setid = %s',(setid,))
        cursorVal = cursor.fetchone()
        identifier = cursorVal[0].split(',')[0]
        if identifier == "item_id":
            return "item_id"
        else:
            cursor.execute('SELECT datatype,string,integ FROM metadata WHERE setid=%s AND item_id = %s AND data_meaning = %s',(setid,given_item_id,identifier))
            metaRow = cursor.fetchone()
            if not metaRow:
                return "item_id"
            if metaRow[0] == "string":
                return metaRow[1]
            else:
                return str(metaRow[2])

    def get_image_for_item(self, setid, given_item_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT identifier FROM dataset WHERE setid = %s',(setid,))
        cursorVal = cursor.fetchone()
        identifier = cursorVal[0].split(',')[1]
        if identifier:
            cursor.execute('SELECT string FROM metadata WHERE setid=%s AND item_id = %s AND data_meaning = %s',(setid,given_item_id,identifier))
            metaValue = cursor.fetchone()
            if metaValue:
                return metaValue[0]
            else:
                return ""
        else:
            return ""

    def fillHistoryMatrix(self,user_histories, item_dictionary):

        history_matrix = scipy.sparse.csr_matrix((len(user_histories), len(item_dictionary)),
                                                 dtype=np.int8)
        for index, user_history in enumerate(user_histories):
            for item_id in user_history:
                history_matrix[index, item_dictionary[item_id]] = 1

        return history_matrix

    def makehistoryForUser(self,user_id,dataframe):
        listToReturn=[]
        for index,x in dataframe.iterrows():
            uid=x['uid']
            iid=x['iid']
            if uid==user_id:
                listToReturn.append(iid)
        return listToReturn

    def makeDictionary(self,given_set_id,scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT distinct item_id FROM subset_of_dataset WHERE setid=%s AND scenario_name=%s',
        (given_set_id,scenario_name,))
        itemidlist=cursor.fetchall()
        dictToReturn={}
        teller=0
        for x in itemidlist:
            dictToReturn[x[0]]=teller
            teller+=1
        return dictToReturn

    def getExperimentHistory(self,expID):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT e_user_id,item_id FROM item_to_e_user WHERE e_id=%s',
            (expID,))
        testlist=cursor.fetchall()
        dataframe=pd.DataFrame(list(testlist))
        if testlist:
            dataframe.columns=['uid','iid']
        return dataframe

    def create_experiment(self, experiment, shared_with):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'INSERT INTO experiment(Model_name,scenario_name,setID,experiment_name) VALUES(%s,%s,%s,%s)',
            (experiment.modelName, experiment.scenario, experiment.setId,
             experiment.name))
        cursor.execute('SELECT LASTVAL();')
        e_id = cursor.fetchone()[0]
        self.dbconnect.commit()
        cursor.execute('SELECT uid FROM dataset_shared_with WHERE setid = %s',(experiment.setId,))
        for row in cursor:
            shared_with += f'{row[0]}'
        self.update_experiment_shared_with(shared_with,
                                           e_id,
                                           experiment.modelName,
                                           experiment.scenario,
                                           experiment.setId)

    def update_experiment_shared_with(self, uids, e_id, model_name,scenario_name, setid):
        cursor = self.dbconnect.get_cursor()
        try:
            for id in uids:  # for each id given, check if already shared
                if id == '':
                    continue
                cursor.execute(
                    'SELECT * FROM experiment_shared_with WHERE uid = %s AND e_id = %s AND model_name =%s AND scenario_name=%s AND setid=%s',
                    (id, e_id, model_name, scenario_name, setid))
                if not cursor.fetchone():  # if not, insert new share row
                    cursor.execute(
                        'INSERT INTO experiment_shared_with VALUES (%s,%s,%s,%s,%s)',
                        (id, e_id, model_name, scenario_name, setid))

                cursor.execute('SELECT * FROM dataset WHERE uid =%s AND setid=%s',(id,setid,))

                if not cursor.fetchone():  # if not, insert new share row

                    cursor.execute('SELECT * FROM dataset_shared_with WHERE setid=%s AND uid=%s',(setid,id,))

                    if not cursor.fetchone():
                        cursor.execute('INSERT INTO dataset_shared_with (setid,uid) VALUES (%s,%s)',(setid,id))
                    else:
                        print("Dataset '" + str(setid) + "' already shared with user " + str(id))
            # now check that everyone the set should be shared with is in the
            # givenuserIDs
            cursor.execute(
                'SELECT uid FROM experiment_shared_with WHERE setid = %s',
                (setid,))
            # we compare each stored uid that the set
            storedShares = cursor.fetchall()
            # was shared with, if not in givenUserIDs, stop sharing
            for row in storedShares:
                if str(row[0]) not in uids:
                    cursor.execute(
                        'DELETE FROM experiment_shared_with WHERE uid = %s AND e_id = %s AND model_name=%s AND scenario_name=%s AND setid=%s',
                        (row[0], e_id, model_name, scenario_name, setid))
            self.dbconnect.commit()
            return
        except:
            self.dbconnect.rollback()
            print('update of experiment_shared_with failed')

    def count_experiments_using_model(self, sid, scenario_name, model_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(e_id) FROM experiment WHERE model_name = %s AND scenario_name = %s AND setid = %s',
            (model_name, scenario_name, sid))
        return cursor.fetchone()[0]

    def get_models(self, id):
        cursor = self.dbconnect.get_cursor()
        setList = self.get_datasets(id,True)[0]
        setIdList = ()
        for set in setList:
            setIdList= setIdList + (set[0],)
        setIdList = tuple(setIdList)
        retList = []
        cursor.execute(
            'SELECT * FROM model WHERE setid IN %s',
            (setIdList,))
        for row in cursor:
            rowDict = {"modelName": row[0],
                       "sid": row[4],
                       "sourceName": row[3],
                       "size": "12KB",
                       "time": f"{str(row[-2])[:5]}sec",
                       "algorithm": row[1],
                       "numberReferences": self.count_experiments_using_model(
                           row[4], row[3], row[0])}
            if row[-1]:
                rowDict['avgRecallAtK'] = f"{row[-1].split(',')[-1][:5]}%"
            retList.append(rowDict)
        return retList

    def get_genInfo(self, set_id, scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT geninfo FROM scenario WHERE setid = %s AND scenario_name = %s',(set_id,scenario_name,))
        return cursor.fetchone()

    def get_static_user_items(self, static_user_id, s_id, scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT item_id,gen_param FROM subset_of_dataset WHERE user_id = %s AND setid = %s AND scenario_name = %s',(static_user_id,s_id,scenario_name))
        return cursor.fetchall()


class UserDataAccess:
    def __init__(self, dbconnect):
        self.dbconnect = dbconnect

    def get_users(self):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM users')
        user_objects = list()
        for row in cursor:
            user_obj = User(row[0], row[1], row[2], row[3], row[4])
            user_objects.append(user_obj)
        return user_objects

    def update_dataset_shared_with(self, given_user_ids, given_set_id):
        """
        updates the dataset_shared_with table based on the given user IDs and setID
        :param given_user_ids: the userIDs the dataset should be shared with
        :param given_set_id: the dataset which we want to update the share on
        :return: nothing
        """
        cursor = self.dbconnect.get_cursor()
        try:
            # for each id given, check if already shared
            for user_id in given_user_ids:
                if user_id == '':
                    continue
                cursor.execute(
                    'SELECT * FROM dataset_shared_with WHERE setid = %s AND uid = %s',
                    (given_set_id, user_id,))
                if not cursor.fetchone():  # if not, insert new share row
                    cursor.execute(
                        'INSERT INTO dataset_shared_with VALUES (%s,%s)',
                        (given_set_id, user_id,))
            # now check that everyone the set should be shared with is in the
            # givenuserIDs
            cursor.execute(
                'SELECT uid FROM dataset_shared_with WHERE setid = %s',
                (given_set_id,))
            # we compare each stored uid that the set
            storedShares = cursor.fetchall()
            # was shared with, if not in givenUserIDs, stop sharing
            for row in storedShares:
                if str(row[0]) not in given_user_ids:
                    cursor.execute(
                        'DELETE FROM dataset_shared_with WHERE setid = %s AND uid = %s',
                        (given_set_id, row[0]))
            self.dbconnect.commit()
            return
        except:
            self.dbconnect.rollback()
            print('update of dataset_shared_with failed')

    def delete_experiment(self, e_id, model_name, scenario_name, setid):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'DELETE FROM experiment WHERE e_id = %s AND model_name=%s AND scenario_name=%s AND setid=%s',
            (e_id, model_name, scenario_name, setid))
        cursor.execute(
            'DELETE FROM experiment_shared_with WHERE e_id = %s AND model_name = %s AND scenario_name = %s AND setid = %s',
            (e_id, model_name, scenario_name, setid))
        self.dbconnect.commit()

    def get_dataset_shared_with(self, givenSetID):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'SELECT uid FROM dataset_shared_with WHERE setid = %s',
                (givenSetID,))
            userList = cursor.fetchall()

            self.dbconnect.commit()
            return userList
        except:
            print('dataset_shared_with function brokey')

    def get_user(self, id):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute('SELECT * FROM users WHERE uid = (%s)', (id,))
            row = cursor.fetchone()
            self.dbconnect.commit()
            
            if row:
                user_obj = User(row[0], row[1], row[2], row[3], row[4])
                return user_obj
            else:
                print("Didn't find user with id: " + str(id))
        except:
            print("Didn't find user with id: " + str(id))
            self.dbconnect.rollback()
            

    def add_user(self, user_obj):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'INSERT INTO Users(fullname,username,email,psswrd) VALUES(%s,%s,%s,%s)',
                (user_obj.fullname, user_obj.username, user_obj.email,
                 user_obj.password,))
            # get id and return updated object
            cursor.execute('SELECT LASTVAL()')
            iden = cursor.fetchone()[0]
            user_obj.id = iden
            self.dbconnect.commit()
            return user_obj
        except:
            self.dbconnect.rollback()
            return False

    def get_username(self, given_user_id=0):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT username FROM users WHERE uid = %s',
                       (given_user_id,))
        return cursor.fetchone()[0]

    def find_username(self, user_name_insert):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(Username) FROM users WHERE username = (%s)',
            (user_name_insert,))
        count = cursor.fetchone()
        return count

    def get_id_based_on_email(self, emailinsert):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT (uid) FROM users WHERE email = (%s)',
                       (emailinsert,))
        return cursor.fetchone()[0]

    def find_email(self, emailinsert):
        cursor = self.dbconnect.get_cursor()

        cursor.execute('SELECT COUNT(email) FROM users WHERE email = (%s)',
                       (emailinsert,))
        count = cursor.fetchone()
        return count

    def email_and_password_match(self, email, password):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(email) FROM users WHERE email = (%s) AND psswrd = (%s)',
            (email, password,))
        count = cursor.fetchone()
        self.dbconnect.commit()
        return count

    def get_models(self, userID):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'select * from model WHERE setid IN (SELECT setid FROM dataset WHERE uid = %s UNION SELECT setid FROM dataset_shared_with WHERE uid=%s)',
            (userID,userID))
        Models = list()
        for row in cursor:
            mdl = Model(row[0], row[1], row[2], row[3], row[4], row[5], row[6])
            Models.append(mdl)
        return Models

    def get_model(self, model_name, scenario_name, setID):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT * FROM Model WHERE model_name=(%s) and Scenario_name=(%s) and setid =(%s)',
            (model_name, scenario_name, setID,))
        row = cursor.fetchone()
        return Model(row[0], row[1], row[2], row[3], row[4],row[5])

    def addModel(self, model):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'INSERT INTO model(Model_name, Algorithm, Parameters, model_info, trained_time ,Scenario_name, SetID ) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (
                    model.Model_name, model.Algorithm, model.Parameters,
                    model.info,
                    model.time, model.Scenario_name, model.SetID,))
            self.dbconnect.commit()
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to save Model!')

    def delete_model(self, Model_name, Scenario_name, SetID):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'DELETE from model where model_name=(%s) and  scenario_name=(%s) and setid=(%s)',
                (Model_name, Scenario_name, SetID,))
            self.dbconnect.commit()
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to delete Model!')

    def db2csv(self, model):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM Dataset_content where setid =(%s)',
                       (model.SetID,))
        interactions = str("userId,itemId,timestamp\n")
        for row in cursor:
            interactions += str(row[0]) + "," + str(row[1]) + "," + str(
                row[2]) + "\n"

        f = open("./" + str(model.Model_name) + ".csv", "w+")
        # print(interactions)
        f.write(interactions)
        f.close()

    def getsubset_content(self,set_id,scen_name):
        cursor = self.dbconnect.get_cursor()
        scenario_list = []
        cursor.execute(
            'SELECT user_id,item_id,tmstmp FROM Subset_of_Dataset WHERE setid= (%s) AND Scenario_name=(%s) AND (gen_param=%s OR gen_param = %s OR gen_param IS null)',
            (set_id,scen_name,'T,','T,Vi'))
        scenario_list += cursor.fetchall()
        dataframe = pd.DataFrame(list(scenario_list))
        dataframe.columns = ['uid', 'iid', 'timestamp']
        return dataframe

    def get_dataset_content(self, set_id):
        cursor = self.dbconnect.get_cursor()
        scenario_list = []
        cursor.execute(
            'SELECT user_id,item_id,tmstmp FROM dataset_content WHERE setid= (%s)',
            (set_id,))
        scenario_list += cursor.fetchall()
        dataframe = pd.DataFrame(list(scenario_list))
        dataframe.columns = ['uid', 'iid', 'timestamp']
        return dataframe

    def get_processing_steps(self, givenSetID, givenScenarioName):
        cursor = self.dbconnect.get_cursor()
        listOfProcessingSteps = []
        cursor.execute(
            'SELECT * FROM processing_step WHERE setid = %s AND scenario_name = %s',
            (givenSetID, givenScenarioName))
        for row in cursor:
            listOfProcessingSteps.append(row)
        return listOfProcessingSteps
    def get_crossval_type(self,scenario_name,set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT geninfo FROM Scenario WHERE setid = %s AND scenario_name = %s',
            (set_id, scenario_name))
        type=cursor.fetchone()
        return type[0]
    def get_retargeting_active(self,givenSetID,givenScenarioName):
        steps = self.get_processing_steps(givenSetID,givenScenarioName)
        for step in steps:
            if step[1] == 'retargetingActive':
                return True
        return False

    def make_subset(self, given_set_id, given_scenario_name):
        cursor = self.dbconnect.get_cursor()
        # print(f'Making subset for setId {given_set_id}, scenario {given_scenario_name}')
        try:
            # Using a view was a hint given to us by the very generous Team8
            # credits to Zlatko & Thomas for helping us fix our performance issues
            cursor.execute('INSERT INTO subset_of_dataset(user_id,item_id,tmstmp,scenario_name,setid) (SELECT user_id,item_id,tmstmp,%s,setid FROM dataset_content WHERE setid = %s)',(given_scenario_name,given_set_id,))
            cursor.execute('CREATE OR REPLACE VIEW tempSubSet AS (SELECT * FROM subset_of_dataset WHERE scenario_name = %s AND setid = %s)',(given_scenario_name,given_set_id,))
            self.dbconnect.commit()
            processingList = self.get_processing_steps(given_set_id,given_scenario_name)
            for step in processingList:
                start_time = time.time()
                self.dbconnect.commit()
                stepType = step[1]
                if stepType == 'retargetingActive':
                    continue
                fromToTuple = step[2].split(',')
                if stepType == 'filterTime':
                    cursor.execute(
                        'DELETE FROM tempSubSet WHERE setid = %s AND scenario_name = %s AND tmstmp < %s',
                        (given_set_id, given_scenario_name, fromToTuple[0],))
                    cursor.execute(
                        'DELETE FROM tempSubSet WHERE setid = %s AND scenario_name = %s AND tmstmp > %s',
                        (given_set_id, given_scenario_name, fromToTuple[1],))
                else:
                    fromToTuple[0] = int(fromToTuple[0])
                    fromToTuple[1] = int(fromToTuple[1])
                    if stepType == 'filterItem':
                        cursor.execute('SELECT item_id FROM (SELECT item_id,COUNT(user_id) FROM '
                                       'tempSubSet WHERE setid = %s AND scenario_name = %s GROUP BY item_id) AS delItemId WHERE count < %s or count > %s',(given_set_id,given_scenario_name,fromToTuple[0],fromToTuple[1]))
                        itemsToDelete = cursor.fetchall()
                        itemsToDeleteTuple = ()
                        for item in itemsToDelete:
                            itemsToDeleteTuple = itemsToDeleteTuple + item
                        if itemsToDeleteTuple:
                            cursor.execute(
                                'DELETE FROM tempSubSet WHERE setid=%s AND scenario_name=%s AND item_id IN %s',
                                (given_set_id, given_scenario_name, itemsToDeleteTuple))
                    elif stepType == 'filterUser':
                        cursor.execute('SELECT user_id FROM (SELECT user_id,COUNT(item_id) FROM '
                                       'tempSubSet WHERE setid = %s AND scenario_name = %s GROUP BY user_id) AS delUserId WHERE count < %s or count > %s',(given_set_id,given_scenario_name,fromToTuple[0],fromToTuple[1]))
                        usersToDelete = cursor.fetchall()
                        usersToDeleteTuple = ()
                        for item in usersToDelete:
                            usersToDeleteTuple = usersToDeleteTuple + item
                        if usersToDeleteTuple:
                            cursor.execute(
                                'DELETE FROM tempSubSet WHERE setid=%s AND scenario_name=%s AND user_id IN %s',
                                (given_set_id, given_scenario_name,
                                 usersToDeleteTuple))
            self.dbconnect.commit()
            return
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct subset')

    def construct_empty_user(self, given_e_id, given_set_id, model_name,
                             scenario_name,static_user_id):
        try:
            cursor = self.dbconnect.get_cursor()
            if static_user_id:
                static_user_id = int(static_user_id)
            cursor.execute(
                'insert into experiment_user(e_id,model_name,scenario_name,setid,static_user_id) values (%s,%s,%s,%s,%s)',
                (
                    int(given_e_id), str(model_name), str(scenario_name),
                    int(given_set_id),static_user_id))
            cursor.execute('SELECT LASTVAL()')
            newUserIden = cursor.fetchone()[0]
            self.dbconnect.commit()
            return newUserIden
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct empty experiment user!')

    def construct_specific_user(self, given_e_id, given_set_id, modelName,
                                scenarioName, given_user_ID,staticUserID):
        cursor = self.dbconnect.get_cursor()
        try:
            newUserID = self.construct_empty_user(given_e_id, given_set_id,
                                                  modelName,
                                                  scenarioName,staticUserID)
            # if static user, no need to do the rest of the function
            if staticUserID:
                return
            cursor.execute(
                'select * from subset_of_dataset where user_id = %s and setid = %s AND scenario_name = %s',
                (given_user_ID, given_set_id, scenarioName,))
            unique_rel_id = 0
            itemRows = cursor.fetchall()
            # for each item the original user interacted with, we want an entry
            # in the item_to_e_user for the new experiment_user
            # now insert these values one by one into the database
            for row in itemRows:
                cursor.execute(
                    'INSERT INTO item_to_e_user values (%s,%s,%s,%s,%s,%s,%s)',
                    (
                        newUserID, row[1], unique_rel_id, given_e_id, modelName,
                        scenarioName, given_set_id,))
                # we store an unique relation id, such that a user can interact
                # with the same item more than once.
                unique_rel_id = unique_rel_id + 1
            self.dbconnect.commit()
            return newUserID
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct specific user!')

    def get_all_userIds_interacted_with(self,given_set_id,given_scenario_name, given_item_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT DISTINCT(user_id) FROM subset_of_dataset WHERE setid = %s AND item_id = %s AND scenario_name = %s',
            (given_set_id, given_item_id, given_scenario_name))
        userList = cursor.fetchall()
        return userList

    def construct_specific_items_users(self, given_e_id, given_set_id,
                                       model_name, scenario_name,
                                       given_item_id,upper_bound,isStatic:bool,generalization):
        cursor = self.dbconnect.get_cursor()
        try:
            # first we get every user ID from the original dataset, which
            # who interacted with the given item_id
            userList = self.get_all_userIds_interacted_with(given_set_id,scenario_name,given_item_id)
            if isStatic and generalization == "SG":
                notTrainedList = self.get_subset_user_ids(given_set_id,scenario_name,"SG")
            newUserIDList = list()
            counter = 0
            for row in userList:
                if isStatic and generalization == "SG":
                    if row[0] not in notTrainedList:
                        continue
                if counter == upper_bound:
                    break
                staticUserID = None
                if isStatic:
                    staticUserID = row[0]
                newUserIDList.append(
                    self.construct_specific_user(given_e_id, given_set_id,
                                                 model_name, scenario_name,
                                                 row[0],staticUserID))
                counter += 1
            self.dbconnect.commit()
            return newUserIDList
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct specific items user list!')

    def construct_rand_user(self, given_e_id, given_set_id, model_name,
                            scenario_name,isStatic:bool, genType):
        cursor = self.dbconnect.get_cursor()
        try:
            # get all user ids available for constructing rand_users from subset
            userIdList = self.get_subset_user_ids(given_set_id,scenario_name,genType)
            # select a random index in the range [0,userCount]
            randUserIndex = random.randrange(0,len(userIdList))
            # and get the userId linked to the dataset which is on that index
            selectedUserId = userIdList[randUserIndex]
            staticUserID = None
            if isStatic:
                staticUserID = selectedUserId
            newUserID = self.construct_specific_user(given_e_id, given_set_id,
                                                     model_name,
                                                     scenario_name,
                                                     selectedUserId,staticUserID)
            # now we store the new experiment_user ID so we can link the items
            # from the original user correctly
            # and we call the emptyUser constructor
            self.dbconnect.commit()
            return newUserID
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct random experiment user!')

    def construct_rand_items_user(self, given_e_id, given_set_id, model_name,
                                  scenario_name, item_count):
        try:
            cursor = self.dbconnect.get_cursor()
            # setup a new user, which returns the new User's ID
            newUserID = self.construct_empty_user(given_e_id, given_set_id,
                                                  model_name,
                                                  scenario_name,None)
            cursor.execute(
                'SELECT DISTINCT item_id FROM subset_of_dataset WHERE setid = %s AND scenario_name = %s',
                (given_set_id, scenario_name))
            # now find all possible items in the dataset
            itemList = cursor.fetchall()
            unique_rel_id = 0
            # for the amount of items, given as a parameter, add random items
            # from the dataset to the e_user
            # generate random index in itemList
            for i in range(int(item_count)):
                randIndex = random.randrange(0, len(itemList))
                newItemID = itemList[randIndex][
                    0]  # select the item on that position
                cursor.execute(
                    'insert into item_to_e_user values (%s,%s,%s,%s,%s,%s,%s)',
                    (
                        newUserID, newItemID, unique_rel_id, given_e_id,
                        model_name,
                        scenario_name, given_set_id))
                # we store an unique relation id, such that a user can interact
                # with the same item more than once.
                unique_rel_id = unique_rel_id + 1
            self.dbconnect.commit()
            return newUserID
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to construct rand item experiment user!')

    def construct_copy_user(self, givenUserID, given_e_id, given_set_id,
                            modelName, scenarioName):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'select * from experiment_user where e_user_id= %s and e_id = %s and setid = %s and model_name = %s and scenario_name = %s',
                (
                    givenUserID, given_e_id, given_set_id, modelName,
                    scenarioName))
            copyAttr = cursor.fetchone()
            newUserID = self.construct_empty_user(copyAttr[1], copyAttr[4],
                                                  copyAttr[2],
                                                  copyAttr[3],None)
            # get all items the original e_user had
            cursor.execute(
                'select item_id from item_to_e_user where e_user_id= %s and e_id = %s and setid = %s and model_name = %s and scenario_name = %s',
                (
                    givenUserID, given_e_id, given_set_id, modelName,
                    scenarioName))

            itemRows = cursor.fetchall()
            unique_rel_id = 0
            for row in itemRows:
                cursor.execute(
                    'insert into item_to_e_user values (%s,%s,%s,%s,%s,%s,%s)',
                    (newUserID, row[0], unique_rel_id, given_e_id, modelName,
                     scenarioName, given_set_id))
                unique_rel_id = unique_rel_id + 1
            self.dbconnect.commit()
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to copy construct experiment user!')

    def add_item_to_experiment_user(self, given_user_id, given_e_id,
                                    given_set_id, model_name, scenario_name,
                                    new_item_id, timestamp=None):
        new_item_id = int(new_item_id)
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'SELECT MAX(unique_rel_id) FROM (SELECT * FROM item_to_e_user WHERE e_user_id= %s and e_id = %s and setid = %s and model_name = %s and scenario_name = %s) as tempID',
                (
                    given_user_id, given_e_id, given_set_id, model_name,
                    scenario_name))
            # we always take the highest unique_rel_id and add 1, since it's
            # possible that an item was removed, so we can't just count the
            # unique_rel IDs
            unique_rel_id = cursor.fetchone()[0]
            if unique_rel_id is None:
                unique_rel_id = 0
            else:
                unique_rel_id = unique_rel_id + 1
            cursor.execute(
                'insert into item_to_e_user values (%s,%s,%s,%s,%s,%s,%s)',
                (given_user_id, new_item_id, unique_rel_id, given_e_id,
                 model_name,
                 scenario_name, given_set_id))
            self.dbconnect.commit()
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to add item to experiment user!')

    def delete_item_from_experiment_user(self, given_user_id, given_e_id,
                                         given_set_id, model_name,
                                         scenario_name, delete_item_id):
        cursor = self.dbconnect.get_cursor()
        try:
            cursor.execute(
                'DELETE FROM item_to_e_user WHERE e_user_id= %s and e_id = %s and setid = %s and model_name = %s and scenario_name = %s and item_id = %s',
                (
                    given_user_id, given_e_id, given_set_id, model_name,
                    scenario_name, delete_item_id))
            self.dbconnect.commit()
        except:
            self.dbconnect.rollback()
            raise Exception('Unable to remove item from experiment user!')

    def get_experiment_items(self, experiment_id, s_id, model_name,
                             scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT DISTINCT(item_id) FROM subset_of_dataset WHERE setid = %s AND scenario_name = %s',
            (s_id, scenario_name,))
        itemDict = {}
        for row in cursor:
            itemDict[f"{row[0]}"] = row[0]
        return itemDict

    def get_experiment_name(self, experiment_id, s_id, model_name,
                            scenario_name):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT experiment_name FROM experiment WHERE e_id = %s AND model_name = %s AND scenario_name = %s AND setid = %s',
            (experiment_id, model_name, scenario_name, s_id))
        return cursor.fetchone()[0]

    def get_experiment_shared_with(self, experiment_id, model_name,
                                   scenario_name, set_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT uid FROM experiment_shared_with WHERE e_id = %s AND model_name = %s AND scenario_name = %s AND setid = %s',
            (experiment_id, model_name, scenario_name, set_id))
        returnUsers = []
        for row in cursor:
            returnUsers.append(row[0])
        return returnUsers

    def get_subset_user_ids(self, given_set_id,given_scenario_name,genType):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT user_id,gen_param FROM subset_of_dataset WHERE setid =%s AND scenario_name = %s',
            (given_set_id, given_scenario_name))
        idList = cursor.fetchall()
        returnIdSet = set()
        for userAndGenParam in idList:
            if genType == "SG":
                if userAndGenParam[1].split(',')[0] == "T":
                    continue
            returnIdSet.add(userAndGenParam[0])
        return list(returnIdSet)

    def experiment_get_item(self, experiment_id, s_id, scenario_name,
                            model_name, item_id):
        itemDict = {"item": item_id}
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT tmstmp FROM dataset_content WHERE setid = %s AND item_id = %s ORDER BY tmstmp asc',
            (s_id, item_id))
        itemDict["firstInteraction"] = cursor.fetchone()[0]
        cursor.execute(
            'SELECT COUNT(user_id) FROM dataset_content WHERE setid = %s',
            (s_id,))
        userTotal = cursor.fetchone()[0]
        cursor.execute(
            'SELECT COUNT(DISTINCT user_id) FROM dataset_content WHERE setid = %s AND item_id = %s',
            (s_id, item_id))
        usersInteractedWithItem = cursor.fetchone()[0]
        itemDict["popularity"] = str(
            usersInteractedWithItem / userTotal * 100) + "%"
        cursor.execute(
            'SELECT * FROM metadata WHERE setid = %s AND item_id = %s',
            (s_id, item_id))
        metadataList = []
        for row in cursor:
            metaDict = {}
            dataType = row[2]
            valueOffset = 0
            if dataType == 'string' or dataType == 'url':
                valueOffset = 1
            metaDict["meaning"] = row[3]
            metaDict["value"] = row[4 + valueOffset]
            if dataType == 'url':
                metaDict["data-type"] = "url"
            metadataList.append(metaDict)
        itemDict["row"] = metadataList
        return itemDict

    # experiment functionalities

    def get_experiment_owned_user_id(self, user_id):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT * FROM experiment e, dataset d , users u WHERE u.uid = (%s) and u.uid = d.uid and d.setid = e.setid ',
            (user_id,))
        x = cursor.fetchall()
        return x

    def get_owner_by_experiment(self, eid):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT u.username FROM experiment e, dataset d , users u WHERE e.E_ID = (%s) and u.uid = d.uid and d.setid = e.setid ',
            (eid,))
        x = cursor.fetchall()
        return x

    def get_experiments(self, experiment_id):
        x = self.get_experiment_owned_user_id(experiment_id)
        experiment = list()
        for row in x:
            number_shared = self.number_shared_experiment(row[0])[0]
            experiment.append({"experimentId": row[0], "experimentName": row[4],
                               "model": row[1], "scenarioName": row[2],
                               "sId": row[3], "numberShared": number_shared[0]})

        cursor = self.dbconnect.get_cursor()
        # cursor.execute('SELECT ex FROM experiment_shared_with e , users u ,
        # experiment ex WHERE u.uid = (%s) and u.uid = e.uid and
        # ex.E_ID = e.E_ID',(id,))
        cursor.execute(
            'SELECT * FROM experiment_shared_with WHERE e_id IN (SELECT e_id FROM experiment WHERE setid IN (SELECT setid FROM dataset WHERE uid= %s))',
            (experiment_id,))
        experiment_shared = cursor.fetchall()
        cursor.execute('SELECT * FROM experiment_shared_with WHERE uid = %s',
                       (experiment_id,))
        experiment_shared = experiment_shared + cursor.fetchall()
        for row in experiment_shared:
            # insTuple = row[0][1:-1].split(',')
            insTuple = row

            number_shared = self.number_shared_experiment(insTuple[1])[0]
            owner = self.get_owner_by_experiment(insTuple[1])
            if owner[0][0] == self.get_username(experiment_id):
                continue
            eName = self.get_experiment_name(insTuple[1], insTuple[4],
                                             insTuple[2], insTuple[3])
            experiment.append(
                {"experimentId": insTuple[1], "experimentName": eName,
                 "model": insTuple[2], "scenarioName": insTuple[3],
                 "sId": insTuple[4], "numberShared": number_shared[0],
                 "originalOwner": owner[0][0]})

        return experiment

    def number_shared_experiment(self, eid):
        cursor = self.dbconnect.get_cursor()
        cursor.execute(
            'SELECT COUNT(E_ID) FROM experiment_shared_with WHERE E_ID = (%s) ',
            (eid,))
        count = cursor.fetchall()
        return count

    def set_scenario_statistics(self, given_dataset_id, scenarioName):
        cursor = self.dbconnect.get_cursor()
        statistics:str = ""
        cursor.execute(
            'SELECT COUNT(*) FROM subset_of_dataset WHERE setid=(%s) AND scenario_name=%s',
            (given_dataset_id,scenarioName))
        statistics += str((cursor.fetchone()[0])) + ","
        cursor.execute(
            'SELECT COUNT (DISTINCT user_id) FROM subset_of_dataset WHERE setid=(%s) AND scenario_name=%s',
            (given_dataset_id,scenarioName))
        statistics += str((cursor.fetchone()[0])) + ","
        cursor.execute(
            'SELECT COUNT ( DISTINCT item_id ) FROM subset_of_dataset WHERE setid=(%s)AND scenario_name=%s',
            (given_dataset_id,scenarioName))
        statistics += str((cursor.fetchone()[0]))

        cursor.execute('UPDATE scenario SET statistics = %s WHERE setid = %s AND scenario_name = %s',(statistics,given_dataset_id,scenarioName))
        self.dbconnect.commit()
        return

    def split_subset(self, setId, scenarioName):
        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM scenario WHERE setid = %s AND scenario_name = %s',(setId,scenarioName))
        rowVal = cursor.fetchone()
        generalizationInfo = rowVal[-1].split(',')  # [genType,valIn,trainingUsers]
        dataframe= self.getsubset_content(setId, scenarioName)
        x = util.df_to_csr(dataframe)
        perc_history = float((100-int(generalizationInfo[1]))/100)
        usersInSubset = int(rowVal[-2].split(',')[1])
        training_users = int(usersInSubset*float(int(generalizationInfo[2])/100))
        test_users = usersInSubset-training_users
        if generalizationInfo[0] == "SG":
            splitSets = strong_generalization.strong_generalization(x,test_users,perc_history)
        else:
            splitSets = weak_generalization.weak_generalization(x,perc_history)
        # we're gonna replace the entries with new ones, based on the splitSets,
        # so we remove the old subset-entries
        cursor.execute('DELETE FROM subset_of_dataset WHERE setid = %s AND scenario_name = %s',(setId,scenarioName))
        # we store the fact that users are Training-users
        trainingMatrix = scipy.sparse.coo_matrix(splitSets[0])
        valInMatrix = scipy.sparse.coo_matrix(splitSets[1])
        valOutMatrix = scipy.sparse.coo_matrix(splitSets[2])

        trainingIdMapping = {}
        if generalizationInfo[0] == "SG":
            genParam = "T,"
            itemId = 0
            for i,j,v in zip(trainingMatrix.row,trainingMatrix.col,trainingMatrix.data):
                if v == 0:
                    continue
                userId = int(i)
                if userId in trainingIdMapping:
                    userId = trainingIdMapping[userId]
                else:
                    newId = len(trainingIdMapping)
                    trainingIdMapping[userId] = newId
                    userId = newId
                itemId = int(j)
                cursor.execute('INSERT INTO subset_of_dataset(user_id,item_id,scenario_name,setid,gen_param) VALUES (%s,%s,%s,%s,%s)',(userId,itemId,scenarioName,setId,genParam))
            # we add mock-interactions from 1 user to all items that fall
            # between the last-added one above, and the actual max(item_id)
            # s.t. the dimensions match for getting recommendations later
            userId = len(trainingIdMapping)
            trainingIdMapping[userId] = userId
            counter = itemId
            while counter != max(dataframe['iid'])+1:
                cursor.execute('INSERT INTO subset_of_dataset(user_id,item_id,scenario_name,setid,gen_param) VALUES (%s,%s,%s,%s,%s)',(userId,counter,scenarioName,setId,genParam))
                counter += 1
            self.dbconnect.commit()
            freeUserId = len(trainingIdMapping)
        else:
            freeUserId = 0

        for i,j,v in zip(valInMatrix.row,valInMatrix.col,valInMatrix.data):
            if v == 0:
                continue
            userId = freeUserId + int(i)
            itemId = int(j)
            genParam = ",Vi"
            if generalizationInfo[0] == "WG":
                genParam = "T,Vi"
            cursor.execute('INSERT INTO subset_of_dataset(user_id,item_id,scenario_name,setid,gen_param) VALUES (%s,%s,%s,%s,%s)',(userId,itemId,scenarioName,setId,genParam))

        if generalizationInfo[0] == "WG":
            genParam = "T,Vi"
            userId = userId+1
            counter = itemId
            while counter != max(dataframe['iid']) + 1:
                cursor.execute(
                    'INSERT INTO subset_of_dataset(user_id,item_id,scenario_name,setid,gen_param) VALUES (%s,%s,%s,%s,%s)',
                    (userId, counter, scenarioName, setId, genParam))
                counter += 1
        self.dbconnect.commit()

        for i,j,v in zip(valOutMatrix.row,valOutMatrix.col,valOutMatrix.data):
            if v == 0:
                continue
            userId = freeUserId + int(i)
            itemId = int(j)
            genParam = ",Vo"
            cursor.execute('INSERT INTO subset_of_dataset(user_id,item_id,scenario_name,setid,gen_param) VALUES (%s,%s,%s,%s,%s)',(userId,itemId,scenarioName,setId,genParam))
        self.dbconnect.commit()
        return

    def graph_data(self,setid,scenario_name,model_name):

        cursor = self.dbconnect.get_cursor()
        cursor.execute('SELECT * FROM subset_of_dataset WHERE setid = %s AND scenario_name=%s',(setid,scenario_name))
        All = cursor.fetchall()
        cursor.execute('SELECT max(user_id) FROM subset_of_dataset WHERE setid = %s AND scenario_name=%s AND gen_param=%s',(setid,scenario_name,"T,"))
        filterUserId = cursor.fetchone()[0]
        users_per_inters = dict()
        users_per_products = dict()
        cursor.execute('SELECT recall_cache FROM model WHERE setid=%s AND scenario_name=%s AND model_name=%s',(setid,scenario_name,model_name))
        listOfRecallPoints = cursor.fetchone()[0]
        recallReturnList = list()
        recallReturnListMax = 100
        if listOfRecallPoints:
            listOfRecallPoints = listOfRecallPoints.split(',')
            for idHistRec in listOfRecallPoints[:-1]:
                splitTuple = idHistRec.split(';')
                userId = splitTuple[0]
                histLength = splitTuple[1]
                recPercent = splitTuple[2]
                recallReturnList.append([histLength,recPercent,userId])

        for row in All:
            if row[0] == filterUserId:
                continue
            if users_per_inters.get(row[0]):
                users_per_inters[row[0]] +=1
            else:
                users_per_inters[row[0]] = 1

        returnvalue1 = list()

        for el in users_per_inters:
            returnvalue1.append([el,users_per_inters[el]])
        ymax = max(users_per_inters.items(), key=operator.itemgetter(1))[1]

        for row in All:
            if users_per_products.get(row[1]):
                users_per_products[row[1]] +=1
            else:
                users_per_products[row[1]] = 1

        output = dict(sorted(users_per_products.items()))
        returnvalue3 = list()

        ymax3 = max(users_per_products.items(), key=operator.itemgetter(1))[1]

        for el in output:
            returnvalue3.append([el,users_per_products[el]])

        ymax2=0
        returnvalue2 = list()

        for i in range(0,ymax+1):
            total = sum(value == i for value in users_per_inters.values())
            if total !=0:
                returnvalue2.append([i,total])
                if total >ymax2:
                    ymax2=total

        returnvalue4 = list()
        ymax4=0
        for i in range(0, ymax3 + 1):
            total = sum(value == i for value in users_per_products.values())
            if total !=0:
                returnvalue4.append([i, total])
                if total > ymax4:
                    ymax4=total

        return returnvalue1,ymax,returnvalue2,ymax2,returnvalue3,ymax3,returnvalue4,ymax4,recallReturnList,recallReturnListMax
