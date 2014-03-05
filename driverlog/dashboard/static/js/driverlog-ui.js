/*
 Copyright (c) 2014 Mirantis Inc.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

 http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
 implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 */

function format_test_result(value) {
    var tooltip = "";
    var result;
    if (typeof value == 'undefined') {
        result = "<span style='color: grey;'>n/a</span>";
    } else {
        if (value.success) {
            result = "<span style='color: green;'>&#x2714;</span>"
        } else {
            result = "<span style='color: red;'>&#x2718;</span>"
        }
        if (value.passed.length > 0) {
            tooltip += "Passed: " + value.passed.join(", ") + " ";
        }
        if (value.failed.length > 0) {
            tooltip += "Failed: " + value.failed.join(", ");
        }
    }

    return "<span title='" + tooltip + "'>" + result + "</span>";
}
function renderTable(table_id) {

    $(document).ready(function () {

        $.ajax({
            url: "/api/1.0/records",
            dataType: "json",
            success: function (data) {

                var matrix = {};
                var driver_map = {};
                var branch_map = {};


                for (var i in data["data"]) {
                    var record = data["data"][i];

                    var driver = record.driver;
                    var project = record.project;
                    var branch = record.branch;

                    if (!matrix[driver]) {
                        matrix[driver] = {};
                    }

                    if (typeof matrix[driver][branch] == 'undefined') {
                        matrix[driver][branch] = {
                            success: record.success,
                            passed: [],
                            failed: []
                        };
                    }
                    if (record.success) {
                        matrix[driver][branch].passed.push(record.endpoint);
                    } else {
                        matrix[driver][branch].failed.push(record.endpoint);
                        matrix[driver][branch].success = false;
                    }

                    driver_map[driver] = true;
                    branch_map[branch] = true;
                }

                var tableColumns = [{"mData": "driver", "sTitle": "Driver"}];
                for (branch in branch_map) {
                    tableColumns.push({"mData": branch,  "sTitle": branch});
                }

                var tableData = [];
                for (driver in driver_map) {
                    var row = {
                        'driver': make_link(driver, driver, 'driver')
                    };
                    for (branch in branch_map) {
                        row[branch] = format_test_result(matrix[driver][branch]);
                    }
                    tableData.push(row);
                }

                $("#" + table_id).dataTable({
                    "bPaginate": false,
//                    "aaSorting": [
//                        [ 0, "asc" ]
//                    ],
                    "aaData": tableData,
                    "aoColumns": tableColumns
                });
            }
        });
    });
}

function renderDriverTable(table_id) {

    $(document).ready(function () {

        $.ajax({
            url: "/api/1.0/records",
            dataType: "json",
            success: function (data) {

                var matrix = {};
                var endpoint_map = {};
                var branch_map = {};


                for (var i in data["data"]) {
                    var record = data["data"][i];

                    var endpoint = record.endpoint;
                    var project = record.project;
                    var branch = record.branch;

                    if (!matrix[endpoint]) {
                        matrix[endpoint] = {};
                    }

                    matrix[endpoint][branch] = record;
                    matrix[endpoint][branch].passed = record.passed_tests;
                    matrix[endpoint][branch].failed = record.failed_tests;
                    endpoint_map[endpoint] = true;
                    branch_map[branch] = true;
                }

                var tableColumns = [{"mData": "endpoint", "sTitle": "Endpoint"}];
                for (branch in branch_map) {
                    tableColumns.push({"mData": branch,  "sTitle": branch});
                }

                var tableData = [];
                for (endpoint in endpoint_map) {
                    var row = {
                        'endpoint': endpoint
                    };
                    for (branch in branch_map) {
                        row[branch] = format_test_result(matrix[endpoint][branch]);
                    }
                    tableData.push(row);
                }

                $("#" + table_id).dataTable({
                    "bPaginate": false,
//                    "aaSorting": [
//                        [ 0, "asc" ]
//                    ],
                    "aaData": tableData,
                    "aoColumns": tableColumns
                });
            }
        });
    });
}

function renderSummaryTable(table_id) {

    $(document).ready(function () {

        $.ajax({
            url: "/api/1.0/drivers",
            dataType: "json",
            success: function (data) {

                var tableColumns = [
                    {"mData": "project_name", "sTitle": "Project"},
                    {"mData": "vendor", "sTitle": "Vendor"},
                    {"mData": "name", "sTitle": "Driver Name"},
                    {"mData": "verification_name", "sTitle": "Verification"}
                ];
                var tableData = data["drivers"];
                for (var i in tableData) {
                    var driver = tableData[i];
                    driver["name"] = "<a href='details?driver=" + driver["id"] + "'>" + driver["name"] + "</a>";
                    driver["verification_name"]
                }

                $("#" + table_id).dataTable({
                    "bPaginate": false,
                    "aaData": tableData,
                    "aoColumns": tableColumns
                });
            }
        });
    });
}

function getUrlVars() {
    var vars = {};
    var parts = window.location.href.replace(/[?&]+([^=&]+)=([^&]*)/gi, function (m, key, value) {
        vars[key] = decodeURIComponent(value);
    });
    return vars;
}

function make_link(id, title, param_name) {
    var options = {};
    options[param_name] = encodeURIComponent(id).toLowerCase();
    var link = make_uri("/", options);
    return "<a href=\"" + link + "\">" + title + "</a>"
}

function make_uri(uri, options) {
    var ops = {};
    $.extend(ops, getUrlVars());
    if (options != null) {
        $.extend(ops, options);
    }
    var str = $.map(ops,function (val, index) {
        return index + "=" + encodeURIComponent(val).toLowerCase();
    }).join("&");

    return (str == "") ? uri : uri + "?" + str;
}

function make_std_options() {
    var options = {};
    options['project_id'] = $('#project_selector').val();
    options['vendor'] = $('#vendor_selector').val();
    options['level_id'] = $('#level_selector').val();
//    options['date'] = $('#date_selector').datepicker("getDate").getTime() / 1000;

    return options;
}

function reload() {
    var ops = {};
    $.extend(ops, getUrlVars());
    $.extend(ops, make_std_options());
    window.location.search = $.map(ops,function (val, index) {
        return index + "=" + encodeURIComponent(val);
    }).join("&")
}

function init_application(project_id, date) {
    $(function () {
        $(document).tooltip();
    });

    $(document).ready(function () {
        $("#project_selector").select2();
        $("#project_selector").select2("val", project_id);
        $("#project_selector").select2().on("change", function(e) {
            reload();
        });
    });

    $(function () {
        var datepicker = $("#date_selector");
        datepicker.datepicker({
            dateFormat: "dd M yy",
            maxDate: "0"
        });
        if (date) {
            datepicker.datepicker("setDate", new Date(parseInt(date) * 1000));
        } else {
            datepicker.datepicker("setDate", "0");
        }
        datepicker.on("change", function(e) {
            reload();
        })
    });
}
