/** Grabs the datasets and renders them using handlebars */
function loadScenarios(template) {
    let settings = {"url": "/API/scenarios", "method": "GET", "timeout": 0,};
    $.ajax(settings).done(function (response) {
        document.getElementById("collectionViewBody").innerHTML = template(response);
        let searchParams = new URLSearchParams(window.location.search)
        if (searchParams.has('search') && searchParams.get('search')) {
            $("#searchFieldInput").val(searchParams.get('search')).trigger('keyup');
        }
    });
}


// - NAME
/**
 * @summary Checks while the user inputs a name into the Name filed if that name is valid
 * Checks if the name is in a list (should later check against the Database)
 * If the name is in the database displays feedback to the user
 * If the name is valid reset the feedback
 */
function checkScenarioName() {
    // On input so that it updates while the user types
    $('#scenarioName').on('input', function () {
        // Checks the Database if th name is valid
        let settings = {"url": "/API/check-scenario-name?name=" + $(this).val(), "method": "POST", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            if (response === "invalid") {
                $("#scenarioNameInvalidFeedback").text("Name is already taken");
                $("#scenarioName")[0].setCustomValidity("invalid");
            } else {
                // Remove the issue and reset the feedback
                $("#scenarioNameInvalidFeedback").text("Please enter a Valid Name");
                $("#scenarioName")[0].setCustomValidity("");
            }
        });
    });
}


// - CREATE SCENARIO FORM

/**
 * @summary Gathers all the information from the create Scenario Form and puts it into a JSON
 * When the Form is submitted this starts to gather the information from the fields and puts them into a JSON
 * for later use, after that it closes the Modal that contains the Form
 */
function handleFormInput(template) {
    $("#createScenario").on("submit", function (event) {
        // Check if Form input is valid
        let form = document.getElementById("createScenario");
        if (!form.checkValidity()) {
            // If not valid
            event.preventDefault();
            event.stopPropagation();

            // Tells Boostrap to display the validation information
            $(this).addClass('was-validated');
        } else {
            // If valid gather the information
            event.preventDefault(); // Not sure if this is needed

            // It may be better to preprocess the Date?
            // Gather the date
            let date = new Date();
            const day = date.toLocaleString('default', {day: '2-digit'});
            const month = date.toLocaleString('default', {month: '2-digit'});
            const year = date.toLocaleString('default', {year: 'numeric'});

            let scenario = {
                "date": `${day}/${month}/${year}`,
                "preProcessingSteps": [],
            };

            // Loop over all Rows
            // Order needs to be preserved
            // what, from ,where, min, max
            $("#preProcessingCollection").find(".ppRow").each(function () {
                let processingStep = {
                    "type": $(this).data('identifier'),
                    "from": $(this).find('.ppFrom').val(),
                    "to": $(this).find('.ppTo').val(),
                    "min": $(this).find('.ppMin').is(":checked"),
                    "max": $(this).find('.ppMax').is(":checked"),
                };
                scenario["preProcessingSteps"].push(processingStep)
            });

            // Cross validation
            scenario["generalizationType"] = $("#generalizationSelector").val();
            scenario["validationIn"] = $("#g-parameter-one").val();
            scenario["trainingUsers"] = $("#g-parameter-two").val();

            scenario["dataset"] = $("#datasetSelector").val();
            scenario["name"] = $("#scenarioName").val();
            scenario["disableRetargeting"] = $("#disableRetargeting").is(":checked");

            // Send the information the server to create a scenario
            let settings = {
                "url": "/API/create-scenario", "method": "POST", "timeout": 0,
                "headers": {"Content-Type": "application/json"},
                "data": JSON.stringify({scenario}),
            };

            $("#createButton").prop("disabled",true).html("Creating...").addClass("btn-secondary").removeClass("btn-success")

            $.ajax(settings).done(function (response) {
                // Close the Modal
                $("#createScenarioModal").modal("hide");
                loadScenarios(template)
            });
        }
    });
}

/**
 * @summary Takes care that the Form is in default position if opened
 * Once the Modal that contains the create scenario Form is told to hide all the input fields are cleared and all
 * collapsable items are collapsed
 */
function clearFormOnHide() {
    $('#createScenarioModal').on('hide.bs.modal', function () {
        let form = $("#createScenario");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
        // Collapse the collapsable sections
        $("#preProcessingCollection").empty();
        $("#datasetSelector").val("").trigger("change").trigger("chosen:updated");

        // Cross validation
        $("#generalizationSelector").prop('selectedIndex', -1).trigger("change").trigger("chosen:updated");
        $("#g-parameter-one-section").addClass("d-none");
        $("#g-parameter-two-section").addClass("d-none");
    });
}

/**
 * Dummy That shows how to pre fill every input field in the Create Scenario Form
 * See: https://getbootstrap.com/docs/4.0/components/modal/
 */
function prefillForm() {
    $('#createScenarioModal').on('show.bs.modal', function (event) {
        $("#createButton").prop("disabled",false).html("Create").addClass("btn-success").removeClass("btn-secondary");
        // Grab the available datasets from the server
        let settings = {"url": "/API/datasets-minified", "method": "GET", "timeout": 0,};
        let selector = $("#datasetSelector");

        selector.empty()
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${key}">${response[key]}</option>`);
                //console.log(key);
            }

            // Check the URL and select the dataset specified in it
            let searchParams = new URLSearchParams(window.location.search)
            if (searchParams.has('create') && searchParams.get('create')) {
                selector.val(parseInt(searchParams.get('create'))).trigger("change");
            }
            // Tell chosen to update
            selector.trigger("chosen:updated");

            // Check the data-fields type to see what pre filling needs to be done
            let type = $(event.relatedTarget).data('fields');

            if (type === "filed") {
                // Grabs the ID
                let id = $(event.relatedTarget).data("scenario-id");
                let name = $(event.relatedTarget).data("scenario-name");
                // Grabs the info from the server
                let settings = {"url": `/API/scenario?id=${id}&name=${name}`, "method": "GET", "timeout": 0,};

                $.ajax(settings).done(function (response) {

                    for(let step in response['preProcessingSteps']){
                        let cur = response['preProcessingSteps'][step];

                        let id = cur['type'];
                        let idToVal = { "filterTime": "Timestamp", "filterUser": "Interactions per User", "filterItem": "Interaction per Item",}
                        let idToType = { "filterTime": "text", "filterUser": "number", "filterItem": "number",}
                        let idToClass = { "filterTime": "inputTimestamp", "filterUser": "inputInt", "filterItem": "inputInt",}
                        let idToIdentifier = { "filterTime": "filterTime", "filterUser": "filterUser", "filterItem": "filterItem",}

                        $("#preProcessingCollection").append(
                            `
                            <tr class="ppRow" data-identifier="${idToIdentifier[id]}">
                                <td class="align-middle"><input class="ppMin ppCheckbox" type="checkbox"></td>
                                <td class="align-middle"><input class="form-control ppInput ppFrom ${idToClass[id]}" type="${idToType[id]}"></td>
                                <td class="align-middle text-secondary"> &le; ${idToVal[id]} &le; </td>
                                <td class="align-middle"><input class="form-control ppInput ppTo ${idToClass[id]}" type="${idToType[id]}"></td>
                                <td class="align-middle"><input class="ppMax ppCheckbox" type="checkbox"></td>
                            </tr>
                            `
                        )
                        // Fill the values
                        let row =  $("#preProcessingCollection .ppRow:last");
                        row.find('.ppMin').prop("checked", cur["min"]);
                        row.find('.ppMax').prop("checked", cur["max"]);
                        row.find('.ppFrom').val(cur['from']);
                        row.find('.ppTo').val(cur['to']);

                    }
                    $(".inputTimestamp").inputmask('9999/99/99 99:99:99', {
                        'placeholder': 'yyyy/mm/dd hh:mm:ss',
                        clearMaskOnLostFocus: false
                    });

                    // Cross validation
                    $("#generalizationSelector").val(response["generalizationType"]).trigger("change").trigger("chosen:updated");

                    if (response["validationIn"] !== "") {
                        $("#g-parameter-one").val(response["validationIn"]);
                        $(".g-parameter-one-section").removeClass("d-none");
                    }
                    if (response["trainingUsers"] !== "") {
                        $("#g-parameter-two").val(response["trainingUsers"]);
                        $(".g-parameter-two-section").removeClass("d-none");
                    }

                    $("#datasetSelector").val(response["datasetSelector"]).trigger("change").trigger("chosen:updated");
                    $("#disableRetargeting").prop("checked", response["disableRetargeting"]);
                });
            }
        });
    });
}

// - CHANGE NAME FORM
/**
 * @summary Checks while the user inputs a new name into the Name filed if that name is valid
 * Checks if the name is in a list (should later check against the Database)
 * If the name is in the database displays feedback to the user
 * If the name is valid reset the feedback
 */
function checkNewScenarioName() {
    // On input so that it updates while the user types
    $('#newScenarioNameInput').on('input', function () {
        let settings = {"url": "/API/check-scenario-name?name=" + $(this).val(), "method": "POST", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            if (response === "invalid") {
                $("#newScenarioNameInvalidFeedback").text("Name is already taken");
                $("#newScenarioNameInput")[0].setCustomValidity("invalid");
            } else {
                // Remove the issue and reset the feedback
                $("#newScenarioNameInvalidFeedback").text("Please enter a Valid Name");
                $("#newScenarioNameInput")[0].setCustomValidity("");
            }
        });
    });
}

/** Gathers all the information from the change Scenario Name Form and print */
function handleChangeNameForm(template) {
    $("#changeNameForm").on("submit", function (event) {
        // Check if Form input is valid
        let form = document.getElementById("changeNameForm");
        if (!form.checkValidity()) {
            // If not valid
            event.preventDefault();
            event.stopPropagation();

            // Tells Boostrap to display the validation information
            $(this).addClass('was-validated');
        } else {
            // If valid gather the information
            event.preventDefault(); // Not sure if this is needed

            let name = $("#newScenarioNameInput").val();
            let id = $("#changeScenarioNameModal").data("scenario-id");
            let oldName = $("#currentName").text();
            let settings = {
                "url": `/API/change-scenario-name?id=${id}&newName=${name}&oldName=${oldName}`,
                "method": "PUT",
                "timeout": 0,
            };

            $.ajax(settings).done(function (response) {
                $("#changeScenarioNameModal").modal("hide");
                loadScenarios(template)
            });
        }
    });
}

/**
 * @summary Takes care that the Form is in default position if opened
 * Once the Modal that contains the change Scenario Name Form is told to hide all the input fields are cleared and all
 * collapsable items are collapsed
 */
function clearChangeNameFormOnHide() {
    $('#changeScenarioNameModal').on('hide.bs.modal', function () {
        let form = $("#changeNameForm");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
    });
}

// - DELETE SCENARIO FORM
function handleDeleteScenario(template) {
    $("#confirmDeleteScenario").on("click", function () {
        let id = $("#deleteScenarioModal").data("scenario-id");
        let name = $("#deleteScenarioModal").data("scenario-name");
        let settings = {"url": `/API/scenario?id=${id}&name=${name}`, "method": "DELETE", "timeout": 0,};

        $.ajax(settings).done(function (response) {
            $("#deleteScenarioModal").modal("hide");
            loadScenarios(template)
        });
    });
}

// Rework
function checkPreProcessingSteps() {
    // On input so that it updates while the user changes it
    $('#preProcessingCollection').on('input', '.ppInput', function () {
        // Find matching checkbox
        let checkBox;
        if($(this).hasClass('ppFrom')){
            checkBox = $(this).parent().parent().find('.ppMin');
        }else{
            checkBox = $(this).parent().parent().find('.ppMax');
        }
        // Clear the checkbox once input it typed
        checkBox.prop("checked", false);

        // Check that there is a value and that the value is positive`
        if ($(this).val() && ($(this).hasClass("inputTimestamp") || $(this).val() >= 0)) {
            $(this)[0].setCustomValidity("");
            checkBox[0].setCustomValidity("");
        } else {
            $(this)[0].setCustomValidity("invalid");
            checkBox[0].setCustomValidity("invalid");
        }
    });

    $('#preProcessingCollection').on('input', '.ppCheckbox', function () {
        // Find matching input
        let input;
        if($(this).hasClass('ppMin')){
            input = $(this).parent().parent().find('.ppFrom');
        }else{
            input = $(this).parent().parent().find('.ppTo');
        }
        // Clear the checkbox once input it typed
        input.val("")

        // Check that there is a value and that the value is positive`
        if ($(this).is(":checked")) {
            $(this)[0].setCustomValidity("");
            input[0].setCustomValidity("");
        } else {
            $(this)[0].setCustomValidity("invalid");
            input[0].setCustomValidity("invalid");
        }
    });
}


// - MAIN
$(document).ready(function () {
    // To activate the chosen components
    $('.form-control-chosen').chosen();
    $('.form-control-chosen-optional').chosen({
        allow_single_deselect: true
    });

    let templateHTML = document.getElementById("scenarioCollectionView").innerHTML;
    let template = Handlebars.compile(templateHTML);
    let sampleTemplateHTML = document.getElementById("sampleCollectionView").innerHTML;
    let sampleTemplate = Handlebars.compile(sampleTemplateHTML);

    loadScenarios(template)

    checkScenarioName();

    handleFormInput(template);
    clearFormOnHide();
    prefillForm();

    handleChangeNameForm(template);
    checkNewScenarioName();
    clearChangeNameFormOnHide();

    handleDeleteScenario(template);

    /** Handles the input field search */
    $("#searchFieldInput").on("keyup", function () {
        // Collapse all the .collapse elements, needed for the filter
        $(".collapse").collapse("hide");
        let value = $(this).val().toLowerCase();
        $("#table .scenarioRow").filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    // Takes care of converting the + to minus and vice versa
    $("#collectionViewBody").on('hide.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("+");
    }).on('show.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("-");
    });

    /** Grabs the ID of the dataset that is opening the Modal and passes it to hte modal */
    $("#changeScenarioNameModal").on("show.bs.modal", function (event) {
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $("#currentName").text($(event.relatedTarget).data("name"));
    });

    // Cross validation
    $("#generalizationSelector").on("change", function () {
        $(".g-parameter-one-section").addClass("d-none");
        $(".g-parameter-two-section").addClass("d-none");
        $("#g-parameter-one").val("");
        $("#g-parameter-two").val("");

        if ($(this).val() === "SG") {
            $(".g-parameter-one-section").removeClass("d-none");
            $(".g-parameter-two-section").removeClass("d-none");
        } else if ($(this).val() === "WG") {
            $(".g-parameter-one-section").removeClass("d-none");
        }
    });

    $("#showScenarioInteraction").on("show.bs.modal", function (event) {
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        let id = $(event.relatedTarget).data("scenario-id");
        let name = $(event.relatedTarget).data("scenario-name");
        let settings = {"url": `/API/get-interaction-sample?id=${id}&name=${name}`, "method": "GET", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            $("#interactionSampleBody").html(sampleTemplate(response));
        });
    });
    $("#showMetaDataSample").on("show.bs.modal", function (event) {
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        $(this).data("meta-file-name", $(event.relatedTarget).data("meta-file-name"));
        let id = $(event.relatedTarget).data("scenario-id");
        let fileName = $(event.relatedTarget).data("meta-file-name");
        let name = $(event.relatedTarget).data("scenario-name");
        let settings = {
            "url": `/API/metafile-sample?id=${id}&name=${name}&filename=${fileName}`,
            "method": "GET",
            "timeout": 0,
        };
        $.ajax(settings).done(function (response) {
            $("#metaSampleBody").html(sampleTemplate(response));
        });
    });

    $("#deleteScenarioModal").on("show.bs.modal", function (event) {
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        // Update the display count
        let id = $(event.relatedTarget).data("scenario-id");
        let name = $(event.relatedTarget).data("scenario-name");
        let settings = {"url": `/API/scenario-reference?id=${id}&name=${name}`, "method": "GET", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            $("#referenceValue").text(response);
        });
    });

    // Grab the search and use it to fill in the search field
    let searchParams = new URLSearchParams(window.location.search)
    if (searchParams.has('create') && searchParams.get('create')) {
        $("#createScenarioModal").modal('show');
    }

    // When any of them clicked then add a row
    // Once they are clicked check the id to make the correct tweaks
    $(".addpp").on("click", function () {
        let id = $(this).attr('id');
        let idToVal = { "addppTime": "Timestamp", "addppUser": "Interactions per User", "addppItem": "Interaction per Item",}
        let idToType = { "addppTime": "text", "addppUser": "number", "addppItem": "number",}
        let idToClass = { "addppTime": "inputTimestamp", "addppUser": "inputInt", "addppItem": "inputInt",}
        let idToIdentifier = { "addppTime": "filterTime", "addppUser": "filterUser", "addppItem": "filterItem",}

        $("#preProcessingCollection").append(
            `
            <tr class="ppRow" data-identifier="${idToIdentifier[id]}">
                <td class="align-middle"><input class="ppMin ppCheckbox" type="checkbox"></td>
                <td class="align-middle"><input class="form-control ppInput ppFrom ${idToClass[id]}" type="${idToType[id]}"></td>
                <td class="align-middle text-secondary"> &le; ${idToVal[id]} &le; </td>
                <td class="align-middle"><input class="form-control ppInput ppTo ${idToClass[id]}" type="${idToType[id]}"></td>
                <td class="align-middle"><input class="ppMax ppCheckbox" type="checkbox"></td>
            </tr>
            `
        ).find(".ppInput").each(function(){
            // Find matching checkbox
            let checkBox;
            if($(this).hasClass('ppFrom')){
                checkBox = $(this).parent().parent().find('.ppMin');
            }else{
                checkBox = $(this).parent().parent().find('.ppMax');
            }

            // If the value has no yet been provided then still flag it as false
            if (!$(this).val() && !checkBox.is(":checked")) {
                $(this)[0].setCustomValidity("invalid");
                checkBox[0].setCustomValidity("invalid");
            }
        });

        $(".inputTimestamp").inputmask('9999/99/99 99:99:99', {
            'placeholder': 'yyyy/mm/dd hh:mm:ss',
            clearMaskOnLostFocus: false
        });

    });

    checkPreProcessingSteps();


});
