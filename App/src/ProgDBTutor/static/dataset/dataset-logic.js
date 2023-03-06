/** Grabs the datasets and renders them using handlebars */
function load_datasets(template) {
    let settings = {"url": "/API/datasets", "method": "GET", "timeout": 0};
    $.ajax(settings).done(function (response) {
        document.getElementById("collectionViewBody").innerHTML = template(response);
    });
}

/** Check that all the Metadata selects are not on default */
function checkMetaSelect() {
    $(".metaSelect").each(function () {
        if (!$(this).val()) {
            $(this)[0].setCustomValidity("invalid");
        } else {
            $(this)[0].setCustomValidity("");
        }
    });
}

/** Make the interface for the Metafile to allow the user to specify all the necessary information */
function processMetadata(event, fileName, id) {
    // Get the first row of the CSV file
    let firstRow = event.target.result.split(/[\r\n]+/)[0].split(',');

    // Add the interface to select the type for each row in the CSV
    let html = `<div class="singleMetaFile" id="${id}">
                    <div class="row justify-content-between form-inline mb-3">
                        <h6 class="mt-2"><span class="text-secondary mr-2">File:</span>${fileName}</h6>
                        <button class="col-md-auto col-sm-12 btn btn-sm btn-danger testRemove" type="button">Remove
                        </button>
                    </div>`;

    firstRow.forEach(column => {
        html += `<div class="input-group mb-3">
                        <div class="input-group-prepend">
                            <span class="input-group-text">${column}</span>
                        </div>
                        <select class="custom-select metaSelect metaTypeSelect" data-column="${column}">
                            <option selected disabled hidden>Select Type...</option>
                            <option value="String">String</option>
                            <option value="Numerical">Numerical</option>
                            <option value="URL">URL</option>
                        </select>
                        <div class="invalid-feedback">Please select a type</div>
                        <div class="valid-feedback">Looks good!</div></td>
                    </div>`;
    });

    // Add the primary identifier selector
    html += `<div class="input-group">
                    <div class="input-group-prepend">
                        <label class="input-group-text" for="itemIdSelect">Primary Identifier:</label>
                    </div>
                    <select class="custom-select metaSelect metaPrimarySelect mb-auto" id="itemIdSelect" required>
                        <option selected disabled hidden>Select column...</option>`;

    // Add the drop down options
    firstRow.forEach(function (value, i) {
        html += `<option value="${i}">${value}</option>`;
    });

    html += `</select>
                    <div class="invalid-feedback">Please select a column</div>
                    <div class="valid-feedback">Looks good!</div>
                </div>
                <hr><div>`;

    // Add the html to the website
    $("#metadataFilesSection").append(html);


    // Add the columns to meta meaning select
    let optgroup = `<optgroup label="${fileName}" id="metaOpt${id}">`
    for (let i = 0; i < firstRow.length; i++) {
        optgroup += `<option value="${id}m${i}">${firstRow[i]}</option>`;
    }
    optgroup += `</optgroup>`

    // Remove any previous opt group
    $("#textRepresentationSelector").find(`#metaOpt${id}`).remove();
    $("#imgRepresentationSelector").find(`#metaOpt${id}`).remove();
    // Add th opt group for the interactions
    $("#textRepresentationSelector").append(optgroup)
    $("#imgRepresentationSelector").append(optgroup)
    // Add the values to the opt group
    $("#textRepresentationSelector").trigger("chosen:updated");
    $("#imgRepresentationSelector").trigger("chosen:updated");

    console.log(optgroup)

    // Check the dropdowns
    checkMetaSelect();
}

/** Process the main CSV file */
function process(event, fileName) {
    // Get the first row
    let firstRow = event.target.result.split(/[\r\n]+/)[0].split(',');
    // Change the options for the select to match the columns
    $(".option1").each(function () {
        $(this).html(firstRow[0]);
    })
    $(".option2").each(function () {
        $(this).html(firstRow[1]);
    })
    // Make the selects visible
    $("#itemIdSection").show();
    $("#userIdSection").show();

    if (firstRow.length > 2) {
        // Make the 3rd option visible and able to select
        $(".option3").each(function () {
            $(this).html(firstRow[2]).show().prop('disabled', false);
            $(this).html(firstRow[2]).show().prop('hidden', false);
        });
        // Make the timestamp section visible
        $("#timestampSection").show();
    } else {
        // Hide and disable the 3rd option
        $(".option3").each(function () {
            $(this).hide(firstRow[2]).prop('disabled', true);
            $(this).html(firstRow[2]).show().prop('hidden', true);
        });
        $("#timestampSection").hide();
    }
    // Reset all of the selections
    [$("#timestampSelect"), $("#itemIdSelect"), $("#userIdSelect")].forEach(s => {
        s.prop('selectedIndex', 0).trigger("change");
    });

    let optgroup = `<optgroup label="${fileName}" id="interactionOpt">`
    for (let i = 0; i < firstRow.length; i++) {
        optgroup += `<option value="i${i}">${firstRow[i]}</option>`;
    }
    optgroup += `</optgroup>`

    // Remove any previous opt group
    $("#textRepresentationSelector").find("#interactionOpt").remove();
    $("#imgRepresentationSelector").find("#interactionOpt").remove();
    // Add th opt group for the interactions
    $("#textRepresentationSelector").append(optgroup)
    $("#imgRepresentationSelector").append(optgroup)
    // Add the values to the opt group
    $("#textRepresentationSelector").trigger("chosen:updated");
    $("#imgRepresentationSelector").prop('selectedIndex', 0).trigger("change").trigger("chosen:updated");
}

/** Checks that the column meanings selections are valid */
function checkColumnMeaningDropdowns() {
    let selectors = [$("#userIdSelect"), $("#itemIdSelect")];
    // If timestamp is visible then also check it
    if ($("#timestampSection").is(":visible")) {
        selectors.push($("#timestampSelect"));
    }
    // Check all the selectors
    selectors.forEach(s => {
        if (!s.val()) {
            // String interpolation to get the correct invalid feedback
            $(`#${s.attr("id")}InvalidFeedback`).text("Please select a column");
            s[0].setCustomValidity("invalid");
        } else if (selectors.some(i => (i !== s) && (i.val() === s.val()))) {
            $(`#${s.attr("id")}InvalidFeedback`).text("Can't select the same column multiple times");
            s[0].setCustomValidity("invalid");
        } else {
            s[0].setCustomValidity("");
        }
    });
}

// - CHANGE NAME FORM
/**
 * @summary Checks while the user inputs a new name into the Name filed if that name is valid
 * Checks if the name is in a list (should later check against the Database)
 * If the name is in the database displays feedback to the user
 * If the name is valid reset the feedback
 */
function checkNewDatasetName() {
    // On input so that it updates while the user types
    $('#newDatasetNameInput').on('input', function () {

        let settings = {
            "url": "/API/check-dataset-name?name=" + $(this).val(),
            "method": "POST",
            "timeout": 0,
        };

        $.ajax(settings).done(function (response) {
            if (response === "invalid") {
                $("#newDatasetNameInvalidFeedback").text("Name is already taken");
                $("#newDatasetNameInput")[0].setCustomValidity("invalid");
            } else {
                // Remove the issue and reset the feedback
                $("#newDatasetNameInvalidFeedback").text("Please enter a Valid Name");
                $("#newDatasetNameInput")[0].setCustomValidity("");
            }
        });
    });
}

function checkDatasetName() {
    // On input so that it updates while the user types
    $('#datasetName').on('input', function () {

        let settings = {
            "url": "/API/check-dataset-name?name=" + $(this).val(),
            "method": "POST",
            "timeout": 0,
        };

        $.ajax(settings).done(function (response) {
            if (response === "invalid") {
                $("#datasetNameInvalidFeedback").text("Name is already taken");
                $("#datasetName")[0].setCustomValidity("invalid");
            } else {
                // Remove the issue and reset the feedback
                $("#datasetNameInvalidFeedback").text("Please enter a Valid Name");
                $("#datasetName")[0].setCustomValidity("");
            }
        });
    });
}

/** Gathers all the information from the change Dataset Name Form and print */
function handleChangeDatasetNameForm(template) {
    $("#changeNameForm").on("submit", function (event) {
        let modal = $("#changeDatasetNameModal");
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

            // Post the new name to the server
            let newName = $("#newDatasetNameInput").val()
            let datasetId = modal.data("dataset-id");
            let settings = {
                "url": `/API/change-dataset-name?name=${newName}&id=${datasetId}`,
                "method": "PUT",
                "timeout": 0,
            };

            $.ajax(settings).done(function () {
                modal.modal("hide");
                load_datasets(template)
            });
        }
    });
}

/**
 * @summary Takes care that the Form is in default position if opened
 * Once the Modal that contains the change Dataset Name Form is told to hide all the input fields are cleared and all
 * collapsable items are collapsed
 */
function clearChangeNameFormOnHide() {
    $('#changeDatasetNameModal').on('hide.bs.modal', function () {
        let form = $("#changeNameForm");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
    });
}

// - DELETE SCENARIO FORM

// - MAIN

$(document).ready(function () {
    // To keep track of the files that need to be uploaded
    let formData = new FormData();
    let id = 0;
    let metaDataFiles = {};
    let templateHTML = document.getElementById("datasetCollectionView").innerHTML;
    let template = Handlebars.compile(templateHTML);
    let sampleTemplateHTML = document.getElementById("sampleCollectionView").innerHTML;
    let sampleTemplate = Handlebars.compile(sampleTemplateHTML);

    // Needs to happen in the beginning
    load_datasets(template);

    // Code for the modals
    clearChangeNameFormOnHide();
    handleChangeDatasetNameForm(template);
    checkNewDatasetName();

    // To activate the chosen components
    $('.form-control-chosen').chosen();
    $('.form-control-chosen-optional').chosen({
        allow_single_deselect: true
    });

    // Takes care of converting the + to minus and vice versa
    $("#collectionViewBody").on('hide.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("+");
    }).on('show.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("-");
    });

    /** Process the Metafile that is uploaded */
    $("#metadataFile").on("change", function () {
        const reader = new FileReader()
        id++;
        reader.onload = event => processMetadata(event, $(this)[0].files[0].name, id);
        reader.onerror = error => reject(error);
        reader.readAsText($(this)[0].files[0]);
        metaDataFiles[id] = $(this)[0].files[0];
    });

    /** Checks the Metadata selects after the user interacted with one of them */
    $("#metadataFilesSection").on("change", ".metaSelect", checkMetaSelect);

    /** Handles the removing of a Metafile section upon remove button click */
    $("#metadataFilesSection").on("click", "button.testRemove", function () {
        let id = $(this).parent().parent().attr("id")
        delete metaDataFiles[id];
        $(this).parent().parent().remove();

        $("#textRepresentationSelector").find(`#metaOpt${id}`).remove();
        $("#imgRepresentationSelector").find(`#metaOpt${id}`).remove();

        $("#textRepresentationSelector").trigger("chosen:updated");
        $("#imgRepresentationSelector").trigger("chosen:updated");
    });

    /** Process the main CSV file that is uploaded */
    $("#interactionFile").on("change", function () {
        const reader = new FileReader()
        reader.onload = event => process(event, $(this)[0].files[0].name);
        reader.onerror = error => reject(error);
        reader.readAsText($(this)[0].files[0]);
        // Change the content of the label to the file name
        $("#interactionFileLabel").text($(this)[0].files[0].name);

        // Overwrites any old file that is still there
        formData.set("interactionFile", $(this)[0].files[0]);
    });

    $(".column-meaning-select").on("change", checkColumnMeaningDropdowns); // Note callback function so no ()

    /** Used to get the immediate text from a div */
    $.fn.immediateText = function () {
        return this.contents().not(this.children()).text();
    };

    /** Handles the create dataset form */
    $("#createDataset").on("submit", function (event) {
        // Check if Form input is valid
        let form = document.getElementById("createDataset");

        // Check them is needed if they haven't been touched yet
        checkColumnMeaningDropdowns();
        checkMetaSelect();
        checkDatasetName();
        if (!form.checkValidity()) {
            // If not valid
            event.preventDefault();
            event.stopPropagation();

            // Tells Boostrap to display the validation information
            $(this).addClass('was-validated');
        } else {
            // If valid gather the information
            event.preventDefault(); // Not sure if this is needed
            //console.log("Valid");

            // Add all the Meta Datafiles
            for (let fileID in metaDataFiles) {
                formData.append(fileID, metaDataFiles[fileID]);
            }

            // Collect the interaction file info
            formData.set("datasetName", $("#datasetName").val());
            formData.set("columnItemId", $("#itemIdSelect").val());
            formData.set("columnUserId", $("#userIdSelect").val());

            if ($("#timestampSection").is(":visible")) {
                formData.set("columnTimestamp", $("#timestampSelect").val());
            } else {
                formData.set("columnTimestamp", "none");
            }

            let metaFilesArray = [];
            // Collect all the info from the metaFileSection
            $("#metadataFilesSection").find(".singleMetaFile").each(function () {
                let metaFile = {};
                metaFile["fileName"] = $(this).find("h6").immediateText();
                metaFile["columns"] = [];
                $(this).find(".metaTypeSelect").each(function () {
                    metaFile["columns"].push({"meaning": $(this).data("column"), "type": $(this).val()});
                })
                metaFile["columnPrimaryIdentifier"] = $(this).find(".metaPrimarySelect").val();
                metaFilesArray.push(metaFile);
            });
            formData.set("metaFilesMeaning", JSON.stringify(metaFilesArray));

            // Collect the share info
            formData.set("sharedWith", $("#shareSelector").val());

            // Gather the date
            let date = new Date();
            const day = date.toLocaleString('default', {day: '2-digit'});
            const month = date.toLocaleString('default', {month: '2-digit'});
            const year = date.toLocaleString('default', {year: 'numeric'});

            formData.set("date", `${day}/${month}/${year}`);

            formData.set("textRepresentation", $("#textRepresentationSelector").val());
            formData.set("imgRepresentation", $("#imgRepresentationSelector").val());
            // Display the key/value pairs for debugging
            //for (let pair of formData.entries()) {console.log(pair);}

            let settings = {
                "url": "/API/create-dataset",
                "method": "POST",
                "timeout": 0,
                "processData": false,
                "mimeType": "multipart/form-data",
                "contentType": false,
                "data": formData
            };

            $("#createButton").prop("disabled",true).html("Creating...").addClass("btn-secondary").removeClass("btn-success")


            $.ajax(settings).done(function (response) {
                // Close the Modal
                $("#createDatasetModal").modal("hide");

                // Reload the Datasets
                load_datasets(template);

            });
        }
    });

    $('#createDatasetModal').on('hide.bs.modal', function () {
        let form = $("#createDataset");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");

        // Clear Metafile section
        $("#metadataFilesSection").empty();

        // Hide the Dataset selects
        $("#itemIdSection").hide();
        $("#userIdSection").hide();
        $("#timestampSection").hide();
        // Reset the name
        $("#interactionFileLabel").text("Choose interactions file");

        // Reset the share, first clear the values and then tell chosen to update
        $("#shareSelector").prop('selectedIndex', -1).trigger("chosen:updated");

        // Reset the variables
        formData = new FormData();
        id = 0;
        metaDataFiles = {};
    });

    /** Adds the users to the select that the Dataset is already shared with  */
    $("#manageDatasetSharing").on("show.bs.modal", function (event) {
        // Grab the id and pass it forward
        $(this).data("dataset-id", $(event.relatedTarget).data("dataset-id"));

        let select = $("#manageShareSelector");

        let settings = {"url": "/API/users", "method": "GET", "timeout": 0};
        $.ajax(settings).done(function (response) {
            console.log(response);
            // Clear the field before the new ones are added
            $("#manageShareSelector").empty();
            // Add an option for each of the users
            for (const key in response) {
                $("#manageShareSelector").append(`<option value="${key}">${response[key]}</option>`);
            }
            // Clear the select before updating it
            select.prop('selectedIndex', -1)

            // Update the select
            let id = $(event.relatedTarget).data("dataset-id")
            console.log(id)
            let settings = {"url": `/API/shared-users?id=${id}`, "method": "GET", "timeout": 0,};
            $.ajax(settings).done(function (response) {
                select.val(response);
                // Tell chosen to update
                select.trigger("chosen:updated");
            });
        });
    });

    /** Gathers the the info from the select upon submit */
    $("#manageDatasetSharingForm").on("submit", function (event) {
        let modal = $("#manageDatasetSharing")
        event.preventDefault();

        let val = $("#manageShareSelector").val().join()
        let id = modal.data("dataset-id");
        // Send the ids of the users to share with to the server
        let settings = {
            "url": `/API/update-dataset-sharing?id=${id}&users=${val}`,
            "method": "PUT",
            "timeout": 0,
        };

        $.ajax(settings).done(function () {
            modal.modal("hide");

            // FIXME: Check if reload here is needed
            load_datasets(template);
        });
    });

    /** Handles the input field search */
    $("#searchFieldInput").on("keyup", function () {
        // Collapse all the .collapse elements, needed for the filter
        $(".collapse").collapse("hide");
        let value = $(this).val().toLowerCase();
        $("#table .datasetRow").filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    /** Grabs the ID of the dataset that is opening the Modal and passes it to hte modal */
    $("#createDatasetModal").on("show.bs.modal", function (event) {
        $("#createButton").prop("disabled",false).html("Create").addClass("btn-success").removeClass("btn-secondary");
        let settings = {"url": "/API/users", "method": "GET", "timeout": 0};
        $.ajax(settings).done(function (response) {
            // Clear the field before the new ones are added
            $("#shareSelector").empty();
            // Add an option for each of the users
            for (const key in response) {
                $("#shareSelector").append(`<option value="${key}">${response[key]}</option>`);
            }
            $("#shareSelector").trigger("chosen:updated");

            // Clear the meaning select
            $("#textRepresentationSelector").empty().trigger("chosen:updated");
            $("#imgRepresentationSelector").empty().trigger("chosen:updated");

        });
    });
    $("#changeDatasetNameModal").on("show.bs.modal", function (event) {
        $(this).data("dataset-id", $(event.relatedTarget).data("dataset-id"));
        $("#currentName").text($(event.relatedTarget).data("name"));
    });
    $("#deleteDatasetModal").on("show.bs.modal", function (event) {
        $(this).data("dataset-id", $(event.relatedTarget).data("dataset-id"))
        // Update the display count
        let id = $(event.relatedTarget).data("dataset-id");
        let settings = {"url": `/API/dataset-reference?id=${id}`, "method": "GET", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            $("#referenceValue").text(response);
        });
    });
    $("#showDatasetInteraction").on("show.bs.modal", function (event) {
        $(this).data("dataset-id", $(event.relatedTarget).data("dataset-id"));
        let id = $(event.relatedTarget).data("dataset-id");
        let settings = {"url": `/API/interaction-sample?id=${id}`, "method": "GET", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            let data = sampleTemplate(response);
            $("#interactionSampleBody").html(data);
        });
    });
    $("#showMetaDataSample").on("show.bs.modal", function (event) {
        $(this).data("dataset-id", $(event.relatedTarget).data("dataset-id"));
        $(this).data("meta-file-name", $(event.relatedTarget).data("meta-file-name"));
        let id = $(event.relatedTarget).data("dataset-id");
        let name = $(event.relatedTarget).data("meta-file-name");
        console.log(id, name)
        let settings = {"url": `/API/metafile-sample?id=${id}&filename=${name}`, "method": "GET", "timeout": 0,};
        $.ajax(settings).done(function (response) {
            let data = sampleTemplate(response);
            $("#metaSampleBody").html(data);
        });
    });
    $("#confirmDeleteDataset").on("click", function () {
        let id = $("#deleteDatasetModal").data("dataset-id");
        let settings = {"url": `/API/dataset?id=${id}`, "method": "DELETE", "timeout": 0,};
        $.ajax(settings).done(function () {
            $("#deleteDatasetModal").modal("hide");
            // Reload the Datasets
            load_datasets(template);
        });
    });

    // Grab the search and use it to fill in the search field
    let searchParams = new URLSearchParams(window.location.search)
    if (searchParams.has('search') && searchParams.get('search')) {
        $("#searchFieldInput").val(searchParams.get('search'));
    }
});
