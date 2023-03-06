/** Loads the Experiments and displays them dynamically */
function loadExperiments(template) {
    let settings = {"url": "/API/experiments", "method": "GET", "timeout": 0};
    $.ajax(settings).done(function (response) {
        document.getElementById("collectionViewBody").innerHTML = template(response);
    });
}

// - MAIN
$(document).ready(function () {
    // To activate the chosen components
    $('.form-control-chosen').chosen();

    let templateHTML = document.getElementById("experimentCollectionView").innerHTML;
    let template = Handlebars.compile(templateHTML);

    loadExperiments(template)

    /** Handles the input field search */
    $("#searchFieldInput").on("keyup", function () {
        // Collapse all the .collapse elements, needed for the filter
        $(".collapse").collapse("hide");
        let value = $(this).val().toLowerCase();
        $("#table .experimentRow").filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $('#experimentName').on('input', function () {
        let settings = {
            "url": "/API/check-experiment-name?name=" + $(this).val(), "method": "POST", "timeout": 0,
        };

        $.ajax(settings).done(function (response) {
            if (response === "invalid") {
                $("#experimentNameInvalidFeedback").text("Name is already taken");
                $("#experimentName")[0].setCustomValidity("invalid");
            } else {
                // Remove the issue and reset the feedback
                $("#experimentNameInvalidFeedback").text("Please enter a Valid Name");
                $("#experimentName")[0].setCustomValidity("");
            }
        });
    });

    // Handles the create dataset form
    $("#createExperiment").on("submit", function (event) {
        // Check if Form input is valid
        let form = document.getElementById("createExperiment");
        event.preventDefault();

        if (!form.checkValidity()) {
            event.stopPropagation();
            $(this).addClass('was-validated');
        } else {
            // Collect the information and send them back
            let data = {}
            data["name"] = $('#experimentName').val();
            data["modal"] = $("#modalSelector").val();
            data["shared"] = $("#shareSelector").val();

            let settings = {
                "url": "/API/create-experiment", "method": "POST", "timeout": 0,
                "headers": {"Content-Type": "application/json"}, "data": JSON.stringify({data}),
            };

            $.ajax(settings).done(function () {
                $("#createExperimentModal").modal('hide');
                loadExperiments(template)
            });
        }
    });

    // Grabs the ID of the dataset that is opening the Modal and passes it to hte modal
    $("#createExperimentModal").on("show.bs.modal", function () {

        let settings = {"url": "/API/models-minified", "method": "GET", "timeout": 0,};
        let selector = $("#modalSelector");

        selector.empty()
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${key}">${response[key]}</option>`);
                console.log(key);
            }

            selector.trigger("chosen:updated");
            // Check the URL and select the dataset specified in it
            let searchParams = new URLSearchParams(window.location.search)
            if (searchParams.has('create') && searchParams.get('create')) {
                selector.val(searchParams.get('create')).trigger("change");
            }
            // Tell chosen to update
            selector.trigger("chosen:updated");


            settings = {"url": "/API/users", "method": "GET", "timeout": 0};
            $.ajax(settings).done(function (response) {
                // Clear the field before the new ones are added
                $("#shareSelector").empty();
                // Add an option for each of the users
                for (const key in response) {
                    $("#shareSelector").append(`<option value="${key}">${response[key]}</option>`);
                }
                $("#shareSelector").trigger("chosen:updated");
            });
        });
    }).on('hide.bs.modal', function () {
        let form = $("#createExperiment");
        form[0].reset();
        // Clear any Validation info
        form.removeClass("was-validated");
        $('#experimentName').val("")
        // Reset the share, first clear the values and then tell chosen to update
        $("#shareSelector").prop('selectedIndex', -1).trigger("chosen:updated");
    })

    // Adds the users to the select that the Experiment is already shared with
    $("#manageExperimentSharing").on("show.bs.modal", function (event) {
        // Grab the id and pass it forward
        $(this).data("experiment-id", $(event.relatedTarget).data("experiment-id"));
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        $(this).data("model-name", $(event.relatedTarget).data("model-name"));

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
            let eId = $(event.relatedTarget).data("experiment-id");
            let sId = $(event.relatedTarget).data("scenario-id");
            let sName = $(event.relatedTarget).data("scenario-name");
            let mName = $(event.relatedTarget).data("model-name");
            let settings = {
                "url": `/API/experiment-get-shared-users?eId=${eId}&sId=${sId}&sName=${sName}&mName=${mName}`,
                "method": "GET",
                "timeout": 0,
            };
            $.ajax(settings).done(function (response) {
                select.val(response);
                // Tell chosen to update
                select.trigger("chosen:updated");
            });
        });
    });

    // Gathers the the info from the select upon submit
    $("#manageExperimentSharingForm").on("submit", function (event) {
        let modal = $("#manageExperimentSharing")
        event.preventDefault();

        let val = $("#manageShareSelector").val().join()
        let id = modal.data("experiment-id");
        let eId = modal.data("experiment-id");
        let sId = modal.data("scenario-id");
        let sName = modal.data("scenario-name");
        let mName = modal.data("model-name");
        // Send the ids of the users to share with to the server
        let settings = {
            "url": `/API/update-experiment-sharing?eId=${eId}&sId=${sId}&sName=${sName}&mName=${mName}&users=${val}`,
            "method": "PUT",
            "timeout": 0,
        };

        $.ajax(settings).done(function () {
            modal.modal("hide");

            // FIXME: Check if reload here is needed
            loadExperiments(template);
        });
    });

    // Pass the ID to the Delete Modal
    $("#deleteExperimentModal").on("show.bs.modal", function (event) {
        $(this).data("experiment-id", $(event.relatedTarget).data("experiment-id"));
        $(this).data("scenario-id", $(event.relatedTarget).data("scenario-id"));
        $(this).data("scenario-name", $(event.relatedTarget).data("scenario-name"));
        $(this).data("model-name", $(event.relatedTarget).data("model-name"));
    });

    // Handle the delete Experiments
    $("#deleteExperiment").on("click", function (event) {
        let modal = $("#deleteExperimentModal");
        let eId = modal.data("experiment-id");
        let sId = modal.data("scenario-id");
        let sName = modal.data("scenario-name");
        let mName = modal.data("model-name");

        let settings = {
            "url": `/API/experiment?eId=${eId}&sId=${sId}&sName=${sName}&mName=${mName}`,
            "method": "DELETE",
            "timeout": 0,
        };

        $.ajax(settings).done(function (response) {
            $("#deleteExperimentModal").modal("hide");
            loadExperiments(template)
        });
    });

    // Grab the search and use it to fill in the search field
    let searchParams = new URLSearchParams(window.location.search)
    if (searchParams.has('create') && searchParams.get('create')) {
        $("#createExperimentModal").modal('show');
    }
    if (searchParams.has('search') && searchParams.get('search')) {
        $("#searchFieldInput").val(searchParams.get('search'));
    }
});
