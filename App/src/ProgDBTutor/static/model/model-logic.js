function renderModels(template) {
    let settings = {"url": `/API/models`, "method": "GET", "timeout": 0};
    $.ajax(settings).done(function (response) {
        document.getElementById("collectionViewBody").innerHTML = template(response);

        // Grab the search and use it to fill in the search field
        let searchParams = new URLSearchParams(window.location.search)
        if (searchParams.has('search') && searchParams.get('search')) {
            $("#searchModelInput").val(searchParams.get('search')).trigger("keyup");
        }
    });
}

function checkModelName() {
    // On input so that it updates while the user types
    $('#modelName').on('input', function () {
        // TODO Make this dynamically
        let takenNames = ["test1", "test2", "Hello"];
        // Checks if the name is already taken
        if (takenNames.includes($(this).val())) {
            $("#modelNameInvalidFeedback").text("Name is already taken");
            $("#modelName")[0].setCustomValidity("invalid");
        } else {
            // Remove the issue and reset the feedback
            $("#modelNameInvalidFeedback").text("Please enter a Valid Name");
            $("#modelName")[0].setCustomValidity("");
        }
    });
}

function handleFormInput() {
    $("#createModel").on("submit", function (event) {
        // Check if Form input is valid
        let form = document.getElementById("createModel");
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

            let model = {"date": Date(), "size": "0B"};

            // Check that user has access to dataset
            // TODO: Query the beginning, end, max and all values and use them to replace the other values
            // TODO: add the algorithm with parameters
            model["scenario_name"] = $("#scenarioSelector").val();
            model["model_name"] = $("#modelName").val();
            model["algorithm"] = $("#algorithmSelector").val();
            model["parameter1"] = $("#parameter1").val();
            model["parameter2"] = $("#parameter2").val();
            model["parameter3"] = $("#parameter3").val();
            model["parameter4"] = $("#parameter4").val();

            // TODO: Remove this, just for debugging
            // console.log(model);

            let settings = {
                "url": "/API/create-model", "method": "POST", "timeout": 0, "headers": {
                    "Content-Type": "application/json",
                }, "data": JSON.stringify({model}),
            };

            $.ajax(settings).done(function (response) {
                // Close the Modal
                $("#createModelModal").modal("hide");
            });
        }
    });
}

function clearFormOnHide() {
    $('#createModelModal').on('hide.bs.modal', function () {
        let form = $("#createModel");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
        // Collapse the collapsable sections
        // TODO: add the parameters dependant on the chosen algorithm
    });
}

function checkNewModelName() {
    // On input so that it updates while the user types
    $('#newModelNameInput').on('input', function () {
        // TODO Make this dynamically
        let takenNames = ["test1", "test2", "Hello"];
        // Checks if the name is already taken
        if (takenNames.includes($(this).val())) {
            $("#newModelNameInvalidFeedback").text("Name is already taken");
            $("#newModelNameInput")[0].setCustomValidity("invalid");
        } else {
            // Remove the issue and reset the feedback
            $("#newModelNameInvalidFeedback").text("Please enter a Valid Name");
            $("#newModelNameInput")[0].setCustomValidity("");
        }
    });
}

function handleChangeNameForm() {
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

            console.log($("#newModelNameInput").val());
            $("#changeModelNameModal").modal("hide");
            // TODO Connect this to the Database
            // TODO Reload the Scenarios on the Website to update the name
        }
    });
}

function clearChangeNameFormOnHide() {
    $('#changeModelNameModal').on('hide.bs.modal', function () {
        let form = $("#changeNameForm");
        // Clear the info from the form
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
    });
}

function handleDeleteModel() {
    $("#deleteModel").on("submit", function (event) {
        console.log("*whoosh* Scenario Delete");
        $("#deleteModelModal").modal("hide");
        // TODO Add the code to delete the Scenario from the Database and reload the all the Scenarios
    });
}

function checkCreateModelForm() {
    // Check that the inputs in the create Scenario Form
    checkModelName();
    //checkScenario();
}

/**
 * @summary: Takes care of converting the '+' to '-' and vice versa for collapsable
 * Selects all elements with class 'collapse-with-indicator' and specifies two functions on them.
 * Function 1 is triggered once the collapse is told to hide it then finds the icon and makes it a '+'
 * Function 2 is triggered once the collapse is told to show it then finds the icon and makes it a '-'
 * For Boostrap Documentation see: https://getbootstrap.com/docs/4.0/components/collapse/#events
 */
function handleCollapseIndicators() {
    let collapse = $('#collectionViewBody');
    collapse.on('hide.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("+");
    }).on('show.bs.collapse', ".collapse-with-indicator", function () {
        $("[data-target='#" + $(this).attr('id') + "']").find("#icon").text("-");
    });
}

$(document).ready(function () {

    // To activate the chosen components
    $('.form-control-chosen').chosen();

    // Render the Handlebars
    let templateHTML = document.getElementById("modelCollectionView").innerHTML;
    let template = Handlebars.compile(templateHTML);

    handleCollapseIndicators()

    renderModels(template);

    checkCreateModelForm();
    handleFormInput();
    clearFormOnHide();

    handleChangeNameForm();
    checkNewModelName();
    clearChangeNameFormOnHide();

    handleDeleteModel();

    let searchParams = new URLSearchParams(window.location.search)
    if (searchParams.has('create') && searchParams.get('create')) {
        $("#createModelModal").modal('toggle');
    }


    $("#createModelModal").on("shown.bs.modal", function () {
        let settings = {"url": "/API/scenarios-minified", "method": "GET", "timeout": 0,};

        let selector = $("#scenarioSelector");
        selector.empty()
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${key}">${response[key]}</option>`);
            }
            selector.trigger("chosen:updated");
            if (searchParams.has('create') && searchParams.get('create')) {
                selector.val(searchParams.get('create')).trigger("change");
            }

            selector.trigger("chosen:updated");
        });
    }).on("hide.bs.modal", function () {
        $("#algorithmSelector").val("").trigger("chosen:updated");
        renderModels(template)

        $(".parameter-one-section").addClass("d-none");
        $(".parameter-two-section").addClass("d-none");
        $(".parameter-three-section").addClass("d-none");
        $(".parameter-four-section").addClass("d-none");
    });

    $("#algorithmSelector").on("change", function () {
        console.log("Yes")
        $(".parameter-one-section").addClass("d-none");
        $(".parameter-two-section").addClass("d-none");
        $(".parameter-three-section").addClass("d-none");
        $(".parameter-four-section").addClass("d-none");

        if ($(this).val() === "Item nearest neighbours") {
            $(".parameter-one-section").removeClass("d-none");
            $(".parameter-two-section").removeClass("d-none");
            $(".parameter-one-label").text("Amount of neighbors (Int)");
            $(".parameter-two-label").text("Normalize (Bool)");

        } else if ($(this).val() === "EASE") {
            $(".parameter-one-section").removeClass("d-none");
            $(".parameter-one-label").text("Norm regularization (Float)");

        } else if ($(this).val() === "Weighted Matrix Factorization") {
            $(".parameter-one-section").removeClass("d-none");
            $(".parameter-two-section").removeClass("d-none");
            $(".parameter-three-section").removeClass("d-none");
            $(".parameter-four-section").removeClass("d-none");

            $(".parameter-one-label").text("Alpha confidence (Float)");
            $(".parameter-two-label").text("Dimension of factors (Int)");
            $(".parameter-three-label").text("L2 norm regularization (Float)");
            $(".parameter-four-label").text("Number of iterations (Int)");
        }
    });


    /** Handles the input field search */
    $("#searchModelInput").on("keyup", function () {
        // Collapse all the .collapse elements, needed for the filter
        $(".collapse").collapse("hide");
        let value = $(this).val().toLowerCase();
        console.log(value)
        $(".table .modelRow").filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $("#deleteModelModal").on("show.bs.modal", function (event) {
        $(this).data("sid", $(event.relatedTarget).data("sid"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        $(this).data("model-name", $(event.relatedTarget).data("model-name"));

        let sid = $(event.relatedTarget).data("sid");
        let scenario_name = $(event.relatedTarget).data("scenario-name");
        let model_name = $(event.relatedTarget).data("model-name");

        let settings = {
            "url": `/API/model-reference?sid=${sid}&sn=${scenario_name}&mn=${model_name}`,
            "method": "GET",
            "timeout": 0,
        };
        $.ajax(settings).done(function (response) {
            $("#modelReference").html(response)
        });
    });


    $("#deleteModel").on("click", function () {
        let modal = $("#deleteModelModal");

        let sid = modal.data("sid");
        let scenario_name = modal.data("scenario-name");
        let model_name = modal.data("model-name");

        let settings = {
            "url": `/API/model?sid=${sid}&sn=${scenario_name}&mn=${model_name}`,
            "method": "DELETE",
            "timeout": 0,
        };
        $.ajax(settings).done(function (response) {
            modal.modal('hide');
            renderModels(template)
        });
    });
});
