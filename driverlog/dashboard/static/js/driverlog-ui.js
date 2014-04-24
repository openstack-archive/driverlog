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
//    options['level_id'] = $('#level_selector').val();
    options['release_id'] = $('#release_selector').val();

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

function init_selectors(base_url) {
    $(document).tooltip();

    var project_id = getUrlVars()["project_id"];

    $("#project_selector").val(project_id).select2({
        allowClear: true,
        placeholder: "Select Project",
        ajax: {
            url: make_uri(base_url + "/api/1.0/list/project_ids"),
            dataType: 'jsonp',
            data: function (term, page) {
                return {
                    query: term
                };
            },
            results: function (data, page) {
                return {results: data["project_ids"]};
            }
        },
        initSelection: function (element, callback) {
            var id = $(element).val();
            if (id !== "") {
                $.ajax(make_uri(base_url + "/api/1.0/list/project_ids/" + id), {
                    dataType: "jsonp"
                }).done(function (data) {
                        callback(data["project_id"]);
                    });
            }
        }
    });

    $('#project_selector')
        .on("change", function (e) {
            reload();
        });

    var vendor = getUrlVars()["vendor"];

    $("#vendor_selector").val(vendor).select2({
        allowClear: true,
        placeholder: "Select Vendor",
        ajax: {
            url: make_uri(base_url + "/api/1.0/list/vendors"),
            dataType: 'jsonp',
            data: function (term, page) {
                return {
                    query: term
                };
            },
            results: function (data, page) {
                return {results: data["vendors"]};
            }
        },
        initSelection: function (element, callback) {
            var id = $(element).val();
            if (id !== "") {
                $.ajax(make_uri(base_url + "/api/1.0/list/vendors/" + id), {
                    dataType: "jsonp"
                }).done(function (data) {
                        callback(data["vendor"]);
                    });
            }
        }
    });

    $('#vendor_selector')
        .on("change", function (e) {
            reload();
        });

    var release_id = getUrlVars()["release_id"];

    $("#release_selector").val(release_id).select2({
        allowClear: true,
        placeholder: "Select Release",
        ajax: {
            url: make_uri(base_url + "/api/1.0/list/releases"),
            dataType: 'jsonp',
            data: function (term, page) {
                return {
                    query: term
                };
            },
            results: function (data, page) {
                return {results: data["releases"]};
            }
        },
        initSelection: function (element, callback) {
            var id = $(element).val();
            if (id !== "") {
                $.ajax(make_uri(base_url + "/api/1.0/list/releases/" + id), {
                    dataType: "jsonp"
                }).done(function (data) {
                        callback(data["release"]);
                    });
            }
        }
    });

    $('#release_selector')
        .on("change", function (e) {
            reload();
        });

}

function show_summary(base_url) {
    var table_column_names = ["project_name", "vendor", "driver_info", "in_trunk", "ci_tested", "maintainer_info"];
    var table_id = "data_table";

    $.ajax({
        url: make_uri(base_url + "/api/1.0/drivers"),
        dataType: "jsonp",

        success: function (data) {
            var tableData = data["drivers"];

            var tableColumns = [];
            for (var i = 0; i < table_column_names.length; i++) {
                tableColumns.push({"mData": table_column_names[i]});
            }

            for (i = 0; i < tableData.length; i++) {
                if (tableData[i].wiki) {
                    tableData[i].driver_info = "<a href=\"" + tableData[i].wiki + "\" target=\"_blank\">" +
                            tableData[i].name + "</a>";
                } else {
                    tableData[i].driver_info = tableData[i].name;
                }
                tableData[i].driver_info = "<div>" + tableData[i].driver_info + "</div>";
                if (tableData[i].description) {
                    tableData[i].driver_info += "<div>" + tableData[i].description + "</div>";
                }

                tableData[i].in_trunk = "";
                for (var j = 0; j < tableData[i].releases_info.length; j++) {
                    tableData[i].in_trunk += "<a href=\"" + tableData[i].releases_info[j].wiki + "\" target=\"_blank\">" +
                            tableData[i].releases_info[j].name + "</a> ";
                }

                tableData[i].ci_tested = "";
                if (tableData[i].os_versions_map["master"]) {
                    var master = tableData[i].os_versions_map["master"];
                    if (master.review_url) {
                        tableData[i].ci_tested = "<a href=\"" + master.review_url +
                                "\" target=\"_blank\" title=\"Click for details\"><span style=\"color: #008000\">&#x2714;</span></a>";
                    } else {
                        tableData[i].ci_tested = "<span style=\"color: #808080\">&#x2714;</span>";
                    }
                } else {
                    tableData[i].ci_tested = "<span style=\"color: darkred\">&#x2716;</span>";
                }

                tableData[i].maintainer_info = "";
                if (tableData[i].maintainer) {
                    var mn = tableData[i].maintainer.name;
                    if (tableData[i].maintainer.email) {
                        tableData[i].maintainer_info = "<a href=\"mailto:" + tableData[i].maintainer.email + "\">" + mn + "</a>";
                    }
                    else if (tableData[i].maintainer.irc) {
                        tableData[i].maintainer_info = "<a href=\"irc:" + tableData[i].maintainer.irc + "\">" + mn + "</a>";
                    } else {
                        tableData[i].maintainer_info = mn;
                    }
                } else {
                    tableData[i].maintainer_info = "";
                }
            }

            if (table_id) {
                $("#" + table_id).dataTable({
                    "aLengthMenu": [
                        [10, 25, 50, -1],
                        [10, 25, 50, "All"]
                    ],
                    "aaSorting": [
                        [ 0, "asc" ],
                        [ 1, "asc"]
                    ],
                    "iDisplayLength": -1,
                    "bAutoWidth": false,
                    "aaData": tableData,
                    "aoColumns": tableColumns
                });
            }
        }
    });
}
