# EARHART project by Aviv, Tobias, Wannes, Sander & Joshua
# based on TUTORIAL Len Feremans, Sandy Moens and Joey De Pauw
import os
import time
import json
import uuid
import threading
import pandas as pd

from flask.templating import render_template
from config import config_data
from user_data_access import *
from flask_login import LoginManager, login_user, login_required, \
    logout_user, current_user
from io import StringIO
from model_training import pop_save, iknn_save, ease_save, wmf_save
from functools import wraps
from flask import Flask, current_app, request, jsonify, redirect
from werkzeug.exceptions import HTTPException, InternalServerError


# INITIALIZE SINGLETON SERVICES
app = Flask('Tutorial ')
app.secret_key = '*^*(*&)(*)(*afafafaSDD47j\3yX R~X@H!jmM]Lwf/,?KT'
tasks = {}
app_data = dict()
app_data['app_name'] = config_data['app_name']
connection = DBConnection(dbname=config_data['dbname'],
                          dbuser=config_data['dbuser'])
users_data_access = UserDataAccess(connection)
dataset_access = datasetDataAcces(connection)

DEBUG = False
HOST = "127.0.0.1" if DEBUG else "0.0.0.0"

login_mananger = LoginManager()
login_mananger.init_app(app)
login_mananger.login_view = "/login"


# Background tasks wrapper.

def flask_async(f):
    """
    This decorator transforms a sync route to asynchronous by running it in a background thread.
    """

    @wraps(f)
    def wrapped(*args, **kwargs):
        def task(app, environ):
            # Create a request context similar to that of the original request
            with app.request_context(environ):
                try:
                    # Run the route function and record the response
                    tasks[task_id]['result'] = f(*args, **kwargs)
                except HTTPException as e:
                    tasks[task_id][
                        'result'] = current_app.handle_http_exception(e)
                except Exception as e:
                    # The function raised an exception, so we set a 500 error
                    tasks[task_id]['result'] = InternalServerError()
                    if current_app.debug:
                        # We want to find out if something happened so reraise
                        raise

        # Assign an id to the asynchronous task
        task_id = uuid.uuid4().hex

        # Record the task, and then launch it
        tasks[task_id] = {'task': threading.Thread(
            target=task,
            args=(current_app._get_current_object(), request.environ))}
        tasks[task_id]['task'].start()

        # Return a 202 response, with an id that the client can use to obtain task status
        return {'TaskId': task_id}, 202

    return wrapped

# Login / Logout

@login_mananger.user_loader
def load_user(user_id):
    # Should return the user object
    return users_data_access.get_user(user_id)


@app.route("/API/login", methods=['POST'])
def user_login_to_url():
    data = request.get_json()
    validation = users_data_access.email_and_password_match(email=data['email'],
                                                            password=data[
                                                                'password'])
    if validation[0] == 1:
        u = load_user(users_data_access.get_id_based_on_email(data['email']))
        login_user(u)
        return jsonify({'message': 'Logged in'}), 200
    else:
        return jsonify({'message': 'email and/or password in incorrect'}), 200


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('index.html', app_data=app_data)


@app.route('/API/signup', methods=['POST'])
def add_user():
    user_fullname = request.form.get('Fullname')
    user_email = request.form.get('EmailAddress')
    user_name = request.form.get('Username')
    user_psswrd = request.form.get('Password')

    user_obj = User(iden=None, fullname=user_fullname, username=user_name,
                    email=user_email, password=user_psswrd)
    print('Adding {}'.format(user_obj.to_dct()))
    user_obj = users_data_access.add_user(user_obj)

    # ---------------------------------------------------------------------------
    data = request.get_json()

    if user_obj is False:
        count_username = users_data_access.find_username(data['username'])
        count_email = users_data_access.find_email(data['email'])

        if count_username[0] != 0:
            return jsonify({'message': 'User already taken'}), 200
        elif count_email[0] != 0:
            return jsonify({'message': 'Email already taken'}), 200
        else:
            return jsonify({'message': 'Insert all required fields'}), 200
    else:
        u = load_user(users_data_access.get_id_based_on_email(user_email))
        login_user(u)
        return redirect("/user")


# VIEW
@app.route("/")
def main():
    return render_template('index.html', app_data=app_data)


@app.route("/about-us")
def about_us():
    return render_template('about-us.html', app_data=app_data)


@app.route("/signup")
def user_signup():
    return render_template('signup.html', app_data=app_data)


@app.route("/login")
def user_login():
    return render_template('login.html', app_data=app_data)


@app.route("/user/")
@login_required
def user_homepage():
    return render_template('user_homepage.html', app_data=app_data)


@app.route("/user/datasets")
@login_required
def user_datasets():
    return render_template('user_datasets.html')


@app.route("/user/scenarios")
@login_required
def user_scenario():
    return render_template('user_scenario.html', app_data=app_data)


@app.route("/user/scenarios")
@login_required
def test2():
    return render_template('user_scenario.html', app_data=app_data)


@app.route("/user/models")
@login_required
def test3():
    return render_template('Model.html', app_data=app_data)


@app.route("/user/experiments")
@login_required
def user_experiment():
    return render_template('user_experiment.html', app_data=app_data)


@app.route("/user/experiments/visualization")
@login_required
def user_experiment_visualization():
    return render_template('user_experiment_visualization.html',
                           app_data=app_data)


# REST API


# - START: API that need the backend
# - All of them are for Datasets
@app.route("/API/metafile-sample")
@login_required
def get_metafile_sample():
    dataset_id = request.args["id"]
    meta_filename = request.args["filename"]
    sample = dataset_access.get_metadata_sample(dataset_id, meta_filename)
    return jsonify({
        "header": sample[0],
        "row": sample[1]})


@app.route("/API/interaction-sample")
@login_required
def get_interaction_sample():
    dataset_id = request.args["id"]
    # gets the first 5 rows from the current set ID's interaction table
    sample = dataset_access.get_interaction_sample(dataset_id)
    return jsonify({"header": sample[0],
                    "row": sample[1]})


@app.route("/API/dataset-reference")
@login_required
def get_dataset_reference():
    dataset_id = request.args["id"]
    scenario_number = dataset_access.get_dataset_scenario_count(dataset_id)
    return jsonify(scenario_number)


@app.route("/API/dataset", methods=['DELETE'])
@login_required
def delete_dataset():
    dataset_id = request.args["id"]
    dataset_access.delete_dataset(dataset_id)
    return jsonify("Dataset has been deleted")


@app.route("/API/change-dataset-name", methods=['PUT'])
@login_required
def change_dataset_name():
    new_name = request.args["name"]
    dataset_id = request.args["id"]
    dataset_access.change_dataset_name(dataset_id, new_name)
    return jsonify("Name has been updated")


@app.route("/API/check-dataset-name", methods=['POST'])
@login_required
def check_dataset_name():
    # TODO OPTIONAL Check if the name is in the Database
    # name = request.args["name"]
    # if name == "invalid":
    #     return jsonify("invalid")
    # else:
    return jsonify("valid")


@app.route("/API/update-dataset-sharing", methods=['PUT'])
@login_required
def update_dataset_sharing():
    users_shared_with = request.args["users"].split(',')  # List of IDs
    dataset_id = request.args["id"]
    users_data_access.update_dataset_shared_with(users_shared_with, dataset_id)
    return jsonify("Sharing has been updated")


@app.route("/API/shared-users")
@login_required
def get_shared_users():
    dataset_id = request.args["id"]
    user_list = users_data_access.get_dataset_shared_with(dataset_id)
    return jsonify(user_list)


@app.route("/API/users")
@login_required
def get_users():
    # TODO: OPTIONAL Add limit select options to the chosen to hide this
    user_list = users_data_access.get_users()
    user_dict = {}
    for u in user_list:
        if u.id is not current_user.id:
            user_dict[f"{u.id}"] = u.username
    return jsonify(user_dict), 200


@app.route("/API/datasets")
@login_required
def get_user_datasets():
    gotten_info = dataset_access.get_datasets(current_user.id)
    gotten_meta_data = dataset_access.get_metadata_info(current_user.id)
    list_of_datasets = []
    current_datasets = gotten_info[0]
    current_statistics = gotten_info[1]
    for i in range(len(current_datasets)):
        data_set_object = {}
        current_set_id = current_datasets[i][0]
        data_set_object["datasetId"] = str(current_set_id)
        data_set_object["numberReferences"] = str(
            dataset_access.get_dataset_scenario_count(current_set_id))
        data_set_object["numberShared"] = str(
            len(users_data_access.get_dataset_shared_with(current_set_id)))
        data_set_object["datasetName"] = str(current_datasets[i][1])
        data_set_object["sourceFile"] = str(current_datasets[i][2])
        data_set_object["date"] = current_datasets[i][3]
        statisticsForDataset = current_statistics[i].split(',')
        data_set_object["totalInteractions"] = statisticsForDataset[0]
        data_set_object["totalUsers"] = statisticsForDataset[1]
        data_set_object["totalProducts"] = statisticsForDataset[2]
        meta_data = []
        for j in range(len(gotten_meta_data[i][0])):
            meta_data_file = {"fileName": gotten_meta_data[i][0][j]}
            column = []
            for dataTuple in gotten_meta_data[i][1][j]:
                tuple_dict = {"type": dataTuple[0], "meaning": dataTuple[1]}
                column.append(tuple_dict)
            meta_data_file["column"] = column
            meta_data.append(meta_data_file)
        data_set_object["metaFile"] = meta_data
        list_of_datasets.append(data_set_object)
    # shared with info starts here
    shared_with_info = dataset_access.get_datasets_shared_with(current_user.id)
    gotten_info = shared_with_info[0]
    gotten_meta_data = shared_with_info[1]
    current_datasets = gotten_info[0]
    current_statistics = gotten_info[1]
    for i in range(len(current_datasets)):
        data_set_object = {}
        current_set_id = current_datasets[i][0]
        data_set_object["datasetId"] = str(current_set_id)
        data_set_object["numberReferences"] = str(
            dataset_access.get_dataset_scenario_count(current_set_id))
        data_set_object["datasetName"] = str(current_datasets[i][1])
        data_set_object["sourceFile"] = str(current_datasets[i][2])
        data_set_object["originalOwner"] = users_data_access.get_username(
            current_datasets[i][4])
        data_set_object["date"] = current_datasets[i][3]
        statisticsForDataset = current_statistics[i].split(',')
        data_set_object["totalInteractions"] = statisticsForDataset[0]
        data_set_object["totalUsers"] = statisticsForDataset[1]
        data_set_object["totalProducts"] = statisticsForDataset[2]
        meta_data = []
        for j in range(len(gotten_meta_data[i][0])):
            meta_data_file = {"fileName": gotten_meta_data[i][0][j]}
            column = []
            for dataTuple in gotten_meta_data[i][1][j]:
                tuple_dict = {"type": dataTuple[0], "meaning": dataTuple[1]}
                column.append(tuple_dict)
            meta_data_file["column"] = column
            meta_data.append(meta_data_file)
        data_set_object["metaFile"] = meta_data
        list_of_datasets.append(data_set_object)
    return jsonify({"dataset": list_of_datasets})


@app.route('/API/create-dataset', methods=['POST'])
@login_required
def get_quote():
    files = []
    dataframes = []
    interactionFile = request.files['interactionFile']
    interactionFile.save(os.path.join("uploads",interactionFile.filename))

    teller = 0
    fileIndexMap = {}
    for x in request.files:
        upload = request.files[x]

        if x != 'interactionFile':
            dataframes.append(
                pd.read_csv(StringIO(str(upload.read(), 'utf-8'))))
            fileIndexMap[x] = teller
            teller += 1

        filename = upload.filename
        files.append(filename)
    # Dict containing the normal info
    data = request.form

    # Value is either i<nr> if the representation is row <nr> from the
    # interaction file
    # or <id>m<i> if it is the ith row of the meta file with id = id
    text_representation = data["textRepresentation"]
    img_representation = data["imgRepresentation"]
    if text_representation[0] == 'i':  # if from interaction file, take itemId
        text_representation = "item_id"
    else:  # else, take meaning from metadata file
        metaId = fileIndexMap[text_representation.split('m')[0]]
        metaMeaningId = int(text_representation.split('m')[1])
        metaMeaningJson = json.loads(data['metaFilesMeaning'])
        text_representation = metaMeaningJson[metaId]['columns'][metaMeaningId]['meaning']
    if img_representation != '':  # if no img_representation, keep it empty
        if img_representation[0] == 'i':  # make it empty if from interaction file
            img_representation = ''  # no images expected in it ^^^
        else:  # if from metadata, take meaning from meta file
            metaId = fileIndexMap[img_representation.split('m')[0]]
            metaMeaningId = int(img_representation.split('m')[1])
            metaMeaningJson = json.loads(data['metaFilesMeaning'])
            img_representation = metaMeaningJson[metaId]['columns'][metaMeaningId]['meaning']
    identifier = f'{text_representation},{img_representation}'
    json.loads(data['metaFilesMeaning'])
    name = data["datasetName"]
    userid = current_user.id
    sequence = [data["columnUserId"], data["columnItemId"],
                data["columnTimestamp"]]
    date = data["date"]
    dataset = Dataset(None, name, userid, files[0], sequence, date,
                      json.loads(data["metaFilesMeaning"]))
    setIdn = dataset_access.add_dataset(dataset, f"uploads/{interactionFile.filename}", dataframes)
    os.remove(os.path.join("uploads", interactionFile.filename))
    dataset_access.set_dataset_statistics(setIdn,identifier)
    users_data_access.update_dataset_shared_with(request.form['sharedWith'].split(','),setIdn)
    return jsonify("Dataset has been created")


# - Scenario related

@app.route('/API/datasets-minified')
def get_datasets_minified():
    user_id = current_user.id
    user_name = users_data_access.get_username(user_id)
    gotten_datasets = dataset_access.get_datasets(user_id, True)[0]
    set_dict = {}
    for currentSet in gotten_datasets:
        set_id = currentSet[0]
        set_name = currentSet[1]
        create_date = currentSet[3]
        owner_name = currentSet[-1]
        if owner_name == user_name:
            owner_name += " (you)"
        set_dict[
            f"{set_id}"] = set_name + " | " + create_date + " | " + owner_name
    return jsonify(set_dict)


@app.route("/API/check-scenario-name", methods=['POST'])
def check_scenario_name():
    # todo (optional) users needs unique scenario names now, update to
    #  allowing same scenario name for different datasets (like in DB)
    name = request.args["name"]
    user_id = current_user.id
    list_of_scenarios = dataset_access.get_scenarios(user_id)
    validity = "valid"
    for scenario in list_of_scenarios:
        if name == scenario[0]:
            validity = "invalid"
    return jsonify(validity)


@app.route("/API/create-scenario", methods=['POST'])
def create_scenario():
    scenarioInfo = request.json['scenario']
    dataset_access.create_scenario(scenarioInfo)
    scenarioName = scenarioInfo['name']
    setId = int(scenarioInfo['dataset'])
    users_data_access.make_subset(setId, scenarioName)
    users_data_access.set_scenario_statistics(setId,scenarioName)
    if scenarioInfo['generalizationType']:
        users_data_access.split_subset(setId,scenarioName)
    return jsonify("Scenario was created")


@app.route("/API/scenario")
def get_scenario():
    set_id = request.args["id"]
    name = request.args["name"]
    returnDict = {'datasetSelector': str(set_id)}
    processingSteps = users_data_access.get_processing_steps(set_id, name)
    preProcessingStepsList = []
    disableRetargeting = True

    genInfo = dataset_access.get_genInfo(set_id,name)[0]
    returnDict["trainingUsers"] = ""
    returnDict["validationIn"] = ""
    if genInfo:
        genInfo = genInfo.split(',')
        returnDict["generalizationType"] = genInfo[0]  # or WG
        returnDict["validationIn"] = genInfo[1]  # Just the number no percentage
        if returnDict["generalizationType"] == "SG":
            returnDict["trainingUsers"] = genInfo[2]  # Only needed for Strong generalization

    for step in processingSteps:
        processingDictEntry = {}
        if step[1] == 'retargetingActive':
            disableRetargeting = False
        else:
            processingDictEntry['type'] = step[1]
            processingDictEntry['from'] = step[2].split(',')[0]
            processingDictEntry['to'] = step[2].split(',')[1]
            preProcessingStepsList.append(processingDictEntry)
    returnDict['preProcessingSteps'] = preProcessingStepsList
    returnDict['disableRetargeting'] = disableRetargeting
    return jsonify(returnDict)


@app.route("/API/change-scenario-name", methods=['PUT'])
def change_scenario_name():
    scenario_id = request.args["id"]
    new_name = request.args["newName"]
    current_name = request.args["oldName"]
    dataset_access.change_scenario_name(current_name, new_name, scenario_id)
    return jsonify("Name has been changed")


@app.route("/API/scenarios")
@login_required
def get_scenarios():
    return_dict = {}
    scenario_list = []
    user_id = current_user.id
    gotten_scenarios_and_steps = dataset_access.get_user_scenarios(user_id)
    gotten_scenarios = gotten_scenarios_and_steps[0]
    gotten_processing_steps = gotten_scenarios_and_steps[1]
    index = 0
    for scenario in gotten_scenarios:
        scenarioStatistics = scenario[2].split(',')
        current_scenario_dict = {'scenarioName': scenario[0],
                                 'scenarioID': scenario[1],
                                 'sourceName': scenario[-1],
                                 'totalInteractions' : scenarioStatistics[0],
                                 'totalProducts' : scenarioStatistics[2],
                                 'totalUsers' : scenarioStatistics[1],
                                 }
        referenceCount = dataset_access.get_scenario_model_count(scenario[1],scenario[0])
        current_scenario_dict["numberReferences"] = referenceCount
        retargetingActive = "No"
        processingStepsList = []

        scenarioGenInfo = scenario[3]  # store (possible) generalization info
        if scenarioGenInfo:
            scenarioGenInfo = scenarioGenInfo.split(',')  # exists -> split str
            genType = scenarioGenInfo[0]
            if genType == "SG":
                current_scenario_dict["generalizationType"] = "Strong generalization"
                current_scenario_dict["trainingUsers"] = f"{scenarioGenInfo[2]}%"  # Only needed for Strong generalization
            else:
                current_scenario_dict["generalizationType"] = "Weak generalization"
            current_scenario_dict["validationIn"] = f"{scenarioGenInfo[1]}%"

        for processingStep in gotten_processing_steps[index]:
            processing_type = processingStep[1]
            if processing_type == 'retargetingActive':
                retargetingActive = "Yes"
            else:
                currentProcessingDict = {}
                if processing_type == 'filterTime':
                    currentProcessingDict["type"] = "Timestamps"
                elif processing_type == 'filterUser':
                    currentProcessingDict["type"] = "Interactions per User"
                elif processing_type == 'filterItem':
                    currentProcessingDict["type"] = "Interactions per Item"
                currentProcessingDict['from'] = processingStep[2].split(',')[0]
                currentProcessingDict['to'] = processingStep[2].split(',')[1]
                processingStepsList.append(currentProcessingDict)
        current_scenario_dict['retargetingActive'] = retargetingActive
        current_scenario_dict['preProcessingStep'] = processingStepsList
        scenario_list.append(current_scenario_dict)
        index = index + 1
    return_dict['scenario'] = scenario_list
    return jsonify(return_dict)


@app.route("/API/scenario-reference")
@login_required
def get_scenario_reference():
    scenario_id = request.args["id"]
    name = request.args["name"]
    number_of_users = dataset_access.get_scenario_model_count(scenario_id, name)
    return jsonify(str(number_of_users))


@app.route("/API/scenario", methods=['DELETE'])
@login_required
def delete_scenario():
    set_id = request.args["id"]
    scenario_name = request.args["name"]
    dataset_access.delete_scenario(scenario_name, set_id)
    return jsonify("Scenario has been deleted")


# - API Model

@app.route("/API/create-model", methods=['POST'])
@login_required
def create_model():
    data = request.json['model']
    model_name = data['model_name']
    scenario_name = data['scenario_name']
    set_id = scenario_name.split(',')[1]
    scenario_name = scenario_name.split(',')[0]
    algorithm = data['algorithm']
    p1 = data['parameter1']
    p2 = data['parameter2']
    p3 = data['parameter3']
    p4 = data['parameter4']

    parameters = p1 + "," + p2 + "," + p3 + "," + p4
    model = Model(model_name, algorithm, parameters, scenario_name, set_id)
    crossvalidation=users_data_access.get_crossval_type(scenario_name,set_id)

    dataframe = users_data_access.getsubset_content(set_id, scenario_name)

    model.info = f"./uploads/SET{set_id}SCENARIO{scenario_name}MODEL{model.Model_name}"
    if algorithm == "Random":

        # guess i'll leave this here?

        time_start = time.time()
        time_result = time.time() - time_start
        model.time = str(time_result) + "sec"
        users_data_access.addModel(model)

    elif algorithm == "Popularity":

        train_popularity(dataframe, model)

    elif algorithm == "Item nearest neighbours":

        train_iknn(dataframe, model, p1, p2)

    elif algorithm == "EASE":

        train_ease(dataframe, model, p1)

    elif algorithm == "Weighted Matrix Factorization":

        train_wmf(dataframe, model, p1, p2, p3, p4)

    else:
        return jsonify("Something went wrong when trying to train the model.")

    # inserts the model into the database happens in the train functions

    return jsonify("Model was created.")

#todo (optional): force refresh model page after addModel is performed for each train func

@app.route("/API/create-model/popularity")  # --> might not be necessary
@login_required  # -->   if the first one isn't needed i assume
#                       this one wouldn't be either
@flask_async
def train_popularity(dataframe, model):
    time_start = time.time()
    pop_save(dataframe, model.info)
    time_result = time.time() - time_start
    model.time = str(time_result) + "sec"
    users_data_access.addModel(model)
    dataset_access.generateRecallAtK(model)



@app.route("/API/create-model/iknn")
@login_required
@flask_async
def train_iknn(dataframe, model, p1, p2):
    boolean = False
    p2 = p2.lower()
    if p2 == "true":
        boolean = True

    time_start = time.time()
    iknn_save(dataframe, model.info, int(p1), boolean)
    time_result = time.time() - time_start
    model.time = str(time_result) + "sec"
    users_data_access.addModel(model)
    dataset_access.generateRecallAtK(model)



@app.route("/API/create-model/ease")
@login_required
@flask_async
def train_ease(dataframe, model, p1):
    time_start = time.time()
    ease_save(dataframe, model.info, float(p1))
    time_result = time.time() - time_start
    model.time = str(time_result) + "sec"
    users_data_access.addModel(model)
    dataset_access.generateRecallAtK(model)



@app.route("/API/create-model/wmf")
@login_required
@flask_async
def train_wmf(dataframe, model, p1, p2, p3, p4):
    time_start = time.time()
    wmf_save(dataframe, model.info,
             float(p1), int(p2), float(p3), int(p4))
    time_result = time.time() - time_start
    model.time = str(time_result) + "sec"
    users_data_access.addModel(model)
    dataset_access.generateRecallAtK(model)



@app.route("/API/model-reference")
@login_required
def get_experiment_reference():
    sid = request.args["sid"]
    scenario_name = request.args["sn"]
    model_name = request.args["mn"]
    count = dataset_access.count_experiments_using_model(sid, scenario_name,
                                                         model_name)
    return jsonify(count)


@app.route("/API/models")
@login_required
def user_get_models():
    dict_return = {"model": dataset_access.get_models(current_user.id)}
    # todo: maybe the fixme below is optional? don't see in project PDF
    #  that we have to show recall@k for everything
    # FIXME: Calculate this value when training the Model
    #   Pass it to the front-end for all Models that use WG/SG

    # dict_return["model"][0]["avgRecallAtK"] = "80%"
    return jsonify(dict_return)


@app.route("/API/model", methods=['DELETE'])
@login_required
def delete_model():
    set_id = request.args["sid"]
    scenario_name = request.args["sn"]
    model_name = request.args["mn"]
    users_data_access.delete_model(model_name, scenario_name, set_id)
    return jsonify("Model has been deleted.")


@app.route("/API/scenarios-minified")
@login_required
def get_scenarios_minified():
    user_id = current_user.id
    user_scenarios = dataset_access.get_scenarios(user_id)
    scenario_dict = {}
    for sc in user_scenarios:
        scenario_dict[f"{sc[0]},{sc[1]}"] = sc[0]
    return jsonify(scenario_dict)


# - API Experiments

@app.route("/API/experiments")
@login_required
def get_experiments():
    expr = users_data_access.get_experiments(current_user.id)
    all_expr = {"experiment": []}
    for x in expr:
        genInfo = dataset_access.get_genInfo(x['sId'],x['scenarioName'])
        if genInfo:
            x["generalizationType"] = genInfo[0].split(',')[0]
        all_expr["experiment"].append(x)

    return jsonify(all_expr)


@app.route('/API/models-minified')
@login_required
def get_models_minified():
    user_id = current_user.id
    user_models = users_data_access.get_models(user_id)
    models_dict = {}
    for m in user_models:
        models_dict[
            f"{m.Scenario_name},{m.Model_name},{m.SetID}"] = m.Model_name
    return jsonify(models_dict)


@app.route("/API/check-experiment-name", methods=['POST'])
@login_required
def check_experiment_name():
    name = request.args["name"]
    # TODO (optional) Check if the name is in the Database
    if name == "invalid":
        return jsonify("invalid")
    else:
        return jsonify("valid")


@app.route("/API/create-experiment", methods=['POST'])
@login_required
def create_experiment():
    data = json.loads(request.data)
    list_of_data = data["data"]["modal"].split(',')
    scenario_name = list_of_data[0]
    model_name = list_of_data[1]
    set_id = int(list_of_data[2])
    shared_with = data["data"]["shared"]

    experiment = Experiment(data["data"]["name"], model_name, scenario_name,
                            set_id)
    dataset_access.create_experiment(experiment, shared_with)
    return jsonify("Experiment has been created")


@app.route("/API/experiment-get-shared-users")
@login_required
def experiment_get_shared():
    set_id = request.args["sId"]
    scenario_name = request.args["sName"]
    model_name = request.args["mName"]
    experiment_id = request.args["eId"]
    user_list = users_data_access.get_experiment_shared_with(experiment_id,model_name,scenario_name,set_id)
    return jsonify(user_list), 200


@app.route("/API/experiment", methods=['DELETE'])
@login_required
def delete_experiment():
    set_id = request.args["sId"]
    scenario_name = request.args["sName"]
    model_name = request.args["mName"]
    experiment_id = request.args["eId"]
    users_data_access.delete_experiment(experiment_id, model_name,
                                        scenario_name, set_id)
    return jsonify("Experiment has been deleted")


@app.route("/API/update-experiment-sharing", methods=['PUT'])
@login_required
def update_experiment_sharing():
    users_shared_with = request.args["users"].split(',')  # List of IDs
    set_id = request.args["sId"]
    scenario_name = request.args["sName"]
    model_name = request.args["mName"]
    experiment_id = request.args["eId"]
    dataset_access.update_experiment_shared_with(users_shared_with,
                                                 experiment_id, model_name,
                                                 scenario_name, set_id)
    return jsonify("Sharing has been updated")


@app.route("/API/experiment-users")
@login_required
def get_experiment_user_names():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    experiment_users = dataset_access.find_all_experiment_users(experiment_id,
                                                                model_name,
                                                                scenario_name,
                                                                s_id)

    if len(experiment_users) == 0:
        return jsonify({})
    listofids = []
    listofStaticIds = []
    for user in experiment_users:
        if user[-1] is None:
            listofids.append(user[0])
        else:
            listofStaticIds.append(user[0])

    #gives back a dataframe with user id and exp id
    expinterinteractions = dataset_access.getExperimentHistory(experiment_id)

    itemdictionary = dataset_access.makeDictionary(s_id,scenario_name)
    # we fill in values for items that were not in the dictionary,
    # to 'plug' gaps
    maxItemId = max(itemdictionary)
    for i in range(maxItemId):
        if i not in itemdictionary:
            newIndex = len(itemdictionary)
            if newIndex > maxItemId:
                break
            itemdictionary[i] = newIndex

    useridlisthistory = []
    reverse_itemdictionary = {v: k for k, v in itemdictionary.items()}

    for x in listofids:
        useridlisthistory.append(
            dataset_access.makehistoryForUser(x, expinterinteractions))

    completematrix = dataset_access.fillHistoryMatrix(useridlisthistory,
                                                      itemdictionary)
    
    staticuseridlisthistory = []
    for x in experiment_users:
        if x[0] in listofStaticIds:
            itemlist = []
            staticUserItems = dataset_access.get_static_user_items(x[-1], s_id,
                                                                   scenario_name)
            for itemAndParam in staticUserItems:
                genParam = itemAndParam[1].split(',')
                if genParam[1] == "Vi":
                    itemlist.append(itemAndParam[0])
            staticuseridlisthistory.append(itemlist)
    completeStaticMatrix = dataset_access.fillHistoryMatrix(staticuseridlisthistory,itemdictionary)
    model = users_data_access.get_model(model_name, scenario_name, s_id)
    # todo (optional) let user choose top-k
    top_k: int = 5
    # generate an abundance (+25) of recommendations for disabled retargeting
    listOfRec = dataset_access.runalgo(model.Algorithm, listofids,
                                       completematrix, model, top_k + 25)
    staticlistOfRec = dataset_access.runalgo(model.Algorithm, listofStaticIds,
                                             completeStaticMatrix, model, top_k + 25)
    enableRetargeting = users_data_access.get_retargeting_active(s_id,
                                                                 scenario_name)
    exp_users_dict = {"user": []}
    teller = 0
    staticteller=0
    for x in experiment_users:
        if x[0] in listofStaticIds:
            staticUserItems = dataset_access.get_static_user_items(x[-1],s_id,scenario_name)
            validationInList = []
            validationOutList = []
            valInIdList = []
            for itemAndParam in staticUserItems:
                time_start = time.time()
                currentItemDict = makeItemDictEntry(itemAndParam[0],s_id,False)
                # print(f'Making single dict entry: {time.time() - time_start}s')
                genParam = itemAndParam[1].split(',')
                if genParam[1] == "Vi":
                    validationInList.append(currentItemDict)
                    valInIdList.append(itemAndParam[0])
                else:
                    validationOutList.append(currentItemDict)
            recommendationslist = []
            for y in range(len(staticlistOfRec[staticteller][0])):
                 statAsPercentage = str(min(staticlistOfRec[staticteller][1][y] * 100, 100))[:5]
                 itemId = int(staticlistOfRec[staticteller][0][y])
                 if model.Algorithm == "Random":
                     itemId = reverse_itemdictionary[itemId]
                 partOfRecommendation = makeItemDictEntry(itemId, s_id,True)
                 partOfRecommendation["stat"] = statAsPercentage
                 recCorrect = "No"
                 for valCheck in validationOutList:
                     if valCheck["itemId"] == itemId:
                         recCorrect = "Yes"
                         break
                 partOfRecommendation["correct_recommendation"] = recCorrect
                 recommendationslist.append(partOfRecommendation)
            # code for retargeting
            newRecList = []
            if not enableRetargeting:
                correctCounter = 0
                for rec in recommendationslist:
                    recItemId = int(rec['item'])
                    if recItemId not in valInIdList:
                        if len(newRecList) < top_k:
                            if rec['correct_recommendation'] == 'Yes':
                                correctCounter += 1
                            newRecList.append(rec)
            else:
                correctCounter = 0
                for i in range(top_k):
                    if recommendationslist[i]['correct_recommendation'] == 'Yes':
                        correctCounter += 1
                    newRecList.append(recommendationslist[i])
            staticteller += 1
            minVal = min(len(newRecList),len(validationOutList))
            if minVal == 0:
                recallAtkVal = 0
            else:
                recallAtkVal = int((correctCounter/minVal)*100)
            dictionary_ids = {"id": x[0],"staticId":x[-1], "recallAtK":f"{recallAtkVal}%",
                              "recommendation": newRecList,
                              "timestamps": "false","validationIn": validationInList, "validationOut":validationOutList}
            exp_users_dict["user"].append(dictionary_ids)
        else:  # standard experiment-user functionality
            experiment_items = dataset_access.find_all_experiments_users_used_items_by_user(x[0], experiment_id, model_name, scenario_name, s_id)

            recommendationslist = []
            for y in range(len(listOfRec[teller][0])):
                statAsPercentage = str(min(listOfRec[teller][1][y] * 100,100))[:5]
                itemId = int(listOfRec[teller][0][y])
                if model.Algorithm == "Random":
                    itemId = reverse_itemdictionary[itemId]  # Debugging
                partOfRecommendation = makeItemDictEntry(itemId,s_id,True)
                partOfRecommendation["stat"] = statAsPercentage
                recommendationslist.append(partOfRecommendation)
            teller += 1
            # filter out for retargeting
            newRecList = []
            if not enableRetargeting:
                for rec in recommendationslist:
                    recItemId = (int(rec['item']),)
                    if recItemId not in experiment_items:
                        if len(newRecList) < top_k:
                            newRecList.append(rec)
            else:  # if retargeting active, just pick top_k from generated
                for i in range(top_k):
                    newRecList.append(recommendationslist[i])

            dictionary_ids = {"id": x[0],
                              "recommendation": newRecList,
                              "timestamps": "false"}

            history_item_array = []
            for y in experiment_items:
                currentItemDict = makeItemDictEntry(y[0],s_id,False)
                history_item_array.append(currentItemDict)
            dictionary_ids["historyItem"] = history_item_array
            exp_users_dict["user"].append(dictionary_ids)
    return jsonify(exp_users_dict)


def makeItemDictEntry(given_item_id,set_id, isRecommendation:bool = False):
    placeHolderImage = "https://uploads-ssl.webflow.com/5ee118733109492e193e63d2/5fc91037939fd969652fc98e_Froomle%20founders.png"
    textRepr: str = dataset_access.get_text_for_item(set_id, given_item_id)
    if textRepr == "item_id":  # if textRepr is just item_id
        textRepr = str(given_item_id)  # we use the item id as representation
    imgRepr: str = dataset_access.get_image_for_item(set_id, given_item_id)
    # imgRepr is empty string '' if no img representation exists
    if isRecommendation:
        history_item_array_dict = {"item": given_item_id, "text_representation": textRepr}
    else:
        history_item_array_dict = {"itemId": given_item_id, "text_representation": textRepr}
    if imgRepr != "":
        history_item_array_dict['image_representation'] = imgRepr
    else:
        history_item_array_dict['image_representation'] = placeHolderImage
    return history_item_array_dict


@app.route("/API/experiment-name")
@login_required
def get_experiment_name():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    e_name = users_data_access.get_experiment_name(experiment_id, s_id,
                                                   model_name, scenario_name)
    return jsonify(e_name)


@app.route("/API/experiment-create-empty-user", methods=['POST'])
@login_required
def create_empty_user():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    users_data_access.construct_empty_user(experiment_id, s_id, model_name,
                                           scenario_name,None)
    return jsonify("Empty user has been added")


@app.route("/API/experiment-create-random-user", methods=['POST'])
@login_required
def create_random_user():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    generalization = request.args["generalization"]  # WG | SG or empty
    isStatic = False
    if generalization:
        isStatic = True
    users_data_access.construct_rand_user(experiment_id, s_id, model_name,
                                          scenario_name,isStatic,generalization)
    return jsonify("Random user has been added")


@app.route("/API/experiment-copy-user", methods=['POST'])
@login_required
def experiment_copy_user():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    user_id = request.args["user-id"]
    users_data_access.construct_copy_user(user_id, experiment_id, s_id,
                                          model_name, scenario_name)
    return jsonify("User had been copied")


@app.route('/API/experiment-items')
@login_required
def experiment_get_items():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    item_list = users_data_access.get_experiment_items(experiment_id, s_id,
                                                       model_name,
                                                       scenario_name)
    return jsonify(item_list)


@app.route("/API/experiment-add-item", methods=['POST'])
@login_required
def experiment_add_item():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    user_id = request.args["id"]
    item = request.args["item"]
    timestamp = request.args["time"]  # Can be empty if the user wants
    users_data_access.add_item_to_experiment_user(user_id, experiment_id, s_id,
                                                  model_name,
                                                  scenario_name, item,
                                                  timestamp)
    return jsonify("Item has been added")


@app.route("/API/experiment-user", methods=['DELETE'])
@login_required
def experiment_delete_user():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    user_id = request.args["id"]
    dataset_access.delete_experiment_user(user_id, experiment_id, model_name,
                                          scenario_name, s_id)
    return jsonify("User has been deleted")


@app.route("/API/experiment-item", methods=['DELETE'])
@login_required
def experiment_delete_item():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    user_id = request.args["user"]
    item = request.args["item"]
    users_data_access.delete_item_from_experiment_user(user_id, experiment_id,
                                                       s_id,
                                                       model_name,
                                                       scenario_name, item)
    return jsonify("Item has been deleted")


@app.route("/API/experiment-add-user-wri", methods=['POST'])
@login_required
def experiment_add_user_wri():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    amount = request.args["amount"]
    users_data_access.construct_rand_items_user(experiment_id, s_id, model_name,
                                                scenario_name, amount)
    return jsonify("User has been created")


@app.route("/API/experiment-add-users-with-item", methods=['POST'])
@login_required
def experiment_add_users_with_item():
    # todo: for generalization, maybe only take users with item in their val_in?
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    item = request.args["item"]
    generalization = request.args["generalization"]  # SG | WG or empty
    isStatic = False
    if generalization:
        isStatic = True
    upper_bound = (
        int(request.args["amount"]) if request.args["amount"] != "" else 15)
    users_data_access.construct_specific_items_users(experiment_id, s_id,
                                                     model_name, scenario_name,
                                                     int(item),upper_bound,isStatic,generalization)
    return jsonify("User has been created")


@app.route("/API/item-info")
@login_required
def experiment_get_item():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    item = request.args["item"]
    # Only specify data-type if url
    item_dict = users_data_access.experiment_get_item(experiment_id, s_id,
                                                      scenario_name, model_name,
                                                      item)
    return jsonify(item_dict)


# Experiment extension


@app.route('/API/experiment-user-ids')
@login_required
def experiment_user_ids():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    generalization = request.args["generalization"]  # SG | WG or empty
    idList = users_data_access.get_subset_user_ids(s_id,scenario_name,generalization)
    return jsonify(idList)


@app.route("/API/experiment-add-user-with-id", methods=['POST'])
@login_required
def experiment_add_user_with_id():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    user_id = request.args["id"]
    generalization = request.args["generalization"]  # SG | WG or empty
    staticUserID = None
    if generalization:
        staticUserID = user_id
    users_data_access.construct_specific_user(experiment_id,s_id,model_name,scenario_name,user_id,staticUserID)
    return jsonify("User has been created")


@app.route('/API/experiment-statistics')
@login_required
def experiment_statistics():
    scenario_name = request.args["scenario-name"]
    s_id = request.args["s-id"]
    model_name = request.args["model-name"]
    experiment_id = request.args["experiment-id"]
    # Return data to plot the graphs
    # User/Interaction + inverse + derivative + scatter plot of k/histlength

    data_graphs = users_data_access.graph_data(s_id,scenario_name,model_name)
    # todo: get recall-atK values: possibly cache them for static e-users?
    returnList = []
    if data_graphs[-2]:
        returnList.append({'type': 'scatter', 'graph_label': 'Recall@K over History size', 'x_label': 'History size', "y_label": 'Recall@K', 'y_min': 0, 'y_max': data_graphs[-1],
                     'datapoints': data_graphs[-2]})
    returnList += [{'type': 'bar', 'graph_label': 'Interactions/User', 'x_label': 'UserID', "y_label": '#Interactions', 'y_min': 0, 'y_max': data_graphs[1]+10,
                     'datapoints': data_graphs[0]},
                    {'type': 'bar', 'graph_label': 'User/#Interaction', 'x_label': '#Interactions', "y_label": '#Users', 'y_min': 0, 'y_max': data_graphs[3]+10,
                     'datapoints': data_graphs[2]},
                    {'type': 'bar', 'graph_label': 'Interactions/Product', 'x_label': 'ProductID', "y_label": '#Interactions', 'y_min': 0, 'y_max': data_graphs[5]+10,
                     'datapoints': data_graphs[4]},
                    {'type': 'bar', 'graph_label': 'Product/#Interaction', 'x_label': '#Interactions', "y_label": '#Products', 'y_min': 0, 'y_max': data_graphs[7]+10,
                     'datapoints': data_graphs[6]},
                    ]

    return jsonify(returnList)

# -END: API that need the backend

# ERROR HANDLING


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html',
                           error_message="Internal Server Error"), 500


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_message="Page Not Found"), 404


@app.errorhandler(403)
def page_forbidden(e):
    return render_template('error.html', error_message="Forbidden"), 403


@app.errorhandler(410)
def page_forbidden(e):
    return render_template('error.html', error_message="Page Gone"), 410


# RUN DEV SERVER
if __name__ == "__main__":
    app.run(HOST, debug=DEBUG)
