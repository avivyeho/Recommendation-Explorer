let scenario_name;
let scenario_id;
let model_name;
let experiment_id;
let generalization = "";

/** Grab the user info from the server and render it */
function loadUsers(templateUser, templateUserName) {

    let settings = {
        "url": `/API/experiment-users?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
        "method": "GET",
        "timeout": 0
    };
    $.ajax(settings).done(function (response) {
        document.getElementById("userNameCollectionView").innerHTML = templateUserName(response);
        document.getElementById("userCollectionView").innerHTML = templateUser(response);

        // Choose which one to display

        if ($("#toggleMode").text() !== "Show Images") {

            let found = false;
            $("#userCollectionView").find(".imgRep").each(function () {
                $(this).removeClass("d-none");
                found = true;
            });
            if (found) {
                $("#userCollectionView").find(".textRep").each(function () {
                    $(this).addClass("d-none");
                });
            }
        } else {
            $("#userCollectionView").find(".imgRep").each(function () {
                $(this).addClass("d-none");
            });
            $("#userCollectionView").find(".textRep").each(function () {
                $(this).removeClass("d-none");
            });

        }
    });
}

function updateHeaders() {
    if(generalization !== ""){
        $("#addScenarioUser").removeClass("d-none");
    }
    let settings = {
        "url": `/API/experiment-name?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
        "method": "GET",
        "timeout": 0
    };
    $.ajax(settings).done(function (response) {
        $("#modelName").html(model_name);
        $("#experimentName").html(response);
    });
}

function loadCharts(){
    // Get the info from the server
    let settings = {
        "url": `/API/experiment-statistics?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
        "method": "GET",
        "timeout": 0
    };
    $.ajax(settings).done(function (response) {

        response.forEach((element, index) => {
            const data = {
                labels: element['datapoints'].map(function(tuple) {return tuple[0];}),
                datasets: [{
                    backgroundColor: 'rgb(63,96,233)',
                    borderColor: 'rgb(63,96,233)',
                    data: element['datapoints'].map(function(tuple) {return tuple[1];}),
                }]
            };
            let plugins = {
                    legend: {
                        display: false,
                    },
                    title: {
                        display: true,
                        text: element['graph_label']
                    }
                };

            if(element['graph_label'] === "Recall@K over History size" ){
                plugins = {
                    legend: {
                        display: false,
                    },
                    title: {
                        display: true,
                        text: element['graph_label']
                    },
                    tooltip: {
                    callbacks: {
                        title: function (a) {
                            return `${a[0].formattedValue}/${a[0].label}`
                        },
                        label: function(a){
                            return `UID: ${element['datapoints'][a.dataIndex][2]}`}
                        }
                    }
                };
            }
            const config = {type: element['type'], data, options: {
                plugins: plugins,
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: element['x_label']
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: element['y_label']
                        },
                        min: element['y_min'],
                        max: element['y_max'],
                    }
                }
            }};
            let m = ['chart-one', 'chart-two', 'chart-three', 'chart-four', 'chart-five'];
            let chart_one = new Chart(document.getElementById(m[index]).getContext("2d"), config);
        });
    });
}
// - MAIN
$(document).ready(function () {

    // To activate the chosen components
    $('.form-control-chosen').chosen();

    // Grab the search and use it to fill in the search field
    let searchParams = new URLSearchParams(window.location.search);
    if (searchParams.has('model-name') && searchParams.get('model-name')) {
        model_name = searchParams.get('model-name');
    }
    if (searchParams.has('scenario-name') && searchParams.get('scenario-name')) {
        scenario_name = searchParams.get('scenario-name');
    }
    if (searchParams.has('s-id') && searchParams.get('s-id')) {
        scenario_id = searchParams.get('s-id');
    }
    if (searchParams.has('experiment-id') && searchParams.get('experiment-id')) {
        experiment_id = searchParams.get('experiment-id');
    }
    if (searchParams.has('generalization') && searchParams.get('generalization')) {
        generalization = searchParams.get('generalization');
    }
    console.log(scenario_name, scenario_id, model_name, experiment_id, generalization);

    // Prevent <enter> from changing the URL
    $(document).keypress(function (event) {
        if (event.keyCode === 10 || event.keyCode === 13) {
            event.preventDefault();
            return false;
        }
    }).keydown(function (event) {
        if (event.keyCode === 10 || event.keyCode === 13) {
            event.preventDefault();
            return false;
        }
    });


    // Activate Handlebars
    let templateHTMLUser = document.getElementById("userCollectionTemplate").innerHTML;
    let templateUser = Handlebars.compile(templateHTMLUser);
    let templateHTMLUserName = document.getElementById("userNameCollectionTemplate").innerHTML;
    let templateUserName = Handlebars.compile(templateHTMLUserName);
    let templateHTMLItemMetadata = document.getElementById("itemMedataCollectionView").innerHTML;
    let templateItemMetadata = Handlebars.compile(templateHTMLItemMetadata);

    loadUsers(templateUser, templateUserName);
    updateHeaders();
    loadCharts();

    $("#userCollectionView").on("keyup", "#validationInSearchFieldInput", function () {
        let value = $(this).val().toLowerCase();
        let id = $(this).data("user-id")
        $(`.validationIn${id} .validationInRow`).filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    })

    $("#userCollectionView").on("keyup", "#historySearchFieldInput", function () {
        let value = $(this).val().toLowerCase();
        let id = $(this).data("user-id")
        $(`.history${id} .historyRow`).filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    }).on("click", ".copyUser", function (event) {
        let user_id = $(this).data("user-id");
        let settings = {
            "url": `/API/experiment-copy-user?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&user-id=${user_id}`,
            "method": "POST",
            "timeout": 0
        };
        $.ajax(settings).done(function (response) {
            loadUsers(templateUser, templateUserName);
        });
    }).on("click", ".deleteItem", function () {
        let user_id = $(this).data("user-id");
        let item_id = $(this).data("item-id");
        let timestamp = $(this).data("timestamp");

        let settings = {
            "url": `/API/experiment-item?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&user=${user_id}&item=${item_id}&time=${timestamp}`,
            "method": "DELETE",
            "timeout": 0
        };
        $.ajax(settings).done(function (response) {
            loadUsers(templateUser, templateUserName);
        });
    }).on("click", ".addRecommendation", function () {
        let settings = {
            "url": `/API/experiment-add-item?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&id=${$(this).data("user-id")}&item=${$(this).data("item-name")}&time=0`,
            "method": "POST",
            "timeout": 0,
        };
        $.ajax(settings).done(function (response) {
            loadUsers(templateUser, templateUserName);
        });
    });

    $("#createEmptyUser").on("click", function () {
        let settings = {
            "url": `/API/experiment-create-empty-user?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
            "method": "POST",
            "timeout": 0
        };
        $.ajax(settings).done(function (response) {
            loadUsers(templateUser, templateUserName);
        });
    });

    $(".createRandom").on("click", function (event) {
        let url = `/API/experiment-create-random-user?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`;
        if($(this).data("user") === "scenario"){
            url += `&generalization=${generalization}`
        }else{
            url += `&generalization=`
        }
        let settings = {
            "url": url,
            "method": "POST",
            "timeout": 0
        };
        $.ajax(settings).done(function (response) {
            loadUsers(templateUser, templateUserName);
        });
    });

    $("#addItemModal").on("show.bs.modal", function (event) {
        $(this).data("user-id", $(event.relatedTarget).data("user-id"));
        $(this).data("item-name", $(event.relatedTarget).data("item-name"));

        let settings = {
            "url": `/API/experiment-items?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
            "method": "GET",
            "timeout": 0,
        };
        let selector = $("#itemSelector");
        selector.empty()
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${key}">${response[key]}</option>`);
            }
            // Tell chosen to update
            if ($(event.relatedTarget).data("item-name")) {
                selector.val($(event.relatedTarget).data("item-name"));
            }
            selector.trigger("chosen:updated");
        });
    }).on("hide.bs.modal", function () {
        let time = $("#itemTimestamp").val("");
    })

    $("#submitAddItem").on("click", function (event) {
        let form = document.getElementById("addItem");
        event.preventDefault();

        if (!form.checkValidity()) {
            event.stopPropagation();
            $("#addItem").addClass('was-validated');
        } else {
            let time = $("#itemTimestamp").val();
            let item = $("#itemSelector").val();
            let id = $("#addItemModal").data("user-id");

            let settings = {
                "url": `/API/experiment-add-item?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&id=${id}&item=${item}&time=${time}`,
                "method": "POST",
                "timeout": 0,
            };
            $.ajax(settings).done(function (response) {
                $("#addItemModal").modal("hide");
                loadUsers(templateUser, templateUserName);
            });
        }
    });

    $("#deleteUserModal").on("show.bs.modal", function (event) {
        $(this).data("user-id", $(event.relatedTarget).data("user-id"));
    });

    $("#confirmDeleteUser").on("click", function () {
        let id = $("#deleteUserModal").data("user-id");
        let settings = {
            "url": `/API/experiment-user?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&id=${id}`,
            "method": "DELETE",
            "timeout": 0,
        };
        $.ajax(settings).done(function (response) {
            $("#deleteUserModal").modal("hide");
            loadUsers(templateUser, templateUserName);
        });
    });

    // Check if input is positive number
    $("#randomAmount").on("input", function () {
        if ($(this).val() && $(this).val() >= 0) {
            $(this)[0].setCustomValidity("");
        } else {
            $(this)[0].setCustomValidity("invalid");
        }
    });

    // Reset the Form
    $("#addUserWithRandomItemsModal").on("hide.bs.modal", function () {
        $("#randomAmount").val("");
    })

    // Handle the Form
    $("#submitCreateUserWithRI").on("click", function (event) {
        let form = document.getElementById("addUserWithRandomItems");
        event.preventDefault();
        if (!form.checkValidity()) {
            event.stopPropagation();
            $("#addUserWithRandomItems").addClass('was-validated');
        } else {
            let amount = $("#randomAmount").val();
            let settings = {
                "url": `/API/experiment-add-user-wri?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&amount=${amount}`,
                "method": "POST",
                "timeout": 0,
            };
            $.ajax(settings).done(function (response) {
                $("#addUserWithRandomItemsModal").modal("hide");
                loadUsers(templateUser, templateUserName);
            });
        }
    });

    // Cross validation
    $("#addUserWithIdModal").on("show.bs.modal", function (event) {
        $(this).data("user", $(event.relatedTarget).data("user"));

        let url = `/API/experiment-user-ids?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`
        if($(this).data("user") === "scenario"){
            url += `&generalization=${generalization}`
        }else{
            url += `&generalization=`
        }

        let settings = {
            "url": url,
            "method": "GET",
            "timeout": 0,
        };
        $("#addUserWithId").removeClass('was-validated');
        let selector = $("#idSelector");
        selector.empty()
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${response[key]}">${response[key]}</option>`);
            }
            selector.trigger("chosen:updated"); // Tell chosen to update
        });
    });

    $("#submitAddUserWithId").on("click", function (event) {
        event.preventDefault();
        let form = document.getElementById("addUserWithId");
        if (!form.checkValidity()) {
            event.stopPropagation();
            $("#addUserWithId").addClass('was-validated');
        } else {
            let id = $("#idSelector").val();

            let url = `/API/experiment-add-user-with-id?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&id=${id}`;
            if($("#addUserWithIdModal").data("user") === "scenario"){
                url += `&generalization=${generalization}`;
            }else{
                url += `&generalization=`;
            }

            let settings = {
                "url": url,
                "method": "POST",
                "timeout": 0,
            };
            $.ajax(settings).done(function (response) {
                $("#addUserWithIdModal").modal("hide");
                loadUsers(templateUser, templateUserName);
            });
        }
    });

    // Add all the items to the select
    $("#addUsersWithItemModal").on("show.bs.modal", function (event) {
        $(this).data("user", $(event.relatedTarget).data("user"));

        let settings = {
            "url": `/API/experiment-items?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}`,
            "method": "GET",
            "timeout": 0,
        };
        let selector = $("#itemSelectorAddUser");
        selector.empty()
        $("#userAmount").val("");
        $.ajax(settings).done(function (response) {
            selector.append(`<option></option>`);
            for (const key in response) {
                selector.append(`<option value="${key}">${response[key]}</option>`);
            }
            // Tell chosen to update
            selector.trigger("chosen:updated");
        });
    });

    // Handle the form
    $("#submitAddUserWithItem").on("click", function (event) {
        event.preventDefault();
        let form = document.getElementById("addUsersWithItem");
        if (!form.checkValidity()) {
            event.stopPropagation();
            $("#addUsersWithItem").addClass('was-validated');
        } else {
            let item = $("#itemSelectorAddUser").val();
            let amount = $("#userAmount").val();

            let url = `/API/experiment-add-users-with-item?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&item=${item}&amount=${amount}`;

            if($("#addUsersWithItemModal").data("user") === "scenario"){
                url += `&generalization=${generalization}`;
            }else{
                url += `&generalization=`;
            }

            let settings = {
                "url": url,
                "method": "POST",
                "timeout": 0,
            };
            $.ajax(settings).done(function (response) {
                $("#addUsersWithItemModal").modal("hide");
                loadUsers(templateUser, templateUserName);
            });
        }
    });


    $("#itemModal").on("show.bs.modal", function (event) {
        let item = $(event.relatedTarget).data("item-id")
        let settings = {
            "url": `/API/item-info?experiment-id=${experiment_id}&scenario-name=${scenario_name}&s-id=${scenario_id}&model-name=${model_name}&item=${item}`,
            "method": "GET",
            "timeout": 0
        };
        $.ajax(settings).done(function (response) {
            document.getElementById("itemMetadataCollection").innerHTML = templateItemMetadata(response);
        });
    });

    $("#itemModal").on("keyup", "#itemSearchFieldInput", function () {
        let value = $(this).val().toLowerCase();

        $(`.metadata .metadataRow`).filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $("#searchUsers").on("keyup", function () {
        let value = $(this).val().toLowerCase();

        $(`#userCollectionView .userRep`).filter(function () {
            $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
        });
    });

    $("#toggleMode").on("click", function () {
        if ($(this).text() === "Show Images") {

            let found = false;
            $("#userCollectionView").find(".imgRep").each(function () {
                $(this).removeClass("d-none");
                found = true;
            });
            if (found) {
                $(this).text("Show Text");
                $("#userCollectionView").find(".textRep").each(function () {
                    $(this).addClass("d-none");
                });
            }
        } else {
            $(this).text("Show Images");
            $("#userCollectionView").find(".imgRep").each(function () {
                $(this).addClass("d-none");
            });
            $("#userCollectionView").find(".textRep").each(function () {
                $(this).removeClass("d-none");
            });

        }
    });
});
